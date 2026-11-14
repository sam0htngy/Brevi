import assert from 'node:assert/strict';
import { test } from 'node:test';
import { getVideoMimeType } from '../src/videoFile';

test('accepts a video type supported by the upload API', () => {
  assert.equal(getVideoMimeType({ name: 'recording.mov', type: 'video/quicktime', size: 128 }), 'video/quicktime');
});

test('uses the filename when the browser cannot determine the video type', () => {
  assert.equal(getVideoMimeType({ name: 'recording.MKV', type: '', size: 128 }), 'video/x-matroska');
});

test('rejects a known unsupported type even with a video extension', () => {
  assert.equal(getVideoMimeType({ name: 'notes.mp4', type: 'text/plain', size: 128 }), null);
});

test('rejects an empty video file', () => {
  assert.equal(getVideoMimeType({ name: 'empty.mp4', type: 'video/mp4', size: 0 }), null);
});
