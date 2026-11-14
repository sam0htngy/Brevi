import { Link } from "react-router-dom";
import { useAuth, SignInButton, UserButton } from "@clerk/clerk-react";
import { useEffect, useRef, useState } from "react";
import * as tus from "tus-js-client";
import { describeVideo, validateVideo } from "../video-file";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL;

type Attempt = Awaited<ReturnType<typeof describeVideo>> & { attempt_id: string; title: string };
type Reservation = { asset_id: string; status: string; object_path?: string; bucket_id?: string; upload_token?: string };
type Asset = { id: string; asset_type: "original" | "export"; status: string; retryable: boolean; error_message: string | null };
type Project = { id: string; title: string; video_assets: Asset[]; upload_attempt_id: string | null };

function transfer(file: File, reservation: Reservation, onProgress: (percent: number) => void) {
  const { upload_token, bucket_id, object_path } = reservation;
  if (!SUPABASE_URL || !upload_token || !bucket_id || !object_path) {
    throw new Error("Video Storage is unavailable.");
  }
  const endpoint = `${SUPABASE_URL.replace(/\/$/, "").replace(".supabase.co", ".storage.supabase.co")}/storage/v1/upload/resumable`;
  return new Promise<void>((resolve, reject) => {
    const upload = new tus.Upload(file, {
      endpoint,
      fingerprint: async () => `brevi:${endpoint}:${reservation.asset_id}`,
      retryDelays: [0, 3000, 5000, 10000, 20000],
      uploadDataDuringCreation: true,
      removeFingerprintOnSuccess: true,
      chunkSize: 6 * 1024 * 1024,
      headers: { "x-signature": upload_token, "x-upsert": "false" },
      metadata: { bucketName: bucket_id, objectName: object_path, contentType: "video/mp4" },
      onProgress: (sent, total) => onProgress(Math.round(sent / total * 100)),
      onError: reject,
      onSuccess: () => resolve(),
    });
    upload.findPreviousUploads().then(([previous]) => {
      if (previous) upload.resumeFromPreviousUpload(previous);
      upload.start();
    }).catch(reject);
  });
}

export default function FileUploader() {
  const { isLoaded, isSignedIn, userId } = useAuth();
  if (!isLoaded) return <p>Loading…</p>;
  if (!isSignedIn) return <SignInButton forceRedirectUrl="/upload" />;
  return <VideoLibrary key={userId} userId={userId} />;
}

class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function VideoLibrary({ userId }: { userId: string }) {
  const { getToken } = useAuth();
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [projects, setProjects] = useState<Project[]>([]);
  const [progress, setProgress] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [libraryError, setLibraryError] = useState("");
  const [playback, setPlayback] = useState<{ project: string; url: string } | null>(null);
  const [resumeProject, setResumeProject] = useState<Project | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const uploading = progress !== null;

  function selectVideo(files: FileList | null) {
    if (uploading || !files?.length) return;
    const selected = files[0];
    try {
      if (files.length !== 1) throw new Error("Choose one MP4 file.");
      validateVideo(selected);
      setError("");
      setFile(selected);
    } catch (failure) {
      setFile(null);
      setError(failure instanceof Error ? failure.message : "Choose an MP4 file.");
    }
  }

