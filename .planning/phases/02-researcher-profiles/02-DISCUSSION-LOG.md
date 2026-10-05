# Phase 2: Researcher Profiles - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-05
**Phase:** 02-researcher-profiles
**Areas discussed:** Form layout & list input, Methods badge behaviour, First-run & view/edit flow

---

## Form layout & list input

| Option | Description | Selected |
|--------|-------------|----------|
| One page, sections | Single scrolling form, headed sections, one Save | ✓ |
| Tabs | st.tabs About / Research / Mentoring | |
| Multi-step wizard | Step 1/2/3 with Next | |

| Option | Description | Selected |
|--------|-------------|----------|
| Suggestions + free entry | st.multiselect with presets + accept_new_options | ✓ |
| Comma-separated text | Split on commas | |
| Preset lists only | Fixed choices | |

| Option | Description | Selected |
|--------|-------------|----------|
| Driven by toggles | Mentor toggle shows offer/need; seeking toggle shows contribute/learn | ✓ |
| Always show all four | All optional, always visible | |

| Option | Description | Selected |
|--------|-------------|----------|
| Interests only | No new column | ✓ |
| Add a 'field' dropdown | New column + migration | |

---

## Methods badge behaviour

| Option | Description | Selected |
|--------|-------------|----------|
| On save, only if text changed | Hash-gated Gemini call | ✓ |
| On every save | Always call | |
| Separate 'Suggest' button | User-triggered | |

| Option | Description | Selected |
|--------|-------------|----------|
| Auto + 3 choices | Segmented control; Auto clears override | ✓ |
| Pre-filled dropdown | Picking a value locks it | |

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, one line | Show a short AI reason | ✓ |
| No, label only | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Save + notice, retry next save | Hash not updated on failure | ✓ |
| Save + keyword heuristic | Local fallback guess | |

---

## First-run & view/edit flow

| Option | Description | Selected |
|--------|-------------|----------|
| Home nudges to profile | CTA, no forced redirect | ✓ |
| Force redirect | Profile page only until saved | |

| Option | Description | Selected |
|--------|-------------|----------|
| Name, stage, 1+ interest | Minimal completeness bar | ✓ |
| Name, stage, interests, bio | | |
| All core fields | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Read-only view + Edit button | Reusable view for Phase 3 | ✓ |
| Always the form | | |

---

## Claude's Discretion

- Mentoring toggle re-default behaviour on stage change (area not selected for discussion)
- Preset suggestion lists, copy, badge styling, module names, hash field set

## Deferred Ideas

None.
