---
status: complete
phase: 01-foundation-sign-in
source: [01-VERIFICATION.md]
started: 2026-10-05T03:24:36Z
updated: 2026-10-05T03:59:40Z
---

## Current Test

[testing complete]

## Tests

### 1. Deployed app runs on Python 3.12
expected: Sidebar caption shows Python 3.12.x (if not, delete the app and redeploy with 3.12 in Advanced settings)
result: pass

### 2. New account sign-up lands on Home
expected: Create account tab with a fresh email + password signs in straight away and shows "Welcome to Findings"
result: pass

### 3. Demo account signs in
expected: The demo email + password on the Sign in tab lands on Home with "Profile record found"
result: pass

### 4. Stays signed in after F5
expected: Pressing F5 while signed in keeps the user on Home (findings_rt cookie present); if not, apply the SameSite=Lax fallback in findings/core/cookies.py, else record AUTH-04 as a limitation
result: pass

### 5. Sign out from any page
expected: Sidebar Sign out works from Home and from Account, and F5 afterwards stays signed out
result: pass

### 6. Two-browser isolation
expected: Two accounts signed in at once in two browsers each show only their own email and id, also after F5
result: pass

### 7. No secret keys in Cloud or GitHub secrets
expected: Streamlit Cloud and GitHub secrets hold only SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY (no sb_secret_ key, no demo password)
result: pass

## Summary

total: 7
passed: 7
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
