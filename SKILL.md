---
name: inspiration-scout
description: "Po podaniu branży przeszukuje galerie inspiracji designerskich (godly.website, awwwards.com, cosmos.so, framer.com/marketplace, webflow.com/templates, dribbble.com, behance.net, pinterest.com) po angielskich hasłach i zapisuje referencje: pełnostronicowe zrzuty żywych stron z podstronami, grafiki mockupów, albo tylko wybrany typ sekcji (testimonials, formularz, usługi) lub jedną podstronę. Użyj gdy użytkownik mówi: inspiracje, znajdź inspiracje, inspiration, galerie designu, referencje dla branży, moodboard stron."
allowed-tools: Bash, Read, Write
---

# inspiration-scout

Przeszukuje galerie inspiracji wg branży i zapisuje materiał referencyjny.
Sterujesz skryptem `scout.py` (Python + Playwright). Twoja rola: zebrać brakujące
parametry, **wygenerować angielskie słowa kluczowe z branży**, dobrać tryb i
uruchomić skrypt, a na końcu pokazać wynik.

## Galerie

- **Żywe strony** (full-page screenshot + podstrony): `godly`, `awwwards`,
  `cosmos`, `framer` (szablony Framera), `webflow` (szablony Webflow).
- **Mockupy** (pobranie grafiki): `dribbble`, `behance`, `pinterest`.

Tryby `section`/`subpage` dotyczą tylko żywych stron; dla mockupów zawsze pobierana jest grafika.

## Proces

1. **Zbierz parametry.** Wymagane: branża. Opcjonalne: tryb (`full` /
   `section <typ>` / `subpage <ścieżka>`), podzbiór galerii, limit, głębokość.
   Jeśli użytkownik nie określił trybu — domyślnie `full`. Dopytaj tylko gdy
   intencja jest realnie niejasna.

2. **Wygeneruj angielskie hasła** — 2–4 trafne frazy. To Twoje zadanie, nie skryptu.
   - Z samej branży: synonimy/warianty (np. „klinika dentystyczna" →
     `dentist, dental clinic, orthodontist`).
   - Gdy użytkownik poda **styl / kolor / cechę** (minimalist, brutalist, dark mode,
     pastel, bold typography…), wpleć je w frazę **połączoną z branżą jako jedno
     hasło** — search jest tekstowy i łączy słowa logiką AND w obrębie frazy.
     Przykład: branża „dentysta" + styl „minimalist, dark" →
     `--keywords "minimalist dentist, dark dental clinic"` (NIE `"dentist, minimalist"`,
     bo osobne hasła = osobne, sumowane wyszukiwania).
   - Możesz też szukać po samym stylu/kolorze (np. `--keywords "brutalist portfolio"`),
     gdy użytkownik chce inspiracji stylistycznej bez konkretnej branży.
   - Uwaga: `godly` ignoruje hasła (feed kuratorowany) — styl/kolor tam nie filtrują.

3. **Sprawdź zależności** (raz):
   ```bash
   python3 -c "import playwright" 2>/dev/null || pip install playwright
   python3 -m playwright install chromium
   ```

4. **Uruchom** z katalogu skilla. Output ląduje w `./inspiration-output/<branża>-<data>/`
   względem bieżącego katalogu roboczego.
   ```bash
   python3 "<ścieżka>/scout.py" --industry "dental clinic" \
       --keywords "dentist,dental clinic,orthodontist" \
       --galleries godly,awwwards,framer,dribbble \
       --mode full --limit 5 --depth 1
   ```
   - Sekcja: `--mode section --section testimonials` (typy: `testimonials`,
     `services`, `form`, `pricing`, `about`, `features`, `faq`).
   - Podstrona: `--mode subpage --subpage /services`.

5. **Treść za loginem** (cosmos / dribbble / behance / pinterest): jeśli skrypt
   raportuje `login-required` / `blocked`, zaproponuj jednorazowy ręczny login:
   ```bash
   python3 "<ścieżka>/scout.py" login cosmos
   ```
   Sesja zapisuje się w `.browser-profile/` i działa przy kolejnych uruchomieniach.

6. **Pokaż wynik.** Po zakończeniu podaj ścieżkę do folderu i do `index.html`
   (kontaktówka miniatur). Zajrzyj do `manifest.json` i zwięźle podsumuj: ile
   pozycji, ile pominięć i dlaczego (statusy: `ok`, `blocked`, `login-required`,
   `section-not-found`, `no-results`, `load-failed`).

## Uwagi

- Galerie bywają kruche (anti-bot, zmiany DOM). Skrypt nie wywraca się na
  błędzie — pomija pozycję i zapisuje status. Raportuj pominięcia szczerze.
- Limity domyślne są zachowawcze (5 stron/galeria, depth 1), by nie puchło.
  Podbijaj `--limit`/`--depth` świadomie.
- Nie forsuj zabezpieczeń ponad zwykłą sesję zalogowaną.
- Pełny opis architektury: `docs/2026-06-17-design.md`.
