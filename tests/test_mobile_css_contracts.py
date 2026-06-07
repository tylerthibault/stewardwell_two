import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = (ROOT / "src/static/css/galactic-opera.css").read_text()
PARENT_CHORES = (ROOT / "src/templates/private/parents/chores/index.html").read_text()


def css_rule(selector: str) -> str:
    match = re.search(rf"{re.escape(selector)}\s*\{{(?P<body>.*?)\}}", CSS, re.DOTALL)
    if not match:
        return ""
    return match.group("body")


def media_rule(query: str, selector: str) -> str:
    matches = re.finditer(rf"@media\s*\({re.escape(query)}\)\s*\{{(?P<body>.*?)\n\}}", CSS, re.DOTALL)
    for media in matches:
        match = re.search(rf"{re.escape(selector)}\s*\{{(?P<body>.*?)\}}", media.group("body"), re.DOTALL)
        if match:
            return match.group("body")
    return ""


class MobileCssContractsTest(unittest.TestCase):
    def test_chore_modal_grid_rules_come_after_generic_row_breakpoints(self):
        last_generic_row_breakpoint = CSS.rfind(".row { grid-template-columns")
        last_chore_grid_rule = CSS.rfind(".chore-create-basics-grid")
        self.assertGreater(last_chore_grid_rule, last_generic_row_breakpoint)

    def test_parent_chore_create_modal_grid_stacks_on_mobile_and_expands_on_desktop(self):
        self.assertNotIn(
            'style="grid-template-columns: repeat(4, minmax(0, 1fr)); align-items: end;"',
            PARENT_CHORES,
        )
        self.assertIn("chore-create-basics-grid", PARENT_CHORES)
        self.assertIn("grid-template-columns: 1fr", css_rule(".chore-create-basics-grid"))
        self.assertIn(
            "grid-template-columns: repeat(2, minmax(0, 1fr))",
            media_rule("min-width: 700px", ".chore-create-basics-grid"),
        )
        self.assertIn(
            "grid-template-columns: repeat(4, minmax(0, 1fr))",
            media_rule("min-width: 960px", ".chore-create-basics-grid"),
        )

    def test_parent_chore_schedule_weeks_are_one_column_on_phones_two_on_wider_screens(self):
        self.assertNotIn(
            'style="grid-template-columns: repeat(2, minmax(0, 1fr));"',
            PARENT_CHORES,
        )
        self.assertIn("chore-schedule-week-grid", PARENT_CHORES)
        self.assertIn("grid-template-columns: 1fr", css_rule(".chore-schedule-week-grid"))
        self.assertIn(
            "grid-template-columns: repeat(2, minmax(0, 1fr))",
            media_rule("min-width: 700px", ".chore-schedule-week-grid"),
        )


if __name__ == "__main__":
    unittest.main()
