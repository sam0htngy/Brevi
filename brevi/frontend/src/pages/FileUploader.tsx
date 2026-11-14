import { UserButton, useAuth } from '@clerk/clerk-react';
import { useRef, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import * as tus from 'tus-js-client';
import { getVideoMimeType, videoAccept } from '../videoFile';

type UploadStatus = 'idle' | 'uploading' | 'success' | 'error';
type UploadReservation = {
  asset_id: string;
  object_path: string;
  bucket_id: string;
  upload_token: string;
};

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL;

export default function FileUploader() {
  const { getToken } = useAuth();
  const fileInput = useRef<HTMLInputElement>(null);
  const [selection, setSelection] = useState<{ file: File; mimeType: string } | null>(null);
  const [title, setTitle] = useState('');
  const [status, setStatus] = useState<UploadStatus>('idle');
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState('');
  const [dragging, setDragging] = useState(false);
  const uploading = status === 'uploading';

  function selectVideo(files: FileList | null) {
    if (uploading || !files?.length) return;

    const file = files[0];
    const mimeType = getVideoMimeType(file);
    if (files.length !== 1 || !mimeType) {
      setSelection(null);
      setStatus('error');
      setError('Choose one non-empty MP4, MOV, WebM, or MKV video.');
      return;
    }

    setSelection({ file, mimeType });
    setStatus('idle');
  }

  async function api(path: string, options: RequestInit) {
    const token = await getToken();
    if (!token) throw new Error('Sign-in required.');

    const response = await fetch(`${API_URL}${path}`, {
      ...options,
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    });
    if (!response.ok) throw new Error('Upload request failed.');
    return response.status === 204 ? null : response.json();
  }

  async function handleFileUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selection || !title.trim() || uploading || status === 'success') return;

    if (!SUPABASE_URL) {
      setStatus('error');
      setError('Video uploads are unavailable. Configure VITE_SUPABASE_URL to enable them.');
      return;
    }

    const { file, mimeType } = selection;
    setStatus('uploading');
    setProgress(0);

    try {
      const reservation: UploadReservation = await api('/projects/uploads', {
        method: 'POST',
        body: JSON.stringify({ title: title.trim(), filename: file.name, mime_type: mimeType, byte_size: file.size }),
      });
      const endpoint = `${SUPABASE_URL.replace(/\/$/, '').replace('.supabase.co', '.storage.supabase.co')}/storage/v1/upload/resumable`;
      await new Promise<void>((resolve, reject) => {
        const upload = new tus.Upload(file, {
          endpoint,
          retryDelays: [0, 3000, 5000, 10000, 20000],
          uploadDataDuringCreation: true,
          removeFingerprintOnSuccess: true,
          chunkSize: 6 * 1024 * 1024,
          headers: { 'x-signature': reservation.upload_token, 'x-upsert': 'false' },
          metadata: { bucketName: reservation.bucket_id, objectName: reservation.object_path, contentType: mimeType },
          onProgress: (sent, total) => setProgress(Math.round((sent / total) * 100)),
          onError: reject,
          onSuccess: () => resolve(),
        });
        upload.findPreviousUploads().then((previous) => {
          const match = previous.find(({ metadata }) => metadata?.objectName === reservation.object_path &&
            metadata.bucketName === reservation.bucket_id);
          if (match) upload.resumeFromPreviousUpload(match);
          upload.start();
        }).catch(reject);
      });
      await api(`/video-assets/${reservation.asset_id}/complete`, { method: 'POST' });
      setStatus('success');
    } catch {
      setError('Upload failed. Please try again.');
      setStatus('error');
    }
  }

  return (
    <div className="site">
      <header className="site-header shell">
        <Link className="wordmark" to="/" aria-label="Brevi home">brevi<span>.</span></Link>
        <UserButton />
      </header>
      <main className="upload-page shell">
        <h1>Upload a video</h1>
        <p className="intro">Add a recording to start a new highlight reel.</p>
        <form className="upload-form" onSubmit={handleFileUpload}>
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
            <strong aria-live="polite">{selection?.file.name ?? 'Drag and drop your video here'}</strong>
            <span className="file-formats">MP4, MOV, WebM, or MKV</span>
            <input
              ref={fileInput}
              type="file"
              accept={videoAccept}
              disabled={uploading}
              hidden
              onChange={(event) => {
                selectVideo(event.currentTarget.files);
                event.currentTarget.value = '';
              }}
            />
            <button type="button" className="button button-outline" disabled={uploading} onClick={() => fileInput.current?.click()}>
              {selection ? 'Choose another file' : 'Browse files'}
            </button>
          </div>
          <label htmlFor="project-title">Project title</label>
          <input
            id="project-title"
            value={title}
            placeholder="e.g. Product walkthrough"
            disabled={uploading}
            onChange={(event) => setTitle(event.target.value)}
          />
          <button className="button button-primary" disabled={!selection || !title.trim() || uploading || status === 'success'}>
            {uploading ? 'Uploading…' : 'Upload video'}
          </button>
          {uploading && <progress aria-label="Upload progress" value={progress} max={100}>{progress}%</progress>}
          {status === 'success' && <p className="success" role="status">Upload complete. Your video is queued for processing.</p>}
          {status === 'error' && <p className="error" role="alert">{error}</p>}
        </form>
      </main>
    </div>
  );
}
