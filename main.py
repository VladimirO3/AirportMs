# sqlite3 нужен для обработки ошибок, которые возвращает база данных.
import os
import sqlite3
import subprocess
import tempfile
from datetime import datetime
# tkinter и ttk используются для создания оконного интерфейса приложения.
import tkinter as tk
from tkinter import messagebox, ttk

# Импортируем готовые функции подключения к базе и работы с запросами.
from database import add_airport, execute, fetch_all, initialize_database
from login_window import LoginWindow


class AirportApplication(tk.Tk):
    """Главное окно диспетчерской службы аэропорта."""

    HELP_TOPICS = {
        "Обзор системы": (
            "Диспетчерская служба предназначена для ведения справочников и "
            "оперативного управления расписанием рейсов.\n\n"
            "Диспетчер может просматривать авиакомпании, аэропорты и рейсы, а также "
            "добавлять новые записи. Выберите нужную вкладку, заполните форму и "
            "нажмите кнопку добавления."
        ),
        "Авиакомпании": (
            "На вкладке «Авиакомпании» можно просматривать список авиакомпаний и "
            "добавлять новые записи.\n\n"
            "Укажите название и уникальный двухсимвольный IATA-код. Код автоматически "
            "переводится в верхний регистр."
        ),
        "Аэропорты": (
            "На вкладке «Аэропорты» можно просматривать и добавлять аэропорты.\n\n"
            "Для новой записи укажите название, город и уникальный трёхсимвольный "
            "IATA-код. Города сохраняются как отдельные справочные данные."
        ),
        "Рейсы": (
            "На вкладке «Рейсы» создаются маршруты между аэропортами.\n\n"
            "Выберите авиакомпанию, самолёт, аэропорты вылета и прилёта, статус и "
            "укажите время в формате ГГГГ-ММ-ДД ЧЧ:ММ. Связанные справочники "
            "заполняются автоматически из базы данных."
        ),
        "Проверка данных": (
            "Приложение проверяет обязательные поля, формат IATA-кодов, уникальность "
            "записей и корректность времени рейса.\n\n"
            "Аэропорты вылета и прилёта должны отличаться, а время прилёта должно "
            "быть позже времени вылета. Ошибки отображаются в отдельном сообщении."
        ),
        "Горячие клавиши": (
            "F1 — открыть справку.\n"
            "Esc — закрыть окно справки.\n\n"
            "В окне справки выберите тему слева или введите слово в поле поиска. "
            "Результаты фильтруются по названию и содержанию темы."
        ),
        "Отчеты и печать": (
            "Нажмите кнопку «Отчеты». Доступны "
            "расписание рейсов, списки авиакомпаний и аэропортов, а также сводка "
            "рейсов по статусам.\n\n"
            "Нажатие на заголовок столбца сортирует данные. Кнопка «Печать» "
            "формирует HTML-отчет и отправляет его системному принтеру Windows."
        ),
    }
    REPORTS = {
        "Расписание рейсов": (
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
        ),
        "Авиакомпании": (
            ("ID", "Название", "IATA-код"),
            "SELECT id, name, iata_code FROM airlines ORDER BY name",
        ),
        "Аэропорты": (
            ("ID", "Название", "Город", "IATA-код"),
            """
            SELECT a.id, a.name, c.name, a.iata_code
            FROM airports a
            JOIN cities c ON c.id = a.city_id
            ORDER BY c.name, a.name
            """,
        ),
        "Распределение рейсов по статусам": (
            ("Статус", "Количество рейсов"),
            """
            SELECT fs.name, COUNT(f.id)
            FROM flight_statuses fs
            LEFT JOIN flights f ON f.status_id = fs.id
            GROUP BY fs.id, fs.name
            ORDER BY COUNT(f.id) DESC, fs.name
            """,
        ),
    }

    def __init__(self) -> None:
        # Инициализируем базовое окно Tkinter.
        super().__init__()
        self.background_color = "#eaf4ff"
        self.configure(bg=self.background_color)
        # Настраиваем заголовок, размер и минимально допустимый размер окна.
        self.title("Диспетчерская служба аэропорта")
        self.geometry("1100x650")
        self.minsize(900, 550)

        # Эта переменная используется для вывода короткого статуса в шапке окна.
        self.status_text = tk.StringVar(value="")
        self._tree_sort_state: dict[int, tuple[str, bool]] = {}
        # Сначала настраиваем внешний вид, затем создаём элементы интерфейса.
        self._configure_style()
        self._build_interface()
        # После создания таблиц загружаем в них данные из базы.
        self.refresh_all()

    def _configure_style(self) -> None:
        # Style позволяет единообразно настроить внешний вид ttk-компонентов.
        style = ttk.Style(self)
        # Тема clam позволяет применять пользовательские цвета к Notebook и кнопкам.
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("TFrame", background=self.background_color)
        style.configure("TLabel", background=self.background_color)
        style.configure("TLabelframe", background=self.background_color)
        style.configure("TLabelframe.Label", background=self.background_color)
        style.configure(
            "TNotebook",
            background=self.background_color,
            borderwidth=0,
        )
        style.configure(
            "TNotebook.Tab",
            background="#cfeeff",
            foreground="#174a6e",
            padding=(12, 6),
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", "#a9dcf5"), ("active", "#b8e5ff")],
            foreground=[("selected", "#123b58")],
        )
        style.configure(
            "TButton",
            background="#cfeeff",
            foreground="#174a6e",
            padding=(8, 4),
        )
        style.map(
            "TButton",
            background=[("active", "#b8e5ff"), ("pressed", "#9fd8f5")],
        )
        # Настраиваем высоту строк таблиц и стиль заголовка приложения.
        style.configure(
            "Treeview",
            rowheight=28,
            background="#ffffff",
            fieldbackground="#ffffff",
        )
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"))

    def _build_interface(self) -> None:
        self._build_menu()
        # Верхняя часть окна содержит название приложения и строку статуса.
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
            text="Диспетчерская служба аэропорта",
            style="Title.TLabel",
        ).pack(side=tk.LEFT)
        ttk.Label(header, textvariable=self.status_text).grid(
            row=0, column=2, sticky=tk.E
        )

        # Вкладки разделяют интерфейс по типам данных.
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=18, pady=(0, 12))
        # Каждая функция создаёт отдельную вкладку и её элементы управления.
        self._build_airlines_tab()
        self._build_airports_tab()
        self._build_flights_tab()
        self.bind("<F1>", self.show_help)

    def _build_menu(self) -> None:
        toolbar = tk.Frame(self, bg=self.background_color)
        toolbar.pack(fill=tk.X, padx=18, pady=(8, 0))
        button_options = {
            "bg": "#cfeeff",
            "activebackground": "#b8e5ff",
            "fg": "#174a6e",
            "activeforeground": "#123b58",
            "relief": tk.FLAT,
            "bd": 0,
            "padx": 12,
            "pady": 5,
            "cursor": "hand2",
        }
        tk.Button(
            toolbar,
            text="Отчеты",
            command=self.show_reports,
            **button_options,
        ).pack(side=tk.LEFT)
        tk.Button(
            toolbar,
            text="Справка",
            command=self.show_help,
            **button_options,
        ).pack(side=tk.LEFT, padx=(4, 0))

    def show_reports(self) -> None:
        """Открывает окно формирования, сортировки и печати отчетов."""
        window = tk.Toplevel(self)
        window.title("Отчеты диспетчерской службы")
        window.geometry("1050x600")
        window.minsize(760, 450)
        window.transient(self)

        controls = ttk.Frame(window, padding=(12, 12, 12, 8))
        controls.pack(fill=tk.X)
        controls.columnconfigure(1, weight=1)
        ttk.Label(controls, text="Тип отчета:").grid(
            row=0, column=0, sticky=tk.W, padx=(0, 8)
        )
        report_name = tk.StringVar(value=next(iter(self.REPORTS)))
        report_combo = ttk.Combobox(
            controls,
            textvariable=report_name,
            values=tuple(self.REPORTS),
            state="readonly",
            width=32,
        )
        report_combo.grid(row=0, column=1, sticky=tk.W)
        ttk.Button(
            controls, text="Сформировать", command=lambda: load_report()
        ).grid(row=0, column=2, padx=8)
        ttk.Button(
            controls, text="Печать", command=lambda: print_report()
        ).grid(row=0, column=3)

        table_frame = ttk.Frame(window, padding=(12, 0, 12, 12))
        table_frame.pack(fill=tk.BOTH, expand=True)
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        report_tree = ttk.Treeview(table_frame, show="headings")
        report_scrollbar = ttk.Scrollbar(
            table_frame, orient=tk.VERTICAL, command=report_tree.yview
        )
        report_tree.configure(yscrollcommand=report_scrollbar.set)
        report_tree.grid(row=0, column=0, sticky=tk.NSEW)
        report_scrollbar.grid(row=0, column=1, sticky=tk.NS)
        current_headers: tuple[str, ...] = ()
        current_rows: list[tuple[object, ...]] = []

        def load_report() -> None:
            nonlocal current_headers, current_rows
            current_headers, query = self.REPORTS[report_name.get()]
            rows = fetch_all(query)
            current_rows = [tuple(row) for row in rows]
            report_tree.delete(*report_tree.get_children())
            report_tree["columns"] = tuple(
                f"column_{index}" for index in range(len(current_headers))
            )
            for index, heading in enumerate(current_headers):
                column = f"column_{index}"
                report_tree.heading(
                    column,
                    text=heading,
                    command=lambda column=column: sort_report(column),
                )
                report_tree.column(column, width=140, minwidth=90, anchor=tk.CENTER)
            for row in current_rows:
                report_tree.insert("", tk.END, values=row)

        def sort_report(column: str) -> None:
            column_index = int(column.rsplit("_", 1)[1])
            rows = [
                tuple(report_tree.item(item, "values"))
                for item in report_tree.get_children()
            ]
            previous = getattr(sort_report, "last_column", None)
            descending = previous == column and not getattr(
                sort_report, "descending", False
            )
            sort_report.last_column = column
            sort_report.descending = descending

            def sort_key(row: tuple[str, ...]) -> tuple[int, object]:
                value = row[column_index]
                try:
                    return (0, float(value))
                except (TypeError, ValueError):
                    return (1, str(value).casefold())

            rows.sort(key=sort_key, reverse=descending)
            report_tree.delete(*report_tree.get_children())
            for row in rows:
                report_tree.insert("", tk.END, values=row)

        def print_report() -> None:
            if not current_headers:
                messagebox.showwarning(
                    "Печать отчета",
                    "Сначала сформируйте отчет.",
                    parent=window,
                )
                return
            report_rows = [
                tuple(report_tree.item(item, "values"))
                for item in report_tree.get_children()
            ]
            separator = "-+-".join("-" * max(12, len(header)) for header in current_headers)
            report_lines = [
                report_name.get(),
                "Диспетчерская служба аэропорта",
                "",
                " | ".join(current_headers),
                separator,
                *(" | ".join(str(value) for value in row) for row in report_rows),
            ]
            try:
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    encoding="utf-8-sig",
                    suffix=".txt",
                    prefix="airport_report_",
                    delete=False,
                ) as report_file:
                    report_file.write("\n".join(report_lines))
                if os.name != "nt":
                    raise OSError("Печать через системный принтер доступна в Windows.")
                try:
                    subprocess.Popen(
                        ["notepad.exe", "/p", report_file.name],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                except OSError:
                    os.startfile(report_file.name, "print")
            except OSError as error:
                messagebox.showerror(
                    "Печать отчета",
                    f"Не удалось отправить отчет на печать:\n{error}",
                    parent=window,
                )

        report_combo.bind("<<ComboboxSelected>>", lambda _event: load_report())
        load_report()

    def show_help(self, topic: str | tk.Event | None = None) -> str:
        """Открывает интерактивную справку и выбирает подходящую тему."""
        if isinstance(topic, tk.Event):
            topic = None
        if topic is None:
            topic = (
                "Авиакомпании",
                "Аэропорты",
                "Рейсы",
            )[self.notebook.index(self.notebook.select())]

        window = tk.Toplevel(self)
        window.title("Справка по системе")
        window.geometry("760x500")
        window.minsize(620, 400)
        window.transient(self)
        window.protocol("WM_DELETE_WINDOW", window.destroy)
        window.bind("<Escape>", lambda _event: window.destroy())

        content = ttk.Frame(window, padding=12)
        content.pack(fill=tk.BOTH, expand=True)
        content.columnconfigure(1, weight=1)
        content.rowconfigure(1, weight=1)

        ttk.Label(content, text="Поиск по справке:").grid(
            row=0, column=0, sticky=tk.W, padx=(0, 10)
        )
        search = tk.StringVar()
        search_entry = ttk.Entry(content, textvariable=search)
        search_entry.grid(row=0, column=1, columnspan=2, sticky=tk.EW, pady=(0, 10))

        topics_frame = ttk.Frame(content)
        topics_frame.grid(row=1, column=0, sticky=tk.NSEW, padx=(0, 10))
        topics_frame.rowconfigure(0, weight=1)
        topic_list = tk.Listbox(topics_frame, exportselection=False, width=24)
        topic_scrollbar = ttk.Scrollbar(
            topics_frame, orient=tk.VERTICAL, command=topic_list.yview
        )
        topic_list.configure(yscrollcommand=topic_scrollbar.set)
        topic_list.grid(row=0, column=0, sticky=tk.NSEW)
        topic_scrollbar.grid(row=0, column=1, sticky=tk.NS)

        text_frame = ttk.Frame(content)
        text_frame.grid(row=1, column=1, columnspan=2, sticky=tk.NSEW)
        text_frame.rowconfigure(0, weight=1)
        text_frame.columnconfigure(0, weight=1)
        help_text = tk.Text(
            text_frame, wrap=tk.WORD, padx=12, pady=10, state=tk.DISABLED
        )
        text_scrollbar = ttk.Scrollbar(
            text_frame, orient=tk.VERTICAL, command=help_text.yview
        )
        help_text.configure(yscrollcommand=text_scrollbar.set)
        help_text.grid(row=0, column=0, sticky=tk.NSEW)
        text_scrollbar.grid(row=0, column=1, sticky=tk.NS)

        visible_topics: list[str] = []

        def display_topic(selected_topic: str) -> None:
            help_text.configure(state=tk.NORMAL)
            help_text.delete("1.0", tk.END)
            help_text.insert("1.0", self.HELP_TOPICS[selected_topic])
            help_text.configure(state=tk.DISABLED)

        def refresh_topics(*_args: object) -> None:
            query = search.get().strip().casefold()
            visible_topics.clear()
            visible_topics.extend(
                name
                for name, description in self.HELP_TOPICS.items()
                if not query
                or query in name.casefold()
                or query in description.casefold()
            )
            topic_list.delete(0, tk.END)
            for name in visible_topics:
                topic_list.insert(tk.END, name)
            if visible_topics:
                selected = topic if topic in visible_topics else visible_topics[0]
                index = visible_topics.index(selected)
                topic_list.selection_set(index)
                topic_list.activate(index)
                topic_list.see(index)
                display_topic(selected)
            else:
                help_text.configure(state=tk.NORMAL)
                help_text.delete("1.0", tk.END)
                help_text.insert("1.0", "По вашему запросу темы не найдены.")
                help_text.configure(state=tk.DISABLED)

        def select_topic(_event: tk.Event) -> None:
            selection = topic_list.curselection()
            if selection:
                display_topic(visible_topics[selection[0]])

        topic_list.bind("<<ListboxSelect>>", select_topic)
        search.trace_add("write", refresh_topics)
        refresh_topics()
        search_entry.focus_set()
        return "break"

    def show_about(self) -> None:
        messagebox.showinfo(
            "О программе",
            "Диспетчерская служба аэропорта\n"
            "Контроль справочников и расписания рейсов.\n\n"
            "Откройте справку клавишей F1 для подробных инструкций.",
        )

    @staticmethod
    def _draw_airplane(canvas: tk.Canvas) -> None:
        canvas.create_polygon(
            4, 16, 35, 11, 39, 14, 35, 17, 4, 20,
            fill="#3b82c4",
            outline="#24527a",
            width=1,
        )
        canvas.create_polygon(
            18, 14, 24, 3, 28, 3, 26, 14,
            fill="#5ca9e6",
            outline="#24527a",
        )
        canvas.create_polygon(
            18, 18, 25, 29, 29, 29, 26, 18,
            fill="#5ca9e6",
            outline="#24527a",
        )
        canvas.create_polygon(
            6, 16, 1, 9, 4, 8, 12, 15,
            fill="#5ca9e6",
            outline="#24527a",
        )

    def _build_airlines_tab(self) -> None:
        # Вкладка для просмотра и добавления авиакомпаний.
        tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(tab, text="Авиакомпании")

        # Форма принимает название компании и её двухсимвольный IATA-код.
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

        # Таблица показывает записи, полученные из таблицы airlines.
        self.airlines_tree = self._create_tree(
            tab, ("id", "name", "iata_code"), ("ID", "Название", "IATA-код")
        )

    def _build_airports_tab(self) -> None:
        # Вкладка для просмотра и добавления аэропортов.
        tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(tab, text="Аэропорты")

        # Форма содержит название аэропорта, город и трёхсимвольный IATA-код.
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
        # Таблица показывает аэропорты, отсортированные по городу и названию.
        self.airports_tree = self._create_tree(
            tab,
            ("id", "name", "city", "iata_code"),
            ("ID", "Название", "Город", "IATA-код"),
        )

    def _build_flights_tab(self) -> None:
        # Вкладка позволяет создавать и просматривать рейсы.
        tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(tab, text="Рейсы")
        form = ttk.LabelFrame(tab, text="Новый рейс", padding=10)
        form.pack(fill=tk.X, pady=(0, 10))

        self.flight_number = tk.StringVar()
        self.flight_airline = tk.StringVar()
        self.flight_aircraft = tk.StringVar()
        self.flight_departure_airport = tk.StringVar()
        self.flight_arrival_airport = tk.StringVar()
        self.flight_departure_time = tk.StringVar()
        self.flight_arrival_time = tk.StringVar()
        self.flight_status = tk.StringVar()
        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)

        ttk.Label(form, text="Номер:").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(form, textvariable=self.flight_number, width=14).grid(
            row=0, column=1, sticky=tk.EW, padx=(6, 14)
        )
        ttk.Label(form, text="Авиакомпания:").grid(row=0, column=2, sticky=tk.W)
        self.flight_airline_combo = ttk.Combobox(
            form, textvariable=self.flight_airline, state="readonly", width=25
        )
        self.flight_airline_combo.grid(row=0, column=3, sticky=tk.EW, padx=(6, 14))
        ttk.Label(form, text="Самолёт:").grid(row=1, column=0, sticky=tk.W, pady=(8, 0))
        self.flight_aircraft_combo = ttk.Combobox(
            form, textvariable=self.flight_aircraft, state="readonly", width=25
        )
        self.flight_aircraft_combo.grid(
            row=1, column=1, sticky=tk.EW, padx=(6, 14), pady=(8, 0)
        )

        ttk.Label(form, text="Откуда:").grid(row=1, column=2, sticky=tk.W, pady=(8, 0))
        self.flight_departure_combo = ttk.Combobox(
            form, textvariable=self.flight_departure_airport, state="readonly", width=25
        )
        self.flight_departure_combo.grid(
            row=1, column=3, sticky=tk.EW, padx=(6, 14), pady=(8, 0)
        )
        ttk.Label(form, text="Куда:").grid(row=2, column=0, sticky=tk.W, pady=(8, 0))
        self.flight_arrival_combo = ttk.Combobox(
            form, textvariable=self.flight_arrival_airport, state="readonly", width=25
        )
        self.flight_arrival_combo.grid(
            row=2, column=1, sticky=tk.EW, padx=(6, 14), pady=(8, 0)
        )
        ttk.Label(form, text="Статус:").grid(row=2, column=2, sticky=tk.W, pady=(8, 0))
        self.flight_status_combo = ttk.Combobox(
            form, textvariable=self.flight_status, state="readonly", width=20
        )
        self.flight_status_combo.grid(
            row=2, column=3, sticky=tk.EW, padx=(6, 14), pady=(8, 0)
        )

        ttk.Label(form, text="Вылет (ГГГГ-ММ-ДД ЧЧ:ММ):").grid(
            row=3, column=0, sticky=tk.W, pady=(8, 0)
        )
        ttk.Entry(form, textvariable=self.flight_departure_time, width=22).grid(
            row=3, column=1, sticky=tk.EW, padx=(6, 14), pady=(8, 0)
        )
        ttk.Label(form, text="Прилёт (ГГГГ-ММ-ДД ЧЧ:ММ):").grid(
            row=3, column=2, sticky=tk.W, pady=(8, 0)
        )
        ttk.Entry(form, textvariable=self.flight_arrival_time, width=22).grid(
            row=3, column=3, sticky=tk.EW, padx=(6, 14), pady=(8, 0)
        )
        ttk.Button(form, text="Добавить рейс", command=self.add_flight).grid(
            row=3, column=4, pady=(8, 0)
        )

        controls = ttk.Frame(tab)
        controls.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(controls, text="Обновить список", command=self.refresh_flights).pack(
            side=tk.LEFT
        )
        ttk.Label(
            controls,
            text="Рейсы объединяют авиакомпании, самолёты и аэропорты.",
        ).pack(side=tk.LEFT, padx=14)
        # Один рейс объединяет данные из нескольких таблиц базы.
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
        self._refresh_flight_references()

    def _refresh_flight_references(self) -> None:
        self._airline_ids = {}
        airlines = fetch_all("SELECT id, name, iata_code FROM airlines ORDER BY name")
        airline_values = []
        for row in airlines:
            label = f"{row['iata_code']} — {row['name']}"
            self._airline_ids[label] = row["id"]
            airline_values.append(label)
        self.flight_airline_combo["values"] = airline_values

        self._aircraft_ids = {}
        aircrafts = fetch_all(
            """
            SELECT ac.id, ac.registration_number, am.name AS model
            FROM aircrafts ac
            JOIN aircraft_models am ON am.id = ac.model_id
            ORDER BY ac.registration_number
            """
        )
        aircraft_values = []
        for row in aircrafts:
            label = f"{row['registration_number']} — {row['model']}"
            self._aircraft_ids[label] = row["id"]
            aircraft_values.append(label)
        self.flight_aircraft_combo["values"] = aircraft_values

        self._airport_ids = {}
        airports = fetch_all(
            """
            SELECT a.id, a.iata_code, a.name, c.name AS city
            FROM airports a
            JOIN cities c ON c.id = a.city_id
            ORDER BY c.name, a.name
            """
        )
        airport_values = []
        for row in airports:
            label = f"{row['iata_code']} — {row['name']} ({row['city']})"
            self._airport_ids[label] = row["id"]
            airport_values.append(label)
        self.flight_departure_combo["values"] = airport_values
        self.flight_arrival_combo["values"] = airport_values

        self._status_ids = {}
        statuses = fetch_all("SELECT id, name FROM flight_statuses ORDER BY id")
        status_values = []
        for row in statuses:
            self._status_ids[row["name"]] = row["id"]
            status_values.append(row["name"])
        self.flight_status_combo["values"] = status_values

    def add_flight(self) -> None:
        flight_number = self.flight_number.get().strip()
        departure_time = self.flight_departure_time.get().strip()
        arrival_time = self.flight_arrival_time.get().strip()
        required = (
            flight_number,
            self.flight_airline.get(),
            self.flight_aircraft.get(),
            self.flight_departure_airport.get(),
            self.flight_arrival_airport.get(),
            departure_time,
            arrival_time,
            self.flight_status.get(),
        )
        if not all(required):
            messagebox.showwarning(
                "Проверка данных",
                "Заполните все поля формы рейса.",
            )
            return
        if self.flight_departure_airport.get() == self.flight_arrival_airport.get():
            messagebox.showwarning(
                "Проверка данных",
                "Аэропорты вылета и прилёта должны отличаться.",
            )
            return
        try:
            departure_datetime = datetime.strptime(
                departure_time, "%Y-%m-%d %H:%M"
            )
            arrival_datetime = datetime.strptime(arrival_time, "%Y-%m-%d %H:%M")
        except ValueError:
            messagebox.showwarning(
                "Проверка данных",
                "Время укажите в формате ГГГГ-ММ-ДД ЧЧ:ММ.",
            )
            return
        if arrival_datetime <= departure_datetime:
            messagebox.showwarning(
                "Проверка данных",
                "Время прилёта должно быть позже времени вылета.",
            )
            return
        try:
            execute(
                """
                INSERT INTO flights(
                    flight_number, airline_id, aircraft_id,
                    departure_airport_id, arrival_airport_id,
                    departure_time, arrival_time, status_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    flight_number,
                    self._airline_ids[self.flight_airline.get()],
                    self._aircraft_ids[self.flight_aircraft.get()],
                    self._airport_ids[self.flight_departure_airport.get()],
                    self._airport_ids[self.flight_arrival_airport.get()],
                    departure_time,
                    arrival_time,
                    self._status_ids[self.flight_status.get()],
                ),
            )
        except (sqlite3.IntegrityError, KeyError) as error:
            messagebox.showerror("Ошибка", f"Не удалось добавить рейс:\n{error}")
            return
        for variable in (
            self.flight_number,
            self.flight_airline,
            self.flight_aircraft,
            self.flight_departure_airport,
            self.flight_arrival_airport,
            self.flight_departure_time,
            self.flight_arrival_time,
            self.flight_status,
        ):
            variable.set("")
        self.refresh_flights()

    def _create_tree(
        self, parent: ttk.Widget, columns: tuple[str, ...], headings: tuple[str, ...]
    ) -> ttk.Treeview:
        # Общий конструктор таблиц, чтобы одинаково оформить все вкладки.
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True)
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        # Полоса прокрутки подключается к вертикальному перемещению таблицы.
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        # Для каждого технического имени столбца задаём заголовок и размеры.
        for column, heading in zip(columns, headings):
            tree.heading(
                column,
                text=heading,
                command=lambda column=column, tree=tree: self._sort_tree(
                    tree, column
                ),
            )
            tree.column(column, width=130, minwidth=80, anchor=tk.CENTER)
        # Первый столбец с идентификатором делаем уже остальных.
        tree.column(columns[0], width=70)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        return tree

    def _sort_tree(self, tree: ttk.Treeview, column: str) -> None:
        """Сортирует строки таблицы по выбранному столбцу."""
        tree_id = id(tree)
        previous_column, previous_descending = self._tree_sort_state.get(
            tree_id, (None, False)
        )
        descending = (
            not previous_descending if previous_column == column else False
        )
        self._tree_sort_state[tree_id] = (column, descending)

        items = list(tree.get_children())

        def sort_key(item: str) -> tuple[int, object]:
            value = tree.set(item, column)
            try:
                return (0, float(value))
            except ValueError:
                return (1, value.casefold())

        items.sort(key=sort_key, reverse=descending)
        for index, item in enumerate(items):
            tree.move(item, "", index)

    def add_airline(self) -> None:
        # Читаем значения формы и удаляем случайные пробелы по краям.
        name = self.airline_name.get().strip()
        # IATA-код приводим к верхнему регистру перед проверкой и сохранением.
        code = self.airline_code.get().strip().upper()
        # Проверяем обязательное название и длину кода авиакомпании.
        if not name or len(code) != 2:
            messagebox.showwarning(
                "Проверка данных", "Введите название и двухсимвольный IATA-код."
            )
            return
        try:
            # Параметры передаются отдельно от SQL-запроса для безопасной вставки.
            execute("INSERT INTO airlines(name, iata_code) VALUES (?, ?)", (name, code))
        except sqlite3.IntegrityError as error:
            # Например, ошибка появляется при повторении уникального названия или кода.
            messagebox.showerror("Ошибка", f"Не удалось добавить авиакомпанию:\n{error}")
            return
        # После успешного добавления очищаем форму и обновляем таблицу.
        self.airline_name.set("")
        self.airline_code.set("")
        self.refresh_airlines()
        self._refresh_flight_references()

    def add_airport(self) -> None:
        # Получаем и нормализуем значения из формы аэропорта.
        name = self.airport_name.get().strip()
        city = self.airport_city.get().strip()
        code = self.airport_code.get().strip().upper()
        # Для аэропорта обязательны название, город и трёхсимвольный IATA-код.
        if not name or not city or len(code) != 3:
            messagebox.showwarning(
                "Проверка данных",
                "Введите название, город и трёхсимвольный IATA-код.",
            )
            return
        try:
            # Добавляем аэропорт в базу с помощью параметризованного запроса.
            add_airport(name, city, code)
        except sqlite3.IntegrityError as error:
            # Уникальный IATA-код не позволяет создать дубликат аэропорта.
            messagebox.showerror("Ошибка", f"Не удалось добавить аэропорт:\n{error}")
            return
        # Очищаем поля формы и показываем новую запись в таблице.
        self.airport_name.set("")
        self.airport_city.set("")
        self.airport_code.set("")
        self.refresh_airports()
        self._refresh_flight_references()

    def refresh_all(self) -> None:
        # Единая точка обновления всех таблиц после запуска приложения.
        self.refresh_airlines()
        self.refresh_airports()
        self._refresh_flight_references()
        self.refresh_flights()

    def refresh_airlines(self) -> None:
        # Получаем авиакомпании по алфавиту и заменяем строки таблицы.
        self._replace_rows(
            self.airlines_tree,
            fetch_all("SELECT id, name, iata_code FROM airlines ORDER BY name"),
        )

    def refresh_airports(self) -> None:
        # Сначала сортируем аэропорты по городу, затем по названию.
        self._replace_rows(
            self.airports_tree,
            fetch_all(
                """
                SELECT a.id, a.name, c.name AS city, a.iata_code
                FROM airports a
                JOIN cities c ON c.id = a.city_id
                ORDER BY c.name, a.name
                """
            ),
        )

    def refresh_flights(self) -> None:
        # Запрос объединяет рейсы с авиакомпаниями, самолётами и аэропортами.
        self._replace_rows(
            self.flights_tree,
            fetch_all(
                """
                SELECT f.flight_number, a.name AS airline, am.name AS aircraft,
                       dep.iata_code AS departure, arr.iata_code AS arrival,
                       f.departure_time, f.arrival_time, fs.name AS status
                FROM flights f
                -- Получаем понятные названия вместо идентификаторов внешних ключей.
                JOIN airlines a ON a.id = f.airline_id
                JOIN aircrafts ac ON ac.id = f.aircraft_id
                JOIN aircraft_models am ON am.id = ac.model_id
                JOIN airports dep ON dep.id = f.departure_airport_id
                JOIN airports arr ON arr.id = f.arrival_airport_id
                JOIN flight_statuses fs ON fs.id = f.status_id
                ORDER BY f.departure_time
                """
            ),
        )

    @staticmethod
    def _replace_rows(tree: ttk.Treeview, rows: list[sqlite3.Row]) -> None:
        # Удаляем старое содержимое, чтобы не дублировать строки при обновлении.
        tree.delete(*tree.get_children())
        # Row преобразуется в кортеж значений, который понимает Treeview.
        for row in rows:
            tree.insert("", tk.END, values=tuple(row))


if __name__ == "__main__":
    # Создаём таблицы и тестовые записи до запуска графического интерфейса.
    initialize_database()
    if LoginWindow().run():
        # mainloop запускает цикл обработки событий окна Tkinter.
        AirportApplication().mainloop()