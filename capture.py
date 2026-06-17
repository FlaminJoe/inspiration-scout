"""Capture żywych stron: full-page, crawl podstron, targetowanie sekcji."""

from __future__ import annotations

import re
from typing import List, Optional
from urllib.parse import urljoin, urlparse

# Słowa kluczowe typów sekcji (do wnioskowania z treści w trybie --mode section).
SECTION_KEYWORDS = {
    "testimonials": ["testimonial", "testimonials", "reviews", "review",
                     "what our clients", "what people say", "kind words",
                     "loved by", "opinie", "co mówią"],
    "services": ["services", "service", "what we do", "our services",
                 "offerings", "offer", "usługi", "co robimy", "oferta"],
    "form": ["contact", "contact us", "get in touch", "form", "kontakt",
             "let's talk", "get started", "request a quote"],
    "pricing": ["pricing", "plans", "price", "pricing plans", "cennik"],
    "about": ["about", "about us", "our story", "who we are", "o nas"],
    "features": ["features", "feature", "capabilities", "benefits", "funkcje"],
    "faq": ["faq", "frequently asked", "questions", "pytania"],
}

# Typowe ścieżki podstron dla fallbacku w trybie section/subpage.
SECTION_SUBPATHS = {
    "services": ["/services", "/offer", "/what-we-do"],
    "about": ["/about", "/about-us", "/o-nas"],
    "form": ["/contact", "/contact-us", "/kontakt"],
    "pricing": ["/pricing", "/plans", "/cennik"],
    "faq": ["/faq", "/help"],
}

COOKIE_BUTTON_TEXTS = [
    "Accept all", "Accept All", "Accept", "I agree", "Agree", "Got it",
    "Allow all", "Allow cookies", "OK", "Zgadzam się", "Akceptuj", "Akceptuję",
]

_JS_FIND_SECTION = """
(keywords) => {
  const kw = keywords.map(k => k.toLowerCase());
  const match = (t) => { t = (t || '').toLowerCase(); return kw.some(k => t.includes(k)); };
  const ascend = (node) => {
    let el = node;
    while (el && el.parentElement) {
      const tag = el.tagName.toLowerCase();
      const r = el.getBoundingClientRect();
      if (tag === 'section' || el.getAttribute('role') === 'region' || r.height > 280) return el;
      el = el.parentElement;
    }
    return node;
  };
  // 1) kotwica po id/name/data-section
  for (const k of kw) {
    const byId = document.getElementById(k)
      || document.querySelector(`[id*="${k}"],[name*="${k}"],[data-section*="${k}"]`);
    if (byId) return ascend(byId);
  }
  // 2) nagłówki
  for (const h of document.querySelectorAll('h1,h2,h3,h4')) {
    if (match(h.textContent)) return ascend(h);
  }
  return null;
}
"""


def dismiss_overlays(page) -> None:
    """Best-effort zamknięcie bannerów cookie / popupów."""
    for txt in COOKIE_BUTTON_TEXTS:
        try:
            btn = page.get_by_role("button", name=re.compile(rf"^{re.escape(txt)}$", re.I))
            if btn.count() and btn.first.is_visible():
                btn.first.click(timeout=1500)
                page.wait_for_timeout(400)
                return
        except Exception:
            continue


def _settle(page) -> None:
    try:
        page.wait_for_load_state("networkidle", timeout=8000)
    except Exception:
        pass
    # lazy-load: przewiń w dół i z powrotem, żeby doładować obrazy
    try:
        page.evaluate("() => new Promise(r => { let y=0; const t=setInterval(()=>{"
                      "window.scrollBy(0, window.innerHeight); y+=window.innerHeight;"
                      "if (y >= document.body.scrollHeight) { clearInterval(t); "
                      "window.scrollTo(0,0); setTimeout(r, 400);} }, 200); })")
    except Exception:
        pass


def full_page_screenshot(page, path: str) -> bool:
    try:
        page.screenshot(path=path, full_page=True)
        return True
    except Exception:
        return False


