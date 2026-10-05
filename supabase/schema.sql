-- Findings: full first migration (Phase 1).
-- Apply in the Supabase SQL Editor (Dashboard -> SQL Editor -> New query -> paste -> Run).
-- Safe to re-run: every statement is idempotent.

-- 1. Extensions ---------------------------------------------------------------
create extension if not exists vector with schema extensions;

-- 2. profiles -----------------------------------------------------------------
-- id equals auth.uid() for real users and is random for synthetic ones, so there is
-- deliberately NO foreign key to auth.users. No email column here (see profile_contacts).
create table if not exists public.profiles (
  id uuid primary key default gen_random_uuid(),
  is_synthetic boolean not null default false,
  is_complete boolean not null default false,
  full_name text not null default '' check (char_length(full_name) <= 120),
  career_stage text check (career_stage in
    ('Undergrad', 'Master''s', 'PhD', 'Postdoc', 'Faculty', 'Industry researcher')),
  institution text check (char_length(institution) <= 2000),
  education text check (char_length(education) <= 2000),
  experience text check (char_length(experience) <= 2000),
  bio text check (char_length(bio) <= 2000),
  looking_for text check (char_length(looking_for) <= 2000),
  interests text[] not null default '{}',
  skills text[] not null default '{}',
  offers text[] not null default '{}',
  needs text[] not null default '{}',
  contributable_skills text[] not null default '{}',
  want_to_learn text[] not null default '{}',
  seeking_mentor boolean not null default false,
  open_to_mentoring boolean not null default false,
  methods_suggested text check (methods_suggested in ('qualitative', 'quantitative', 'mixed')),
  methods_override text check (methods_override in ('qualitative', 'quantitative', 'mixed')),
  methods_effective text generated always as (coalesce(methods_override, methods_suggested)) stored,
  stage_tier text generated always as (
    case
      when career_stage in ('Undergrad', 'Master''s', 'PhD') then 'junior'
      when career_stage in ('Postdoc', 'Faculty', 'Industry researcher') then 'senior'
    end
  ) stored,
  embedding extensions.vector(768),
  embedding_model text,
  embedding_hash text,
  embedded_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists profiles_methods_effective_idx on public.profiles (methods_effective);
create index if not exists profiles_career_stage_idx on public.profiles (career_stage);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists set_updated_at on public.profiles;
create trigger set_updated_at
  before update on public.profiles
  for each row execute function public.set_updated_at();

-- 3. profile_contacts (private email, zero policies) ---------------------------
create table if not exists public.profile_contacts (
  profile_id uuid primary key references public.profiles (id) on delete cascade,
  email text not null
);
alter table public.profile_contacts enable row level security;
revoke all on public.profile_contacts from anon, authenticated;

-- 4. Auth triggers + backfill ---------------------------------------------------
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.profiles (id) values (new.id) on conflict do nothing;
  insert into public.profile_contacts (profile_id, email) values (new.id, coalesce(new.email, ''))
    on conflict (profile_id) do update set email = excluded.email;
  return new;
end;
$$;

create or replace function public.handle_deleted_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  delete from public.profiles where id = old.id;
  return old;
end;
$$;

revoke execute on function public.handle_new_user() from public, anon, authenticated;
revoke execute on function public.handle_deleted_user() from public, anon, authenticated;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

drop trigger if exists on_auth_user_deleted on auth.users;
create trigger on_auth_user_deleted
  after delete on auth.users
  for each row execute function public.handle_deleted_user();

-- Backfill users created before this schema existed (Plan 01 tracer sign-ins).
insert into public.profiles (id)
  select id from auth.users
  on conflict do nothing;
insert into public.profile_contacts (profile_id, email)
  select id, coalesce(email, '') from auth.users
  on conflict (profile_id) do update set email = excluded.email;

-- 5. connections ----------------------------------------------------------------
create table if not exists public.connections (
  id uuid primary key default gen_random_uuid(),
  requester_id uuid not null references public.profiles (id) on delete cascade,
  recipient_id uuid not null references public.profiles (id) on delete cascade,
  note text check (char_length(note) <= 500),
  status text not null default 'pending' check (status in ('pending', 'accepted', 'declined')),
  created_at timestamptz default now(),
  responded_at timestamptz,
  check (requester_id <> recipient_id)
);

create unique index if not exists connections_pair_uniq
  on public.connections (least(requester_id, recipient_id), greatest(requester_id, recipient_id));
create index if not exists connections_recipient_status_idx
  on public.connections (recipient_id, status);
create index if not exists connections_requester_status_idx
  on public.connections (requester_id, status);

create or replace function public.guard_connection_update()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if old.status <> 'pending' then
    raise exception 'connection already answered';
  end if;
  if new.status not in ('accepted', 'declined') then
    raise exception 'status must become accepted or declined';
  end if;
  if new.requester_id <> old.requester_id
     or new.recipient_id <> old.recipient_id
     or new.note is distinct from old.note then
    raise exception 'only status may change';
  end if;
  new.responded_at = now();
  return new;
end;
$$;

drop trigger if exists guard_connection_update on public.connections;
create trigger guard_connection_update
  before update on public.connections
  for each row execute function public.guard_connection_update();

-- 6. match_cache -----------------------------------------------------------------
create table if not exists public.match_cache (
  user_id uuid not null references public.profiles (id) on delete cascade,
  mode text not null check (mode in ('peer', 'mentor')),
  profile_hash text not null,
  source text check (source in ('ai', 'embedding')),
  results jsonb not null default '[]',
  created_at timestamptz default now(),
  primary key (user_id, mode)
);

-- 7. keepalive --------------------------------------------------------------------
create table if not exists public.keepalive (
  id smallint primary key default 1 check (id = 1),
  note text not null default 'ok'
);
insert into public.keepalive (id, note) values (1, 'ok') on conflict do nothing;

-- 8. RLS, policies and grants ------------------------------------------------------
alter table public.profiles enable row level security;
alter table public.profile_contacts enable row level security;
alter table public.connections enable row level security;
alter table public.match_cache enable row level security;
alter table public.keepalive enable row level security;

-- profiles
revoke all on public.profiles from anon;
revoke delete on public.profiles from authenticated;

drop policy if exists profiles_select on public.profiles;
create policy profiles_select on public.profiles
  for select to authenticated
  using (is_complete or id = (select auth.uid()));

drop policy if exists profiles_insert on public.profiles;
create policy profiles_insert on public.profiles
  for insert to authenticated
  with check (id = (select auth.uid()) and is_synthetic = false);

drop policy if exists profiles_update on public.profiles;
create policy profiles_update on public.profiles
  for update to authenticated
  using (id = (select auth.uid()))
  with check (id = (select auth.uid()) and is_synthetic = false);

revoke update on public.profiles from authenticated;
grant update (
  full_name, career_stage, institution, education, experience, bio, looking_for,
  interests, skills, offers, needs, contributable_skills, want_to_learn,
  seeking_mentor, open_to_mentoring, methods_suggested, methods_override,
  embedding, embedding_model, embedding_hash, embedded_at, is_complete, updated_at
) on public.profiles to authenticated;

-- connections
revoke all on public.connections from anon;

drop policy if exists connections_select on public.connections;
create policy connections_select on public.connections
  for select to authenticated
  using ((select auth.uid()) in (requester_id, recipient_id));

drop policy if exists connections_insert on public.connections;
create policy connections_insert on public.connections
  for insert to authenticated
  with check (requester_id = (select auth.uid()) and status = 'pending');

drop policy if exists connections_update on public.connections;
create policy connections_update on public.connections
  for update to authenticated
  using (recipient_id = (select auth.uid()))
  with check (recipient_id = (select auth.uid()));

drop policy if exists connections_delete on public.connections;
create policy connections_delete on public.connections
  for delete to authenticated
  using (requester_id = (select auth.uid()) and status = 'pending');

revoke update on public.connections from authenticated;
grant update (status) on public.connections to authenticated;

-- match_cache
revoke all on public.match_cache from anon;

drop policy if exists match_cache_own on public.match_cache;
create policy match_cache_own on public.match_cache
  for all to authenticated
  using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));

