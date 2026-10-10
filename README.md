# blcup-downloader

Downloads every MP3 listed on a BLCUP (blcup.com) mobile resource series page,
e.g. the audio for *新实用汉语课本 (第3版 西班牙文)*.

Requires Python 3.8+ and nothing else (standard library only).

## Usage

```
python blcup_download.py "http://www.blcup.com/MobileResSeries?rid=<id>" -o audio
```

Options:

- `-o DIR`: output folder (default: current folder)
- `-j N`: parallel downloads (default: 8)
- `--full-names`: keep the full title as the filename instead of just the track number

Files are saved by track number (`1-01-01-01.mp3`, ...). Each file is checked against
the size reported by the server, and complete files are skipped, so re-running the
script resumes an interrupted download.

On Windows, if Chinese titles print as errors in the console, run with
`set PYTHONIOENCODING=utf-8` (cmd) or `$env:PYTHONIOENCODING="utf-8"` (PowerShell).
