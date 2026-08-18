"""Resumably materialize the official Panda asset from local Git-tree metadata.

The Menagerie sparse checkout supplies authoritative paths, byte sizes, and Git
blob IDs. Files are fetched one-by-one from the matching immutable GitHub commit
with curl resume support, then verified as Git blobs before atomic promotion.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path


# Each entry is a URL template.  jsDelivr's immutable GitHub form requires an
# ``@<commit>`` separator; without it, the server may return an HTML directory
# page with HTTP 200, which looks like a successful curl transfer but cannot
# possibly pass the Git-blob checksum.
REPOSITORY_URL_TEMPLATES = (
    "https://cdn.jsdelivr.net/gh/google-deepmind/mujoco_menagerie@{commit}/{path}",
    "https://raw.githubusercontent.com/google-deepmind/mujoco_menagerie/{commit}/{path}",
)
TARGET_ROOT = Path("/root/shared-nvme/openpi-robot-runtime/assets/panda_menagerie")
METADATA_REPOSITORY = Path("/root/shared-nvme/openpi-robot-runtime/assets/mujoco_menagerie")
SUBTREE = "franka_emika_panda"
SOURCE_COMMIT = "da76818e269b82289eba39808e2fb91d679d6994"
EXPECTED_TOTAL_BYTES = 36_560_926
TREE_API = "https://api.github.com/repos/google-deepmind/mujoco_menagerie/git/trees"


@dataclass(frozen=True)
class Entry:
    path: str
    size: int | None
    blob_id: str


def git_blob_id(path: Path, size: int | None = None) -> str:
    actual_size = path.stat().st_size if size is None else size
    digest = hashlib.sha1()
    digest.update(f"blob {actual_size}\0".encode())
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def local_manifest() -> list[Entry] | None:
    """Read immutable blob metadata from the existing official Git object store.

    This avoids making every resumable run depend on GitHub's Tree API.  The
    downloaded bytes are still verified against these official blob IDs.
    """
    result = subprocess.run(
        [
            "git", "-C", str(METADATA_REPOSITORY), "ls-tree", "-r", "-z",
            SOURCE_COMMIT, "--", SUBTREE,
        ],
        check=False,
        capture_output=True,
    )
    if result.returncode:
        return None
    entries: list[Entry] = []
    for raw_line in result.stdout.split(b"\0"):
        if not raw_line:
            continue
        metadata, raw_path = raw_line.split(b"\t", maxsplit=1)
        _mode, kind, blob_id = metadata.split()
        if kind == b"blob":
            entries.append(Entry(raw_path.decode(), None, blob_id.decode()))
    return entries or None


def manifest() -> tuple[str, list[Entry]]:
    entries = local_manifest()
    if entries is not None:
        print("MANIFEST_SOURCE local_official_git_metadata", flush=True)
        return SOURCE_COMMIT, entries
    request = urllib.request.Request(
        f"{TREE_API}/{SOURCE_COMMIT}?recursive=1",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "openpi-robot-runtime"},
    )
    last_error: Exception | None = None
    payload: dict[str, object] | None = None
    for _ in range(6):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = json.load(response)
            break
        except Exception as error:
            last_error = error
            time.sleep(3)
    if payload is None:
        raise RuntimeError("Unable to retrieve the official Git tree manifest.") from last_error
    entries: list[Entry] = []
    for item in payload.get("tree", []):  # type: ignore[union-attr]
        if item.get("type") == "blob" and item.get("path", "").startswith(f"{SUBTREE}/"):
            entries.append(Entry(path=item["path"], size=int(item["size"]), blob_id=item["sha"]))
    if not entries:
        raise RuntimeError("Official Panda manifest is empty or incomplete.")
    return SOURCE_COMMIT, entries


def verified(path: Path, entry: Entry) -> bool:
    return (
        path.is_file()
        and (entry.size is None or path.stat().st_size == entry.size)
        and git_blob_id(path, entry.size) == entry.blob_id
    )


def write_status(commit: str, entries: list[Entry]) -> None:
    completed = [entry for entry in entries if verified(TARGET_ROOT / entry.path, entry)]
    status = {
        "source_commit": commit,
        "subtree": SUBTREE,
        "files_expected": len(entries),
        "bytes_expected": EXPECTED_TOTAL_BYTES,
        "files_verified": len(completed),
        "bytes_verified": sum((TARGET_ROOT / entry.path).stat().st_size for entry in completed),
    }
    temporary = TARGET_ROOT / "download_status.tmp"
    temporary.write_text(json.dumps(status, indent=2), encoding="utf-8")
    os.replace(temporary, TARGET_ROOT / "download_status.json")
    print(json.dumps(status), flush=True)


def download(commit: str, entry: Entry) -> None:
    destination = TARGET_ROOT / entry.path
    destination.parent.mkdir(parents=True, exist_ok=True)
    if verified(destination, entry):
        return
    partial = destination.with_name(destination.name + ".partial")
    if partial.exists() and entry.size is not None and partial.stat().st_size > entry.size:
        partial.unlink()
    failures: list[str] = []
    for url_template in REPOSITORY_URL_TEMPLATES:
        url = url_template.format(commit=commit, path=entry.path)
        command = [
            "curl",
            "--fail-with-body",
            "--location",
            "--silent",
            "--show-error",
            "--retry",
            "3",
            "--retry-all-errors",
            "--retry-delay",
            "2",
            "--connect-timeout",
            "20",
            "--speed-time",
            "45",
            "--speed-limit",
            "1024",
            "--continue-at",
            "-",
            "--output",
            str(partial),
            url,
        ]
        result = subprocess.run(command, check=False, text=True, capture_output=True)
        if verified(partial, entry):
            os.replace(partial, destination)
            print(f"VERIFIED {entry.path} via {url.split('/')[2]}", flush=True)
            return
        detail = result.stderr.strip().replace("\n", " ")[-300:]
        failures.append(f"{url.split('/')[2]} exit={result.returncode}: {detail}")
        print(f"SOURCE_FAILED {entry.path}: {failures[-1]}", flush=True)
    raise RuntimeError(
        f"Verification failed for {entry.path}; partial is retained for resume. "
        + " | ".join(failures)
    )


def main() -> None:
    TARGET_ROOT.mkdir(parents=True, exist_ok=True)
    commit, entries = manifest()
    write_status(commit, entries)
    for entry in entries:
        download(commit, entry)
        write_status(commit, entries)
    print("PANDA_ASSET_VERIFIED", flush=True)


if __name__ == "__main__":
    try:
        main()
    except BaseException as error:
        print(f"DOWNLOAD_FAILED: {type(error).__name__}: {error}", file=sys.stderr, flush=True)
        raise
