import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox, ttk

from database import (
    DatabaseError,
    add_passenger,
    delete_passenger,
    list_passengers,
    passport_number_exists,
    update_passenger,
)
from .common import SortableTreeMixin, show_database_error


class PassengersTab(ttk.Frame, SortableTreeMixin):
    def __init__(
        self, parent: ttk.Notebook, on_changed: Callable[[], None] | None = None
    ) -> None:
        ttk.Frame.__init__(self, parent, padding=12)
        SortableTreeMixin.__init__(self)
        self._on_changed = on_changed or (lambda: None)
        parent.add(self, text="Пассажиры")

        form = ttk.LabelFrame(self, text="Пассажир", padding=10)
        form.pack(fill=tk.X, pady=(0, 10))
        self.full_name = tk.StringVar()
        self.passport_number = tk.StringVar()
        self.phone = tk.StringVar()
        self.email = tk.StringVar()
        fields = (
            ("ФИО:", self.full_name, 25),
            ("Паспорт:", self.passport_number, 16),
            ("Телефон:", self.phone, 16),
            ("E-mail:", self.email, 22),
        )
        for column, (label, variable, width) in enumerate(fields):
            ttk.Label(form, text=label).grid(row=0, column=column * 2, sticky=tk.W)
            ttk.Entry(form, textvariable=variable, width=width).grid(
                row=0, column=column * 2 + 1, padx=(6, 12)
            )
        buttons = ttk.Frame(form)
        buttons.grid(row=0, column=8)
        ttk.Button(buttons, text="Добавить", command=self.add).pack(side=tk.LEFT)
        ttk.Button(buttons, text="Изменить", command=self.edit).pack(
            side=tk.LEFT, padx=(6, 0)
        )
        ttk.Button(buttons, text="Удалить", command=self.delete).pack(
            side=tk.LEFT, padx=(6, 0)
        )

        self.tree = self._create_tree(
            self,
            ("id", "full_name", "passport", "phone", "email"),
            ("ID", "ФИО", "Паспорт", "Телефон", "E-mail"),
        )
        self.tree.bind("<<TreeviewSelect>>", self._load_selected)

    def refresh(self) -> None:
        try:
            rows = list_passengers()
        except DatabaseError as error:
            show_database_error(self, error, "Не удалось обновить список пассажиров")
            return
        self.tree.delete(*self.tree.get_children())
        for row in rows:
            self.tree.insert(
                "", tk.END, iid=str(row["id"]),
                values=(row["id"], row["full_name"], row["passport_number"],
                        row["phone"] or "", row["email"] or ""),
            )

    def _values(self) -> tuple[str, str, str, str] | None:
        values = tuple(
            variable.get().strip()
            for variable in (self.full_name, self.passport_number, self.phone, self.email)
        )
        if not values[0] or not values[1]:
            messagebox.showwarning(
                "Проверка данных", "Укажите ФИО и номер паспорта."
            )
            return None
        return values

    def _selected_id(self) -> int | None:
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Выбор записи", "Выберите пассажира в таблице.")
            return None
        return int(selection[0])

    def add(self) -> None:
        self._save(None)

    def edit(self) -> None:
        passenger_id = self._selected_id()
        if passenger_id is not None:
            self._save(passenger_id)

    def _save(self, passenger_id: int | None) -> None:
        values = self._values()
        if values is None:
            return
        full_name, passport, phone, email = values
        try:
            if passport_number_exists(passport, passenger_id):
                messagebox.showwarning(
                    "Проверка данных", "Пассажир с таким номером паспорта уже существует."
                )
                return
            if passenger_id is None:
                add_passenger(full_name, passport, phone, email)
            else:
                update_passenger(passenger_id, full_name, passport, phone, email)
        except DatabaseError as error:
            if error.is_integrity_error:
                messagebox.showerror("Ошибка", f"Не удалось сохранить пассажира:\n{error}", parent=self)
            else:
                show_database_error(self, error, "Не удалось сохранить пассажира")
            return
        self._clear()
        self.refresh()
        self._on_changed()

    def delete(self) -> None:
        passenger_id = self._selected_id()
        if passenger_id is None or not messagebox.askyesno(
            "Подтверждение удаления", "Удалить выбранного пассажира?"
        ):
            return
        try:
            delete_passenger(passenger_id)
        except DatabaseError as error:
            if error.is_integrity_error:
                messagebox.showerror(
                    "Ошибка удаления",
                    "Пассажир используется в билетах и не может быть удалён.",
                    parent=self,
                )
            else:
                show_database_error(self, error, "Не удалось удалить пассажира")
            return
        self._clear()
        self.refresh()
        self._on_changed()

    def _load_selected(self, _event: tk.Event) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        values = self.tree.item(selection[0], "values")
        self.full_name.set(values[1])
        self.passport_number.set(values[2])
        self.phone.set(values[3])
        self.email.set(values[4])

    def _clear(self) -> None:
        for variable in (self.full_name, self.passport_number, self.phone, self.email):
            variable.set("")
