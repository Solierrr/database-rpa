import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from id_mapping import IdMapping  # noqa: E402


class IdMappingTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.directory.name, "mapping.sqlite")
        self.mapping = IdMapping(self.path)

    def tearDown(self):
        self.directory.cleanup()

    def test_pending_entries_are_visible_before_the_flush(self):
        self.mapping.save("usuario", 1, "person", "p-1")
        self.assertEqual("p-1", self.mapping.get("usuario", 1, "person"))
        self.assertEqual(set(), self.mapping.origin_ids("usuario", "person"))

    def test_flush_persists_across_instances(self):
        self.mapping.save("usuario", 1, "person", "p-1")
        self.mapping.flush()
        reopened = IdMapping(self.path)
        self.assertEqual("p-1", reopened.get("usuario", 1, "person"))
        self.assertEqual({1}, reopened.origin_ids("usuario", "person"))

    def test_discard_drops_what_was_not_flushed(self):
        self.mapping.save("usuario", 1, "person", "p-1")
        self.mapping.discard()
        self.mapping.flush()
        self.assertIsNone(IdMapping(self.path).get("usuario", 1, "person"))

    def test_first_value_wins(self):
        self.mapping.save("usuario", 1, "person", "p-1")
        self.mapping.save("usuario", 1, "person", "p-2")
        self.mapping.flush()
        self.mapping.save("usuario", 1, "person", "p-3")
        self.mapping.flush()
        self.assertEqual("p-1", self.mapping.get("usuario", 1, "person"))

    def test_destination_ids_are_distinct_and_scoped(self):
        self.mapping.save("produto", 1, "model", "m-1")
        self.mapping.save("produto", 2, "model", "m-1")
        self.mapping.save("produto", 3, "model", "m-2")
        self.mapping.save("produto", 3, "offer", "o-1")
        self.mapping.flush()
        self.assertEqual(["m-1", "m-2"], self.mapping.destination_ids("produto", "model"))

    def test_destination_ids_are_stored_as_text(self):
        self.mapping.save("usuario", 1, "person", 123)
        self.mapping.flush()
        self.assertEqual("123", self.mapping.get("usuario", 1, "person"))


if __name__ == "__main__":
    unittest.main()
