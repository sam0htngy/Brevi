import hashlib
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from storage3.exceptions import StorageApiError

with patch.dict(os.environ, {
    "SUPABASE_URL": "http://127.0.0.1:54321",
    "SUPABASE_SERVICE_ROLE_KEY": "test-key",
}):
    import main
    import worker

ASSET_ID = "00000000-0000-4000-8000-000000000001"


class UploadTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)
        main.app.dependency_overrides[main.get_current_user] = lambda: {"sub": "owner"}
        self.addCleanup(main.app.dependency_overrides.clear)

    def test_oversize_request_is_rejected_before_accessing_supabase(self):
        with patch.object(main, "supabase") as db:
            response = self.client.post("/projects/uploads", json={
                "attempt_id": ASSET_ID, "title": "Video", "filename": "video.mp4",
                "mime_type": "video/mp4", "byte_size": 25 * 1024 * 1024 + 1,
                "sha256": hashlib.sha256(b"video").hexdigest(),
            })
        self.assertEqual(response.status_code, 413)
        self.assertEqual(db.mock_calls, [])

    def test_resume_finalizes_bytes_already_in_storage(self):
        content = b"video"
        digest = hashlib.sha256(content).hexdigest()
        db = Mock()
        db.rpc.return_value.execute.return_value.data = {
            "id": ASSET_ID, "project_id": "project", "status": "pending_upload",
            "bucket_id": "video-originals", "object_path": "source.mp4",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "byte_size": len(content), "sha256": digest,
        }
        bucket = db.storage.from_.return_value
        bucket.info.return_value = {"size": len(content)}
        bucket.download.return_value = content
        with patch.object(main, "supabase", db), patch.object(
            main, "transition", return_value={"status": "ready"}
        ):
            response = self.client.post("/projects/uploads", json={
                "attempt_id": ASSET_ID, "title": "Video", "filename": "video.mp4",
                "mime_type": "video/mp4", "byte_size": len(content), "sha256": digest,
            })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "ready")
        self.assertNotIn("upload_token", response.json())

    def test_missing_object_can_start_a_resumable_upload(self):
        bucket = Mock()
        bucket.info.side_effect = StorageApiError("Missing", "Not Found", "404")
        with patch.object(main.supabase.storage, "from_", return_value=bucket):
            self.assertFalse(main.verify_upload({"bucket_id": "video-originals", "object_path": "missing"}))


class WorkerTests(unittest.TestCase):
    def test_existing_export_is_published_after_restart_without_rendering_again(self):
        db = Mock()
        query = db.table.return_value.select.return_value.eq.return_value.is_.return_value
        query.or_.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {"id": ASSET_ID, "project_id": "project"}
        ]
        deadline = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
        job = {"id": ASSET_ID, "object_path": "edited.mp4", "bucket_id": "video-exports",
               "render_deadline": deadline, "render_attempts": 2}
        db.storage.from_.return_value.info.return_value = {"size": 42}
        published = {}

        def transition(_db, project, action, **fields):
            if action == "claim":
                return job
            if action == "publish":
                published[project] = (fields["asset"], fields["bytes"])
                return {"status": "ready"}
            self.fail(f"Unexpected transition: {action}")

        with patch.object(worker, "supabase", db), patch.object(worker, "transition", transition):
            self.assertTrue(worker.process_next_job())
        self.assertEqual(published, {"project": (ASSET_ID, 42)})
        db.storage.from_.return_value.upload.assert_not_called()
