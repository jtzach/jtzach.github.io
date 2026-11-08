# Recover a saved video

On the archive page, choose **Load saved video**. When it is ready, use the video controls or **Download video**. The saved video loads only after you request it; it does not autoplay.

If JavaScript is unavailable or the browser cannot load the video, download this website repository from [GitHub](https://github.com/jtzach/jtzach.github.io) using **Code → Download ZIP**, then extract it. The repository includes every saved video file.

Two larger videos are stored as ordered binary parts. The following Python 3 command reconstructs complete MP4 files and checks their SHA-256 checksums:

```sh
python scripts/restore_videos.py --output recovered-videos
```

Run that command from the extracted repository folder. You may replace `recovered-videos` with another output folder. No packages or network access are required. Existing files with different contents are never overwritten; an already-correct file is verified and kept.

The saved parts and their order, complete file size, original filename, and SHA-256 checksum are listed in `data/archive.json`. The reconstructed MP4s preserve exactly the bytes of the archived video delivery copies. Other videos are available directly as MP4s under `assets/archive/video/`.
