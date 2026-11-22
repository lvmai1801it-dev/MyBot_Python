"""Catalog-driven web UI: render + consistency tests (no Qt, no webview)."""

from __future__ import annotations

import unittest

from COCbot.webui import catalog, render


class CatalogIntegrityTests(unittest.TestCase):
    """Mọi khai báo trong catalog phải renderer hiểu được."""

    def test_every_field_has_supported_type(self) -> None:
        supported = {"number", "select", "switch"}
        for tab in catalog.TABS:
            for card in tab.get("cards", []):
                for field in card.get("fields", []):
                    self.assertIn(
                        field["type"],
                        supported,
                        f"{tab['id']}/{field['name']}: "
                        f"type {field['type']!r} khong duoc render ho tro",
                    )
                    self.assertTrue(
                        field["name"], f"field thieu ten trong tab {tab['id']}"
                    )
                    if field["type"] == "select":
                        self.assertTrue(
                            field.get("options"),
                            f"{field['name']}: select thieu options",
                        )

    def test_unknown_type_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            render._field_html({"name": "x", "type": "radio", "label": "X"})

    def test_field_names_unique(self) -> None:
        seen: set[str] = set()
        for tab in catalog.TABS:
            for card in tab.get("cards", []):
                for field in card.get("fields", []):
                    name = field["name"]
                    self.assertNotIn(
                        name, seen, f"field trung ten trong catalog: {name}"
                    )
                    seen.add(name)


class RenderedPageTests(unittest.TestCase):
    """Trang sinh ra phải chứa đủ catalog và glue của bridge."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.page = render.render_page()

    def test_page_contains_every_field(self) -> None:
        for tab in catalog.TABS:
            for card in tab.get("cards", []):
                for field in card.get("fields", []):
                    self.assertIn(
                        f'data-field="{field["name"]}"',
                        self.page,
                        f'thiếu field {field["name"]}',
                    )

    def test_page_contains_tabs_and_log(self) -> None:
        for tab in catalog.TABS:
            self.assertIn(f'data-tab="{tab["id"]}"', self.page)
            self.assertIn(f'id="pane-{tab["id"]}"', self.page)
        self.assertIn('<div id="log"></div>', self.page)

    def test_page_contains_bridge_glue(self) -> None:
        for call in (
            "pywebviewready",
            "get_settings",
            "get_logs",
            "get_state",
            "api().start(collectForm())",
        ):
            self.assertIn(call, self.page)

    def test_theme_tokens_rendered(self) -> None:
        for key, value in catalog.THEME.items():
            self.assertIn(f"--{key}: {value}", self.page)

    def test_control_buttons_present(self) -> None:
        for button in catalog.CONTROL_CARD["buttons"]:
            self.assertIn(f'id="{button["id"]}"', self.page)


if __name__ == "__main__":
    unittest.main()
