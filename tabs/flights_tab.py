import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk
from collections.abc import Callable

from config import FLIGHT_DATETIME_FORMAT
from database import (
    DatabaseError,
    add_flight,
    delete_flight,
    flight_number_exists,
    get_flight,
    list_airline_references,
    list_aircraft_references,
    list_airport_references,
    list_statuses,
    search_flights,
    update_flight,
    update_flight_status,
)
from .common import SortableTreeMixin, show_database_error


def validate_flight_times(departure: str, arrival: str) -> tuple[bool, str | None]:
    try:
        departure_datetime = datetime.strptime(departure, FLIGHT_DATETIME_FORMAT)
        arrival_datetime = datetime.strptime(arrival, FLIGHT_DATETIME_FORMAT)
    except ValueError:
        return False, "Время укажите в формате ГГГГ-ММ-ДД ЧЧ:ММ."
    if arrival_datetime <= departure_datetime:
        return False, "Время прилёта должно быть позже времени вылета."
    return True, None


class FlightsTab(ttk.Frame, SortableTreeMixin):
    def __init__(
        self, parent: ttk.Notebook, on_changed: Callable[[], None] | None = None
    ) -> None:
        ttk.Frame.__init__(self, parent, padding=12)
        SortableTreeMixin.__init__(self)
        self._on_changed = on_changed or (lambda: None)
        parent.add(self, text="Рейсы")

        form = ttk.LabelFrame(self, text="Рейс", padding=10)
        form.pack(fill=tk.X, pady=(0, 10))
        self.flight_number = tk.StringVar()
        self.airline = tk.StringVar()
        self.aircraft = tk.StringVar()
        self.departure_airport = tk.StringVar()
        self.arrival_airport = tk.StringVar()
        self.departure_time = tk.StringVar()
        self.arrival_time = tk.StringVar()
        self.status = tk.StringVar()
        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)

        ttk.Label(form, text="Номер:").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(form, textvariable=self.flight_number, width=14).grid(
            row=0, column=1, sticky=tk.EW, padx=(6, 14)
        )
        ttk.Label(form, text="Авиакомпания:").grid(row=0, column=2, sticky=tk.W)
        self.airline_combo = ttk.Combobox(
            form, textvariable=self.airline, state="readonly", width=25
        )
        self.airline_combo.grid(row=0, column=3, sticky=tk.EW, padx=(6, 14))

        ttk.Label(form, text="Самолёт:").grid(row=1, column=0, sticky=tk.W, pady=(8, 0))
        self.aircraft_combo = ttk.Combobox(
            form, textvariable=self.aircraft, state="readonly", width=25
        )
        self.aircraft_combo.grid(
            row=1, column=1, sticky=tk.EW, padx=(6, 14), pady=(8, 0)
        )
        ttk.Label(form, text="Откуда:").grid(row=1, column=2, sticky=tk.W, pady=(8, 0))
        self.departure_combo = ttk.Combobox(
            form, textvariable=self.departure_airport, state="readonly", width=25
        )
        self.departure_combo.grid(
            row=1, column=3, sticky=tk.EW, padx=(6, 14), pady=(8, 0)
        )

        ttk.Label(form, text="Куда:").grid(row=2, column=0, sticky=tk.W, pady=(8, 0))
        self.arrival_combo = ttk.Combobox(
            form, textvariable=self.arrival_airport, state="readonly", width=25
        )
        self.arrival_combo.grid(
            row=2, column=1, sticky=tk.EW, padx=(6, 14), pady=(8, 0)
        )
        ttk.Label(form, text="Статус:").grid(row=2, column=2, sticky=tk.W, pady=(8, 0))
        self.status_combo = ttk.Combobox(
            form, textvariable=self.status, state="readonly", width=20
        )
        self.status_combo.grid(
            row=2, column=3, sticky=tk.EW, padx=(6, 14), pady=(8, 0)
        )

        ttk.Label(form, text="Вылет (ГГГГ-ММ-ДД ЧЧ:ММ):").grid(
            row=3, column=0, sticky=tk.W, pady=(8, 0)
        )
        ttk.Entry(form, textvariable=self.departure_time, width=22).grid(
            row=3, column=1, sticky=tk.EW, padx=(6, 14), pady=(8, 0)
        )
        ttk.Label(form, text="Прилёт (ГГГГ-ММ-ДД ЧЧ:ММ):").grid(
            row=3, column=2, sticky=tk.W, pady=(8, 0)
        )
        ttk.Entry(form, textvariable=self.arrival_time, width=22).grid(
            row=3, column=3, sticky=tk.EW, padx=(6, 14), pady=(8, 0)
        )
        buttons = ttk.Frame(form)
        buttons.grid(row=3, column=4, pady=(8, 0))
        ttk.Button(buttons, text="Добавить", command=self.add).pack(side=tk.LEFT)
        ttk.Button(buttons, text="Изменить", command=self.edit).pack(
            side=tk.LEFT, padx=(6, 0)
        )
        ttk.Button(buttons, text="Удалить", command=self.delete).pack(
            side=tk.LEFT, padx=(6, 0)
        )
        ttk.Button(buttons, text="Обновить статус", command=self.update_status).pack(
            side=tk.LEFT, padx=(6, 0)
        )

        controls = ttk.Frame(self)
        controls.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(controls, text="Поиск:").pack(side=tk.LEFT)
        self.search = tk.StringVar()
        search_entry = ttk.Entry(controls, textvariable=self.search, width=28)
        search_entry.pack(side=tk.LEFT, padx=(6, 14))
        ttk.Label(controls, text="Статус:").pack(side=tk.LEFT)
        self.status_filter = tk.StringVar(value="Все статусы")
        self.status_filter_combo = ttk.Combobox(
            controls, textvariable=self.status_filter, state="readonly", width=18
        )
        self.status_filter_combo.pack(side=tk.LEFT, padx=(6, 14))
        ttk.Button(controls, text="Обновить список", command=self.refresh).pack(
            side=tk.LEFT
        )
        self.search.trace_add("write", lambda *_args: self.refresh())
        self.status_filter_combo.bind(
            "<<ComboboxSelected>>", lambda _event: self.refresh()
        )

        self.tree = self._create_tree(
            self,
            (
                "flight_number", "airline", "aircraft", "departure",
                "arrival", "departure_time", "arrival_time", "status",
            ),
            (
                "Рейс", "Авиакомпания", "Самолёт", "Откуда",
                "Куда", "Вылет", "Прилёт", "Статус",
            ),
        )
        self.tree.bind("<<TreeviewSelect>>", self._load_selected)
        self._editing_id: int | None = None
        self._airline_ids: dict[str, int] = {}
        self._aircraft_ids: dict[str, int] = {}
        self._airport_ids: dict[str, int] = {}
        self._status_ids: dict[str, int] = {}
        self.refresh_references()

    def refresh(self) -> None:
        search = self.search.get()
        selected_status = self.status_filter.get()
        status = selected_status if selected_status and selected_status != "Все статусы" else None
        try:
            rows = search_flights(search, status)
        except DatabaseError as error:
            show_database_error(self, error, "Не удалось обновить список рейсов")
            return
        self.tree.delete(*self.tree.get_children())
        for row in rows:
            self.tree.insert(
                "", tk.END, iid=str(row["id"]),
                values=tuple(row[column] for column in (
                    "flight_number", "airline", "aircraft", "departure",
                    "arrival", "departure_time", "arrival_time", "status",
                )),
            )

    def refresh_references(self) -> None:
        try:
            airlines = list_airline_references()
            aircrafts = list_aircraft_references()
            airports = list_airport_references()
            statuses = list_statuses()
        except DatabaseError as error:
            show_database_error(self, error, "Не удалось загрузить справочные списки")
            return
        self._airline_ids = {}
        airline_values = []
        for row in airlines:
            label = f"{row['iata_code']} — {row['name']}"
            self._airline_ids[label] = row["id"]
            airline_values.append(label)
        self.airline_combo["values"] = airline_values

        self._aircraft_ids = {}
        aircraft_values = []
        for row in aircrafts:
            label = f"{row['registration_number']} — {row['model']}"
            self._aircraft_ids[label] = row["id"]
            aircraft_values.append(label)
        self.aircraft_combo["values"] = aircraft_values

        self._airport_ids = {}
        airport_values = []
        for row in airports:
            label = f"{row['iata_code']} — {row['name']} ({row['city']})"
            self._airport_ids[label] = row["id"]
            airport_values.append(label)
        self.departure_combo["values"] = airport_values
        self.arrival_combo["values"] = airport_values

        self._status_ids = {}
        status_values = []
        for row in statuses:
            self._status_ids[row["name"]] = row["id"]
            status_values.append(row["name"])
        self.status_combo["values"] = status_values
        self.status_filter_combo["values"] = ("Все статусы", *status_values)
        if self.status_filter.get() not in self.status_filter_combo["values"]:
            self.status_filter.set("Все статусы")

    def add(self) -> None:
        self._save(None)

    def edit(self) -> None:
        flight_id = self._selected_id()
        if flight_id is not None:
            self._save(flight_id)

    def _save(self, flight_id: int | None) -> None:
        values = self._validated_values()
        if values is None:
            return
        number, airline_id, aircraft_id, departure_id, arrival_id, departure, arrival, status_id = values
        try:
            duplicate = flight_number_exists(number, flight_id)
        except DatabaseError as error:
            show_database_error(self, error, "Не удалось проверить номер рейса")
            return
        if duplicate:
            messagebox.showwarning(
                "Проверка данных",
                f"Рейс с номером «{number}» уже существует.",
            )
            return
        try:
            if flight_id is None:
                add_flight(number, airline_id, aircraft_id, departure_id, arrival_id, departure, arrival, status_id)
            else:
                update_flight(flight_id, number, airline_id, aircraft_id, departure_id, arrival_id, departure, arrival, status_id)
        except DatabaseError as error:
            if error.is_integrity_error:
                messagebox.showerror("Ошибка", f"Не удалось сохранить рейс:\n{error}", parent=self)
            else:
                show_database_error(self, error, "Не удалось сохранить рейс")
            return
        self._clear_form()
        self.refresh()
        self._on_changed()

    def _validated_values(self) -> tuple[object, ...] | None:
        number = self.flight_number.get().strip().upper()
        departure = self.departure_time.get().strip()
        arrival = self.arrival_time.get().strip()
        required = (
            number, self.airline.get(), self.aircraft.get(),
            self.departure_airport.get(), self.arrival_airport.get(),
            departure, arrival, self.status.get(),
        )
        if not all(required):
            messagebox.showwarning("Проверка данных", "Заполните все поля формы рейса.")
            return None
        if self.departure_airport.get() == self.arrival_airport.get():
            messagebox.showwarning(
                "Проверка данных",
                "Аэропорты вылета и прилёта должны отличаться.",
            )
            return None
        valid, error_message = validate_flight_times(departure, arrival)
        if not valid:
            messagebox.showwarning(
                "Проверка данных", error_message or "Некорректное время рейса."
            )
            return None
        try:
            return (
                number,
                self._airline_ids[self.airline.get()],
                self._aircraft_ids[self.aircraft.get()],
                self._airport_ids[self.departure_airport.get()],
                self._airport_ids[self.arrival_airport.get()],
                departure,
                arrival,
                self._status_ids[self.status.get()],
            )
        except KeyError:
            messagebox.showerror(
                "Ошибка", "Выберите значения из всех справочных списков."
            )
            return None

    def update_status(self) -> None:
        flight_id = self._selected_id()
        if flight_id is None:
            return
        status_id = self._status_ids.get(self.status.get())
        if status_id is None:
            messagebox.showwarning("Проверка данных", "Выберите новый статус рейса.")
            return
        try:
            update_flight_status(flight_id, status_id)
        except DatabaseError as error:
            if error.is_integrity_error:
                messagebox.showerror("Ошибка", f"Не удалось обновить статус:\n{error}", parent=self)
            else:
                show_database_error(self, error, "Не удалось обновить статус")
            return
        self.refresh()

    def delete(self) -> None:
        flight_id = self._selected_id()
        if flight_id is None:
            return
        if not messagebox.askyesno("Подтверждение удаления", "Удалить выбранный рейс?"):
            return
        try:
            delete_flight(flight_id)
        except DatabaseError as error:
            show_database_error(self, error, "Не удалось удалить рейс")
            return
        self._clear_form()
        self.refresh()
        self._on_changed()

    def _selected_id(self) -> int | None:
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Выбор записи", "Выберите рейс в таблице.")
            return None
        return int(selection[0])

    def _load_selected(self, _event: tk.Event) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        flight_id = int(selection[0])
        try:
            data = get_flight(flight_id)
        except DatabaseError as error:
            show_database_error(self, error, "Не удалось загрузить рейс")
            return
        if data is None:
            return
        self._editing_id = flight_id
        self.flight_number.set(data["flight_number"])
        self.airline.set(self._label_for_id(self._airline_ids, data["airline_id"]))
        self.aircraft.set(self._label_for_id(self._aircraft_ids, data["aircraft_id"]))
        self.departure_airport.set(
            self._label_for_id(self._airport_ids, data["departure_airport_id"])
        )
        self.arrival_airport.set(
            self._label_for_id(self._airport_ids, data["arrival_airport_id"])
        )
        self.departure_time.set(data["departure_time"])
        self.arrival_time.set(data["arrival_time"])
        self.status.set(self._label_for_id(self._status_ids, data["status_id"]))

    @staticmethod
    def _label_for_id(mapping: dict[str, int], value: int) -> str:
        return next((label for label, item_id in mapping.items() if item_id == value), "")

    def _clear_form(self) -> None:
        self._editing_id = None
        for variable in (
            self.flight_number, self.airline, self.aircraft,
            self.departure_airport, self.arrival_airport,
            self.departure_time, self.arrival_time, self.status,
        ):
            variable.set("")
