# Brevi video library spec

## First milestone

A signed-in user can upload a video, refresh the page, find it in their library, and play its private MP4 export. The first Export is a full-length transcode of the Original to MP4. Prove the workflow with one small MP4 and two Clerk accounts against a fresh development Supabase project. See the [glossary](../GLOSSARY.md) for domain terms.

## Data and storage

- `projects` records the title and Clerk owner ID. Each Project has one Original and can have zero or more Exports. Uploading a different Original starts a new Project.
- `video_assets` is the catalog for both original and export files. It tracks the project, owner, bucket, object path, processing status, and file metadata. Each export references its original through `source_asset_id`.
- `video-originals` holds uploaded source files. `video-exports` holds generated Exports. Both buckets are private. Keep completed Originals until their owner deletes the Project. Expire abandoned uploads and remove the Original and all Exports when the owner deletes the Project.
- FastAPI verifies the Clerk session and checks ownership before returning records or issuing signed URLs. Keep the Supabase service-role key on the server. The browser uploads with a signed token and plays ready exports through short-lived signed URLs.

## Implementation order

1. **Make the schema reproducible.** Add a baseline migration for `public.projects` that runs before the [existing storage migration](../brevi/supabase/migrations/20260930_video_storage.sql). The existing migration already defines `video_assets`, the two buckets, and access policies. Verify the migration sequence on a fresh development database.
2. **Verify upload and storage.** Use the [existing upload endpoints](../brevi/api/main.py) and the browser's resumable upload flow. Confirm the MP4 lands in `video-originals`, its catalog row has the expected owner and object path, and completion makes the Original available and queues the initial render. Verify that a second Clerk account cannot access the first account's asset.
3. **Add library reads.** Implement authenticated `GET /projects` and `GET /projects/{project_id}`. Scope results to the verified Clerk user and return asset IDs and statuses so the frontend can show progress and find the ready export after refresh. Request a signed playback URL through the existing endpoint when the user opens the export.
4. **Verify a single render.** Use the [FFmpeg worker](../brevi/api/worker.py) to transcode the source, write the MP4 to `video-exports`, and create a linked `ready` asset row. The worker currently deletes the source after a successful export. Change the worker to retain the Original and record a successful processing outcome. This keeps the source available for retries and future Exports. Confirm the export appears after refresh and plays for its owner.

## Failure and recovery

- **Upload retries.** The browser reuses the same attempt ID when retrying an upload reservation. Scope the attempt ID to the verified Clerk owner. An identical request returns the existing reservation for the same Project and Original. Reusing the ID with different reservation inputs returns HTTP 409. An intentional new upload gets a new attempt ID. Repeated completion requests return the current status without queuing another render.
- **Original availability.** A verified Original remains available until Project deletion. Track the render outcome separately. A render can be queued, processing, failed, or ready. If a render fails, the library still shows the Project and its Original.
- **Worker recovery.** Run one worker and give the initial render a stable identity and a processing deadline. If the worker stops after writing the MP4 but before publishing it, restarting the worker must converge on exactly one playable Export. Include this interruption in the milestone test.
- **Project deletion.** Record deletion before removing files. Immediately hide the Project and stop issuing new playback URLs. A render finishing during deletion cannot publish an Export. Cleanup runs asynchronously and is safe to retry. Keep the deletion record until in-flight renders and previously authorized uploads have finished or can no longer write. Recheck both buckets before marking cleanup complete. Test by deleting a Project during a render and checking that it disappears from the library and leaves no files in either bucket.

## User recovery and development limits

- **Interrupted upload.** Show incomplete uploads after refresh. Let the owner reselect the same file to resume a valid reservation or discard the Project. Record the SHA-256 digest when reserving the upload and require the same digest when the owner reselects the file. Use a 24-hour abandonment window and wait until outstanding upload authorization can no longer write before removing abandoned files. On resume, check whether Storage already has a complete object. If it passes upload validation, finalize the existing Original and queue the initial render once. The abandonment window applies to attempts that remain incomplete or unconfirmed. Show expired uploads as expired and let the owner start a new upload.
- **Render failure.** Allow one automatic retry for an interrupted render or transient Storage failure, with a five-minute deadline per attempt. After that, offer **Retry render** on the same Project using its retained Original and the same Export identity. For invalid or unsupported files, explain the failure and prompt the owner to start a Project with a different Original.
- **Previously issued playback URLs.** Keep signed URLs short-lived. A URL issued before deletion may still work while the object exists and the URL is valid. Begin cleanup immediately and verify that the old URL can no longer serve the object after cleanup completes.
- **Supported input.** The development milestone accepts small MP4s only. Enforce a maximum of 25 MiB (26,214,400 bytes) in the browser, API, and originals bucket.

## Development setup

1. Apply the SQL files in [migration order](../brevi/supabase/migrations/) to a fresh development Supabase project. For an existing database, check that its `projects` table has a UUID primary key with a default and the `title` and `user_id` columns before applying the library migration.
2. Set `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and `CLERK_DOMAIN` in `brevi/.env`. Set `CORS_ORIGINS` to the frontend origin if it differs from `http://localhost:5173`.
3. Install the root `requirements.txt` in a Python virtual environment. With FFmpeg on your PATH, run `python -m uvicorn main:app --reload` and `python worker.py` in separate terminals from `brevi/api`.
4. In `brevi/frontend/.env.local`, set `VITE_CLERK_PUBLISHABLE_KEY`, `VITE_SUPABASE_URL`, and optionally `VITE_API_URL` (defaults to `http://localhost:8000`). Run `bun run dev` from `brevi/frontend` and open `/upload`.

From the repository root, run `PYTHONPATH=brevi/api python -m unittest discover -s brevi/api/tests` for the API and worker tests. Run `bun test` and `bun run build` from `brevi/frontend`.

## Milestone acceptance

Apply the migrations to a fresh development Supabase project and verify the following with two Clerk accounts.

- Upload an approximately 20 MiB MP4 across multiple chunks, resume it after a browser refresh, then open the Project from the library and play its full-length private Export. Confirm the Original remains available. Verify that a file one byte over the cap is rejected.
- Replay identical reservation and completion requests. Also resume after Storage accepts the final chunk and the browser closes before confirming completion. Verify that the attempt creates exactly one Project, one Original, and one initial Export. Reuse the same attempt ID with different inputs and verify HTTP 409.
- Stop the worker after it writes the MP4 but before it publishes the Export. Restart it and verify that the Project shows exactly one playable Export.
- Exercise deletion during a render and during an authorized upload. Verify that it disappears from the library immediately, no new playback URL is issued, and cleanup removes all of its files from both buckets. Check that any previously issued playback URL fails after cleanup.
- Verify that the second account cannot list or open the owner's Project, obtain an asset playback URL, or delete the Project.

## Deferred

AI highlight selection, transcription, captions, a browser editor, and multi-worker infrastructure. The first export only needs to prove the upload, storage, catalog, and playback workflow.
