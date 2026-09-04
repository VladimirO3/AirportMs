from pathlib import Path
import sqlite3


DATABASE_PATH = Path(__file__).with_name("airport.db")


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database() -> None:
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS airlines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                iata_code TEXT NOT NULL UNIQUE CHECK(length(iata_code) = 2)
            );

            CREATE TABLE IF NOT EXISTS airports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                city TEXT NOT NULL,
                iata_code TEXT NOT NULL UNIQUE CHECK(length(iata_code) = 3)
            );

            CREATE TABLE IF NOT EXISTS aircrafts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model TEXT NOT NULL,
                registration_number TEXT NOT NULL UNIQUE,
                seats INTEGER NOT NULL CHECK(seats > 0)
            );

            CREATE TABLE IF NOT EXISTS flights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                flight_number TEXT NOT NULL,
                airline_id INTEGER NOT NULL REFERENCES airlines(id),
                aircraft_id INTEGER NOT NULL REFERENCES aircrafts(id),
                departure_airport_id INTEGER NOT NULL REFERENCES airports(id),
                arrival_airport_id INTEGER NOT NULL REFERENCES airports(id),
                departure_time TEXT NOT NULL,
                arrival_time TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Запланирован',
                CHECK(departure_airport_id <> arrival_airport_id),
                CHECK(arrival_time > departure_time)
            );
            """
        )

        airline_count = connection.execute(
            "SELECT COUNT(*) AS count FROM airlines"
        ).fetchone()["count"]
        if airline_count == 0:
            connection.executemany(
                "INSERT INTO airlines(name, iata_code) VALUES (?, ?)",
                [
                    ("Аэрофлот", "SU"),
                    ("S7 Airlines", "S7"),
                    ("Уральские авиалинии", "U6"),
                ],
            )
            connection.executemany(
                "INSERT INTO airports(name, city, iata_code) VALUES (?, ?, ?)",
                [
                    ("Шереметьево", "Москва", "SVO"),
                    ("Пулково", "Санкт-Петербург", "LED"),
                    ("Кольцово", "Екатеринбург", "SVX"),
                ],
            )
            connection.executemany(
                "INSERT INTO aircrafts(model, registration_number, seats) VALUES (?, ?, ?)",
                [
                    ("Airbus A320", "RA-32001", 180),
                    ("Sukhoi Superjet 100", "RA-89001", 100),
                ],
            )


def fetch_all(query: str, parameters: tuple = ()) -> list[sqlite3.Row]:
    with get_connection() as connection:
        return connection.execute(query, parameters).fetchall()


def execute(query: str, parameters: tuple = ()) -> int:
    with get_connection() as connection:
        cursor = connection.execute(query, parameters)
        return cursor.lastrowid