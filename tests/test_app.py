import tempfile
import unittest
from pathlib import Path

import database
from help_window import HELP_TOPICS
from login_window import validate_credentials
from reports import (
    report_aircrafts,
    report_airlines,
    report_airports,
    report_employees,
    report_flight_statuses,
    report_passengers,
    report_schedule,
    report_tickets,
)
from tabs.common import sort_rows
from tabs.flights_tab import validate_flight_times


class LoginTests(unittest.TestCase):
    def test_default_credentials_are_valid(self) -> None:
        self.assertTrue(validate_credentials("admin", "admin"))

    def test_invalid_credentials_are_rejected(self) -> None:
        self.assertFalse(validate_credentials("admin", "wrong"))
        self.assertFalse(validate_credentials("dispatcher", "admin"))


class DatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()
        self.original_database_path = database.DATABASE_PATH
        database.DATABASE_PATH = Path(self.temp_directory.name) / "test.db"
        database.initialize_database()

    def tearDown(self) -> None:
        database.DATABASE_PATH = self.original_database_path
        self.temp_directory.cleanup()

    def test_add_airline_and_airport(self) -> None:
        database.add_airline("Тестовая авиакомпания", "TA")
        database.add_airport("Тестовый аэропорт", "Тестовый город", "TST")

        self.assertTrue(
            any(row["iata_code"] == "TA" for row in database.list_airlines())
        )
        self.assertTrue(
            any(row["iata_code"] == "TST" for row in database.list_airports())
        )

    def test_reports_return_rows(self) -> None:
        self.assertTrue(report_schedule())
        self.assertTrue(report_airlines())
        self.assertTrue(report_airports())
        self.assertTrue(report_aircrafts())
        self.assertTrue(report_passengers())
        self.assertTrue(report_employees())
        self.assertTrue(report_tickets())
        self.assertTrue(report_flight_statuses())

    def test_create_passenger_employee_and_ticket(self) -> None:
        passenger_id = database.add_passenger(
            "Иван Иванов", "1234 567890", "+79990000000", "ivan@example.com"
        )
        employee_id = database.add_employee("Анна Петрова", "Диспетчер")
        self.assertGreater(passenger_id, 0)
        self.assertGreater(employee_id, 0)
        flight_id = database.list_ticket_flight_references()[0]["id"]
        ticket_id = database.add_ticket(
            "T-90001", passenger_id, flight_id, "12A", "Забронирован", 2500
        )
        self.assertGreater(ticket_id, 0)
        self.assertTrue(
            any(row["ticket_number"] == "T-90001" for row in database.list_tickets())
        )

    def test_duplicate_ticket_number_is_rejected(self) -> None:
        passenger_id = database.add_passenger("Пётр Сидоров", "9876 543210")
        flight_id = database.list_ticket_flight_references()[0]["id"]
        database.add_ticket(
            "T-20001", passenger_id, flight_id, "14B", "Оплачен", 3000
        )
        self.assertTrue(database.ticket_number_exists("T-20001"))
        with self.assertRaises(database.DatabaseError):
            database.add_ticket(
                "T-20001", passenger_id, flight_id, "14C", "Оплачен", 3000
            )


class ValidationTests(unittest.TestCase):
    def test_flight_time_validation(self) -> None:
        self.assertEqual(
            validate_flight_times("2026-09-06 10:00", "2026-09-06 12:00"),
            (True, None),
        )
        valid, error = validate_flight_times(
            "2026-09-06 12:00", "2026-09-06 10:00"
        )
        self.assertFalse(valid)
        self.assertIn("позже", error)


class SortingTests(unittest.TestCase):
    def test_sorting_rows_ascending_and_descending(self) -> None:
        rows = [("SU-20", "Аэрофлот"), ("SU-3", "Аэрофлот"), ("DP-1", "Победа")]
        self.assertEqual(
            sort_rows(rows, 0),
            [("DP-1", "Победа"), ("SU-20", "Аэрофлот"), ("SU-3", "Аэрофлот")],
        )
        self.assertEqual(
            sort_rows(rows, 1, descending=True),
            [("DP-1", "Победа"), ("SU-20", "Аэрофлот"), ("SU-3", "Аэрофлот")],
        )


class HelpTests(unittest.TestCase):
    def test_help_topics_are_available(self) -> None:
        self.assertIn("Рейсы", HELP_TOPICS)
        self.assertIn("Отчеты и печать", HELP_TOPICS)


if __name__ == "__main__":
    unittest.main()