  async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
    const token = await getToken();
    if (!token) throw new Error("Sign in to access your videos.");
    const response = await fetch(`${API_URL}${path}`, {
      ...options,
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    });
    if (!response.ok) {
      const body = await response.json().catch(() => null);
      throw new ApiError(response.status, typeof body?.detail === "string" ? body.detail : "Request failed.");
    }
    return response.status === 204 ? undefined as T : response.json();
  }

  async function refresh() {
    setProjects(await api<Project[]>("/projects"));
    setLibraryError("");
  }

  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const token = await getToken();
        if (!token) throw new Error("Sign in to access your videos.");
        const response = await fetch(`${API_URL}/projects`, { headers: { Authorization: `Bearer ${token}` } });
        if (!response.ok) throw new Error("Could not load your video library.");
        const items: Project[] = await response.json();
        if (active) {
          setProjects(items);
          setLibraryError("");
        }
      } catch {
        if (active) setLibraryError("Could not load your video library. Retrying…");
      }
      if (active) timer = setTimeout(poll, 4000);
    }
    void poll();
    return () => { active = false; clearTimeout(timer); };
  }, [getToken]);

  async function uploadVideo() {
    if (progress !== null || !file || !(resumeProject?.title ?? title.trim())) return;
    setProgress(0);
    setError("");
    let storageKey: string | undefined;
    try {
      const video = await describeVideo(file);
      const attemptTitle = resumeProject?.title ?? title.trim();
      let attempt: Attempt | undefined;
      if (resumeProject) {
        const saved = await api<Attempt>(`/projects/${resumeProject.id}/upload-attempt`);
        if (saved.sha256 !== video.sha256 || saved.byte_size !== video.byte_size) {
          throw new Error("Reselect the same MP4 to resume this upload.");
        }
        attempt = saved;
      }
      storageKey = `brevi:upload:${userId}:${JSON.stringify([attemptTitle, video.filename, video.sha256])}`;
      attempt ??= { ...video, title: attemptTitle, attempt_id: localStorage.getItem(storageKey) ?? crypto.randomUUID() };
      localStorage.setItem(storageKey, attempt.attempt_id);
      const reserve = () => api<Reservation>("/projects/uploads", { method: "POST", body: JSON.stringify(attempt) });
      const reservation = await reserve();
      if (reservation.status !== "ready") {
        try {
          await transfer(file, reservation, setProgress);
        } catch (transferError) {
          if ((await reserve()).status !== "ready") throw transferError;
        }
        await api(`/video-assets/${reservation.asset_id}/complete`, { method: "POST" });
      }
      localStorage.removeItem(storageKey);
      setFile(null);
      setTitle("");
      setResumeProject(null);
      await refresh();
    } catch (failure) {
      if (storageKey && failure instanceof ApiError && failure.status === 410) {
        localStorage.removeItem(storageKey);
        setResumeProject(null);
      }
      setError(failure instanceof Error ? failure.message : "Upload failed.");
    } finally {
      setProgress(null);
    }
  }

  async function libraryAction(action: () => Promise<void>) {
    setError("");
    try {
      await action();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Request failed.");
    }
  }

  return (
    <div className="site">
      <header className="site-header shell">
        <Link className="wordmark" to="/" aria-label="Brevi home">brevi<span>.</span></Link>
        <UserButton />
      </header>
    <main className="upload-page shell">
      <h1>Video library</h1>
      <form className="upload-form" onSubmit={(event) => { event.preventDefault(); void uploadVideo(); }}>
        <h2>{resumeProject ? `Resume ${resumeProject.title}` : "Upload a video"}</h2>
        {!resumeProject && <label>Project title <input value={title} maxLength={200} onChange={(event) => setTitle(event.target.value)} /></label>}
          <div
            className="drop-zone"
            data-dragging={dragging}
            onDragOver={(event) => {
              event.preventDefault();
              event.dataTransfer.dropEffect = uploading ? 'none' : 'copy';
              setDragging(!uploading);
            }}
            onDragLeave={(event) => {
              if (!(event.relatedTarget instanceof Node) || !event.currentTarget.contains(event.relatedTarget)) {
                setDragging(false);
              }
            }}
            onDrop={(event) => {
              event.preventDefault();
              setDragging(false);
              selectVideo(event.dataTransfer.files);
            }}
          >
            <span className="upload-icon" aria-hidden="true">↑</span>
            <strong aria-live="polite">{file?.name ?? 'Drag and drop your video here'}</strong>
            <span className="file-formats">MP4 up to 25 MiB</span>
            <input
              ref={fileInput}
              type="file"
              accept=".mp4,video/mp4"
              disabled={uploading}
              hidden
              onChange={(event) => {
                selectVideo(event.currentTarget.files);
                event.currentTarget.value = '';
              }}
            />
            <button type="button" className="button button-outline" disabled={uploading} onClick={() => fileInput.current?.click()}>
              {file ? 'Choose another file' : 'Browse files'}
            </button>
          </div>
        <button className="button button-primary" disabled={!file || (!resumeProject && !title.trim()) || progress !== null}>
          {uploading ? "Uploading…" : resumeProject ? "Resume upload" : "Upload video"}
        </button>
        {resumeProject && <button type="button" disabled={progress !== null} onClick={() => setResumeProject(null)}>Cancel resume</button>}
        {progress !== null && <progress aria-label="Upload progress" value={progress} max={100}>{progress}%</progress>}
      </form>
      {error && <p role="alert">{error}</p>}
      {libraryError && <p role="status">{libraryError}</p>}
      <ul>
        {projects.map((project) => {
          const original = project.video_assets.find((asset) => asset.asset_type === "original");
          const exports = project.video_assets.filter((asset) => asset.asset_type === "export");
          return (
            <li key={project.id}>
              <h2>{project.title}</h2>
              {original?.status === "pending_upload" && (
                <>
                  <p>Upload incomplete</p>
                  {project.upload_attempt_id && <button disabled={progress !== null} onClick={() => setResumeProject(project)}>Resume</button>}
                </>
              )}
              {original?.status === "deleted" && <p>Upload expired. Start a new upload.</p>}
              {original?.status === "ready" && <p>Original uploaded</p>}
              {exports.map((asset) => (
                <div key={asset.id}>
                  <p>Export: {asset.status}</p>
                  {asset.error_message && <p>{asset.error_message}</p>}
                  {asset.status === "failed" && asset.retryable && (
                    <button onClick={() => void libraryAction(async () => {
                      await api(`/video-assets/${asset.id}/retry`, { method: "POST" });
                      await refresh();
                    })}>Retry render</button>
                  )}
                  {asset.status === "ready" && (
                    <button onClick={() => void libraryAction(async () => {
                      const { url } = await api<{ url: string }>(`/video-assets/${asset.id}/playback-url`);
                      setPlayback({ project: project.id, url });
                    })}>Play export</button>
                  )}
                </div>
              ))}
              {playback?.project === project.id && <video key={playback.url} src={playback.url} controls autoPlay />}
              <button onClick={() => {
                if (!window.confirm(`Delete “${project.title}” and its videos?`)) return;
                void libraryAction(async () => {
                  await api(`/projects/${project.id}`, { method: "DELETE" });
                  if (resumeProject?.id === project.id) setResumeProject(null);
                  if (playback?.project === project.id) setPlayback(null);
                  await refresh();
                });
              }}>{original?.status === "pending_upload" ? "Discard upload" : "Delete project"}</button>
            </li>
          );
        })}
      </ul>
    </main>
    </div>
  );
}
