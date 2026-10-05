"""Profile autofill from pasted text or a PDF CV (AUTO-01..04). No Streamlit imports.

Autofill only produces a draft; nothing is saved until the user clicks Save on the form.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass
from typing import Any

from findings.ai.autofill_prompt import (
    AUTOFILL_SYSTEM,
    PDF_PROMPT,
    ProfileDraft,
    build_text_prompt,
)
from findings.ai.client import AIUnavailable, generate_structured
from findings.core.constants import CAREER_STAGES
from findings.services.profile_service import FORM_KEYS, mentoring_defaults, normalise_list

MAX_TEXT_CHARS = 20_000
MIN_TEXT_CHARS = 20
MAX_PDF_BYTES = 5 * 1024 * 1024
MAX_PDF_PAGES = 10

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_SHORT_FIELDS = ("full_name", "institution")
_LONG_FIELDS = ("education", "experience", "bio", "looking_for")


class AutofillError(Exception):
    """User-safe failure message; the form can still be filled manually."""


@dataclass
class PdfInfo:
    pages: int | None
    size: int


def _scrub(text: str | None, limit: int) -> str:
    if not text:
        return ""
    return _EMAIL_RE.sub("", str(text)).strip()[:limit]


def sanitize_draft(draft: ProfileDraft) -> dict[str, Any]:
    """Return a plain dict limited to known fields, with emails scrubbed and stage validated."""
    out: dict[str, Any] = {}
    out["full_name"] = _scrub(draft.full_name, 120)
    out["institution"] = _scrub(draft.institution, 300)
    for key in _LONG_FIELDS:
        out[key] = _scrub(getattr(draft, key), 2000)
    stage = (draft.career_stage or "").strip()
    out["career_stage"] = next((s for s in CAREER_STAGES if s.casefold() == stage.casefold()), None)
    out["interests"] = normalise_list([_scrub(i, 80) for i in draft.interests])[:8]
    out["skills"] = normalise_list([_scrub(i, 80) for i in draft.skills])[:10]
    return out


def merge_draft(
    current: dict[str, Any], draft: dict[str, Any], *, overwrite: bool = False
) -> dict[str, Any]:
    """Map a sanitized draft onto form widget keys.

    By default only empty form fields are filled so a user's own entries are never clobbered.
    Lists are merged without duplicates. A newly filled career stage also applies the
    mentoring toggle defaults, exactly as picking the stage by hand does.
    """
    updates: dict[str, Any] = {}

    def is_empty(value: Any) -> bool:
        return value in (None, "", [], ())

    for field in _SHORT_FIELDS + _LONG_FIELDS + ("career_stage",):
        new = draft.get(field)
        if is_empty(new):
            continue
        key = FORM_KEYS[field]
        if overwrite or is_empty(current.get(key)):
            updates[key] = new

    for field in ("interests", "skills"):
        new = draft.get(field) or []
        if not new:
            continue
        key = FORM_KEYS[field]
        existing = list(current.get(key) or [])
        merged = normalise_list(new if overwrite else existing + new)
        if merged != existing:
            updates[key] = merged

    stage_key = FORM_KEYS["career_stage"]
    if stage_key in updates:
        defaults = mentoring_defaults(updates[stage_key])
        if defaults is not None:
            updates[FORM_KEYS["seeking_mentor"]], updates[FORM_KEYS["open_to_mentoring"]] = defaults
    return updates


def autofill_from_text(text: str) -> dict[str, Any]:
    """Draft profile fields from pasted text. Raises AutofillError with a user-safe message."""
    text = (text or "").strip()
    if len(text) < MIN_TEXT_CHARS:
        raise AutofillError("Paste a little more text (at least a couple of sentences) to autofill.")
    try:
        draft = generate_structured(
            build_text_prompt(text[:MAX_TEXT_CHARS]), ProfileDraft, system=AUTOFILL_SYSTEM
        )
    except AIUnavailable:
        raise AutofillError(
            "Autofill is unavailable right now. You can fill in the form manually."
        ) from None
    return sanitize_draft(draft)  # type: ignore[arg-type]


def preflight_pdf(data: bytes) -> PdfInfo:
    """Cheap checks before spending a Gemini call. Raises AutofillError on a bad file."""
    size = len(data or b"")
    if size == 0:
        raise AutofillError("That file is empty.")
    if size > MAX_PDF_BYTES:
        raise AutofillError("That PDF is larger than 5 MB. Try a smaller file or paste the text instead.")
    if not data.lstrip()[:5].startswith(b"%PDF"):
        raise AutofillError("That does not look like a PDF file.")
    try:
        from pypdf import PdfReader
    except ImportError:
        return PdfInfo(pages=None, size=size)
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise AutofillError("That PDF is password protected. Remove the password or paste the text.")
        pages = len(reader.pages)
    except AutofillError:
        raise
    except Exception:
        raise AutofillError("Could not read that PDF. Try another file or paste the text.") from None
    if pages > MAX_PDF_PAGES:
        raise AutofillError(f"That PDF has {pages} pages; the limit is {MAX_PDF_PAGES}.")
    return PdfInfo(pages=pages, size=size)


def autofill_from_pdf(data: bytes) -> dict[str, Any]:
    """Draft profile fields from a CV PDF sent inline to Gemini. The file is never stored."""
    preflight_pdf(data)
    from google.genai import types

    part = types.Part.from_bytes(data=data, mime_type="application/pdf")
    try:
        draft = generate_structured(PDF_PROMPT, ProfileDraft, parts=[part], system=AUTOFILL_SYSTEM)
    except AIUnavailable:
        raise AutofillError(
            "Autofill is unavailable right now. You can fill in the form manually."
        ) from None
    return sanitize_draft(draft)  # type: ignore[arg-type]
