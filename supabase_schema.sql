create table if not exists public.profiles (
    user_id uuid primary key references auth.users (id) on delete cascade,
    display_name text not null default 'Scout'
);

create table if not exists public.troops (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    invite_code text not null unique default upper(substr(replace(gen_random_uuid()::text, '-', ''), 1, 10)),
    created_by uuid not null references auth.users (id) on delete restrict,
    created_at timestamptz not null default now()
);

create table if not exists public.memberships (
    troop_id uuid not null references public.troops (id) on delete cascade,
    user_id uuid not null references auth.users (id) on delete cascade,
    role text not null default 'membre' check (role in ('chef', 'assistant', 'membre')),
    joined_at timestamptz not null default now(),
    primary key (troop_id, user_id)
);

create table if not exists public.troop_data (
    troop_id uuid primary key references public.troops (id) on delete cascade,
    data jsonb not null default '{"parishes":[],"parish_data":{},"meetings":[]}'::jsonb,
    updated_at timestamptz not null default now()
);

create table if not exists public.meetings (
    id uuid primary key default gen_random_uuid(),
    troop_id uuid not null references public.troops (id) on delete cascade,
    title text not null,
    starts_at timestamptz not null,
    location text not null default '',
    notes text not null default '',
    created_by uuid not null default auth.uid() references auth.users (id) on delete restrict,
    created_at timestamptz not null default now()
);

create table if not exists public.meeting_attendance (
    meeting_id uuid not null references public.meetings (id) on delete cascade,
    user_id uuid not null references auth.users (id) on delete cascade,
    status text not null default 'pending' check (status in ('pending', 'present', 'absent')),
    updated_at timestamptz not null default now(),
    primary key (meeting_id, user_id)
);

create index if not exists memberships_user_id_idx on public.memberships (user_id);
create index if not exists meetings_troop_starts_idx on public.meetings (troop_id, starts_at);
create index if not exists attendance_user_id_idx on public.meeting_attendance (user_id);

