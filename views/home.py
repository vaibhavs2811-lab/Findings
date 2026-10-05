import streamlit as st

from findings.core import session
from findings.repos.profiles import get_own_profile
from findings.services import connection_service
from ui.components import (
    avatar_html,
    completeness,
    esc,
    meter_html,
    pill_html,
    section_header,
)

user = session.current_user() or {}
sb = st.session_state["sb"]

try:
    profile = get_own_profile(sb, user.get("id", ""))
except Exception:
    st.title("Welcome to Findings")
    st.write(f"Signed in as {user.get('email', '')}")
    st.warning("Could not load your profile record. Try again in a moment.")
    st.stop()

complete = bool(profile and profile.get("is_complete"))
name = (profile or {}).get("full_name") or ""
pct, missing = completeness(profile)

# ---------- Hero ----------
with st.container(key="fxhero-home"):
    left, right = st.columns([3, 1], vertical_alignment="center")
    with left:
        st.html('<span class="fx-eyebrow">Your research network</span>')
        st.title("Welcome to Findings")
        st.write(f"Signed in as {user.get('email', '')}")
        st.caption("Findings matches researchers who want to collaborate, and pairs juniors with mentors.")
    with right:
        if name:
            st.html(
                '<div style="display:flex;flex-direction:column;align-items:center;gap:.5rem">'
                + avatar_html(name, 84)
                + f'<div class="fx-sub" style="text-align:center">{esc(name)}</div></div>'
            )

if not complete:
    with st.container(key="fxpanel-onboard"):
        st.html('<div class="fx-tile-title">Step 1: build your profile</div>')
        st.info(
            "Your profile is not complete yet. Add your name, career stage and at least "
            "one research interest so other researchers can find you."
        )
        st.html(meter_html(pct))
        st.caption(f"{pct}% complete" + (f" · still to add: {', '.join(missing[:3])}" if missing else ""))
        st.page_link("views/profile.py", label="Complete your profile", icon=":material/badge:")
    section_header("How Findings works")
    st.html(
        '<div class="fx-steps">'
        '<div class="fx-step"><div class="n">1</div><div class="fx-tile-title">Build your profile</div>'
        '<div class="fx-sub">Tell us your interests, methods and what you want from a collaboration.</div></div>'
        '<div class="fx-step"><div class="n">2</div><div class="fx-tile-title">Get matched</div>'
        '<div class="fx-sub">AI ranks researchers and mentors for you and explains each match.</div></div>'
        '<div class="fx-step"><div class="n">3</div><div class="fx-tile-title">Connect</div>'
        '<div class="fx-sub">Send a request. When it is accepted, you both see each other\'s email.</div></div>'
        "</div>"
    )
    st.stop()

# ---------- Complete profile: dashboard ----------
pending = accepted = 0
try:
    conns = connection_service.list_connections(sb, user["id"])
    pending, accepted = len(conns["received"]), len(conns["accepted"])
except Exception:
    pass

st.success("Your profile is complete.")

stats = st.columns(4)
methods = (profile or {}).get("methods_effective")
tiles = [
    (f"{pct}%", "Profile strength"),
    (str(pending), "Requests waiting"),
    (str(accepted), "Connections"),
    ((methods or "not set").title(), "Methods"),
]
for col, (value, label) in zip(stats, tiles, strict=True):
    with col.container(key=f"fxtile-stat-{label.split()[0].lower()}"):
        st.html(f'<div class="fx-stat"><div class="v">{esc(value)}</div><div class="l">{esc(label)}</div></div>')

section_header("Jump back in")
c1, c2, c3 = st.columns(3)
with c1.container(key="fxtile-act-matches"):
    st.html('<div class="fx-tile-icon">🤝</div><div class="fx-tile-title">My Matches</div>')
    st.caption("AI-ranked collaborators and mentors, with a reason for each.")
    st.page_link("views/matches.py", label="See my matches", icon=":material/arrow_forward:")
with c2.container(key="fxtile-act-discover"):
    st.html('<div class="fx-tile-icon">🔭</div><div class="fx-tile-title">Discover</div>')
    st.caption("Browse, filter and search researchers across fields.")
    st.page_link("views/discover.py", label="Browse researchers", icon=":material/arrow_forward:")
with c3.container(key="fxtile-act-connections"):
    st.html('<div class="fx-tile-icon">💬</div><div class="fx-tile-title">Connections</div>')
    st.caption(f"{pending} request(s) waiting for you." if pending else "Requests you sent and received.")
    st.page_link("views/connections.py", label="Open connections", icon=":material/arrow_forward:")

mentor_bits = []
if (profile or {}).get("seeking_mentor"):
    mentor_bits.append(pill_html("Seeking a mentor", "cyan"))
if (profile or {}).get("open_to_mentoring"):
    mentor_bits.append(pill_html("Open to mentoring", "pink"))
if mentor_bits:
    st.html('<div class="fx-pills" style="margin-top:1rem">' + "".join(mentor_bits) + "</div>")

st.page_link("views/profile.py", label="View my profile", icon=":material/badge:")
