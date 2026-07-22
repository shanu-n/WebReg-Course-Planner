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
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable

# Ad-supported variant: WEBREG_ADS=1 adds gutter ad rails + content pages
# (About/Guide/FAQ/Privacy/Terms) so the site has real content for AdSense.
# The clean build (no flag) is byte-for-byte unchanged.
ADS = os.environ.get("WEBREG_ADS") == "1"


def run(script):
    print(f"→ {script}")
    subprocess.run([PY, str(ROOT / script)], cwd=ROOT, check=True)


def _ver(path):
    """Short content hash for cache-busting — changes only when the file does."""
    return hashlib.md5(Path(path).read_bytes()).hexdigest()[:8]


def regen_index():
    # Cache-bust CSS/JS: append a content hash so browsers always fetch the
    # current version after an update (stale CSS was rendering the tip corner
    # unstyled). Unchanged files keep the same hash and stay cacheable.
    css_v = _ver(ROOT / "static/css/webreg.css")
    js_v = _ver(ROOT / "static/js/webreg.js")
    ldb_v = _ver(ROOT / "site/js/localdb.js")
    src = (ROOT / "templates" / "index.html").read_text()
    # bake the "Data as of" date (Flask fills this in dev; the static site
    # has no server, so substitute the committed value here)
    stamp = ROOT / "data" / "refreshed_at.txt"
    asof = stamp.read_text().strip() if stamp.exists() else "—"
    src = src.replace("{{ data_asof }}", asof)
    src = src.replace("/static/css/webreg.css", f"css/webreg.css?v={css_v}")
    src = src.replace("/static/img/", "img/")
    src = src.replace(
        '<script src="/static/js/webreg.js"></script>',
        f'<script src="js/localdb.js?v={ldb_v}"></script>\n'
        f'<script src="js/webreg.js?v={js_v}"></script>')
    if ADS:
        import ads_content  # local module (scripts/ is on sys.path here)
        # keep the tool visually unchanged: only add gutter ad rails + a small
        # footer nav to the content pages
        footer_nav = ('<div class="footer-nav">More: '
                      '<a href="guide.html">Planning Guide</a> &middot; '
                      '<a href="faq.html">FAQ</a> &middot; '
                      '<a href="about.html">About</a> &middot; '
                      '<a href="privacy.html">Privacy</a> &middot; '
                      '<a href="terms.html">Terms</a></div>')
        src = src.replace('<div class="feedback-note">',
                          footer_nav + '\n  <div class="feedback-note">')
        src = src.replace('</body>', ads_content.AD_RAILS + '\n</body>')
    (ROOT / "site" / "index.html").write_text(src)
    print(f"→ site/index.html regenerated (cache-busted css/js{'; ads' if ADS else ''})")


def copy_images():
    src = ROOT / "static" / "img"
    if not src.is_dir():
        return
    dst = ROOT / "site" / "img"
    dst.mkdir(parents=True, exist_ok=True)
    for f in src.iterdir():
        if f.is_file():
            shutil.copyfile(f, dst / f.name)
    print("→ copied static/img → site/img")


def main():
    run("seed.py")
    run("scripts/export_static.py")
    regen_index()
    copy_images()
    # the static build reuses the exact frontend; localdb.js (site-only) stays
    shutil.copyfile(ROOT / "static/css/webreg.css", ROOT / "site/css/webreg.css")
    shutil.copyfile(ROOT / "static/js/webreg.js", ROOT / "site/js/webreg.js")
    print("→ copied css/webreg.css, js/webreg.js")
    if ADS:
        sys.path.insert(0, str(ROOT / "scripts"))
        import ads_content
        css_v = _ver(ROOT / "static/css/webreg.css")
        pages = ads_content.build_pages(ROOT / "site", css_v)
        print(f"→ built ad content pages: {', '.join(pages)}")
    print("site/ is ready to deploy")


if __name__ == "__main__":
    main()
