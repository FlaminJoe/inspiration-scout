# inspiration-scout

Claude Code skill: po podaniu branży przeszukuje galerie inspiracji designerskich
po angielskich hasłach i zapisuje materiał referencyjny — full-page screenshoty
żywych stron (z podstronami), grafiki mockupów, albo wybrany typ sekcji / jedną
podstronę.

Status: działa. Design: `docs/2026-06-17-design.md`.

## Użycie

```bash
python3 scout.py --industry "dental clinic" --keywords "dentist,dental clinic" \
    --galleries godly,awwwards,framer,dribbble,behance --mode full --limit 5 --depth 1
python3 scout.py --industry "law firm" --keywords "law firm" --mode section --section testimonials
python3 scout.py --industry "law firm" --keywords "law firm" --mode subpage --subpage /services
python3 scout.py login cosmos     # jednorazowy ręczny login dla treści gated
```

Output: `./inspiration-output/<branża>-<data>/` (PNG/grafiki + `index.html` + `manifest.json`).

## Galerie

- Żywe strony (full-page + podstrony): `godly`, `awwwards`, `cosmos`, `framer`, `webflow`.
- Mockupy (pobranie grafiki): `dribbble`, `behance`, `pinterest`.

## Stan zweryfikowany (2026-06-17)

- **Działa po haśle**: `dribbble`, `behance` (mockupy), `webflow`, `framer` (żywe
  preview szablonów). webflow — URL search; framer — search po polu (client-side);
  oba resolvują do żywych preview (`*.webflow.io`, `*.framer.website`).
- **Kuratorowane**: `godly` — brak URL-owego wyszukiwania (search client-side), zwraca
  top live-sites niezależnie od hasła; screenshoty żywych stron działają.
- **Best-effort / może wymagać dostrojenia lub loginu**: `awwwards`, `cosmos`,
  `pinterest` — selektory/URL mogą wymagać tuningu po pierwszym realnym
  uruchomieniu; treść gated odblokuje `scout.py login <galeria>`.

Galerie bywają kruche (anti-bot, zmiany DOM). Skrypt pomija pozycję i zapisuje status
w `manifest.json` zamiast się wywracać.
