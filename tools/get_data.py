"""Download and unpack the HydRA results of your hulls into data/.

    python tools/get_data.py KCS_L1p100            (your variant; its baseline is fetched too)

The files are the downloads of the project chapter of the course notes.
"""

import io
import os
import sys
import urllib.request
import zipfile

URL = "https://oe3035.mavlab.in/project/downloads/{}.zip"
FAMILIES = ["KVLCC2", "JBC", "KCS", "S175", "DTMB"]
FACTORS = ["0p900", "0p950", "1p000", "1p050", "1p100"]
MEMBERS = [f"{h}_L{f}" for h in FAMILIES for f in FACTORS]


def fetch(name, dest):
    print(f"downloading {name} ...")
    req = urllib.request.Request(URL.format(name), headers={"User-Agent": "oe3035-get-data"})   # the site refuses Python's default agent
    with urllib.request.urlopen(req, timeout=120) as resp:
        zf = zipfile.ZipFile(io.BytesIO(resp.read()))
    root = os.path.abspath(dest)
    for item in zf.infolist():
        target = os.path.abspath(os.path.join(root, item.filename))
        if not target.startswith(root + os.sep):
            raise SystemExit(f"unexpected path in the archive: {item.filename}")
    zf.extractall(root)
    print(f"  -> {os.path.join(dest, name)}/")


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in MEMBERS:
        raise SystemExit(f"usage: python tools/get_data.py MEMBER\nMEMBER is one of: {', '.join(MEMBERS)}")
    variant = sys.argv[1]
    dest = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    os.makedirs(dest, exist_ok=True)
    for name in dict.fromkeys([variant.split("_")[0] + "_L1p000", variant]):
        fetch(name, dest)


if __name__ == "__main__":
    main()
