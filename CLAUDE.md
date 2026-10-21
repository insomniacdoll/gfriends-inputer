# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Gfriends Inputer (v3.04) is a Simplified-Chinese CLI tool that imports actress portraits into an Emby/Jellyfin server from the [Gfriends](https://github.com/gfriends/gfriends) avatar repository, with optional local avatar folders, face-aware cropping, and metadata scraping. It is a single-file Python application distributed as a PyInstaller executable.

## Commands

```bash
# Install dependencies (use Python 3.9, as CI does; the pinned deps are old
# and may not build on 3.12+)
python3 -m pip install -r requirements.txt

# Run from source
python3 "./Gfriends Inputer.py"

# CLI options
python3 "./Gfriends Inputer.py" -c <config path> -q --skip-update --debug -v
```

First run generates `config.ini` and exits; the user must fill in `Host_Url` and `Host_API` under `[媒体服务器]` and rerun.

Build (matches `.github/workflows/main.yml`):

```bash
pip install pyinstaller
pyinstaller -F 'Gfriends Inputer.py' --collect-all grapheme
mkdir -p ./dist/Lib/
cp ./Lib/opencv_face_detector_uint8.pb ./Lib/opencv_face_detector.pbtxt ./dist/Lib/
```

The two model files must sit next to the executable in `Lib/`, because `Lib/cv2dnn.py` loads them from the relative path `./Lib/`.

Tests: `python3 -m unittest discover -s tests -v`. There is no linter or type checker configured. Verification of the full tool still means running it against an Emby/Jellyfin instance and reading `Getter/logger.log`.

## Architecture

**`Gfriends Inputer.py` is the entire application and is a script, not a module.** It has no `main()` guard: importing it runs argument parsing, config loading, logging setup, update checking, and the full import pipeline. You cannot import individual functions for testing without triggering a run; refactoring into functions/modules is a meaningful change, not a drop-in edit.

Pipeline, all at module scope:

1. `argparse_function` → `read_config` reads the Chinese-sectioned `config.ini` (`媒体服务器`, `下载设置`, `导入设置`, `调试功能`) and returns a tuple unpacked into module globals.
2. Setup: `requests.Session` with retry adapters, proxy detection (intranet/localhost bypasses the configured proxy), optional update check, optional `DEL_ALL`.
3. `read_persons` calls `Persons?api_key=` on the server.
4. `get_gfriends_map` downloads `Filetree.json` from the repository, caches it in `Getter/Filetree.json` after a HEAD size check, and builds `{actor name: url or [urls]}`. When `AI_Fix` is off, the `AI-Fix-` filename prefix is stripped.
5. Name matching prefers `Avatar/<name>.jpg` (local) over the repository; parenthesized suffixes (`（...）` / `(...)`) are stripped for a second lookup.
6. `download_avatar` downloads into `Downloads/` (threaded).
7. `fix_size` normalizes non-2:3 images: `1` Gaussian-blur padding, `2` center crop, `3` local OpenCV face detection, `4` Baidu AI; `0` disables it. Mode 3 lazily imports `Lib.cv2dnn` after config is read.
8. `input_avatar` uploads base64 JPEG bytes to `Items/{id}/Images/Primary`.
9. Optional `xslist_search` scrapes profile data and POSTs it to the item.

**Global state is pervasive.** Functions rely on module globals assigned during config load (`host_url`, `api_key`, `session`, `proxies`, `actor_dict`, `link_dict`, `inputed_dict`, `gfriends_map`, etc.). Adding a config key requires updating both the `read_config` return tuple and the unpacking statement near the bottom of the file, plus the generated `config.ini` template when relevant. `compatible_conf_version` gates old config files; bump it deliberately when the format changes.

**Server authentication compatibility** lives in `Lib/jellyfin_auth.py`. At startup the script calls the unauthenticated `System/Info/Public` endpoint and switches to the modern `Authorization: MediaBrowser Token="..."` header for Jellyfin 12+, where the lowercase `api_key` query parameter was disabled. Emby and Jellyfin 10.x keep the legacy `?api_key=` form. Auth headers are attached per server request through `server_headers()` rather than on the shared `session`, because the same session also talks to GitHub, the avatar repository, and xslist.org and must not leak the API key to them.

**Concurrency** uses the `@asyncc` decorator, which starts a raw thread per call. There is no pool or semaphore: loops poll `threading.activeCount()` against `MAX_DL` / `MAX_UL` and the main thread joins all threads between phases. Upload/download failures happen inside threads and are logged, not raised.

**Resume and incremental state** live under `Getter/`:

- `proc.tmp`: md5 of the server's person list plus md5 of the config, then per-actor step markers (`md5(name+0)` check, `+1` download, `+2` resize, `+3` upload). Resume only happens when both header md5s match.
- `down<md5(host_url)>.log`: ledger for `OverWrite = 2` (incremental). Values are the repository image mtime (`t=` in the URL) or local file size. Deleting it resets incremental detection.
- `logger.log` is deleted at every startup; `演员清单.txt` records matched/skipped actors.

All paths are relative to the working directory (`Downloads/`, `Avatar/`, `Getter/`, `Lib/`). On macOS/Linux the script `chdir`s to its own directory at startup; on Windows it relies on the current directory.

## Conventions

- All user-facing output, logs, and comments are Simplified Chinese. Keep new strings consistent with that.
- Version lives in `version` at the top of the script and must also be added to `compatible_conf_version`; README `CLI 命令` help text mirrors the argparse options.
- Release builds are produced only by GitHub Actions as build artifacts (no publishing/release automation in the repo).
- `OverWrite`: `0` skip actors that already have an image, `1` overwrite all, `2` incremental. `Conflict_Proc = 1` downloads every avatar for an actor and pauses for manual selection; it is ignored in quiet mode.
- Network access goes through the shared `session`; do not create ad-hoc `requests.get` calls for repository/server traffic.
