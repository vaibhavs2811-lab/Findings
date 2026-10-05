# API Coverage — Supabase (Auth + Data API) and GitHub Actions, Phase 1

> Full coverage by default. Opt-outs are explicit, reasoned decisions.
> Brevo is reached only through Supabase custom SMTP (dashboard config, no direct API calls). Streamlit is the app framework, not an external API.

| capability | decision | reason |
|---|---|---|
| supabase.auth.sign_in_with_otp | INTEGRATE | |
| supabase.auth.verify_otp | INTEGRATE | |
| supabase.auth.sign_in_with_password | INTEGRATE | |
| supabase.auth.refresh_session | INTEGRATE | |
| supabase.auth.get_session | INTEGRATE | |
| supabase.auth.sign_out | INTEGRATE | |
| supabase.auth.settings (GET /auth/v1/settings) | INTEGRATE | |
| supabase.auth.get_user | OPT-OUT | not needed: verify/refresh responses and get_session already carry the user identity |
| supabase.auth.set_session | OPT-OUT | not needed: restore uses refresh_session with the refresh token alone; no access token is persisted |
| supabase.auth.sign_up (password) | OPT-OUT | explicitly out of scope: accounts are created only by OTP (AUTH-02); the demo user is created in the dashboard |
| supabase.auth.resend | OPT-OUT | not needed: re-calling sign_in_with_otp after the 60 s cooldown resends for both new and returning users |
| supabase.auth.magic_link / exchange_code_for_session | OPT-OUT | explicitly out of scope: Streamlit cannot read URL-fragment tokens (REQUIREMENTS Out of Scope) |
| supabase.auth.sign_in_with_oauth | OPT-OUT | explicitly out of scope: email OTP is the only end-user sign-in method |
| supabase.auth.sign_in_with_sso | OPT-OUT | explicitly out of scope: no institutional SSO for a course project |
| supabase.auth.sign_in_with_id_token | OPT-OUT | explicitly out of scope: no third-party identity providers |
| supabase.auth.sign_in_anonymously | OPT-OUT | explicitly out of scope: every user needs an email identity for contact unlock |
| supabase.auth.reset_password_for_email / update_user(password) | OPT-OUT | not needed: app is passwordless; the demo password is managed in the dashboard |
| supabase.auth.update_user (email change, metadata) | OPT-OUT | not needed yet: profile data lives in public.profiles (Phase 2) |
| supabase.auth.mfa.* | OPT-OUT | explicitly out of scope for the course demo |
| supabase.auth.admin.* | OPT-OUT | requires the secret key, which never enters the app; later seed scripts use it locally only |
| supabase.auth.on_auth_state_change | OPT-OUT | not needed: Streamlit reruns read session state on every run |
| supabase.auth.link_identity / unlink_identity / get_user_identities | OPT-OUT | not needed: one email identity per user |
| supabase.auth.reauthenticate | OPT-OUT | not needed: no sensitive account changes in the app |
| supabase.postgrest.select | INTEGRATE | |
| supabase.postgrest.update | INTEGRATE | |
| supabase.postgrest.rpc | INTEGRATE | |
| supabase.postgrest.insert / upsert | OPT-OUT | not needed yet: profile writes arrive in Phase 2, connection inserts in Phase 5; signup rows are created by the database trigger |
| supabase.postgrest.delete | OPT-OUT | not needed yet: deletion only via auth-user cascade in Phase 1 |
| supabase.realtime | OPT-OUT | not needed: no live updates in the product |
| supabase.storage | OPT-OUT | explicitly out of scope: CVs go straight to Gemini and are never stored |
| supabase.functions (Edge Functions) | OPT-OUT | not needed: all server rules live in Postgres (RLS, triggers, RPCs) |
| github.actions.schedule | INTEGRATE | |
| github.actions.workflow_dispatch | INTEGRATE | |
| github.actions.repository_secrets | INTEGRATE | |
| github.rest.list_workflow_runs | INTEGRATE | |
