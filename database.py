# Path помогает сформировать путь к базе рядом с этим файлом.
from pathlib import Path
# sqlite3 предоставляет встроенную работу с базой SQLite.
import sqlite3


# Файл базы хранится в корне проекта рядом с database.py.
DATABASE_PATH = Path(__file__).with_name("airport.db")
SCHEMA_VERSION = 1


def get_connection() -> sqlite3.Connection:
    # Открываем соединение с локальной базой данных.
    connection = sqlite3.connect(DATABASE_PATH)
    # Строки результата можно получать по именам столбцов, а не только по индексам.
    connection.row_factory = sqlite3.Row
    # Включаем проверку внешних ключей для текущего соединения.
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database() -> None:
    with get_connection() as connection:
        if connection.execute("PRAGMA user_version").fetchone()[0] == 0:
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(airports)")
            }
            if "city" in columns:
                _migrate_to_third_normal_form(connection)
            else:
                _create_normalized_schema(connection)
            connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

        _insert_seed_data(connection)


def _create_normalized_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS airlines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            iata_code TEXT NOT NULL UNIQUE CHECK(length(iata_code) = 2)
        );

        CREATE TABLE IF NOT EXISTS cities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS airports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            city_id INTEGER NOT NULL REFERENCES cities(id),
            iata_code TEXT NOT NULL UNIQUE CHECK(length(iata_code) = 3),
            UNIQUE(name, city_id)
        );

        CREATE TABLE IF NOT EXISTS aircraft_models (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS aircrafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_id INTEGER NOT NULL REFERENCES aircraft_models(id),
            registration_number TEXT NOT NULL UNIQUE,
            seats INTEGER NOT NULL CHECK(seats > 0)
        );

        CREATE TABLE IF NOT EXISTS flight_statuses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
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
            status_id INTEGER NOT NULL REFERENCES flight_statuses(id),
            CHECK(departure_airport_id <> arrival_airport_id),
            CHECK(arrival_time > departure_time)
        );
        """
    )


def _migrate_to_third_normal_form(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA foreign_keys = OFF")
    connection.executescript(
        """
        CREATE TABLE cities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );
        INSERT INTO cities(name) SELECT DISTINCT city FROM airports;

        CREATE TABLE aircraft_models (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );
        INSERT INTO aircraft_models(name) SELECT DISTINCT model FROM aircrafts;

        CREATE TABLE flight_statuses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );
        INSERT INTO flight_statuses(name)
        SELECT DISTINCT status FROM flights;
        INSERT OR IGNORE INTO flight_statuses(name) VALUES ('Запланирован');

        CREATE TABLE airports_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            city_id INTEGER NOT NULL REFERENCES cities(id),
            iata_code TEXT NOT NULL UNIQUE CHECK(length(iata_code) = 3),
            UNIQUE(name, city_id)
        );
        INSERT INTO airports_new(id, name, city_id, iata_code)
        SELECT a.id, a.name, c.id, a.iata_code
        FROM airports a JOIN cities c ON c.name = a.city;
        DROP TABLE airports;
        ALTER TABLE airports_new RENAME TO airports;

        CREATE TABLE aircrafts_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_id INTEGER NOT NULL REFERENCES aircraft_models(id),
            registration_number TEXT NOT NULL UNIQUE,
            seats INTEGER NOT NULL CHECK(seats > 0)
        );
        INSERT INTO aircrafts_new(id, model_id, registration_number, seats)
        SELECT a.id, m.id, a.registration_number, a.seats
        FROM aircrafts a JOIN aircraft_models m ON m.name = a.model;
        DROP TABLE aircrafts;
        ALTER TABLE aircrafts_new RENAME TO aircrafts;

        CREATE TABLE flights_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            flight_number TEXT NOT NULL,
            airline_id INTEGER NOT NULL REFERENCES airlines(id),
            aircraft_id INTEGER NOT NULL REFERENCES aircrafts(id),
            departure_airport_id INTEGER NOT NULL REFERENCES airports(id),
            arrival_airport_id INTEGER NOT NULL REFERENCES airports(id),
            departure_time TEXT NOT NULL,
            arrival_time TEXT NOT NULL,
            status_id INTEGER NOT NULL REFERENCES flight_statuses(id),
            CHECK(departure_airport_id <> arrival_airport_id),
            CHECK(arrival_time > departure_time)
        );
        INSERT INTO flights_new(
            id, flight_number, airline_id, aircraft_id,
            departure_airport_id, arrival_airport_id,
            departure_time, arrival_time, status_id
        )
        SELECT f.id, f.flight_number, f.airline_id, f.aircraft_id,
               f.departure_airport_id, f.arrival_airport_id,
               f.departure_time, f.arrival_time, s.id
        FROM flights f JOIN flight_statuses s ON s.name = f.status;
        DROP TABLE flights;
        ALTER TABLE flights_new RENAME TO flights;
        """
    )
    connection.execute("PRAGMA foreign_keys = ON")


def _insert_seed_data(connection: sqlite3.Connection) -> None:
    # Начальные записи помогают сразу увидеть работающий интерфейс после запуска.
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
            "INSERT INTO cities(name) VALUES (?)",
            [("Москва",), ("Санкт-Петербург",), ("Екатеринбург",)],
        )
        connection.executemany(
            "INSERT INTO airports(name, city_id, iata_code) VALUES (?, ?, ?)",
            [
                ("Шереметьево", 1, "SVO"),
                ("Пулково", 2, "LED"),
                ("Кольцово", 3, "SVX"),
            ],
        )
        connection.executemany(
            "INSERT INTO aircraft_models(name) VALUES (?)",
            [("Airbus A320",), ("Sukhoi Superjet 100",)],
        )
        connection.executemany(
            "INSERT INTO aircrafts(model_id, registration_number, seats) VALUES (?, ?, ?)",
            [(1, "RA-32001", 180), (2, "RA-89001", 100)],
        )
        connection.execute(
            "INSERT INTO flight_statuses(name) VALUES (?)", ("Запланирован",)
        )

    connection.executemany(
        "INSERT OR IGNORE INTO airlines(name, iata_code) VALUES (?, ?)",
        [
            ("Победа", "DP"),
            ("Россия", "FV"),
            ("Utair", "UT"),
        ],
    )
    connection.executemany(
        "INSERT OR IGNORE INTO flight_statuses(name) VALUES (?)",
        [("Запланирован",), ("Вылетел",), ("Задержан",), ("Прибыл",)],
    )

    flight_count = connection.execute(
        "SELECT COUNT(*) AS count FROM flights"
    ).fetchone()["count"]
    if flight_count == 0:
        airline_ids = {
            row["iata_code"]: row["id"]
            for row in connection.execute("SELECT id, iata_code FROM airlines")
        }
        aircraft_ids = {
            row["registration_number"]: row["id"]
            for row in connection.execute(
                "SELECT id, registration_number FROM aircrafts"
            )
        }
        airport_ids = {
            row["iata_code"]: row["id"]
            for row in connection.execute("SELECT id, iata_code FROM airports")
        }
        status_ids = {
            row["name"]: row["id"]
            for row in connection.execute("SELECT id, name FROM flight_statuses")
        }
        examples = [
            ("SU-101", "SU", "RA-32001", "SVO", "LED",
             "2026-09-06 08:00", "2026-09-06 09:30", "Запланирован"),
            ("S7-205", "S7", "RA-89001", "LED", "SVX",
             "2026-09-06 10:15", "2026-09-06 12:35", "Запланирован"),
            ("U6-310", "U6", "RA-32001", "SVX", "SVO",
             "2026-09-06 13:00", "2026-09-06 14:20", "Задержан"),
            ("DP-404", "DP", "RA-89001", "SVO", "SVX",
             "2026-09-06 15:40", "2026-09-06 17:50", "Запланирован"),
            ("FV-512", "FV", "RA-32001", "LED", "SVO",
             "2026-09-06 18:10", "2026-09-06 19:35", "Вылетел"),
        ]
        if all(
            airline in airline_ids
            and aircraft in aircraft_ids
            and departure in airport_ids
            and arrival in airport_ids
            and status in status_ids
            for _, airline, aircraft, departure, arrival, _, _, status in examples
        ):
            connection.executemany(
                """
                INSERT INTO flights(
                    flight_number, airline_id, aircraft_id,
                    departure_airport_id, arrival_airport_id,
                    departure_time, arrival_time, status_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        number,
                        airline_ids[airline],
                        aircraft_ids[aircraft],
                        airport_ids[departure],
                        airport_ids[arrival],
                        departure_time,
                        arrival_time,
                        status_ids[status],
                    )
                    for (
                        number,
                        airline,
                        aircraft,
                        departure,
                        arrival,
                        departure_time,
                        arrival_time,
                        status,
                    ) in examples
                ],
            )


def fetch_all(query: str, parameters: tuple = ()) -> list[sqlite3.Row]:
    # Выполняем SELECT-запрос и возвращаем все строки результата.
    with get_connection() as connection:
        return connection.execute(query, parameters).fetchall()


def execute(query: str, parameters: tuple = ()) -> int:
    # Выполняем INSERT/UPDATE/DELETE и возвращаем идентификатор последней записи.
    with get_connection() as connection:
        cursor = connection.execute(query, parameters)
        return cursor.lastrowid


def add_airport(name: str, city: str, iata_code: str) -> None:
    with get_connection() as connection:
        connection.execute(
            "INSERT OR IGNORE INTO cities(name) VALUES (?)",
            (city,),
        )
        city_id = connection.execute(
            "SELECT id FROM cities WHERE name = ?", (city,)
        ).fetchone()["id"]
        connection.execute(
            "INSERT INTO airports(name, city_id, iata_code) VALUES (?, ?, ?)",
            (name, city_id, iata_code),
        )