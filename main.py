import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk

from database import execute, fetch_all, initialize_database


class AirportApplication(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Система управления аэропортом")
        self.geometry("1100x650")
        self.minsize(900, 550)

        self.status_text = tk.StringVar(value="Готово")
        self._configure_style()
        self._build_interface()
        self.refresh_all()

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Treeview", rowheight=28)
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"))

    def _build_interface(self) -> None:
        header = ttk.Frame(self, padding=(18, 14, 18, 8))
        header.pack(fill=tk.X)
        ttk.Label(
            header,
            text="Система управления аэропортом",
            style="Title.TLabel",
        ).pack(side=tk.LEFT)
        ttk.Label(header, textvariable=self.status_text).pack(side=tk.RIGHT)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=18, pady=(0, 12))
        self._build_airlines_tab()
        self._build_airports_tab()
        self._build_flights_tab()

    def _build_airlines_tab(self) -> None:
        tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(tab, text="Авиакомпании")

        form = ttk.LabelFrame(tab, text="Новая авиакомпания", padding=10)
        form.pack(fill=tk.X, pady=(0, 10))
        self.airline_name = tk.StringVar()
        self.airline_code = tk.StringVar()
        ttk.Label(form, text="Название:").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(form, textvariable=self.airline_name, width=35).grid(
            row=0, column=1, padx=8
        )
        ttk.Label(form, text="IATA-код:").grid(row=0, column=2, sticky=tk.W)
        ttk.Entry(form, textvariable=self.airline_code, width=10).grid(
            row=0, column=3, padx=8
        )
        ttk.Button(form, text="Добавить", command=self.add_airline).grid(
            row=0, column=4, padx=8
        )

        self.airlines_tree = self._create_tree(
            tab, ("id", "name", "iata_code"), ("ID", "Название", "IATA-код")
        )

    def _build_airports_tab(self) -> None:
        tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(tab, text="Аэропорты")

        form = ttk.LabelFrame(tab, text="Новый аэропорт", padding=10)
        form.pack(fill=tk.X, pady=(0, 10))
        self.airport_name = tk.StringVar()
        self.airport_city = tk.StringVar()
        self.airport_code = tk.StringVar()
        fields = [
            ("Название:", self.airport_name, 32),
            ("Город:", self.airport_city, 22),
            ("IATA-код:", self.airport_code, 10),
        ]
        for column, (label, variable, width) in enumerate(fields):
            ttk.Label(form, text=label).grid(row=0, column=column * 2, sticky=tk.W)
            ttk.Entry(form, textvariable=variable, width=width).grid(
                row=0, column=column * 2 + 1, padx=(6, 14)
            )
        ttk.Button(form, text="Добавить", command=self.add_airport).grid(
            row=0, column=6
        )
        self.airports_tree = self._create_tree(
            tab,
            ("id", "name", "city", "iata_code"),
            ("ID", "Название", "Город", "IATA-код"),
        )

    def _build_flights_tab(self) -> None:
        tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(tab, text="Рейсы")
        controls = ttk.Frame(tab)
        controls.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(controls, text="Обновить список", command=self.refresh_flights).pack(
            side=tk.LEFT
        )
        ttk.Label(
            controls,
            text="Рейсы объединяют авиакомпании, самолёты и аэропорты.",
        ).pack(side=tk.LEFT, padx=14)
        self.flights_tree = self._create_tree(
            tab,
            (
                "flight_number",
                "airline",
                "aircraft",
                "departure",
                "arrival",
                "departure_time",
                "arrival_time",
                "status",
            ),
            (
                "Рейс",
                "Авиакомпания",
                "Самолёт",
                "Откуда",
                "Куда",
                "Вылет",
                "Прилёт",
                "Статус",
            ),
        )

    def _create_tree(
        self, parent: ttk.Widget, columns: tuple[str, ...], headings: tuple[str, ...]
    ) -> ttk.Treeview:
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True)
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        for column, heading in zip(columns, headings):
            tree.heading(column, text=heading)
            tree.column(column, width=130, minwidth=80, anchor=tk.CENTER)
        tree.column(columns[0], width=70)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        return tree

    def add_airline(self) -> None:
        name = self.airline_name.get().strip()
        code = self.airline_code.get().strip().upper()
        if not name or len(code) != 2:
            messagebox.showwarning(
                "Проверка данных", "Введите название и двухсимвольный IATA-код."
            )
            return
        try:
            execute("INSERT INTO airlines(name, iata_code) VALUES (?, ?)", (name, code))
        except sqlite3.IntegrityError as error:
            messagebox.showerror("Ошибка", f"Не удалось добавить авиакомпанию:\n{error}")
            return
        self.airline_name.set("")
        self.airline_code.set("")
        self.refresh_airlines()

    def add_airport(self) -> None:
        name = self.airport_name.get().strip()
        city = self.airport_city.get().strip()
        code = self.airport_code.get().strip().upper()
        if not name or not city or len(code) != 3:
            messagebox.showwarning(
                "Проверка данных",
                "Введите название, город и трёхсимвольный IATA-код.",
            )
            return
        try:
            execute(
                "INSERT INTO airports(name, city, iata_code) VALUES (?, ?, ?)",
                (name, city, code),
            )
        except sqlite3.IntegrityError as error:
            messagebox.showerror("Ошибка", f"Не удалось добавить аэропорт:\n{error}")
            return
        self.airport_name.set("")
        self.airport_city.set("")
        self.airport_code.set("")
        self.refresh_airports()

    def refresh_all(self) -> None:
        self.refresh_airlines()
        self.refresh_airports()
        self.refresh_flights()

    def refresh_airlines(self) -> None:
        self._replace_rows(
            self.airlines_tree,
            fetch_all("SELECT id, name, iata_code FROM airlines ORDER BY name"),
        )

    def refresh_airports(self) -> None:
        self._replace_rows(
            self.airports_tree,
            fetch_all(
                "SELECT id, name, city, iata_code FROM airports ORDER BY city, name"
            ),
        )

    def refresh_flights(self) -> None:
        self._replace_rows(
            self.flights_tree,
            fetch_all(
                """
                SELECT f.flight_number, a.name AS airline, ac.model AS aircraft,
                       dep.iata_code AS departure, arr.iata_code AS arrival,
                       f.departure_time, f.arrival_time, f.status
                FROM flights f
                JOIN airlines a ON a.id = f.airline_id
                JOIN aircrafts ac ON ac.id = f.aircraft_id
                JOIN airports dep ON dep.id = f.departure_airport_id
                JOIN airports arr ON arr.id = f.arrival_airport_id
                ORDER BY f.departure_time
                """
            ),
        )

    @staticmethod
    def _replace_rows(tree: ttk.Treeview, rows: list[sqlite3.Row]) -> None:
        tree.delete(*tree.get_children())
        for row in rows:
            tree.insert("", tk.END, values=tuple(row))


if __name__ == "__main__":
    initialize_database()
    AirportApplication().mainloop()