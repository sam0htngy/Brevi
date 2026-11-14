alter table public.projects
  add column if not exists created_at timestamptz not null default now(),
  add column upload_attempt_id uuid,
  add column upload_request jsonb,
  add column deleting_at timestamptz,
  add column cleanup_after timestamptz,
  add column cleanup_started_at timestamptz,
  add column cleaned_at timestamptz;

create unique index projects_upload_attempt_idx
  on public.projects (user_id, upload_attempt_id);
create index projects_library_idx on public.projects (user_id, created_at desc);

alter table public.video_assets
  add column sha256 text,
  add column render_attempts integer not null default 0,
  add column render_deadline timestamptz,
  add column retryable boolean not null default false;

update storage.buckets set file_size_limit = 26214400,
  allowed_mime_types = array['video/mp4']
where id = 'video-originals';

-- Retain completed legacy Originals and recover their unfinished initial renders.
insert into public.video_assets
  (id, project_id, owner_id, bucket_id, object_path, asset_type, status,
   source_asset_id, original_filename, mime_type, byte_size)
select output.id, original.project_id, original.owner_id, 'video-exports',
       original.project_id || '/' || output.id || '/edited.mp4', 'export',
       case when original.status = 'failed' then 'failed' else 'queued' end,
       original.id, 'edited.mp4', 'video/mp4', original.byte_size
from public.video_assets original
cross join lateral (select gen_random_uuid() as id where original.id is not null) output
where original.asset_type = 'original' and original.status in ('queued', 'processing', 'failed')
  and not exists (select 1 from public.video_assets existing where existing.source_asset_id = original.id);

update public.video_assets set status = 'ready'
where asset_type = 'original' and status in ('queued', 'processing', 'failed');

create index video_exports_queue_idx on public.video_assets (status, created_at)
  where asset_type = 'export' and status in ('queued', 'processing');

create function public.reserve_video_upload(owner text, attempt uuid, inputs jsonb)
returns jsonb language plpgsql set search_path = '' as $$
declare
  project public.projects;
  asset public.video_assets;
begin
  insert into public.projects (user_id, title, upload_attempt_id, upload_request)
  values (owner, inputs->>'title', attempt, inputs)
  on conflict (user_id, upload_attempt_id) do nothing;

  select * into strict project from public.projects
  where user_id = owner and upload_attempt_id = attempt for update;
  if project.upload_request is distinct from inputs then
    return jsonb_build_object('result', 'conflict');
  end if;
  if project.deleting_at is not null then
    return jsonb_build_object('result', 'unavailable');
  end if;

  select * into asset from public.video_assets
  where project_id = project.id and asset_type = 'original';
  if not found then
    asset.id := gen_random_uuid();
    insert into public.video_assets
      (id, project_id, owner_id, bucket_id, object_path, asset_type, status,
       original_filename, mime_type, byte_size, sha256)
    values (asset.id, project.id, owner, 'video-originals',
      project.id || '/' || asset.id || '/source.mp4', 'original', 'pending_upload',
      'source.mp4', 'video/mp4', (inputs->>'byte_size')::bigint, inputs->>'sha256')
    returning * into asset;
  end if;
  return to_jsonb(asset);
end;
$$;

-- Serialize state changes for the same Project. Storage calls happen outside
-- the transaction, so record each authorization or render deadline first.
create function public.transition_video(project uuid, action text, asset uuid default null,
    actor text default null, deadline timestamptz default null, bytes bigint default null,
    failure text default null, transient boolean default false)
returns jsonb language plpgsql set search_path = '' as $$
declare
  p public.projects;
  a public.video_assets;
  output_id uuid;
begin
  select * into p from public.projects
  where id = project and (actor is null or user_id = actor) for update;
  if not found then return null; end if;

  if action = 'delete' then
    update public.projects set deleting_at = coalesce(deleting_at, now()),
      cleanup_after = greatest(cleanup_after, now())
    where id = p.id;
    return jsonb_build_object('status', 'deleting');
  end if;

  select * into a from public.video_assets where id = asset and project_id = p.id;
  if not found or p.deleting_at is not null then return null; end if;

  if action = 'authorize' and a.status = 'pending_upload' and a.asset_type = 'original'
      and a.created_at > now() - interval '24 hours' then
    -- A signed token can create a TUS session near the end of its two-hour
    -- lifetime. Allow another 24 hours for that session and a one-hour margin.
    update public.projects set cleanup_after = greatest(cleanup_after, now() + interval '27 hours') where id = p.id;
    return to_jsonb(a);
  elsif action = 'complete' and a.asset_type = 'original' then
    if a.status = 'pending_upload' and a.created_at > now() - interval '24 hours' then
      update public.video_assets set status = 'ready', uploaded_at = now() where id = a.id returning * into a;
      output_id := gen_random_uuid();
      insert into public.video_assets
        (id, project_id, owner_id, bucket_id, object_path, asset_type, status,
         source_asset_id, original_filename, mime_type, byte_size)
      values (output_id, p.id, p.user_id, 'video-exports', p.id || '/' || output_id || '/edited.mp4',
        'export', 'queued', a.id, 'edited.mp4', 'video/mp4', a.byte_size);
    end if;
    return to_jsonb(a);
  elsif action = 'expire' and a.asset_type = 'original' and a.status = 'pending_upload'
      and a.created_at <= now() - interval '24 hours' then
    update public.video_assets set status = 'deleted', deleted_at = now() where id = a.id returning * into a;
    return to_jsonb(a);
  elsif a.asset_type = 'export' then
    if action = 'claim' and a.status in ('queued', 'processing')
        and (a.status = 'queued' or a.render_deadline <= now()) then
      update public.video_assets set status = 'processing',
        render_deadline = now() + interval '5 minutes',
        render_attempts = render_attempts + 1
      where id = a.id returning * into a;
      update public.projects set cleanup_after = greatest(cleanup_after, a.render_deadline) where id = p.id;
      return to_jsonb(a);
    elsif action = 'write' and a.status = 'processing' and a.render_deadline = deadline
        and a.render_deadline > now() then
      return to_jsonb(a);
    elsif action in ('publish', 'fail') and a.status = 'processing'
        and a.render_deadline = deadline
        and (action = 'fail' or a.render_deadline > now()) then
      update public.video_assets set
        status = case when action = 'publish' then 'ready'
          when transient and a.render_attempts < 2 then 'queued' else 'failed' end,
        byte_size = coalesce(bytes, byte_size),
        completed_at = case when action = 'publish' then now() end,
        error_message = failure, retryable = transient, render_deadline = null
      where id = a.id returning * into a;
      return to_jsonb(a);
    elsif action = 'retry' and a.status = 'failed' and a.retryable then
      update public.video_assets set status = 'queued', render_attempts = 0, error_message = null
      where id = a.id returning * into a;
      return to_jsonb(a);
    end if;
  end if;
  return null;
end;
$$;

grant select, insert, update, delete on public.projects, public.video_assets to service_role;

revoke execute on function public.reserve_video_upload(text, uuid, jsonb) from public, anon, authenticated;
revoke execute on function public.transition_video(uuid, text, uuid, text, timestamptz, bigint, text, boolean)
  from public, anon, authenticated;
grant execute on function public.reserve_video_upload(text, uuid, jsonb) to service_role;
grant execute on function public.transition_video(uuid, text, uuid, text, timestamptz, bigint, text, boolean)
  to service_role;
