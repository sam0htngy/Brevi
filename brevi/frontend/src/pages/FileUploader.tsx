import { useAuth } from "@clerk/clerk-react";
import * as tus from "tus-js-client";
import { useState, type ChangeEvent } from "react";

type UploadStatus = "idle" | "uploading" | "success" | "error";
const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL;
type UploadReservation = { asset_id: string; object_path: string; bucket_id: string; upload_token: string };

export default function FileUploader() {
  const { getToken } = useAuth();
  const [file, setFile] = useState<File | null>(null), [title, setTitle] = useState(""), [status, setStatus] = useState<UploadStatus>("idle"), [progress, setProgress] = useState(0), [error, setError] = useState("");
  function handleFileChange(event: ChangeEvent<HTMLInputElement>) { setFile(event.target.files?.[0] ?? null); setStatus("idle"); }
  async function api(path: string, options: RequestInit = {}) {
    const token = await getToken();
    const response = await fetch(`${API_URL}${path}`, { ...options, headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json", ...options.headers } });
    if (!response.ok) throw new Error((await response.json().catch(() => null))?.detail ?? "Request failed");
    return response.status === 204 ? null : response.json();
  }
  async function handleFileUpload() {
    if (!file || !title.trim() || !SUPABASE_URL) return;
    setStatus("uploading"); setProgress(0); setError("");
    try {
      const reservation = await api("/projects/uploads", { method: "POST", body: JSON.stringify({ title: title.trim(), filename: file.name, mime_type: file.type, byte_size: file.size }) }) as UploadReservation;
      const endpoint = `${SUPABASE_URL.replace(/\/$/, "").replace(".supabase.co", ".storage.supabase.co")}/storage/v1/upload/resumable`;
      await new Promise<void>((resolve, reject) => {
        const upload = new tus.Upload(file, { endpoint, retryDelays: [0, 3000, 5000, 10000, 20000], uploadDataDuringCreation: true, removeFingerprintOnSuccess: true, chunkSize: 6 * 1024 * 1024, headers: { "x-signature": reservation.upload_token, "x-upsert": "false" }, metadata: { bucketName: reservation.bucket_id, objectName: reservation.object_path, contentType: file.type }, onProgress: (sent, total) => setProgress(Math.round((sent / total) * 100)), onError: reject, onSuccess: () => resolve() });
        upload.findPreviousUploads().then((previous) => { if (previous[0]) upload.resumeFromPreviousUpload(previous[0]); upload.start(); }).catch(reject);
      });
      await api(`/video-assets/${reservation.asset_id}/complete`, { method: "POST" }); setStatus("success");
    } catch { setError("Upload failed. Please try again."); setStatus("error"); }
  }
  return <main className="flex min-h-screen items-center justify-center bg-gray-100"><section className="w-96 rounded bg-white p-6 shadow"><h1 className="mb-4 text-xl font-semibold">Upload a video</h1><input className="mb-3 w-full" value={title} placeholder="Project title" onChange={(event) => setTitle(event.target.value)} /><input className="mb-3 w-full" type="file" accept="video/mp4,video/quicktime,video/webm,video/x-matroska" onChange={handleFileChange} /><button disabled={!file || !title.trim() || status === "uploading"} onClick={handleFileUpload}>Upload</button>{status === "uploading" && <p className="mt-3">Uploading: {progress}%</p>}{status === "success" && <p className="mt-3">Upload complete. Your edit is queued.</p>}{status === "error" && <p className="mt-3 text-red-700">{error}</p>}</section></main>;
}
