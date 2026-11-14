const videoTypes = {
  mp4: 'video/mp4',
  mov: 'video/quicktime',
  webm: 'video/webm',
  mkv: 'video/x-matroska',
} as const;

export const videoAccept = Object.entries(videoTypes)
  .flatMap(([extension, mimeType]) => [`.${extension}`, mimeType])
  .join(',');

export function getVideoMimeType({ name, type, size }: Pick<File, 'name' | 'type' | 'size'>) {
  if (size === 0) return null;

  const formats = Object.entries(videoTypes);
  if (type && type !== 'application/octet-stream') {
    return formats.find(([, mimeType]) => mimeType === type)?.[1] ?? null;
  }

  const extension = name.toLowerCase().match(/\.([^.]+)$/)?.[1];
  return formats.find(([format]) => format === extension)?.[1] ?? null;
}
