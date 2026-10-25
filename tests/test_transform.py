import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("ORIGEM_DB_URL", "postgresql://unused")
os.environ.setdefault("DESTINO_DB_URL", "postgresql://unused")

try:
    import pandas as pd
    from transform import transformar
except ImportError:
    pd = None


@unittest.skipIf(pd is None, "pandas and faker are not installed")
class TransformTest(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame([
            {"id": 7, "nome": "Joao Silva", "email": "joao.silva@x.com", "senha": "x", "tipo_usuario": "client", "raio_procura_km": 10},
        ])

    def test_uses_the_new_key_names(self):
        row = transformar(self.df).iloc[0]
        self.assertIn("user_id", row.index)
        self.assertNotIn("users_id", row.index)
        self.assertEqual(7, row["id_origem"])

    def test_generates_a_distinct_auth_id_per_user(self):
        row = transformar(self.df).iloc[0]
        self.assertNotEqual(row["user_id"], row["auth_id"])
        self.assertEqual(36, len(row["auth_id"]))

    def test_is_deterministic_for_mocked_fields(self):
        first, second = transformar(self.df).iloc[0], transformar(self.df).iloc[0]
        self.assertEqual(first["cpf"], second["cpf"])
        self.assertEqual(first["birth_date"], second["birth_date"])

    def test_empty_input_is_returned_as_is(self):
        self.assertTrue(transformar(self.df.iloc[0:0]).empty)


if __name__ == "__main__":
    unittest.main()
