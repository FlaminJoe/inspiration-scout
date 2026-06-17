"""Zapis manifestu i renderowanie kontaktówki (index.html)."""

from __future__ import annotations

import html
import json
import os
from typing import List


def write_manifest(out_dir: str, run_meta: dict, results: List[dict]) -> str:
    path = os.path.join(out_dir, "manifest.json")
    data = dict(run_meta)
    data["items"] = results
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def _rel(path: str, out_dir: str) -> str:
    return os.path.relpath(path, out_dir) if path else ""


_STATUS_BADGE = {
    "ok": "#1a7f37",
    "section-not-found": "#9a6700",
}


def write_contact_sheet(out_dir: str, run_meta: dict, results: List[dict]) -> str:
    cells = []
    for item in results:
        gallery = html.escape(item.get("gallery", ""))
        kw = html.escape(item.get("keyword", ""))
        src = html.escape(item.get("source_url", ""))
        title = html.escape(item.get("title", "") or src)
        files = item.get("files", [])
        if not files:
            color = "#cf222e"
            cells.append(
                f'<figure class="cell miss"><div class="ph">brak<br><small>{html.escape(item.get("status",""))}</small></div>'
                f'<figcaption><span class="g">{gallery}</span> · {kw}<br>'
                f'<a href="{src}" target="_blank">{title}</a></figcaption></figure>'
            )
            continue
        for fa in files:
            f = fa.get("file")
            status = fa.get("status", "")
            ftype = html.escape(fa.get("type", ""))
            page_url = html.escape(fa.get("page_url", src))
            color = _STATUS_BADGE.get(status, "#57606a")
            if f and os.path.exists(f):
                thumb = f'<a href="{html.escape(_rel(f, out_dir))}" target="_blank">' \
                        f'<img loading="lazy" src="{html.escape(_rel(f, out_dir))}"></a>'
            else:
                thumb = f'<div class="ph">brak<br><small>{html.escape(status)}</small></div>'
            cells.append(
                f'<figure class="cell"><div class="thumb">{thumb}</div>'
                f'<figcaption><span class="g">{gallery}</span> · {kw} '
                f'<span class="badge" style="background:{color}">{ftype} · {html.escape(status)}</span><br>'
                f'<a href="{page_url}" target="_blank">{title}</a> · '
                f'<a href="{src}" target="_blank">źródło</a></figcaption></figure>'
            )

    industry = html.escape(run_meta.get("industry", ""))
    generated = html.escape(run_meta.get("generated_at", ""))
    mode = html.escape(run_meta.get("mode", ""))
    kws = html.escape(", ".join(run_meta.get("keywords", [])))

    doc = f"""<!doctype html><html lang="pl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Inspiracje: {industry}</title>
<style>
:root{{color-scheme:light dark}}
*{{box-sizing:border-box}}
body{{font:15px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;margin:0;padding:24px;background:#f6f8fa;color:#1f2328}}
@media(prefers-color-scheme:dark){{body{{background:#0d1117;color:#e6edf3}}.cell{{background:#161b22}}}}
header{{margin-bottom:20px}}
h1{{margin:0 0 4px;font-size:22px}}
.meta{{color:#57606a;font-size:13px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px}}
.cell{{background:#fff;border:1px solid #d0d7de;border-radius:10px;overflow:hidden}}
.thumb,.ph{{aspect-ratio:16/10;background:#eaeef2;display:flex;align-items:center;justify-content:center;overflow:hidden}}
.ph{{color:#57606a;text-align:center;font-size:13px}}
.thumb img{{width:100%;height:100%;object-fit:cover;object-position:top;display:block}}
figcaption{{padding:10px 12px;font-size:12.5px}}
.g{{font-weight:600;text-transform:capitalize}}
.badge{{color:#fff;border-radius:6px;padding:1px 6px;font-size:11px}}
a{{color:#0969da;text-decoration:none}}a:hover{{text-decoration:underline}}
</style></head><body>
<header><h1>Inspiracje — {industry}</h1>
<div class="meta">tryb: {mode} · hasła: {kws} · wygenerowano: {generated} · pozycji: {len(results)}</div></header>
<div class="grid">{''.join(cells)}</div>
</body></html>"""

    path = os.path.join(out_dir, "index.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(doc)
    return path
