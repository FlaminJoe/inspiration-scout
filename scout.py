#!/usr/bin/env python3
"""inspiration-scout — przeszukuje galerie inspiracji wg branży i zapisuje
referencje (screenshoty żywych stron / grafiki mockupów).

Przykłady:
  python scout.py --industry "dental clinic" \\
      --keywords "dentist,dental clinic,orthodontist" \\
      --galleries godly,awwwards,framer,dribbble --mode full --limit 5 --depth 1

  python scout.py --industry "law firm" --keywords "law firm" --mode section --section testimonials
  python scout.py --industry "law firm" --keywords "law firm" --mode subpage --subpage /services
  python scout.py login cosmos     # jednorazowy ręczny login do trwałego profilu
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import sys
import time
from urllib.parse import urlparse

import galleries
from galleries import REGISTRY
import capture
import download
import report

HERE = os.path.dirname(os.path.abspath(__file__))
PROFILE_DIR = os.path.join(HERE, ".browser-profile")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
STEALTH_JS = "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"


def slugify(text: str, maxlen: int = 60) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return (s or "item")[:maxlen]


def _launch(p, headless: bool):
    ctx = p.chromium.launch_persistent_context(
        PROFILE_DIR,
        headless=headless,
        viewport={"width": 1440, "height": 900},
        user_agent=UA,
        locale="en-US",
        args=["--disable-blink-features=AutomationControlled"],
    )
    try:
        ctx.add_init_script(STEALTH_JS)
    except Exception:
        pass
    return ctx


def cmd_login(gallery_name: str) -> int:
    from playwright.sync_api import sync_playwright
    g = galleries.get(gallery_name)
    base = g.base if g else f"https://{gallery_name}"
    os.makedirs(PROFILE_DIR, exist_ok=True)
    with sync_playwright() as p:
        ctx = _launch(p, headless=False)
        page = ctx.new_page()
        page.goto(base)
        print(f"\n[login] Zaloguj się ręcznie do '{gallery_name}' w otwartym oknie.")
        print("[login] Po zalogowaniu wróć tu i naciśnij Enter, aby zapisać sesję...")
        try:
            input()
        except EOFError:
            time.sleep(30)
        ctx.close()
    print("[login] Sesja zapisana w profilu.")
    return 0


def run(args) -> int:
    from playwright.sync_api import sync_playwright

    selected = [g.strip() for g in args.galleries.split(",") if g.strip()] \
        if args.galleries else galleries.ALL
    selected = [g for g in selected if g in REGISTRY]
    if not selected:
        print("Brak prawidłowych galerii.", file=sys.stderr)
        return 2

    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    if not keywords:
        print("Podaj --keywords (angielskie hasła oddzielone przecinkiem).", file=sys.stderr)
        return 2

    date = dt.date.today().isoformat()
    out_dir = os.path.join(os.getcwd(), "inspiration-output", f"{slugify(args.industry)}-{date}")
    os.makedirs(out_dir, exist_ok=True)

    run_meta = {
        "industry": args.industry,
        "keywords": keywords,
        "galleries": selected,
        "mode": args.mode,
        "section": args.section,
        "subpage": args.subpage,
        "limit": args.limit,
        "depth": args.depth,
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
    }

    results = []
    with sync_playwright() as p:
        ctx = _launch(p, headless=not args.headful)
        ctx.set_default_navigation_timeout(45000)
        disco = ctx.new_page()

        for gname in selected:
            g = REGISTRY[gname]
            found = []
            for kw in keywords:
                if len(found) >= args.limit:
                    break
                try:
                    items = g.search(disco, kw, args.limit - len(found))
                except Exception as e:
                    print(f"[{gname}] discovery error ({kw}): {type(e).__name__}", file=sys.stderr)
                    items = []
                found.extend(items)
                time.sleep(1.0)

            if not found:
                results.append({"gallery": gname, "kind": g.kind, "source_url": g.search_url(keywords[0]),
                                "keyword": keywords[0], "title": "", "status": "no-results", "files": []})
                print(f"[{gname}] brak wyników")
                continue

            for it in found[:args.limit]:
                base = {"gallery": it.gallery, "kind": it.kind, "source_url": it.source_url,
                        "live_url": it.url, "keyword": it.keyword, "title": it.title}
                # żywe strony: nazwa z hosta (informatywna); mockupy: z tytułu
                label = urlparse(it.url).netloc if it.kind == "site" else (it.title or it.url)
                slug = f"{it.gallery}-{slugify(label, 40)}"
                try:
                    if it.kind == "site":
                        assets = capture.capture_site(
                            ctx, it, mode=args.mode, depth=args.depth,
                            section=args.section, subpage=args.subpage,
                            out_dir=out_dir, slug=slug)
                    else:
                        assets = download.download_mockup(ctx, it, out_dir=out_dir, slug=slug)
                except Exception as e:
                    assets = [{"file": None, "page_url": it.url, "type": it.kind,
                               "status": f"capture-error:{type(e).__name__}"}]
                base["files"] = assets
                base["status"] = assets[0]["status"] if assets else "no-assets"
                results.append(base)
                ok = sum(1 for a in assets if a.get("status") == "ok")
                print(f"[{gname}] {slug}: {ok}/{len(assets)} ok")
                time.sleep(0.8)

        disco.close()
        ctx.close()

    report.write_manifest(out_dir, run_meta, results)
    sheet = report.write_contact_sheet(out_dir, run_meta, results)
    total_files = sum(len([a for a in r.get("files", []) if a.get("file")]) for r in results)
    print(f"\nGotowe. Pozycji: {len(results)}, plików: {total_files}")
    print(f"Output: {out_dir}")
    print(f"Kontaktówka: {sheet}")
    return 0


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if argv and argv[0] == "login":
        if len(argv) < 2:
            print("Użycie: scout.py login <gallery>", file=sys.stderr)
            return 2
        return cmd_login(argv[1])

    ap = argparse.ArgumentParser(description="inspiration-scout")
    ap.add_argument("--industry", required=True, help="Branża (po angielsku lub polsku)")
    ap.add_argument("--keywords", required=True, help="Angielskie hasła, przecinkami")
    ap.add_argument("--galleries", default="", help=f"Podzbiór: {','.join(galleries.ALL)} (domyślnie wszystkie)")
    ap.add_argument("--mode", choices=["full", "section", "subpage"], default="full")
    ap.add_argument("--section", default=None, help="Typ sekcji dla --mode section (testimonials, services, form, pricing, about, features, faq)")
    ap.add_argument("--subpage", default=None, help="Ścieżka dla --mode subpage, np. /services")
    ap.add_argument("--limit", type=int, default=5, help="Maks. pozycji na galerię (domyślnie 5)")
    ap.add_argument("--depth", type=int, default=1, help="Głębokość crawlu podstron w trybie full (domyślnie 1)")
    ap.add_argument("--headful", action="store_true", help="Widoczna przeglądarka (debug)")
    args = ap.parse_args(argv)

    if args.mode == "section" and not args.section:
        ap.error("--mode section wymaga --section <typ>")
    if args.mode == "subpage" and not args.subpage:
        ap.error("--mode subpage wymaga --subpage <ścieżka>")
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
