#!/usr/bin/env python3
"""Build the deployable static site into site/ from source.

Runs everything the GitHub Pages deploy needs, using only committed inputs
(data/parsed/, data/*.json, templates/, static/) and the Python standard
library — no third-party packages, so CI needs no pip install:

  1. seed.py            -> data/webreg.db   (from committed data/parsed/)
  2. export_static.py   -> site/data/*.json (FA26 catalog bundle)
  3. regenerate         -> site/index.html  (from templates/index.html)
  4. copy               -> site/css, site/js (from static/), keeping localdb.js

Run locally to preview, or let .github/workflows/deploy.yml run it on push.
"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable


def run(script):
    print(f"→ {script}")
    subprocess.run([PY, str(ROOT / script)], cwd=ROOT, check=True)


def regen_index():
    src = (ROOT / "templates" / "index.html").read_text()
    src = src.replace("/static/css/webreg.css", "css/webreg.css")
    src = src.replace(
        '<script src="/static/js/webreg.js"></script>',
        '<script src="js/localdb.js"></script>\n'
        '<script src="js/webreg.js"></script>')
    (ROOT / "site" / "index.html").write_text(src)
    print("→ site/index.html regenerated")


def main():
    run("seed.py")
    run("scripts/export_static.py")
    regen_index()
    # the static build reuses the exact frontend; localdb.js (site-only) stays
    shutil.copyfile(ROOT / "static/css/webreg.css", ROOT / "site/css/webreg.css")
    shutil.copyfile(ROOT / "static/js/webreg.js", ROOT / "site/js/webreg.js")
    print("→ copied css/webreg.css, js/webreg.js")
    print("site/ is ready to deploy")


if __name__ == "__main__":
    main()
