"""SQLite repository for the airport dispatch application.

The UI talks to this module through named operations rather than embedding SQL.
All SQLite errors are translated to :class:`DatabaseError` at this boundary.
"""

from contextlib import contextmanager
from pathlib import Path
from collections.abc import Iterator
import sqlite3


DATABASE_PATH = Path(__file__).with_name("airport.db")
SCHEMA_VERSION = 1


class DatabaseError(RuntimeError):
    """A user-facing repository error caused by SQLite."""

    def __init__(self, message: str, original: sqlite3.Error | None = None) -> None:
        super().__init__(message)
        self.original = original

    @property
    def is_integrity_error(self) -> bool:
        return isinstance(self.original, sqlite3.IntegrityError)


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def _connection(operation: str) -> Iterator[sqlite3.Connection]:
    connection: sqlite3.Connection | None = None
    try:
        connection = get_connection()
        yield connection
        connection.commit()
    except sqlite3.Error as error:
        if connection is not None:
            connection.rollback()
        raise DatabaseError(f"{operation}: {error}", error) from error
    finally:
        if connection is not None:
            connection.close()


def _fetch_all(
    query: str, parameters: tuple[object, ...] = (), operation: str = "Не удалось прочитать данные"
) -> list[sqlite3.Row]:
    with _connection(operation) as connection:
        return connection.execute(query, parameters).fetchall()


def _execute(
    query: str, parameters: tuple[object, ...] = (), operation: str = "Не удалось сохранить данные"
) -> int:
    with _connection(operation) as connection:
        return connection.execute(query, parameters).lastrowid


def initialize_database() -> None:
    """Create or upgrade the schema and add missing seed/reference data."""
    try:
        with _connection("Не удалось инициализировать базу данных") as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            airport_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(airports)")
            }
            if version == 0:
                if "city" in airport_columns:
                    _migrate_to_third_normal_form(connection)
                else:
                    _create_normalized_schema(connection)
                connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            else:
                _create_normalized_schema(connection)
            _ensure_indexes(connection)
            _insert_seed_data(connection)
    except DatabaseError:
        raise


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


def _ensure_indexes(connection: sqlite3.Connection) -> None:
    try:
        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS "
            "idx_flights_flight_number_unique ON flights(flight_number)"
        )
    except sqlite3.IntegrityError:
        # Keep an existing database usable when legacy data contains duplicates.
        # The regular lookup index below still supports searches; new writes are
        # checked by flight_number_exists before insertion.
        pass
    for statement in (
        "CREATE INDEX IF NOT EXISTS idx_airlines_code ON airlines(iata_code)",
        "CREATE INDEX IF NOT EXISTS idx_airlines_name ON airlines(name)",
        "CREATE INDEX IF NOT EXISTS idx_airports_code ON airports(iata_code)",
        "CREATE INDEX IF NOT EXISTS idx_airports_city ON airports(city_id)",
        "CREATE INDEX IF NOT EXISTS idx_aircrafts_registration ON aircrafts(registration_number)",
        "CREATE INDEX IF NOT EXISTS idx_aircrafts_model ON aircrafts(model_id)",
        "CREATE INDEX IF NOT EXISTS idx_flights_number ON flights(flight_number)",
        "CREATE INDEX IF NOT EXISTS idx_flights_departure ON flights(departure_time)",
        "CREATE INDEX IF NOT EXISTS idx_flights_status ON flights(status_id)",
        "CREATE INDEX IF NOT EXISTS idx_flights_airline ON flights(airline_id)",
        "CREATE INDEX IF NOT EXISTS idx_flights_aircraft ON flights(aircraft_id)",
        "CREATE INDEX IF NOT EXISTS idx_flights_departure_airport ON flights(departure_airport_id)",
        "CREATE INDEX IF NOT EXISTS idx_flights_arrival_airport ON flights(arrival_airport_id)",
    ):
        connection.execute(statement)


