from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, List
import hashlib
import os
import fnmatch

@dataclass
class FileInfo: #One file's metadata we care about.
    relpath: str       # path relative to root, POSIX-style (with "/")
    abs_path: Path     # absolute path on disk
    size: int          # file size in bytes
    sha256: str        # SHA-256 content hash (hex string)
    mtime: float       # last modified time (epoch seconds, float)

def _sha256_of(path: Path, chunk_size: int = 65536) -> str:  #Stream the file so we don't load big files into memory.
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

def _matches_any(patterns: List[str], s: str) -> bool:   #Return True if string s matches any of the glob patterns.
    return any(fnmatch.fnmatch(s, pat) for pat in patterns)

def is_text_file(path: Path, probe_bytes: int = 8192) -> bool:
    """
    Crude but effective probe:
    - read the first few KB
    - if we see a NUL byte, assume it's binary
    """
    try:
        with path.open("rb") as f:
            chunk = f.read(probe_bytes)
        return b"\x00" not in chunk
    except Exception:
        return False

def iter_files(root: Path, include: List[str], exclude: List[str]) -> Iterator[FileInfo]:
    """
    Walk 'root' recursively and yield FileInfo for files that:
      - match at least one include pattern (if include list is non-empty)
      - do NOT match any exclude pattern
    Matching is done against the POSIX relative path (e.g., 'src/app/main.py').
    """
    root = root.resolve()

    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            abs_path = Path(dirpath) / name
            # relative path like "subdir/file.txt" (no leading "/")
            rel = abs_path.relative_to(root).as_posix()

            # includes: if provided, file must match at least one
            if include and not _matches_any(include, rel):
                continue

            # excludes: if provided, any match means "skip"
            if exclude and _matches_any(exclude, rel):
                continue

            # get metadata; skip if unreadable
            try:
                st = abs_path.stat()
                size = int(st.st_size)
                mtime = float(st.st_mtime)
                digest = _sha256_of(abs_path)
            except (OSError, PermissionError):
                continue

            yield FileInfo(
                relpath=rel,
                abs_path=abs_path,
                size=size,
                sha256=digest,
                mtime=mtime,
            )
