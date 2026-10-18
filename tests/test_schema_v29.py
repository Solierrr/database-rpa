import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schema_v29 import USERNAME_PATTERN, slugify, unique_username, username_from  # noqa: E402


class SlugifyTest(unittest.TestCase):
    def test_removes_accents_and_symbols(self):
        self.assertEqual("mercado-bom-preco", slugify("Mercado Bom Preço"))

    def test_falls_back_when_nothing_is_left(self):
        self.assertEqual("item", slugify("***"))

    def test_respects_the_length_limit(self):
        self.assertLessEqual(len(slugify("a" * 400, 160)), 160)


class UsernameTest(unittest.TestCase):
    def test_comes_from_the_email_and_matches_the_schema_pattern(self):
        for email, name in [("joao.silva@x.com", "João"), ("carlos+teste@x.com", "Carlos"), ("z@x.com", "Zé"), (None, "Ana Maria")]:
            self.assertRegex(username_from(email, name, 7), USERNAME_PATTERN.pattern)

    def test_short_email_falls_back_to_the_legacy_id(self):
        self.assertEqual("usuario_4", username_from("z@x.com", "Zé", 4))

    def test_is_unique_inside_the_taken_set(self):
        taken = {"joao_silva"}
        self.assertEqual("joao_silva_2", unique_username(taken, "joao_silva"))
        self.assertEqual("joao_silva_3", unique_username(taken, "joao_silva"))

    def test_suffix_keeps_the_thirty_character_limit(self):
        base = "a" * 30
        taken = {base}
        self.assertLessEqual(len(unique_username(taken, base)), 30)


if __name__ == "__main__":
    unittest.main()