def _insert_seed_data(connection: sqlite3.Connection) -> None:
    if connection.execute("SELECT COUNT(*) FROM airlines").fetchone()[0] == 0:
        connection.executemany(
            "INSERT INTO airlines(name, iata_code) VALUES (?, ?)",
            [("Аэрофлот", "SU"), ("S7 Airlines", "S7"), ("Уральские авиалинии", "U6")],
        )
        connection.executemany(
            "INSERT OR IGNORE INTO cities(name) VALUES (?)",
            [("Москва",), ("Санкт-Петербург",), ("Екатеринбург",)],
        )
        city_ids = {
            row["name"]: row["id"]
            for row in connection.execute("SELECT id, name FROM cities")
        }
        connection.executemany(
            "INSERT INTO airports(name, city_id, iata_code) VALUES (?, ?, ?)",
            [
                ("Шереметьево", city_ids["Москва"], "SVO"),
                ("Пулково", city_ids["Санкт-Петербург"], "LED"),
                ("Кольцово", city_ids["Екатеринбург"], "SVX"),
            ],
        )
        connection.executemany(
            "INSERT OR IGNORE INTO aircraft_models(name) VALUES (?)",
            [("Airbus A320",), ("Sukhoi Superjet 100",)],
        )
        model_ids = {
            row["name"]: row["id"]
            for row in connection.execute("SELECT id, name FROM aircraft_models")
        }
        connection.executemany(
            "INSERT INTO aircrafts(model_id, registration_number, seats) VALUES (?, ?, ?)",
            [
                (model_ids["Airbus A320"], "RA-32001", 180),
                (model_ids["Sukhoi Superjet 100"], "RA-89001", 100),
            ],
        )
    connection.executemany(
        "INSERT OR IGNORE INTO airlines(name, iata_code) VALUES (?, ?)",
        [("Победа", "DP"), ("Россия", "FV"), ("Utair", "UT")],
    )
    connection.executemany(
        "INSERT OR IGNORE INTO flight_statuses(name) VALUES (?)",
        [("Запланирован",), ("Вылетел",), ("Задержан",), ("Прибыл",)],
    )
    if connection.execute("SELECT COUNT(*) FROM flights").fetchone()[0] == 0:
        ids = {
            "airlines": {r["iata_code"]: r["id"] for r in connection.execute("SELECT id, iata_code FROM airlines")},
            "aircrafts": {r["registration_number"]: r["id"] for r in connection.execute("SELECT id, registration_number FROM aircrafts")},
            "airports": {r["iata_code"]: r["id"] for r in connection.execute("SELECT id, iata_code FROM airports")},
            "statuses": {r["name"]: r["id"] for r in connection.execute("SELECT id, name FROM flight_statuses")},
        }
        examples = [
            ("SU-101", "SU", "RA-32001", "SVO", "LED", "2026-09-06 08:00", "2026-09-06 09:30", "Запланирован"),
            ("S7-205", "S7", "RA-89001", "LED", "SVX", "2026-09-06 10:15", "2026-09-06 12:35", "Запланирован"),
            ("U6-310", "U6", "RA-32001", "SVX", "SVO", "2026-09-06 13:00", "2026-09-06 14:20", "Задержан"),
            ("DP-404", "DP", "RA-89001", "SVO", "SVX", "2026-09-06 15:40", "2026-09-06 17:50", "Запланирован"),
            ("FV-512", "FV", "RA-32001", "LED", "SVO", "2026-09-06 18:10", "2026-09-06 19:35", "Вылетел"),
        ]
        if all(x[1] in ids["airlines"] and x[2] in ids["aircrafts"] and x[3] in ids["airports"] and x[4] in ids["airports"] and x[7] in ids["statuses"] for x in examples):
            connection.executemany(
                """
                INSERT INTO flights(
                    flight_number, airline_id, aircraft_id,
                    departure_airport_id, arrival_airport_id,
                    departure_time, arrival_time, status_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (x[0], ids["airlines"][x[1]], ids["aircrafts"][x[2]], ids["airports"][x[3]], ids["airports"][x[4]], x[5], x[6], ids["statuses"][x[7]])
                    for x in examples
                ],
            )


# Compatibility primitives for callers outside the tabs.
def fetch_all(query: str, parameters: tuple = ()) -> list[sqlite3.Row]:
    return _fetch_all(query, parameters)


def execute(query: str, parameters: tuple = ()) -> int:
    return _execute(query, parameters)


def list_airlines() -> list[sqlite3.Row]:
    return _fetch_all("SELECT id, name, iata_code FROM airlines ORDER BY name", operation="Не удалось загрузить авиакомпании")


def add_airline(name: str, iata_code: str) -> int:
    return _execute("INSERT INTO airlines(name, iata_code) VALUES (?, ?)", (name, iata_code), "Не удалось добавить авиакомпанию")


def update_airline(airline_id: int, name: str, iata_code: str) -> int:
    return _execute("UPDATE airlines SET name = ?, iata_code = ? WHERE id = ?", (name, iata_code, airline_id), "Не удалось изменить авиакомпанию")


def delete_airline(airline_id: int) -> int:
    return _execute("DELETE FROM airlines WHERE id = ?", (airline_id,), "Не удалось удалить авиакомпанию")


def list_airports() -> list[sqlite3.Row]:
    return _fetch_all(
        "SELECT a.id, a.name, c.name AS city, a.iata_code FROM airports a JOIN cities c ON c.id = a.city_id ORDER BY c.name, a.name",
        operation="Не удалось загрузить аэропорты",
    )


def _city_id(connection: sqlite3.Connection, city: str) -> int:
    connection.execute("INSERT OR IGNORE INTO cities(name) VALUES (?)", (city,))
    return connection.execute("SELECT id FROM cities WHERE name = ?", (city,)).fetchone()["id"]


def add_airport(name: str, city: str, iata_code: str) -> int:
    with _connection("Не удалось добавить аэропорт") as connection:
        city_id = _city_id(connection, city)
        return connection.execute(
            "INSERT INTO airports(name, city_id, iata_code) VALUES (?, ?, ?)",
            (name, city_id, iata_code),
        ).lastrowid


def update_airport(airport_id: int, name: str, city: str, iata_code: str) -> int:
    with _connection("Не удалось изменить аэропорт") as connection:
        city_id = _city_id(connection, city)
        return connection.execute(
            "UPDATE airports SET name = ?, city_id = ?, iata_code = ? WHERE id = ?",
            (name, city_id, iata_code, airport_id),
        ).lastrowid


def delete_airport(airport_id: int) -> int:
    return _execute("DELETE FROM airports WHERE id = ?", (airport_id,), "Не удалось удалить аэропорт")


def list_aircraft_models() -> list[sqlite3.Row]:
    return _fetch_all("SELECT id, name FROM aircraft_models ORDER BY name", operation="Не удалось загрузить модели самолётов")


def list_aircrafts() -> list[sqlite3.Row]:
    return _fetch_all(
        "SELECT ac.id, am.name AS model, ac.registration_number, ac.seats FROM aircrafts ac JOIN aircraft_models am ON am.id = ac.model_id ORDER BY ac.registration_number",
        operation="Не удалось загрузить самолёты",
    )


def _model_id(connection: sqlite3.Connection, model: str) -> int:
    connection.execute("INSERT OR IGNORE INTO aircraft_models(name) VALUES (?)", (model,))
    return connection.execute("SELECT id FROM aircraft_models WHERE name = ?", (model,)).fetchone()["id"]


def add_aircraft(model: str, registration_number: str, seats: int) -> int:
    with _connection("Не удалось добавить самолёт") as connection:
        model_id = _model_id(connection, model)
        return connection.execute(
            "INSERT INTO aircrafts(model_id, registration_number, seats) VALUES (?, ?, ?)",
            (model_id, registration_number, seats),
        ).lastrowid


def update_aircraft(aircraft_id: int, model: str, registration_number: str, seats: int) -> int:
    with _connection("Не удалось изменить самолёт") as connection:
        model_id = _model_id(connection, model)
        return connection.execute(
            "UPDATE aircrafts SET model_id = ?, registration_number = ?, seats = ? WHERE id = ?",
            (model_id, registration_number, seats, aircraft_id),
        ).lastrowid


def delete_aircraft(aircraft_id: int) -> int:
    return _execute("DELETE FROM aircrafts WHERE id = ?", (aircraft_id,), "Не удалось удалить самолёт")


def list_airline_references() -> list[sqlite3.Row]:
    return _fetch_all("SELECT id, name, iata_code FROM airlines ORDER BY name", operation="Не удалось загрузить список авиакомпаний")


def list_aircraft_references() -> list[sqlite3.Row]:
    return _fetch_all(
        "SELECT ac.id, ac.registration_number, am.name AS model FROM aircrafts ac JOIN aircraft_models am ON am.id = ac.model_id ORDER BY ac.registration_number",
        operation="Не удалось загрузить список самолётов",
    )


def list_airport_references() -> list[sqlite3.Row]:
    return _fetch_all(
        "SELECT a.id, a.iata_code, a.name, c.name AS city FROM airports a JOIN cities c ON c.id = a.city_id ORDER BY c.name, a.name",
        operation="Не удалось загрузить список аэропортов",
    )


def list_statuses() -> list[sqlite3.Row]:
    return _fetch_all("SELECT id, name FROM flight_statuses ORDER BY id", operation="Не удалось загрузить статусы рейсов")


def search_flights(search: str = "", status: str | None = None) -> list[sqlite3.Row]:
    query = """
        SELECT f.id, f.flight_number, a.name AS airline, am.name AS aircraft,
               dep.iata_code AS departure, arr.iata_code AS arrival,
               f.departure_time, f.arrival_time, fs.name AS status
        FROM flights f
        JOIN airlines a ON a.id = f.airline_id
        JOIN aircrafts ac ON ac.id = f.aircraft_id
        JOIN aircraft_models am ON am.id = ac.model_id
        JOIN airports dep ON dep.id = f.departure_airport_id
        JOIN airports arr ON arr.id = f.arrival_airport_id
        JOIN flight_statuses fs ON fs.id = f.status_id
        WHERE (f.flight_number LIKE ? COLLATE NOCASE
               OR a.name LIKE ? COLLATE NOCASE
               OR am.name LIKE ? COLLATE NOCASE
               OR dep.iata_code LIKE ? COLLATE NOCASE
               OR arr.iata_code LIKE ? COLLATE NOCASE)
    """
    parameters: list[object] = [f"%{search.strip()}%"] * 5
    if status:
        query += " AND fs.name = ?"
        parameters.append(status)
    query += " ORDER BY f.departure_time"
    return _fetch_all(query, tuple(parameters), "Не удалось загрузить рейсы")


def get_flight(flight_id: int) -> sqlite3.Row | None:
    rows = _fetch_all(
        "SELECT id, flight_number, airline_id, aircraft_id, departure_airport_id, arrival_airport_id, departure_time, arrival_time, status_id FROM flights WHERE id = ?",
        (flight_id,),
        "Не удалось загрузить рейс",
    )
    return rows[0] if rows else None


def flight_number_exists(number: str, exclude_id: int | None = None) -> bool:
    rows = _fetch_all(
        "SELECT 1 FROM flights WHERE flight_number = ? AND id <> ?",
        (number, exclude_id if exclude_id is not None else -1),
        "Не удалось проверить номер рейса",
    )
    return bool(rows)


def add_flight(number: str, airline_id: int, aircraft_id: int, departure_airport_id: int, arrival_airport_id: int, departure_time: str, arrival_time: str, status_id: int) -> int:
    return _execute(
        "INSERT INTO flights(flight_number, airline_id, aircraft_id, departure_airport_id, arrival_airport_id, departure_time, arrival_time, status_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (number, airline_id, aircraft_id, departure_airport_id, arrival_airport_id, departure_time, arrival_time, status_id),
        "Не удалось добавить рейс",
    )


def update_flight(flight_id: int, number: str, airline_id: int, aircraft_id: int, departure_airport_id: int, arrival_airport_id: int, departure_time: str, arrival_time: str, status_id: int) -> int:
    return _execute(
        "UPDATE flights SET flight_number = ?, airline_id = ?, aircraft_id = ?, departure_airport_id = ?, arrival_airport_id = ?, departure_time = ?, arrival_time = ?, status_id = ? WHERE id = ?",
        (number, airline_id, aircraft_id, departure_airport_id, arrival_airport_id, departure_time, arrival_time, status_id, flight_id),
        "Не удалось изменить рейс",
    )


def update_flight_status(flight_id: int, status_id: int) -> int:
    return _execute("UPDATE flights SET status_id = ? WHERE id = ?", (status_id, flight_id), "Не удалось обновить статус рейса")


def delete_flight(flight_id: int) -> int:
    return _execute("DELETE FROM flights WHERE id = ?", (flight_id,), "Не удалось удалить рейс")


def report_schedule() -> list[sqlite3.Row]:
    return _fetch_all(
        """
        SELECT f.flight_number, a.name, am.name,
               dep.iata_code, arr.iata_code,
               f.departure_time, f.arrival_time, fs.name
        FROM flights f
        JOIN airlines a ON a.id = f.airline_id
        JOIN aircrafts ac ON ac.id = f.aircraft_id
        JOIN aircraft_models am ON am.id = ac.model_id
        JOIN airports dep ON dep.id = f.departure_airport_id
        JOIN airports arr ON arr.id = f.arrival_airport_id
        JOIN flight_statuses fs ON fs.id = f.status_id
        ORDER BY f.departure_time
        """,
        operation="Не удалось сформировать расписание",
    )


def report_airlines() -> list[sqlite3.Row]:
    return _fetch_all("SELECT id, name, iata_code FROM airlines ORDER BY name", operation="Не удалось сформировать отчет по авиакомпаниям")


def report_airports() -> list[sqlite3.Row]:
    return _fetch_all(
        "SELECT a.id, a.name, c.name, a.iata_code FROM airports a JOIN cities c ON c.id = a.city_id ORDER BY c.name, a.name",
        operation="Не удалось сформировать отчет по аэропортам",
    )


def report_flight_statuses() -> list[sqlite3.Row]:
    return _fetch_all(
        "SELECT fs.name, COUNT(f.id) FROM flight_statuses fs LEFT JOIN flights f ON f.status_id = fs.id GROUP BY fs.id, fs.name ORDER BY COUNT(f.id) DESC, fs.name",
        operation="Не удалось сформировать отчет по статусам",
    )
