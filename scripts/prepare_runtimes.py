"""Assemble checksum-pinned browser runtimes at image build time.

All requests are to public upstream distributions. No site credentials are needed.
Only explicitly listed tar members are read; archives are never extracted wholesale.
"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import time
import urllib.request


def verified(data, expected, label):
    if hashlib.sha256(data).hexdigest() != expected:
        raise RuntimeError(f"Checksum mismatch: {label}; refusing changed upstream bytes")
    return data


def download(item):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(item["url"], timeout=60) as response:
                data = response.read(32 * 1024 * 1024 + 1)
            if len(data) > 32 * 1024 * 1024:
                raise RuntimeError("Runtime download exceeds 32 MiB")
            return verified(data, item["sha256"], item["url"])
        except (OSError, TimeoutError):
            if attempt == 2:
                raise
            time.sleep(attempt + 1)


def assemble(root, manifest):
    root = root.resolve()
    def save(item, data):
        target = (root / item["path"]).resolve()
        if not target.is_relative_to(root):
            raise RuntimeError("Invalid runtime destination")
        verified(data, item["sha256"], item["path"])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    def package(item):
        with tarfile.open(fileobj=io.BytesIO(download(item)), mode="r:gz") as archive:
            for entry in item["files"]:
                member = archive.getmember(entry["member"])
                if not member.isfile() or member.size > 32 * 1024 * 1024:
                    raise RuntimeError("Invalid runtime archive member")
                save(entry, archive.extractfile(member).read())

    def standalone(item):
        save(item, download(item))

    with ThreadPoolExecutor(max_workers=3) as pool:
        tasks = [pool.submit(package, item) for item in manifest["packages"]]
        tasks += [pool.submit(standalone, item) for item in manifest["files"]]
        for task in tasks:
            task.result()
    print("Browser runtimes assembled and every dependency checksum verified.")


if __name__ == "__main__":
    manifest = json.loads(Path(__file__).with_name("runtime-manifest.json").read_text())
    assemble(Path(sys.argv[1]), manifest)
