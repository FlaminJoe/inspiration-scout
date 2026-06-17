"""Pobieranie grafik mockupów (dribbble / behance / pinterest)."""

from __future__ import annotations

import mimetypes
from typing import List, Optional
from urllib.parse import urlparse


def _best_image_url(page) -> Optional[str]:
    """Najpewniejszy adres grafiki: og:image, w razie braku największy <img>."""
    try:
        og = page.eval_on_selector(
            "meta[property='og:image'], meta[name='og:image']",
            "el => el && el.content",
        )
        if og:
            return og
    except Exception:
        pass
    try:
        return page.evaluate(
            """() => {
                let best = null, area = 0;
                for (const img of document.images) {
                    const a = (img.naturalWidth||0) * (img.naturalHeight||0);
                    const src = img.currentSrc || img.src;
                    if (src && a > area && !src.startsWith('data:')) { area = a; best = src; }
                }
                return best;
            }"""
        )
    except Exception:
        return None


def _ext_for(url: str, content_type: str) -> str:
    path_ext = "." + url.split("?")[0].rsplit(".", 1)[-1] if "." in url.split("?")[0] else ""
    if path_ext.lower() in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        return path_ext
    guessed = mimetypes.guess_extension(content_type.split(";")[0].strip()) if content_type else None
    return guessed or ".jpg"


def download_mockup(context, item, *, out_dir: str, slug: str) -> List[dict]:
    """Zwraca listę assetów: {file, page_url, type, status}."""
    page = context.new_page()
    try:
        try:
            page.goto(item.url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(1500)
        except Exception:
            return [{"file": None, "page_url": item.url, "type": "mockup",
                     "status": "load-failed"}]

        img_url = _best_image_url(page)
        if not img_url:
            return [{"file": None, "page_url": item.url, "type": "mockup",
                     "status": "no-image-found"}]

        try:
            resp = context.request.get(img_url, timeout=30000)
            if not resp.ok:
                return [{"file": None, "page_url": item.url, "type": "mockup",
                         "status": f"download-failed:{resp.status}"}]
            body = resp.body()
            ext = _ext_for(img_url, resp.headers.get("content-type", ""))
            path = f"{out_dir}/{slug}__mockup{ext}"
            with open(path, "wb") as f:
                f.write(body)
            return [{"file": path, "page_url": item.url, "type": "mockup",
                     "status": "ok"}]
        except Exception as e:
            return [{"file": None, "page_url": item.url, "type": "mockup",
                     "status": f"download-error:{type(e).__name__}"}]
    finally:
        page.close()
