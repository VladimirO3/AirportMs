import tkinter as tk
from tkinter import messagebox, ttk
from collections.abc import Callable

from database import (
    DatabaseError,
    add_aircraft,
    delete_aircraft,
    list_aircraft_models,
    list_aircrafts,
    update_aircraft,
)
from .common import SortableTreeMixin, show_database_error


class AircraftsTab(ttk.Frame, SortableTreeMixin):
    def __init__(self, parent: ttk.Notebook, on_changed: Callable[[], None]) -> None:
        ttk.Frame.__init__(self, parent, padding=12)
        SortableTreeMixin.__init__(self)
        self._on_changed = on_changed
        parent.add(self, text="Самолёты")

        form = ttk.LabelFrame(self, text="Самолёт", padding=10)
        form.pack(fill=tk.X, pady=(0, 10))
        self.model = tk.StringVar()
        self.registration = tk.StringVar()
        self.seats = tk.StringVar()
        ttk.Label(form, text="Модель:").grid(row=0, column=0, sticky=tk.W)
        self.model_combo = ttk.Combobox(
            form, textvariable=self.model, width=25
        )
        self.model_combo.grid(row=0, column=1, padx=(6, 14))
        ttk.Label(form, text="Регистрационный номер:").grid(
            row=0, column=2, sticky=tk.W
        )
        ttk.Entry(form, textvariable=self.registration, width=18).grid(
            row=0, column=3, padx=(6, 14)
        )
        ttk.Label(form, text="Мест:").grid(row=0, column=4, sticky=tk.W)
        ttk.Entry(form, textvariable=self.seats, width=8).grid(
            row=0, column=5, padx=(6, 14)
        )
        buttons = ttk.Frame(form)
        buttons.grid(row=0, column=6)
        ttk.Button(buttons, text="Добавить", command=self.add).pack(side=tk.LEFT)
        ttk.Button(buttons, text="Изменить", command=self.edit).pack(
            side=tk.LEFT, padx=(6, 0)
        )
        ttk.Button(buttons, text="Удалить", command=self.delete).pack(
            side=tk.LEFT, padx=(6, 0)
        )

        self.tree = self._create_tree(
            self,
            ("id", "model", "registration_number", "seats"),
            ("ID", "Модель", "Регистрационный номер", "Мест"),
        )
        self.tree.bind("<<TreeviewSelect>>", self._load_selected)
        self.refresh()

    def refresh(self) -> None:
        try:
            models = list_aircraft_models()
            rows = list_aircrafts()
        except DatabaseError as error:
            show_database_error(self, error, "Не удалось обновить список самолётов")
            return
        self.model_combo["values"] = tuple(row["name"] for row in models)
        self.tree.delete(*self.tree.get_children())
        for row in rows:
            self.tree.insert("", tk.END, iid=str(row["id"]), values=(
                row["id"], row["model"], row["registration_number"], row["seats"]
            ))

    def _values(self) -> tuple[str, str, int] | None:
        model = self.model.get().strip()
        registration = self.registration.get().strip().upper()
        try:
            seats = int(self.seats.get().strip())
        except ValueError:
            seats = 0
        if not model or not registration or seats <= 0:
            messagebox.showwarning(
                "Проверка данных",
                "Укажите модель, регистрационный номер и положительное число мест.",
            )
            return None
        return model, registration, seats

    def add(self) -> None:
        values = self._values()
        if values is None:
            return
        model, registration, seats = values
        try:
            add_aircraft(model, registration, seats)
        except DatabaseError as error:
            if error.is_integrity_error:
                messagebox.showerror("Ошибка", f"Не удалось добавить самолёт:\n{error}", parent=self)
            else:
                show_database_error(self, error, "Не удалось добавить самолёт")
            return
        self._clear()
        self.refresh()
        self._on_changed()

    def _selected_id(self) -> int | None:
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Выбор записи", "Выберите самолёт в таблице.")
            return None
        return int(selection[0])

    def edit(self) -> None:
        aircraft_id = self._selected_id()
        if aircraft_id is None:
            return
        values = self._values()
        if values is None:
            return
        model, registration, seats = values
        try:
            update_aircraft(aircraft_id, model, registration, seats)
        except DatabaseError as error:
            if error.is_integrity_error:
                messagebox.showerror("Ошибка", f"Не удалось изменить самолёт:\n{error}", parent=self)
            else:
                show_database_error(self, error, "Не удалось изменить самолёт")
            return
        self.refresh()
        self._on_changed()

    def delete(self) -> None:
        aircraft_id = self._selected_id()
        if aircraft_id is None:
            return
        if not messagebox.askyesno(
            "Подтверждение удаления", "Удалить выбранный самолёт?"
        ):
            return
        try:
            delete_aircraft(aircraft_id)
        except DatabaseError as error:
            if error.is_integrity_error:
                messagebox.showerror("Ошибка удаления", "Самолёт используется в рейсах и не может быть удалён.", parent=self)
            else:
                show_database_error(self, error, "Не удалось удалить самолёт")
            return
        self.refresh()
        self._on_changed()

    def _load_selected(self, _event: tk.Event) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        values = self.tree.item(selection[0], "values")
        self.model.set(values[1])
        self.registration.set(values[2])
        self.seats.set(values[3])

    def _clear(self) -> None:
        self.model.set("")
        self.registration.set("")
        self.seats.set("")
