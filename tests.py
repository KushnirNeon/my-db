import unittest
from models import Database, Column, join_tables

class TestMiniDBMS(unittest.TestCase):
    def setUp(self):
        self.db = Database("TestDB")
        t1 = self.db.create_table("Users")
        t1.add_column(Column("id", "integer"))
        t1.add_column(Column("name", "string"))
        t1.add_column(Column("email", "email"))
        t1.add_row({"id": 1, "name": "Alice", "email": "alice@example.com"})
        t1.add_row({"id": 2, "name": "Bob", "email": "bob@example.com"})

        t2 = self.db.create_table("Orders")
        t2.add_column(Column("id", "integer"))
        t2.add_column(Column("user_id", "integer"))
        t2.add_column(Column("status", "enum", enum_values=["NEW", "PAID", "CANCELLED"]))
        t2.add_row({"id": 10, "user_id": 1, "status": "NEW"})
        t2.add_row({"id": 11, "user_id": 1, "status": "PAID"})
        t2.add_row({"id": 12, "user_id": 2, "status": "NEW"})

    def test_email_validation(self):
        users = self.db.get_table("Users")
        with self.subTest("reject invalid email"):
            with self.assertRaises(ValueError, msg="Очікувався ValueError для 'not-an-email'"):
                users.add_row({"id": 3, "name": "Bad", "email": "not-an-email"})
        with self.subTest("accept and edit to valid email with +tag"):
            users.edit_row(0, {"email": "alice+1@example.org"})
            self.assertEqual(users.rows[0]["email"], "alice+1@example.org", msg="Email мав оновитися")

    def test_enum_validation(self):
        orders = self.db.get_table("Orders")
        with self.subTest("reject unknown enum value"):
            with self.assertRaises(ValueError, msg="Очікувався ValueError для невідомого статусу"):
                orders.add_row({"id": 13, "user_id": 2, "status": "UNKNOWN"})
        with self.subTest("allow changing to PAID"):
            orders.edit_row(0, {"status": "PAID"})
            self.assertEqual(orders.rows[0]["status"], "PAID", msg="Статус мав стати PAID")

    def test_join_operation(self):
        users = self.db.get_table("Users")
        orders = self.db.get_table("Orders")
        users.add_column(Column("user_id", "integer"))
        for r in users.rows:
            r["user_id"] = r["id"]

        joined = join_tables(orders, users, key="user_id")
        with self.subTest("row count"):
            self.assertEqual(len(joined.rows), 3, msg="Очікувалось 3 рядки у результаті")
        with self.subTest("columns present"):
            self.assertIn("email", joined.column_names(), msg="У join має бути колонка email")
            self.assertIn("name", joined.column_names(), msg="У join має бути колонка name")

    def test_char_and_real_validation(self):
        books = self.db.create_table("Books")
        books.add_column(Column("rating", "real"))
        books.add_column(Column("grade", "char"))

        with self.subTest("accept real and single char"):
            books.add_row({"rating": "4.5", "grade": "A"})
            self.assertIsInstance(books.rows[0]["rating"], float, msg="rating має бути float")

        with self.subTest("reject non-numeric real"):
            with self.assertRaises(ValueError, msg="Очікувався ValueError для rating='abc'"):
                books.add_row({"rating": "abc", "grade": "B"})

        with self.subTest("reject char length > 1"):
            with self.assertRaises(ValueError, msg="Очікувався ValueError для grade='TooLong'"):
                books.add_row({"rating": 3.9, "grade": "TooLong"})

    def test_join_missing_key_raises(self):
        users = self.db.get_table("Users")
        orders = self.db.get_table("Orders")
        with self.assertRaises(ValueError, msg="Очікувався ValueError для unknown_key"):
            _ = join_tables(orders, users, key="unknown_key")


if __name__ == "__main__":
    unittest.main(verbosity=2)
