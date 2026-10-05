"""Autofill panel for the My profile edit form (AUTO-01..04)."""

from __future__ import annotations

import streamlit as st

from findings.services import autofill


def _apply(draft: dict, *, overwrite: bool) -> None:
    current = {k: v for k, v in st.session_state.items() if k.startswith("f_")}
    updates = autofill.merge_draft(current, draft, overwrite=overwrite)
    for key, value in updates.items():
        st.session_state[key] = value
    st.session_state["autofill_flash"] = (
        f"Filled {len(updates)} field(s). Review everything below, then click Save."
        if updates
        else "Nothing new to fill in. Your form already has those details."
    )


def _on_text() -> None:
    try:
        with st.spinner("Reading your text..."):
            draft = autofill.autofill_from_text(st.session_state.get("autofill_text", ""))
        _apply(draft, overwrite=bool(st.session_state.get("autofill_overwrite")))
    except autofill.AutofillError as err:
        st.session_state["autofill_error"] = str(err)


def _uploader_key() -> str:
    return f"autofill_pdf_{st.session_state.get('autofill_pdf_nonce', 0)}"


def _on_pdf() -> None:
    upload = st.session_state.get(_uploader_key())
    if upload is None:
        return
    data = upload.getvalue()
    try:
        info = autofill.preflight_pdf(data)
        with st.spinner("Reading your CV..."):
            draft = autofill.autofill_from_pdf(data)
        _apply(draft, overwrite=bool(st.session_state.get("autofill_overwrite")))
        if info.has_text is False:
            st.session_state["autofill_flash"] += (
                " This PDF looks scanned (no text layer), so results may be limited."
            )
    except autofill.AutofillError as err:
        st.session_state["autofill_error"] = str(err)
    finally:
        # Drop the uploaded file from the page: a new nonce gives a fresh, empty uploader.
        st.session_state["autofill_pdf_nonce"] = st.session_state.get("autofill_pdf_nonce", 0) + 1


def render_autofill_panel() -> None:
    """Expander with paste-text and PDF autofill. Only fills the form; never saves."""
    if "autofill_flash" in st.session_state:
        st.success(st.session_state.pop("autofill_flash"))
    if "autofill_error" in st.session_state:
        st.warning(st.session_state.pop("autofill_error"))

    with st.expander("Autofill from your bio or CV (optional)", icon=":material/auto_awesome:"):
        st.caption(
            "Paste a bio, CV text or a LinkedIn/Scholar 'about', or upload a PDF CV. "
            "Gemini drafts the form; you review and edit before saving. "
            "Text is sent to Google's Gemini API and PDFs are not stored by Findings. "
            "Scanned PDFs without text may give limited results."
        )
        st.checkbox(
            "Overwrite fields I have already filled",
            key="autofill_overwrite",
            help="Off by default: only empty fields are filled.",
        )
        tab_text, tab_pdf = st.tabs(["Paste text", "Upload PDF"])
        with tab_text:
            st.text_area("Bio or CV text", key="autofill_text", height=160, max_chars=20000)
            st.button("Autofill from text", key="autofill_text_btn", on_click=_on_text)
        with tab_pdf:
            st.file_uploader("CV (PDF, up to 5 MB, 10 pages)", type=["pdf"], key=_uploader_key())
            st.button("Autofill from PDF", key="autofill_pdf_btn", on_click=_on_pdf)
