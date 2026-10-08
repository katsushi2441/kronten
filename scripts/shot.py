#!/usr/bin/env python3
"""map.html を端末幅で撮り、横はみ出し（scrollWidth）を数字で確かめる。使い捨てのブラウザ（chrome-profile は使わない）。

  /usr/bin/python3 scripts/shot.py outputs/<slug>/map.html
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

page_path = Path(sys.argv[1]).resolve()
with sync_playwright() as p:
    b = p.chromium.launch()
    for w in (360, 390, 1280):
        pg = b.new_page(viewport={"width": w, "height": 900})
        pg.goto(page_path.as_uri())
        pg.wait_for_timeout(1500)
        sw = pg.evaluate("document.documentElement.scrollWidth")
        out = page_path.with_name(f"shot-{w}.png")
        pg.screenshot(path=str(out), full_page=False)
        print(f"{w}px scrollWidth={sw} {'OK' if sw <= w else 'はみ出し'} → {out.name}")
        pg.close()
    b.close()
