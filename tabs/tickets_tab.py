import tkinter as tk
from tkinter import messagebox, ttk

from database import (
    DatabaseError,
    add_ticket,
    delete_ticket,
    get_ticket,
    list_ticket_flight_references,
    list_ticket_passenger_references,
    list_ticket_statuses,
    list_tickets,
    ticket_number_exists,
    update_ticket,
)
from .common import SortableTreeMixin, show_database_error


class TicketsTab(ttk.Frame, SortableTreeMixin):
    def __init__(self, parent: ttk.Notebook) -> None:
        ttk.Frame.__init__(self, parent, padding=12)
        SortableTreeMixin.__init__(self)
        parent.add(self, text="Билеты")

        form = ttk.LabelFrame(self, text="Билет", padding=10)
        form.pack(fill=tk.X, pady=(0, 10))
        self.ticket_number = tk.StringVar()
        self.passenger = tk.StringVar()
        self.flight = tk.StringVar()
        self.seat_number = tk.StringVar()
        self.booking_status = tk.StringVar()
        self.price = tk.StringVar()
        self.passenger_combo = ttk.Combobox(
            form, textvariable=self.passenger, state="readonly", width=28
        )
        self.flight_combo = ttk.Combobox(
            form, textvariable=self.flight, state="readonly", width=32
        )
        self.status_combo = ttk.Combobox(
            form, textvariable=self.booking_status, state="readonly", width=17
        )
        fields = (
            ("Номер билета:", self.ticket_number, 0, 0, 16),
            ("Пассажир:", self.passenger_combo, 0, 3, 28),
            ("Рейс:", self.flight_combo, 1, 0, 32),
            ("Место:", self.seat_number, 1, 3, 10),
            ("Статус:", self.status_combo, 2, 0, 17),
            ("Цена:", self.price, 2, 3, 12),
        )
        for label, widget, row, column, width in fields:
            ttk.Label(form, text=label).grid(
                row=row, column=column, sticky=tk.W, pady=(0 if row == 0 else 8, 0)
            )
            if isinstance(widget, tk.StringVar):
                widget = ttk.Entry(form, textvariable=widget, width=width)
            widget.grid(
                row=row, column=column + 1, sticky=tk.EW,
                padx=(6, 14), pady=(0 if row == 0 else 8, 0)
            )
        buttons = ttk.Frame(form)
        buttons.grid(row=0, column=6, rowspan=3, padx=(4, 0))
        ttk.Button(buttons, text="Добавить", command=self.add).pack(fill=tk.X)
        ttk.Button(buttons, text="Изменить", command=self.edit).pack(
            fill=tk.X, pady=(6, 0)
        )
        ttk.Button(buttons, text="Удалить", command=self.delete).pack(
            fill=tk.X, pady=(6, 0)
        )

        self.tree = self._create_tree(
            self,
            ("id", "ticket_number", "passenger", "flight", "seat", "status", "price"),
            ("ID", "Номер", "Пассажир", "Рейс", "Место", "Статус", "Цена"),
        )
        self.tree.bind("<<TreeviewSelect>>", self._load_selected)
        self._passenger_ids: dict[str, int] = {}
        self._flight_ids: dict[str, int] = {}
        self.refresh_references()

    def refresh(self) -> None:
        try:
            rows = list_tickets()
        except DatabaseError as error:
            show_database_error(self, error, "Не удалось обновить список билетов")
            return
        self.tree.delete(*self.tree.get_children())
        for row in rows:
            self.tree.insert(
                "", tk.END, iid=str(row["id"]),
                values=(
                    row["id"], row["ticket_number"], row["passenger"], row["flight"],
                    row["seat_number"], row["booking_status"], f"{row['price']:.2f}",
                ),
            )

    def refresh_references(self) -> None:
        try:
            passengers = list_ticket_passenger_references()
            flights = list_ticket_flight_references()
            statuses = list_ticket_statuses()
        except DatabaseError as error:
            show_database_error(self, error, "Не удалось загрузить списки для билетов")
            return
        self._passenger_ids = {
            f"{row['full_name']} — {row['passport_number']}": row["id"]
            for row in passengers
        }
        self.passenger_combo["values"] = tuple(self._passenger_ids)
        self._flight_ids = {
            f"{row['flight_number']} ({row['departure']}–{row['arrival']}, "
            f"{row['departure_time']})": row["id"]
            for row in flights
        }
        self.flight_combo["values"] = tuple(self._flight_ids)
        self.status_combo["values"] = statuses

    def add(self) -> None:
        self._save(None)

    def edit(self) -> None:
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Выбор записи", "Выберите билет в таблице.")
            return
        self._save(int(selection[0]))

    def _save(self, ticket_id: int | None) -> None:
        values = self._values()
        if values is None:
            return
        number, passenger_id, flight_id, seat, status, price = values
        try:
            if ticket_number_exists(number, ticket_id):
                messagebox.showwarning(
                    "Проверка данных", "Билет с таким номером уже существует."
                )
                return
            if ticket_id is None:
                add_ticket(number, passenger_id, flight_id, seat, status, price)
            else:
                update_ticket(ticket_id, number, passenger_id, flight_id, seat, status, price)
        except DatabaseError as error:
            if error.is_integrity_error:
                messagebox.showerror("Ошибка", f"Не удалось сохранить билет:\n{error}", parent=self)
            else:
                show_database_error(self, error, "Не удалось сохранить билет")
            return
        self._clear()
        self.refresh()

    def _values(self) -> tuple[str, int, int, str, str, float] | None:
        number = self.ticket_number.get().strip().upper()
        seat = self.seat_number.get().strip().upper()
        status = self.booking_status.get().strip()
        try:
            price = float(self.price.get().strip().replace(",", "."))
        except ValueError:
            price = 0
        if not number or not seat or not self.passenger.get() or not self.flight.get():
            messagebox.showwarning(
                "Проверка данных", "Заполните номер, пассажира, рейс и место."
            )
            return None
        if status not in self.status_combo["values"] or price <= 0:
            messagebox.showwarning(
                "Проверка данных", "Выберите статус и укажите положительную цену."
            )
            return None
        try:
            return (
                number,
                self._passenger_ids[self.passenger.get()],
                self._flight_ids[self.flight.get()],
                seat,
                status,
                price,
            )
        except KeyError:
            messagebox.showwarning(
                "Проверка данных", "Выберите пассажира, рейс и статус из списков."
            )
            return None

    def delete(self) -> None:
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Выбор записи", "Выберите билет в таблице.")
            return
        if not messagebox.askyesno(
            "Подтверждение удаления", "Удалить выбранный билет?"
        ):
            return
        try:
            delete_ticket(int(selection[0]))
        except DatabaseError as error:
            show_database_error(self, error, "Не удалось удалить билет")
            return
        self._clear()
        self.refresh()

    def _load_selected(self, _event: tk.Event) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        try:
            data = get_ticket(int(selection[0]))
        except DatabaseError as error:
            show_database_error(self, error, "Не удалось загрузить билет")
            return
        if data is None:
            return
        self.ticket_number.set(data["ticket_number"])
        self.passenger.set(self._label_for_id(self._passenger_ids, data["passenger_id"]))
        self.flight.set(self._label_for_id(self._flight_ids, data["flight_id"]))
        self.seat_number.set(data["seat_number"])
        self.booking_status.set(data["booking_status"])
        self.price.set(str(data["price"]))

    @staticmethod
    def _label_for_id(mapping: dict[str, int], value: int) -> str:
        return next((label for label, item_id in mapping.items() if item_id == value), "")

    def _clear(self) -> None:
        for variable in (
            self.ticket_number, self.passenger, self.flight,
            self.seat_number, self.booking_status, self.price,
        ):
            variable.set("")