def _internal_links(page, base_url: str, limit: int) -> List[str]:
    host = urlparse(base_url).netloc.lower()
    try:
        hrefs = page.eval_on_selector_all(
            "a[href]", "els => els.map(e => e.getAttribute('href'))"
        )
    except Exception:
        hrefs = []
    out, seen = [], set()
    for h in hrefs or []:
        if not h or h.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        absu = urljoin(base_url, h).split("#")[0].rstrip("/")
        if urlparse(absu).netloc.lower() != host:
            continue
        if absu == base_url.rstrip("/") or absu in seen:
            continue
        if re.search(r"\.(pdf|zip|jpg|png|svg|mp4|webp)$", absu, re.I):
            continue
        seen.add(absu)
        out.append(absu)
        if len(out) >= limit:
            break
    return out


def _goto(page, url: str) -> bool:
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        dismiss_overlays(page)
        _settle(page)
        return True
    except Exception:
        return False


def capture_section(page, section_type: str, path: str) -> bool:
    """Zrzut pojedynczej sekcji wywnioskowanej z treści. False = nie znaleziono."""
    keywords = SECTION_KEYWORDS.get(section_type, [section_type])
    try:
        handle = page.evaluate_handle(_JS_FIND_SECTION, keywords)
        el = handle.as_element()
        if not el:
            return False
        el.scroll_into_view_if_needed(timeout=3000)
        page.wait_for_timeout(400)
        el.screenshot(path=path)
        return True
    except Exception:
        return False


def capture_site(context, item, *, mode: str, depth: int, section: Optional[str],
                 subpage: Optional[str], out_dir: str, slug: str) -> List[dict]:
    """Zwraca listę assetów: {file, page_url, type, status}."""
    page = context.new_page()
    assets: List[dict] = []
    try:
        if not _goto(page, item.url):
            return [{"file": None, "page_url": item.url, "type": "home",
                     "status": "load-failed"}]

        if mode == "section" and section:
            f = f"{out_dir}/{slug}__section-{section}.png"
            if capture_section(page, section, f):
                assets.append({"file": f, "page_url": item.url,
                               "type": f"section:{section}", "status": "ok"})
            else:
                # fallback 1: typowa podstrona
                done = False
                for sub in SECTION_SUBPATHS.get(section, []):
                    cand = urljoin(item.url, sub)
                    if _goto(page, cand):
                        sf = f"{out_dir}/{slug}__{section}-subpage.png"
                        if full_page_screenshot(page, sf):
                            assets.append({"file": sf, "page_url": cand,
                                           "type": f"section:{section}:subpage-fallback",
                                           "status": "ok"})
                            done = True
                            break
                if not done:
                    # fallback 2: full-page + log
                    _goto(page, item.url)
                    ff = f"{out_dir}/{slug}__full.png"
                    full_page_screenshot(page, ff)
                    assets.append({"file": ff, "page_url": item.url,
                                   "type": "home", "status": "section-not-found"})
            return assets

        if mode == "subpage" and subpage:
            cand = urljoin(item.url, subpage)
            if _goto(page, cand):
                sf = f"{out_dir}/{slug}__subpage.png"
                if full_page_screenshot(page, sf):
                    assets.append({"file": sf, "page_url": cand,
                                   "type": "subpage", "status": "ok"})
            else:
                assets.append({"file": None, "page_url": cand,
                               "type": "subpage", "status": "load-failed"})
            return assets

        # mode == "full"
        hf = f"{out_dir}/{slug}__full.png"
        if full_page_screenshot(page, hf):
            assets.append({"file": hf, "page_url": item.url,
                           "type": "home", "status": "ok"})
        if depth >= 1:
            for i, link in enumerate(_internal_links(page, item.url, limit=4)):
                if _goto(page, link):
                    lf = f"{out_dir}/{slug}__sub{i + 1}.png"
                    if full_page_screenshot(page, lf):
                        assets.append({"file": lf, "page_url": link,
                                       "type": "subpage", "status": "ok"})
        return assets
    finally:
        page.close()
