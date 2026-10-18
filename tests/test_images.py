import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from images import ImageCatalog, load_catalog  # noqa: E402

ASSETS = [
    {"id": "a", "category": "users/pfp/clients"},
    {"id": "b", "category": "users/pfp/clients", "attributes": {"crop": {"x": 1, "y": 2, "width": 3, "height": 4}}},
    {"id": "c", "category": "products/solar-panels/hero"},
]


class ImageCatalogTest(unittest.TestCase):
    def setUp(self):
        self.catalog = ImageCatalog(ASSETS, "demo", "mocks")

    def test_pick_is_deterministic_per_key(self):
        self.assertEqual(self.catalog.pick("users/pfp/clients", "k1"), self.catalog.pick("users/pfp/clients", "k1"))

    def test_pick_returns_none_for_unknown_category(self):
        self.assertIsNone(self.catalog.pick("nope", "k1"))

    def test_offset_walks_through_the_category(self):
        picked = {self.catalog.pick("users/pfp/clients", "k1", offset) for offset in range(2)}
        self.assertEqual({"a", "b"}, picked)

    def test_url_and_public_id_use_the_prefix(self):
        self.assertEqual("https://res.cloudinary.com/demo/image/upload/mocks/a.webp", self.catalog.url("a"))
        self.assertEqual("mocks/a", self.catalog.public_id("a"))

    def test_crop_columns_always_have_the_four_columns(self):
        self.assertEqual({"crop_x": None, "crop_y": None, "crop_width": None, "crop_height": None}, self.catalog.crop_columns("a"))
        self.assertEqual(1, self.catalog.crop_columns("b")["crop_x"])


class LoadCatalogTest(unittest.TestCase):
    def test_is_skipped_without_the_cloud_name(self):
        self.assertIsNone(load_catalog({}))

    def test_is_skipped_when_the_manifest_is_missing(self):
        self.assertIsNone(load_catalog({"CLOUDINARY_CLOUD_NAME": "demo", "MOCKS_MANIFEST": "nao-existe.json"}))


if __name__ == "__main__":
    unittest.main()
