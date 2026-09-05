import tkinter as tk
from tkinter import ttk, messagebox

from config import APP_TITLE, COLORS, MAIN_GEOMETRY, MAIN_MIN_HEIGHT, MAIN_MIN_WIDTH
from database import DatabaseError, initialize_database
from help_window import HELP_TOPICS, show_help as open_help
from login_window import LoginWindow
from reports import REPORTS, show_reports as open_reports
from tabs import AircraftsTab, AirlinesTab, AirportsTab, FlightsTab


class AirportApplication(tk.Tk):
    """Главное окно диспетчерской службы аэропорта."""

    HELP_TOPICS = HELP_TOPICS
    REPORTS = REPORTS

    def __init__(self) -> None:
        super().__init__()
        self.background_color = COLORS["background"]
        self.configure(bg=self.background_color)
        self.title(APP_TITLE)
        self.geometry(MAIN_GEOMETRY)
        self.minsize(MAIN_MIN_WIDTH, MAIN_MIN_HEIGHT)
        self.status_text = tk.StringVar(value="")
        self._configure_style()
        self._build_interface()
        self.refresh_all()

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("TFrame", background=self.background_color)
        style.configure("TLabel", background=self.background_color)
        style.configure("TLabelframe", background=self.background_color)
        style.configure("TLabelframe.Label", background=self.background_color)
        style.configure(
            "TNotebook", background=self.background_color, borderwidth=0
        )
        style.configure(
            "TNotebook.Tab",
            background=COLORS["button"],
            foreground=COLORS["text"],
            padding=(12, 6),
        )
        style.map(
            "TNotebook.Tab",
            background=[
                ("selected", COLORS["tab_selected"]),
                ("active", COLORS["button_active"]),
            ],
            foreground=[("selected", COLORS["text_active"])],
        )
        style.configure(
            "TButton",
            background=COLORS["button"],
            foreground=COLORS["text"],
            padding=(8, 4),
        )
        style.map(
            "TButton",
            background=[
                ("active", COLORS["button_active"]),
                ("pressed", COLORS["button_pressed"]),
            ],
        )
        style.configure(
            "Treeview",
            rowheight=28,
            background=COLORS["table"],
            fieldbackground=COLORS["table"],
        )
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"))

    def _build_interface(self) -> None:
        self._build_menu()
        header = ttk.Frame(self, padding=(18, 14, 18, 8))
        header.pack(fill=tk.X)
        header.columnconfigure(1, weight=1)
        title_frame = ttk.Frame(header)
        title_frame.grid(row=0, column=1)
        airplane = tk.Canvas(
            title_frame,
            width=42,
            height=32,
            bg=self.background_color,
            highlightthickness=0,
        )
        airplane.pack(side=tk.LEFT, padx=(0, 8))
        self._draw_airplane(airplane)
        ttk.Label(
            title_frame,
            text=APP_TITLE,
            style="Title.TLabel",
        ).pack(side=tk.LEFT)
        ttk.Label(header, textvariable=self.status_text).grid(
            row=0, column=2, sticky=tk.E
        )

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=18, pady=(0, 12))
        self.airlines_tab = AirlinesTab(self.notebook, self._refresh_flight_references)
        self.airports_tab = AirportsTab(self.notebook, self._refresh_flight_references)
        self.aircrafts_tab = AircraftsTab(
            self.notebook, self._refresh_flight_references
        )
        self.flights_tab = FlightsTab(self.notebook)
        self.bind("<F1>", self.show_help)

        # Keep the former tree attributes available to callers of the application.
        self.airlines_tree = self.airlines_tab.tree
        self.airports_tree = self.airports_tab.tree
        self.aircrafts_tree = self.aircrafts_tab.tree
        self.flights_tree = self.flights_tab.tree
        self.airline_name = self.airlines_tab.name
        self.airline_code = self.airlines_tab.code
        self.airport_name = self.airports_tab.name
        self.airport_city = self.airports_tab.city
        self.airport_code = self.airports_tab.code
        self.aircraft_model = self.aircrafts_tab.model
        self.aircraft_registration = self.aircrafts_tab.registration
        self.aircraft_seats = self.aircrafts_tab.seats
        self.flight_number = self.flights_tab.flight_number
        self.flight_airline = self.flights_tab.airline
        self.flight_aircraft = self.flights_tab.aircraft
        self.flight_departure_airport = self.flights_tab.departure_airport
        self.flight_arrival_airport = self.flights_tab.arrival_airport
        self.flight_departure_time = self.flights_tab.departure_time
        self.flight_arrival_time = self.flights_tab.arrival_time
        self.flight_status = self.flights_tab.status
        self.flight_airline_combo = self.flights_tab.airline_combo
        self.flight_aircraft_combo = self.flights_tab.aircraft_combo
        self.flight_departure_combo = self.flights_tab.departure_combo
        self.flight_arrival_combo = self.flights_tab.arrival_combo
        self.flight_status_combo = self.flights_tab.status_combo

    def _build_menu(self) -> None:
        toolbar = tk.Frame(self, bg=self.background_color)
        toolbar.pack(fill=tk.X, padx=18, pady=(8, 0))
        button_options = {
            "bg": COLORS["button"],
            "activebackground": COLORS["button_active"],
            "fg": COLORS["text"],
            "activeforeground": COLORS["text_active"],
            "relief": tk.FLAT,
            "bd": 0,
            "padx": 12,
            "pady": 5,
            "cursor": "hand2",
        }
        tk.Button(
            toolbar, text="Отчеты", command=self.show_reports, **button_options
        ).pack(side=tk.LEFT)
        tk.Button(
            toolbar, text="Справка", command=self.show_help, **button_options
        ).pack(side=tk.LEFT, padx=(4, 0))

    def show_reports(self) -> str:
        """Открывает окно формирования, сортировки и печати отчетов."""
        self.report_window = open_reports(self)
        return "break"

    def show_help(self, topic: str | tk.Event | None = None) -> str:
        """Открывает интерактивную справку и выбирает подходящую тему."""
        if isinstance(topic, tk.Event):
            topic = None
        if topic is None:
            topics = ("Авиакомпании", "Аэропорты", "Самолёты", "Рейсы")
            topic = topics[self.notebook.index(self.notebook.select())]
        self.help_window = open_help(self, topic)
        return "break"

    def show_about(self) -> None:
        messagebox.showinfo(
            "О программе",
            f"{APP_TITLE}\n"
            "Контроль справочников и расписания рейсов.\n\n"
            "Откройте справку клавишей F1 для подробных инструкций.",
            parent=self,
        )

    def refresh_all(self) -> None:
        self.refresh_airlines()
        self.refresh_airports()
        self.aircrafts_tab.refresh()
        self._refresh_flight_references()
        self.refresh_flights()

    def refresh_airlines(self) -> None:
        self.airlines_tab.refresh()

    def refresh_airports(self) -> None:
        self.airports_tab.refresh()

    def refresh_aircrafts(self) -> None:
        self.aircrafts_tab.refresh()

    def refresh_flights(self) -> None:
        self.flights_tab.refresh()

    def _refresh_flight_references(self) -> None:
        self.flights_tab.refresh_references()

    def add_airline(self) -> None:
        self.airlines_tab.add()

    def add_airport(self) -> None:
        self.airports_tab.add()

    def add_aircraft(self) -> None:
        self.aircrafts_tab.add()

    def add_flight(self) -> None:
        self.flights_tab.add()

    @staticmethod
    def _draw_airplane(canvas: tk.Canvas) -> None:
        canvas.create_polygon(
            4, 16, 35, 11, 39, 14, 35, 17, 4, 20,
            fill="#3b82c4", outline="#24527a", width=1,
        )
        canvas.create_polygon(
            18, 14, 24, 3, 28, 3, 26, 14,
            fill="#5ca9e6", outline="#24527a",
        )
        canvas.create_polygon(
            18, 18, 25, 29, 29, 29, 26, 18,
            fill="#5ca9e6", outline="#24527a",
        )
        canvas.create_polygon(
            6, 16, 1, 9, 4, 8, 12, 15,
            fill="#5ca9e6", outline="#24527a",
        )


def run() -> None:
    try:
        initialize_database()
    except DatabaseError as error:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Ошибка базы данных",
            f"Не удалось инициализировать базу данных:\n{error}",
            parent=root,
        )
        root.destroy()
        return
    if LoginWindow().run():
        AirportApplication().mainloop()


if __name__ == "__main__":
    run()
