"""Fetch the official nuScenes-hosted detection results for the val split.

nuScenes publishes detection outputs from three detectors so that tracking work
can skip inference (see python-sdk/nuscenes/eval/tracking/README.md, Baselines).
Two of them form an exact camera-only vs lidar-only pair on the same split in
the same format:

  megvii_val.json      Megvii / CBGS   lidar-only    51.9 mAP / 62.8 NDS
  mapillary_val.json   MonoDIS         camera-only   29.8 mAP / 36.9 NDS

Zip central directories live at the tail, so a Range-request file object lets
zipfile read only the member we name: ~66 MB and ~93 MB of transfer instead of
458 MB and 676 MB.

Licence: derivatives of nuScenes, inheriting CC BY-NC-SA 4.0, non-commercial.
"""
import io, os, sys, urllib.request, zipfile

TARGETS = [
    ("https://www.nuscenes.org/data/detection-megvii.zip", "megvii_val.json", "lidar-only"),
    ("https://www.nuscenes.org/data/detection-mapillary.zip", "mapillary_val.json", "camera-only"),
    ("https://www.nuscenes.org/data/detection-pointpillars.zip", "pointpillars-val.json", "lidar-only"),
]
OUT = sys.argv[1] if len(sys.argv) > 1 else "predictions"


class HttpRangeFile(io.RawIOBase):
    """Minimal seekable file over HTTP Range requests."""

    def __init__(self, url):
        self.url = url
        self.pos = 0
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=60) as r:
            self.size = int(r.headers["Content-Length"])
        self.read_bytes = 0

    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else (self.pos + off if whence == 1 else self.size + off)
        return self.pos

    def tell(self):
        return self.pos

    def seekable(self):
        return True

    def readable(self):
        return True

    def read(self, n=-1):
        if n < 0:
            n = self.size - self.pos
        if n == 0 or self.pos >= self.size:
            return b""
        end = min(self.pos + n, self.size) - 1
        req = urllib.request.Request(self.url, headers={"Range": f"bytes={self.pos}-{end}"})
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=180) as r:
                    data = r.read()
                break
            except Exception as exc:
                if attempt == 3:
                    raise
                print(f"    retry {attempt + 1} after {type(exc).__name__}", file=sys.stderr)
        self.pos += len(data)
        self.read_bytes += len(data)
        return data

    def readinto(self, b):
        data = self.read(len(b))
        n = len(data)
        b[:n] = data
        return n


os.makedirs(OUT, exist_ok=True)
for url, member, modality in TARGETS:
    dest = os.path.join(OUT, member)
    if os.path.exists(dest) and os.path.getsize(dest) > 1_000_000:
        print(f"{member}: already present ({os.path.getsize(dest):,} bytes)")
        continue
    print(f"{member} ({modality}) from {url}")
    raw = HttpRangeFile(url)
    zf = zipfile.ZipFile(io.BufferedReader(raw, buffer_size=1 << 20))
    names = [n for n in zf.namelist() if n.endswith(member)]
    if not names:
        print(f"  MEMBER NOT FOUND. archive holds: {zf.namelist()[:8]}")
        continue
    with zf.open(names[0]) as src, open(dest, "wb") as out:
        while True:
            chunk = src.read(1 << 22)
            if not chunk:
                break
            out.write(chunk)
    print(f"  wrote {dest}: {os.path.getsize(dest):,} bytes "
          f"(transferred {raw.read_bytes / 1e6:.1f} MB of {raw.size / 1e6:.1f} MB)")
