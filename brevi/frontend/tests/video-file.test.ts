import { expect, test } from "bun:test";
import { describeVideo } from "../src/video-file";

test("hashes the bytes and accepts MP4 files with an empty browser MIME type", async () => {
  const file = new File(["abc"], "source.MP4");
  expect(await describeVideo(file)).toEqual({
    filename: "source.MP4",
    mime_type: "video/mp4",
    byte_size: 3,
    sha256: "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
  });
});

test("rejects files above 25 MiB and other formats", async () => {
  await expect(describeVideo(new File([new Uint8Array(25 * 1024 * 1024 + 1)], "large.mp4"))).rejects.toThrow("25 MiB");
  await expect(describeVideo(new File(["abc"], "source.webm"))).rejects.toThrow("MP4");
});