create or replace function public.is_troop_member(target_troop uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
    select exists (
        select 1 from public.memberships
        where troop_id = target_troop and user_id = auth.uid()
    );
$$;

create or replace function public.is_troop_manager(target_troop uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
    select exists (
        select 1 from public.memberships
        where troop_id = target_troop
          and user_id = auth.uid()
          and role in ('chef', 'assistant')
    );
$$;

create or replace function public.shares_troop_with(target_user uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
    select exists (
        select 1
        from public.memberships own_membership
        join public.memberships other_membership
          on other_membership.troop_id = own_membership.troop_id
        where own_membership.user_id = auth.uid()
          and other_membership.user_id = target_user
    );
$$;

create or replace function public.create_troop(troop_name text)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
    new_troop_id uuid;
begin
    if auth.uid() is null then
        raise exception 'Authentification requise';
    end if;
    if length(trim(troop_name)) < 2 then
        raise exception 'Le nom de la troupe doit contenir au moins 2 caractères';
    end if;

    insert into public.troops (name, created_by)
    values (trim(troop_name), auth.uid())
    returning id into new_troop_id;

    insert into public.memberships (troop_id, user_id, role)
    values (new_troop_id, auth.uid(), 'chef');

    insert into public.troop_data (troop_id)
    values (new_troop_id);

    return new_troop_id;
end;
$$;

create or replace function public.join_troop(invite_code_input text)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
    selected_troop_id uuid;
begin
    if auth.uid() is null then
        raise exception 'Authentification requise';
    end if;

    select id into selected_troop_id
    from public.troops
    where invite_code = upper(trim(invite_code_input));

    if selected_troop_id is null then
        raise exception 'Code d’invitation invalide';
    end if;

    insert into public.memberships (troop_id, user_id, role)
    values (selected_troop_id, auth.uid(), 'membre')
    on conflict (troop_id, user_id) do nothing;

    return selected_troop_id;
end;
$$;

create or replace function public.get_troop_invite_code(target_troop uuid)
returns text
language plpgsql
stable
security definer
set search_path = public
as $$
declare
    code text;
begin
    if not exists (
        select 1 from public.memberships
        where troop_id = target_troop and user_id = auth.uid() and role = 'chef'
    ) then
        raise exception 'Seul le chef peut consulter le code d’invitation';
    end if;

    select invite_code into code from public.troops where id = target_troop;
    return code;
end;
$$;

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
    insert into public.profiles (user_id, display_name)
    values (
        new.id,
        coalesce(nullif(trim(new.raw_user_meta_data ->> 'display_name'), ''), split_part(new.email, '@', 1), 'Scout')
    );
    return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users
for each row execute procedure public.handle_new_user();

alter table public.profiles enable row level security;
alter table public.troops enable row level security;
alter table public.memberships enable row level security;
alter table public.troop_data enable row level security;
alter table public.meetings enable row level security;
alter table public.meeting_attendance enable row level security;

drop policy if exists "Profiles visible to troop members" on public.profiles;
create policy "Profiles visible to troop members"
on public.profiles for select to authenticated
using (user_id = auth.uid() or public.shares_troop_with(user_id));

drop policy if exists "Users update their own profile" on public.profiles;
create policy "Users update their own profile"
on public.profiles for update to authenticated
using (user_id = auth.uid()) with check (user_id = auth.uid());

drop policy if exists "Troop members can read their troops" on public.troops;
create policy "Troop members can read their troops"
on public.troops for select to authenticated
using (public.is_troop_member(id));

drop policy if exists "Members can read troop memberships" on public.memberships;
create policy "Members can read troop memberships"
on public.memberships for select to authenticated
using (public.is_troop_member(troop_id));

drop policy if exists "Members can read troop data" on public.troop_data;
create policy "Members can read troop data"
on public.troop_data for select to authenticated
using (public.is_troop_member(troop_id));

drop policy if exists "Managers create troop data" on public.troop_data;
create policy "Managers create troop data"
on public.troop_data for insert to authenticated
with check (public.is_troop_manager(troop_id));

drop policy if exists "Managers update troop data" on public.troop_data;
create policy "Managers update troop data"
on public.troop_data for update to authenticated
using (public.is_troop_manager(troop_id))
with check (public.is_troop_manager(troop_id));

drop policy if exists "Troop members can read meetings" on public.meetings;
create policy "Troop members can read meetings"
on public.meetings for select to authenticated
using (public.is_troop_member(troop_id));

drop policy if exists "Managers create meetings" on public.meetings;
create policy "Managers create meetings"
on public.meetings for insert to authenticated
with check (public.is_troop_manager(troop_id) and created_by = auth.uid());

drop policy if exists "Managers delete meetings" on public.meetings;
create policy "Managers delete meetings"
on public.meetings for delete to authenticated
using (public.is_troop_manager(troop_id));

drop policy if exists "Members read attendance for their troop" on public.meeting_attendance;
create policy "Members read attendance for their troop"
on public.meeting_attendance for select to authenticated
using (
    user_id = auth.uid()
    or exists (
        select 1 from public.meetings
        where meetings.id = meeting_attendance.meeting_id
          and public.is_troop_manager(meetings.troop_id)
    )
);

drop policy if exists "Members respond to their own attendance" on public.meeting_attendance;
create policy "Members respond to their own attendance"
on public.meeting_attendance for insert to authenticated
with check (
    user_id = auth.uid()
    and exists (
        select 1 from public.meetings
        where meetings.id = meeting_attendance.meeting_id
          and public.is_troop_member(meetings.troop_id)
    )
);

drop policy if exists "Members update their own attendance" on public.meeting_attendance;
create policy "Members update their own attendance"
on public.meeting_attendance for update to authenticated
using (user_id = auth.uid())
with check (
    user_id = auth.uid()
    and exists (
        select 1 from public.meetings
        where meetings.id = meeting_attendance.meeting_id
          and public.is_troop_member(meetings.troop_id)
    )
);

grant usage on schema public to authenticated;
grant select, update on public.profiles to authenticated;
grant select on public.memberships to authenticated;
grant select, insert, update on public.troop_data to authenticated;
grant select, insert, delete on public.meetings to authenticated;
grant select, insert, update on public.meeting_attendance to authenticated;
revoke all on function public.is_troop_member(uuid) from public, anon;
revoke all on function public.is_troop_manager(uuid) from public, anon;
revoke all on function public.shares_troop_with(uuid) from public, anon;
revoke all on function public.create_troop(text) from public, anon;
revoke all on function public.join_troop(text) from public, anon;
revoke all on function public.get_troop_invite_code(uuid) from public, anon;
revoke all on function public.handle_new_user() from public, anon;
revoke all on public.troops from authenticated;
grant select (id, name, created_at) on public.troops to authenticated;
grant execute on function public.is_troop_member(uuid) to authenticated;
grant execute on function public.is_troop_manager(uuid) to authenticated;
grant execute on function public.shares_troop_with(uuid) to authenticated;
grant execute on function public.create_troop(text) to authenticated;
grant execute on function public.join_troop(text) to authenticated;
grant execute on function public.get_troop_invite_code(uuid) to authenticated;
