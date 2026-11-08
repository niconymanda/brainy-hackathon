import unittest
from datetime import date

from brainy.agent.route import (
    DayConstraint,
    _slot_date,
    doctolib_url,
    has_specialty,
    parse_day_constraint,
)


class DoctolibRouteTests(unittest.TestCase):
    def test_common_specialty_slugs(self):
        cases = {
            "dermatologue": "dermatologue",
            "dentiste": "dentiste",
            "médecin généraliste": "medecin-generaliste",
            "ophtalmologue": "ophtalmologue",
            "gynécologue": "gynecologue",
            "kiné": "masseur-kinesitherapeute",
            "pédiatre": "pediatre",
            "ORL": "orl",
            "psychiatre": "psychiatre",
            "psychologue": "psychologue",
            "ostéopathe": "osteopathe",
            "cardiologue": "cardiologue",
        }
        for specialty, slug in cases.items():
            with self.subTest(specialty=specialty):
                self.assertEqual(doctolib_url(f"Un rendez-vous avec un {specialty}"),
                                 f"https://www.doctolib.fr/{slug}/paris")

    def test_specialty_boundaries_and_arrondissement(self):
        self.assertIsNone(doctolib_url("Je cherche un bikini"))
        self.assertFalse(has_specialty("un mannequin"))
        self.assertEqual(doctolib_url("Je veux un dentiste dans le 11e"),
                         "https://www.doctolib.fr/dentiste/paris-75011")
        self.assertEqual(doctolib_url("un kine dans le 9e"),
                         "https://www.doctolib.fr/masseur-kinesitherapeute/paris-75009")

    def test_parses_explicit_and_relative_days(self):
        today = date(2026, 11, 8)
        self.assertTrue(parse_day_constraint("demain", today).matches(date(2026, 11, 9)))
        self.assertFalse(parse_day_constraint("aujourd'hui", today).matches(date(2026, 11, 9)))
        self.assertTrue(parse_day_constraint("lundi", today).matches(date(2026, 11, 9)))
        self.assertTrue(parse_day_constraint("9 novembre", today).matches(date(2026, 11, 9)))
        self.assertTrue(parse_day_constraint("le 12", today).matches(date(2026, 11, 12)))
        self.assertTrue(parse_day_constraint("cette semaine", today).matches(date(2026, 11, 12)))
        self.assertTrue(parse_day_constraint("la semaine prochaine", today).matches(date(2026, 11, 15)))

    def test_day_constraint_intersects_week_and_weekday(self):
        constraint = DayConstraint(
            weekdays={0},
            periods=[(date(2026, 11, 9), date(2026, 11, 15))],
        )
        self.assertTrue(constraint.matches(date(2026, 11, 9)))
        self.assertFalse(constraint.matches(date(2026, 11, 16)))

    def test_extracts_selected_slot_date(self):
        metadata = {
            "href": "https://www.doctolib.fr/booking?selected_slot=2026-11-10T11%3A00%3A00.000%2B01%3A00",
            "attributes": "",
            "context": "",
        }
        self.assertEqual(_slot_date(metadata, date(2026, 11, 8)), date(2026, 11, 10))


class SlotDateTests(unittest.TestCase):
    def test_abbreviated_column_date_from_accessible_name(self):
        metadata = {"href": "", "labelled": "jeudi\n12 nov. Rendez-vous assuré par un remplaçant : Dr. B",
                    "attributes": "", "context": "dimanche\n8 nov.\n—\njeudi\n12 nov.\n09:30"}
        self.assertEqual(_slot_date(metadata, date(2026, 11, 8)), date(2026, 11, 12))

    def test_full_month_names_still_parse(self):
        metadata = {"href": "", "attributes": "", "context": "lundi 1er février"}
        self.assertEqual(_slot_date(metadata, date(2026, 11, 8)), date(2027, 2, 1))
