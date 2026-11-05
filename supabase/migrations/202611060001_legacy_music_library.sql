create table if not exists public.songs (
    id uuid primary key default gen_random_uuid(),
    title text not null,
    artist text not null,
    album text,
    duration integer not null default 0 check (duration >= 0),
    audio_url text not null,
    created_at timestamptz not null default now()
);

do $$
declare
    missing_columns text[];
    song_id_type text;
begin
    select array_agg(required.column_name)
    into missing_columns
    from (values
        ('id'),
        ('title'),
        ('artist'),
        ('album'),
        ('duration'),
        ('audio_url'),
        ('created_at')
    ) as required(column_name)
    where not exists (
        select 1
        from information_schema.columns column_info
        where column_info.table_schema = 'public'
          and column_info.table_name = 'songs'
          and column_info.column_name = required.column_name
    );

    select data_type into song_id_type
    from information_schema.columns
    where table_schema = 'public'
      and table_name = 'songs'
      and column_name = 'id';

    if missing_columns is not null then
        raise exception
            'Prism legacy music requires public.songs columns: %.',
            array_to_string(missing_columns, ', ');
    end if;
    if song_id_type is distinct from 'uuid' then
        raise exception 'Prism legacy music requires public.songs.id to be UUID.';
    end if;
end
$$;

create table if not exists public.liked_songs (
    user_id uuid not null references auth.users(id) on delete cascade,
    song_id uuid not null references public.songs(id) on delete cascade,
    created_at timestamptz not null default now(),
    primary key (user_id, song_id)
);

alter table public.songs enable row level security;
alter table public.liked_songs enable row level security;

drop policy if exists "Prism authenticated users read songs"
    on public.songs;
create policy "Prism authenticated users read songs"
    on public.songs
    for select
    to authenticated
    using (true);

drop policy if exists "Prism users manage their own liked songs"
    on public.liked_songs;
create policy "Prism users manage their own liked songs"
    on public.liked_songs
    for all
    to authenticated
    using ((select auth.uid()) = user_id)
    with check ((select auth.uid()) = user_id);

revoke all on public.songs from anon;
revoke all on public.liked_songs from anon;
grant select on public.songs to authenticated;
grant select, insert, delete on public.liked_songs to authenticated;