-- keepalive
drop policy if exists keepalive_read on public.keepalive;
create policy keepalive_read on public.keepalive
  for select to anon, authenticated
  using (true);

revoke insert, update, delete on public.keepalive from anon, authenticated;
grant select on public.keepalive to anon, authenticated;

-- 9. get_contact_email RPC (the only door to profile_contacts) -----------------------
create or replace function public.get_contact_email(p_profile uuid)
returns text
language sql
stable
security definer
set search_path = ''
as $$
  select pc.email
  from public.profile_contacts pc
  where pc.profile_id = p_profile
    and (
      p_profile = auth.uid()
      or exists (
        select 1
        from public.connections c
        where c.status = 'accepted'
          and (
            (c.requester_id = auth.uid() and c.recipient_id = p_profile)
            or (c.recipient_id = auth.uid() and c.requester_id = p_profile)
          )
      )
    );
$$;

revoke execute on function public.get_contact_email(uuid) from public, anon;
grant execute on function public.get_contact_email(uuid) to authenticated;

-- 10. Phase 2: methods suggestion bookkeeping (additive, nullable). Must stay after section 8, which re-runs revoke update + grant update on profiles.
alter table public.profiles add column if not exists methods_hash text;
alter table public.profiles add column if not exists methods_reason text check (char_length(methods_reason) <= 300);
grant update (methods_hash, methods_reason) on public.profiles to authenticated;
notify pgrst, 'reload schema';

