# Brevi video library spec

## First milestone

A signed-in user can upload a video, refresh the page, find it in their library, and play its private MP4 export. Prove the full workflow with one small MP4 in a development Supabase project before adding editing features.

## Data and storage

- `projects` groups videos under a project title and Clerk owner ID.
- `video_assets` is the catalog for both original and export files. It tracks the project, owner, bucket, object path, processing status, and file metadata. Each export references its original through `source_asset_id`.
- `video-originals` holds uploaded source files. `video-exports` holds rendered clips. Both buckets are private.
- FastAPI verifies the Clerk session and checks ownership before returning records or issuing signed URLs. Keep the Supabase service-role key on the server. The browser uploads with a signed token and plays ready exports through short-lived signed URLs.

## Implementation order

1. **Make the schema reproducible.** Add a baseline migration for `public.projects` that runs before the [existing storage migration](../brevi/supabase/migrations/20260930_video_storage.sql). The existing migration already defines `video_assets`, the two buckets, and access policies. Verify the migration sequence on a fresh development database.
2. **Verify upload and storage.** Use the [existing upload endpoints](../brevi/api/main.py) and the browser's resumable upload flow. Confirm the MP4 lands in `video-originals`, its catalog row has the expected owner and object path, and completion moves it from `pending_upload` to `queued`. Verify that a second Clerk account cannot access the first account's asset.
3. **Add library reads.** Implement authenticated `GET /projects` and `GET /projects/{project_id}`. Scope results to the verified Clerk user and return asset IDs and statuses so the frontend can show progress and find the ready export after refresh. Request a signed playback URL through the existing endpoint when the user opens the export.
4. **Verify a single render.** Use the [FFmpeg worker](../brevi/api/worker.py) to transcode the source, write the MP4 to `video-exports`, and create a linked `ready` asset row. The worker currently deletes the source after a successful export. Retain originals during this milestone so users can retry processing or generate another clip. Confirm the export appears after refresh and plays for its owner.

## Deferred

AI highlight selection, transcription, captions, a browser editor, and multi-worker infrastructure. The first export only needs to prove the upload, storage, catalog, and playback workflow.
