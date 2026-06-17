"""Unit testy czystych funkcji (bez Playwrighta / sieci).

Uruchom z katalogu skilla:  python3 -m unittest discover -s tests
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import galleries          # noqa: E402
import capture            # noqa: E402
import download           # noqa: E402
import report             # noqa: E402
import scout              # noqa: E402


class TestGalleries(unittest.TestCase):
    def test_registry_kinds(self):
        self.assertEqual(set(galleries.SITE_GALLERIES),
                         {"godly", "awwwards", "cosmos", "framer", "webflow"})
        self.assertEqual(set(galleries.MOCKUP_GALLERIES),
                         {"dribbble", "behance", "pinterest"})

    def test_all_has_eight(self):
        self.assertEqual(len(galleries.ALL), 8)

    def test_search_url_quoting(self):
        g = galleries.get("behance")
        self.assertEqual(g.search_url("dental clinic"),
                         "https://www.behance.net/search/projects?search=dental%20clinic")

    def test_search_url_all_galleries(self):
        for name in galleries.ALL:
            g = galleries.get(name)
            url = g.search_url("law firm")
            self.assertTrue(url.startswith("http"))
            if not g.curated:   # kuratorowane (godly) nie wstawiają hasła do URL
                self.assertIn("law", url)

    def test_href_validation(self):
        self.assertTrue(galleries.get("dribbble")._valid_href("https://dribbble.com/shots/123-foo"))
        self.assertFalse(galleries.get("dribbble")._valid_href("https://dribbble.com/shots/popular"))

    def test_get_unknown(self):
        self.assertIsNone(galleries.get("nope"))


class TestSlugify(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(scout.slugify("Dental Clinic!"), "dental-clinic")

    def test_empty_fallback(self):
        self.assertEqual(scout.slugify(""), "item")

    def test_maxlen(self):
        self.assertLessEqual(len(scout.slugify("x" * 200, maxlen=20)), 20)


class TestCaptureConstants(unittest.TestCase):
    def test_section_keywords(self):
        for key in ("testimonials", "services", "form", "pricing"):
            self.assertIn(key, capture.SECTION_KEYWORDS)
            self.assertTrue(capture.SECTION_KEYWORDS[key])


class TestDownloadExt(unittest.TestCase):
    def test_ext_from_url(self):
        self.assertEqual(download._ext_for("https://x/y/a.png?v=2", ""), ".png")

    def test_ext_from_content_type(self):
        self.assertEqual(download._ext_for("https://x/y/img", "image/jpeg"), ".jpg")

    def test_ext_default(self):
        self.assertEqual(download._ext_for("https://x/y/img", ""), ".jpg")


class TestReport(unittest.TestCase):
    def _results(self):
        return [
            {"gallery": "godly", "kind": "site", "source_url": "https://godly.website/websites/x",
             "live_url": "https://x.com", "keyword": "dentist", "title": "X Studio",
             "status": "ok",
             "files": [{"file": None, "page_url": "https://x.com", "type": "home", "status": "ok"}]},
            {"gallery": "dribbble", "kind": "mockup", "source_url": "https://dribbble.com/shots/1",
             "keyword": "dentist", "title": "Shot", "status": "no-image-found", "files": []},
        ]

    def test_manifest_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            meta = {"industry": "dental", "keywords": ["dentist"], "mode": "full",
                    "generated_at": "2026-06-17T10:00:00"}
            path = report.write_manifest(d, meta, self._results())
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(data["industry"], "dental")
            self.assertEqual(len(data["items"]), 2)

    def test_contact_sheet_renders(self):
        with tempfile.TemporaryDirectory() as d:
            meta = {"industry": "dental", "keywords": ["dentist"], "mode": "full",
                    "generated_at": "2026-06-17T10:00:00"}
            path = report.write_contact_sheet(d, meta, self._results())
            with open(path, encoding="utf-8") as f:
                html = f.read()
            self.assertIn("Inspiracje", html)
            self.assertIn("godly", html)
            self.assertIn("no-image-found", html)  # status pominięcia widoczny


if __name__ == "__main__":
    unittest.main()
