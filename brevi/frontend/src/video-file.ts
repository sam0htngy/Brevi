export const MAX_VIDEO_BYTES = 25 * 1024 * 1024;

export function validateVideo(file: File) {
  if (!/\.mp4$/i.test(file.name) || (file.type && file.type !== "video/mp4")) {
    throw new Error("Choose an MP4 file.");
  }
  if (file.size === 0 || file.size > MAX_VIDEO_BYTES) {
    throw new Error("Choose a non-empty MP4 up to 25 MiB.");
  }
}

export async function describeVideo(file: File) {
  validateVideo(file);
  const hash = await crypto.subtle.digest("SHA-256", await file.arrayBuffer());
  const sha256 = Array.from(new Uint8Array(hash), (byte) => byte.toString(16).padStart(2, "0")).join("");
  return { filename: file.name, mime_type: "video/mp4", byte_size: file.size, sha256 };
}
