-- Run with `supabase db push` (or paste into the Supabase SQL editor).
-- Storage objects are private by default. The application service-role key is
-- the only credential that creates signed URLs or accesses either bucket.

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values
  ('video-originals', 'video-originals', false, 5368709120,
    array['video/mp4', 'video/quicktime', 'video/webm', 'video/x-matroska']),
  ('video-exports', 'video-exports', false, 5368709120,
    array['video/mp4', 'video/webm'])
on conflict (id) do update
set public = excluded.public,
    file_size_limit = excluded.file_size_limit,
    allowed_mime_types = excluded.allowed_mime_types;

create table if not exists public.video_assets (
  id uuid primary key,
  project_id uuid not null references public.projects(id) on delete cascade,
  owner_id text not null,
  bucket_id text not null check (bucket_id in ('video-originals', 'video-exports')),
  object_path text not null unique,
  asset_type text not null check (asset_type in ('original', 'export')),
  status text not null check (status in ('pending_upload', 'queued', 'processing', 'ready', 'failed', 'deleted')),
  source_asset_id uuid references public.video_assets(id),
  original_filename text not null,
  mime_type text not null,
  byte_size bigint not null check (byte_size > 0),
  error_message text,
  created_at timestamptz not null default now(),
  uploaded_at timestamptz,
  completed_at timestamptz,
  deleted_at timestamptz
);

create index if not exists video_assets_owner_project_idx
  on public.video_assets (owner_id, project_id, created_at desc);
create index if not exists video_assets_queue_idx
  on public.video_assets (status, created_at)
  where asset_type = 'original' and status = 'queued';

-- Clerk identities are verified by FastAPI, which uses the server-only service
-- role. Block direct anon/authenticated database access even if other policies
-- are added later.
alter table public.projects enable row level security;
alter table public.video_assets enable row level security;
drop policy if exists video_assets_server_only on public.video_assets;
create policy video_assets_server_only on public.video_assets
  as restrictive for all to anon, authenticated
  using (false) with check (false);
drop policy if exists projects_server_only on public.projects;
create policy projects_server_only on public.projects
  as restrictive for all to anon, authenticated
  using (false) with check (false);

-- A broad storage policy elsewhere in the project must not grant direct
-- client access to these two private buckets. Service-role requests bypass RLS.
drop policy if exists video_buckets_server_only on storage.objects;
create policy video_buckets_server_only on storage.objects
  as restrictive for all to anon, authenticated
  using (bucket_id not in ('video-originals', 'video-exports'))
  with check (bucket_id not in ('video-originals', 'video-exports'));
