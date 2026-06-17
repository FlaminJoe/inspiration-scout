"""Adaptery galerii inspiracji.

Każda galeria ma typ ("site" — żywa strona do screenshotowania, "mockup" —
grafika do pobrania), szablon URL wyszukiwania i selektor kart wyników.

Selektory są best-effort: galerie zmieniają DOM i bywają chronione anti-botem.
Discovery jest odporne na błędy — gdy adapter nic nie znajdzie, scout.py loguje
to w manifeście i leci dalej. Po pierwszym realnym uruchomieniu selektory mogą
wymagać dostrojenia (patrz docs/2026-06-17-design.md, sekcja Testy).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import quote, urljoin, urlparse

# Hosty pomijane przy wnioskowaniu zewnętrznego linku "live" na stronie detalu.
EXCLUDE_HOSTS = {
    "twitter.com", "x.com", "facebook.com", "instagram.com", "linkedin.com",
    "youtube.com", "youtu.be", "github.com", "tiktok.com", "pinterest.com",
    "dribbble.com", "behance.net", "medium.com", "discord.com", "discord.gg",
    "apple.com", "play.google.com", "t.me", "wa.me", "mailto",
}

# Słowa, które na stronie detalu wskazują link do żywej witryny / preview.
LIVE_LINK_HINTS = ["visit", "live", "preview", "website", "view site", "open", "demo"]


@dataclass
class Item:
    gallery: str
    kind: str          # "site" | "mockup"
    url: str           # site: finalny URL żywej strony/preview; mockup: strona z grafiką
    title: str = ""
    source_url: str = ""   # URL w obrębie galerii (do linkowania w kontaktówce)
    keyword: str = ""


@dataclass
class Gallery:
    name: str
    kind: str
    search_tpl: str
    card_selector: str
    resolve: bool = False           # site: czy karta wskazuje detal galerii (two-hop)
    base: str = ""
    nav_wait_ms: int = 1800
    href_re: str = ""               # opcjonalny wzorzec walidujący href karty (odsiewa nav)
    curated: bool = False           # galeria nie filtruje po haśle (feed kuratorowany)

    def search_url(self, keyword: str) -> str:
        return self.search_tpl.format(kw=quote(keyword))

    def _valid_href(self, url: str) -> bool:
        return bool(re.search(self.href_re, url)) if self.href_re else True

    def _host(self, url: str) -> str:
        try:
            return urlparse(url).netloc.lower()
        except Exception:
            return ""

    def _gallery_host(self) -> str:
        return self._host(self.base or self.search_tpl)

    def resolve_live_url(self, page, detail_url: str) -> Optional[str]:
        """Otwiera stronę detalu galerii i wnioskuje link do żywej witryny."""
        try:
            page.goto(detail_url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(self.nav_wait_ms)
        except Exception:
            return None
        gallery_host = self._gallery_host()
        try:
            anchors = page.eval_on_selector_all(
                "a[href^='http']",
                "els => els.map(e => ({href: e.href, text: (e.textContent||'').trim().toLowerCase()}))",
            )
        except Exception:
            anchors = []

        def external(href: str) -> bool:
            host = self._host(href)
            if not host or gallery_host in host or host in gallery_host:
                return False
            return not any(bad in host for bad in EXCLUDE_HOSTS)

        # 1) link z tekstem-podpowiedzią (visit/preview/live...)
        for a in anchors:
            if external(a["href"]) and any(h in a["text"] for h in LIVE_LINK_HINTS):
                return a["href"]
        # 2) pierwszy sensowny link zewnętrzny
        for a in anchors:
            if external(a["href"]):
                return a["href"]
        return None

    def search(self, page, keyword: str, limit: int) -> List[Item]:
        url = self.search_url(keyword)
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(self.nav_wait_ms)
        except Exception:
            return []

        base = self.base or f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        try:
            raw = page.eval_on_selector_all(
                self.card_selector,
                "els => els.map(e => ({href: e.getAttribute('href'),"
                " title: (e.getAttribute('title') || e.textContent || '').trim()}))",
            )
        except Exception:
            raw = []

        seen, hrefs = set(), []
        for r in raw:
            href = r.get("href")
            if not href:
                continue
            absu = urljoin(base, href)
            if not self._valid_href(absu):
                continue
            pu = urlparse(absu)
            key = f"{pu.netloc}{pu.path}".rstrip("/")   # dedup po ścieżce (bez query)
            if key in seen:
                continue
            seen.add(key)
            hrefs.append((absu, (r.get("title") or "")[:120]))
            if len(hrefs) >= limit * 4:
                break

        items: List[Item] = []
        for href, title in hrefs:
            if len(items) >= limit:
                break
            if self.kind == "site" and self.resolve:
                live = self.resolve_live_url(page, href)
                if not live:
                    continue
                items.append(Item(self.name, "site", live, title, href, keyword))
            else:
                items.append(Item(self.name, self.kind, href, title, href, keyword))
        return items


REGISTRY = {
    # --- galerie żywych stron ---
    # godly nie ma URL-owego wyszukiwania po haśle (search jest client-side) —
    # traktujemy jako feed kuratorowany: bierzemy top pozycje, hasło nie filtruje.
    "godly": Gallery(
        "godly", "site",
        "https://godly.website/",
        "a[href*='/website/']", resolve=True, curated=True,
        base="https://godly.website", href_re=r"/website/[^/]+",
    ),
    "awwwards": Gallery(
        "awwwards", "site",
        "https://www.awwwards.com/websites/?keyword={kw}",
        "a[href*='/sites/']", resolve=True,
        base="https://www.awwwards.com", href_re=r"/sites/[^/]+",
    ),
    "cosmos": Gallery(
        "cosmos", "site",
        "https://www.cosmos.so/search?q={kw}",
        "a[href*='/e/'], a[href*='/c/']", resolve=True,
        base="https://www.cosmos.so", href_re=r"/(e|c)/[^/]+",
    ),
    "framer": Gallery(
        "framer", "site",
        "https://www.framer.com/marketplace/templates/?search={kw}",
        "a[href*='/marketplace/templates/']", resolve=True,
        base="https://www.framer.com", href_re=r"/marketplace/templates/[^/]+/[^/]+",
    ),
    "webflow": Gallery(
        "webflow", "site",
        "https://webflow.com/templates/search/{kw}",
        "a[href*='/templates/']", resolve=True,
        base="https://webflow.com", href_re=r"/templates/[^/]+/[^/]+",
    ),
    # --- galerie mockupów ---
    "dribbble": Gallery(
        "dribbble", "mockup",
        "https://dribbble.com/search/{kw}",
        "a[href*='/shots/']",
        base="https://dribbble.com", href_re=r"/shots/\d+",
    ),
    "behance": Gallery(
        "behance", "mockup",
        "https://www.behance.net/search/projects?search={kw}",
        "a[href*='/gallery/']",
        base="https://www.behance.net", href_re=r"/gallery/\d+",
    ),
    "pinterest": Gallery(
        "pinterest", "mockup",
        "https://www.pinterest.com/search/pins/?q={kw}",
        "a[href*='/pin/']",
        base="https://www.pinterest.com", href_re=r"/pin/\d+",
    ),
}

ALL = list(REGISTRY.keys())
SITE_GALLERIES = [n for n, g in REGISTRY.items() if g.kind == "site"]
MOCKUP_GALLERIES = [n for n, g in REGISTRY.items() if g.kind == "mockup"]


def get(name: str) -> Optional[Gallery]:
    return REGISTRY.get(name)