-- 11. Phase 4: AI Peer Matching - pgvector shortlist RPC ----------------------------
drop function if exists public.match_profiles(extensions.vector, integer, uuid[], text);
create or replace function public.match_profiles(
  query_embedding extensions.vector(768) default null,
  match_count int default 15,
  exclude_ids uuid[] default '{}',
  mode text default 'peer'
)
returns table (
  id uuid,
  full_name text,
  career_stage text,
  stage_tier text,
  methods_effective text,
  interests text[],
  skills text[],
  experience text,
  bio text,
  looking_for text,
  offers text[],
  needs text[],
  contributable_skills text[],
  want_to_learn text[],
  seeking_mentor boolean,
  open_to_mentoring boolean,
  is_synthetic boolean,
  similarity double precision
)
language sql
stable
security invoker
set search_path = public, extensions
as $$
  with caller_vec as (
    select coalesce(
      match_profiles.query_embedding,
      (select p.embedding from public.profiles p where p.id = (select auth.uid()))
    ) as vec
  )
  select
    p.id,
    p.full_name,
    p.career_stage,
    p.stage_tier,
    p.methods_effective,
    p.interests,
    p.skills,
    p.experience,
    p.bio,
    p.looking_for,
    p.offers,
    p.needs,
    p.contributable_skills,
    p.want_to_learn,
    p.seeking_mentor,
    p.open_to_mentoring,
    p.is_synthetic,
    (1 - (p.embedding <=> cv.vec)) as similarity
  from public.profiles p
  cross join caller_vec cv
  where match_profiles.mode = 'peer'
    and cv.vec is not null
    and p.id <> (select auth.uid())
    and p.is_complete
    and p.embedding is not null
    and not (p.id = any(coalesce(match_profiles.exclude_ids, '{}'::uuid[])))
    and not exists (
      select 1
      from public.connections c
      where (c.requester_id = (select auth.uid()) and c.recipient_id = p.id)
         or (c.recipient_id = (select auth.uid()) and c.requester_id = p.id)
    )
  order by p.embedding <=> cv.vec asc
  limit least(greatest(match_profiles.match_count, 1), 50);
$$;

revoke execute on function public.match_profiles(extensions.vector, integer, uuid[], text) from public, anon;
grant execute on function public.match_profiles(extensions.vector, integer, uuid[], text) to authenticated;

-- Phase 6 replaces this function in its own appended section with the same signature and columns.
notify pgrst, 'reload schema';

-- 10. Phase 5: connections (auto-accept, insert columns, my_connections) -------

-- (a) D-02: Column-level insert permissions (clients cannot insert status or timestamps)
revoke insert on public.connections from authenticated;
grant insert (requester_id, recipient_id, note) on public.connections to authenticated;

-- (b) D-01: Auto-accept trigger for synthetic profiles
create or replace function public.auto_accept_synthetic()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if exists (
    select 1
    from public.profiles
    where id = new.recipient_id
      and is_synthetic = true
  ) then
    update public.connections
    set status = 'accepted'
    where id = new.id
      and status = 'pending';
  end if;
  return null;
end;
$$;

revoke execute on function public.auto_accept_synthetic() from public, anon, authenticated;

drop trigger if exists auto_accept_synthetic on public.connections;
create trigger auto_accept_synthetic
  after insert on public.connections
  for each row execute function public.auto_accept_synthetic();

-- (c) D-03: my_connections security-definer RPC with gated email via get_contact_email
create or replace function public.my_connections()
returns table (
  connection_id uuid,
  direction text,
  status text,
  note text,
  created_at timestamptz,
  responded_at timestamptz,
  other_id uuid,
  other_name text,
  other_stage text,
  other_is_synthetic boolean,
  other_email text
)
language sql
stable
security definer
set search_path = ''
as $$
  select
    c.id as connection_id,
    case
      when c.requester_id = (select auth.uid()) then 'sent'
      else 'received'
    end as direction,
    c.status,
    c.note,
    c.created_at,
    c.responded_at,
    o.id as other_id,
    coalesce(nullif(o.full_name, ''), 'Unnamed researcher') as other_name,
    o.career_stage as other_stage,
    o.is_synthetic as other_is_synthetic,
    case
      when c.status = 'accepted' then public.get_contact_email(o.id)
      else null
    end as other_email
  from public.connections c
  join public.profiles o on o.id = (
    case
      when c.requester_id = (select auth.uid()) then c.recipient_id
      else c.requester_id
    end
  )
  where c.requester_id = (select auth.uid())
     or c.recipient_id = (select auth.uid())
  order by c.created_at desc;
$$;

revoke execute on function public.my_connections() from public, anon;
grant execute on function public.my_connections() to authenticated;

notify pgrst, 'reload schema';


