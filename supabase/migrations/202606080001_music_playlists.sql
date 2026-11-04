create table if not exists public.playlists (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    name text not null check (char_length(btrim(name)) between 1 and 80),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

do $$
declare
    playlist_id_type text;
    playlist_owner_type text;
begin
    select data_type into playlist_id_type
    from information_schema.columns
    where table_schema = 'public'
      and table_name = 'playlists'
      and column_name = 'id';
    select data_type into playlist_owner_type
    from information_schema.columns
    where table_schema = 'public'
      and table_name = 'playlists'
      and column_name = 'user_id';

    if playlist_id_type is distinct from 'uuid'
       or playlist_owner_type is distinct from 'uuid' then
        raise exception
            'Prism playlists require public.playlists.id and user_id to be UUID columns.';
    end if;
end
$$;

alter table public.playlists
    add column if not exists updated_at timestamptz not null default now();

create unique index if not exists playlists_id_user_id_uidx
    on public.playlists (id, user_id);

create table if not exists public.playlist_tracks (
    id uuid primary key default gen_random_uuid(),
    playlist_id uuid not null,
    user_id uuid not null references auth.users(id) on delete cascade,
    track_key text not null check (char_length(btrim(track_key)) > 0),
    track_data jsonb not null
        check (coalesce(track_data ->> 'source', '') = 'jamendo'),
    position integer not null check (position >= 0),
    created_at timestamptz not null default now(),
    constraint playlist_tracks_owner_fk
        foreign key (playlist_id, user_id)
        references public.playlists (id, user_id)
        on delete cascade,
    constraint playlist_tracks_unique_track
        unique (playlist_id, track_key),
    constraint playlist_tracks_key_matches_data
        check (track_key = track_data ->> 'jamendo_id')
);

create index if not exists playlist_tracks_owner_order_idx
    on public.playlist_tracks (user_id, playlist_id, position);

alter table public.playlists enable row level security;
alter table public.playlist_tracks enable row level security;

drop policy if exists "Prism users manage their own playlists"
    on public.playlists;
drop policy if exists "Prism restrict playlist access to owner"
    on public.playlists;
drop policy if exists "Prism users manage their own playlist tracks"
    on public.playlist_tracks;
drop policy if exists "Prism restrict playlist track access to owner"
    on public.playlist_tracks;

create policy "Prism users manage their own playlists"
    on public.playlists
    for all
    to authenticated
    using ((select auth.uid()) = user_id)
    with check ((select auth.uid()) = user_id);

create policy "Prism restrict playlist access to owner"
    on public.playlists
    as restrictive
    for all
    to authenticated
    using ((select auth.uid()) = user_id)
    with check ((select auth.uid()) = user_id);

create policy "Prism users manage their own playlist tracks"
    on public.playlist_tracks
    for all
    to authenticated
    using ((select auth.uid()) = user_id)
    with check ((select auth.uid()) = user_id);

create policy "Prism restrict playlist track access to owner"
    on public.playlist_tracks
    as restrictive
    for all
    to authenticated
    using ((select auth.uid()) = user_id)
    with check ((select auth.uid()) = user_id);

revoke all on public.playlists from anon;
revoke all on public.playlist_tracks from anon;
grant select, insert, update, delete on public.playlists to authenticated;
grant select, insert, update, delete on public.playlist_tracks to authenticated;
