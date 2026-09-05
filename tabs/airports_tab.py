import tkinter as tk
from tkinter import messagebox, ttk
from collections.abc import Callable

from database import (
    DatabaseError,
    add_airport,
    delete_airport,
    list_airports,
    update_airport,
)
from .common import SortableTreeMixin, show_database_error


class AirportsTab(ttk.Frame, SortableTreeMixin):
    def __init__(self, parent: ttk.Notebook, on_changed: Callable[[], None]) -> None:
        ttk.Frame.__init__(self, parent, padding=12)
        SortableTreeMixin.__init__(self)
        self._on_changed = on_changed
        parent.add(self, text="Аэропорты")

        form = ttk.LabelFrame(self, text="Аэропорт", padding=10)
        form.pack(fill=tk.X, pady=(0, 10))
        self.name = tk.StringVar()
        self.city = tk.StringVar()
        self.code = tk.StringVar()
        fields = [
            ("Название:", self.name, 32),
            ("Город:", self.city, 22),
            ("IATA-код:", self.code, 10),
        ]
        for column, (label, variable, width) in enumerate(fields):
            ttk.Label(form, text=label).grid(row=0, column=column * 2, sticky=tk.W)
            ttk.Entry(form, textvariable=variable, width=width).grid(
                row=0, column=column * 2 + 1, padx=(6, 14)
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
            ("id", "name", "city", "iata_code"),
            ("ID", "Название", "Город", "IATA-код"),
        )
        self.tree.bind("<<TreeviewSelect>>", self._load_selected)

    def refresh(self) -> None:
        try:
            rows = list_airports()
        except DatabaseError as error:
            show_database_error(self, error, "Не удалось обновить список аэропортов")
            return
        self.tree.delete(*self.tree.get_children())
        for row in rows:
            self.tree.insert("", tk.END, iid=str(row["id"]), values=(
                row["id"], row["name"], row["city"], row["iata_code"]
            ))

    def add(self) -> None:
        name = self.name.get().strip()
        city = self.city.get().strip()
        code = self.code.get().strip().upper()
        if not name or not city or len(code) != 3:
            messagebox.showwarning(
                "Проверка данных",
                "Введите название, город и трёхсимвольный IATA-код.",
            )
            return
        try:
            add_airport(name, city, code)
        except DatabaseError as error:
            if error.is_integrity_error:
                messagebox.showerror("Ошибка", f"Не удалось добавить аэропорт:\n{error}", parent=self)
            else:
                show_database_error(self, error, "Не удалось добавить аэропорт")
            return
        self.name.set("")
        self.city.set("")
        self.code.set("")
        self.refresh()
        self._on_changed()

    def _selected_id(self) -> int | None:
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning(
                "Выбор записи", "Выберите аэропорт в таблице."
            )
            return None
        return int(selection[0])

    def _load_selected(self, _event: tk.Event) -> None:
        selection = self.tree.selection()
        if selection:
            values = self.tree.item(selection[0], "values")
            self.name.set(values[1])
            self.city.set(values[2])
            self.code.set(values[3])

    def edit(self) -> None:
        airport_id = self._selected_id()
        if airport_id is None:
            return
        name = self.name.get().strip()
        city = self.city.get().strip()
        code = self.code.get().strip().upper()
        if not name or not city or len(code) != 3:
            messagebox.showwarning(
                "Проверка данных",
                "Введите название, город и трёхсимвольный IATA-код.",
            )
            return
        try:
            update_airport(airport_id, name, city, code)
        except DatabaseError as error:
            if error.is_integrity_error:
                messagebox.showerror("Ошибка", f"Не удалось изменить аэропорт:\n{error}", parent=self)
            else:
                show_database_error(self, error, "Не удалось изменить аэропорт")
            return
        self.refresh()
        self._on_changed()

    def delete(self) -> None:
        airport_id = self._selected_id()
        if airport_id is None:
            return
        if not messagebox.askyesno(
            "Подтверждение удаления",
            "Удалить выбранный аэропорт?",
        ):
            return
        try:
            delete_airport(airport_id)
        except DatabaseError as error:
            if error.is_integrity_error:
                messagebox.showerror("Ошибка удаления", "Аэропорт используется в рейсах и не может быть удалён.", parent=self)
            else:
                show_database_error(self, error, "Не удалось удалить аэропорт")
            return
        self.refresh()
        self._on_changed()
