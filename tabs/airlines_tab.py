import tkinter as tk
from tkinter import messagebox, ttk
from collections.abc import Callable

from database import DatabaseError, add_airline, delete_airline, list_airlines, update_airline
from .common import SortableTreeMixin, show_database_error


class AirlinesTab(ttk.Frame, SortableTreeMixin):
    def __init__(self, parent: ttk.Notebook, on_changed: Callable[[], None]) -> None:
        ttk.Frame.__init__(self, parent, padding=12)
        SortableTreeMixin.__init__(self)
        self._on_changed = on_changed
        parent.add(self, text="Авиакомпании")

        form = ttk.LabelFrame(self, text="Авиакомпания", padding=10)
        form.pack(fill=tk.X, pady=(0, 10))
        self.name = tk.StringVar()
        self.code = tk.StringVar()
        ttk.Label(form, text="Название:").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(form, textvariable=self.name, width=35).grid(
            row=0, column=1, padx=8
        )
        ttk.Label(form, text="IATA-код:").grid(row=0, column=2, sticky=tk.W)
        ttk.Entry(form, textvariable=self.code, width=10).grid(
            row=0, column=3, padx=8
        )
        buttons = ttk.Frame(form)
        buttons.grid(row=0, column=4, padx=8)
        ttk.Button(buttons, text="Добавить", command=self.add).pack(side=tk.LEFT)
        ttk.Button(buttons, text="Изменить", command=self.edit).pack(
            side=tk.LEFT, padx=(6, 0)
        )
        ttk.Button(buttons, text="Удалить", command=self.delete).pack(
            side=tk.LEFT, padx=(6, 0)
        )
        self.tree = self._create_tree(
            self, ("id", "name", "iata_code"), ("ID", "Название", "IATA-код")
        )
        self.tree.bind("<<TreeviewSelect>>", self._load_selected)

    def refresh(self) -> None:
        try:
            rows = list_airlines()
        except DatabaseError as error:
            show_database_error(self, error, "Не удалось обновить список авиакомпаний")
            return
        self.tree.delete(*self.tree.get_children())
        for row in rows:
            self.tree.insert("", tk.END, iid=str(row["id"]), values=(row["id"], row["name"], row["iata_code"]))

    def add(self) -> None:
        name = self.name.get().strip()
        code = self.code.get().strip().upper()
        if not name or len(code) != 2:
            messagebox.showwarning(
                "Проверка данных", "Введите название и двухсимвольный IATA-код."
            )
            return
        try:
            add_airline(name, code)
        except DatabaseError as error:
            if error.is_integrity_error:
                messagebox.showerror("Ошибка", f"Не удалось добавить авиакомпанию:\n{error}", parent=self)
            else:
                show_database_error(self, error, "Не удалось добавить авиакомпанию")
            return
        self.name.set("")
        self.code.set("")
        self.refresh()
        self._on_changed()

    def _selected_id(self) -> int | None:
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning(
                "Выбор записи", "Выберите авиакомпанию в таблице."
            )
            return None
        return int(selection[0])

    def _load_selected(self, _event: tk.Event) -> None:
        selection = self.tree.selection()
        if selection:
            values = self.tree.item(selection[0], "values")
            self.name.set(values[1])
            self.code.set(values[2])

    def edit(self) -> None:
        airline_id = self._selected_id()
        if airline_id is None:
            return
        name = self.name.get().strip()
        code = self.code.get().strip().upper()
        if not name or len(code) != 2:
            messagebox.showwarning(
                "Проверка данных", "Введите название и двухсимвольный IATA-код."
            )
            return
        try:
            update_airline(airline_id, name, code)
        except DatabaseError as error:
            if error.is_integrity_error:
                messagebox.showerror("Ошибка", f"Не удалось изменить авиакомпанию:\n{error}", parent=self)
            else:
                show_database_error(self, error, "Не удалось изменить авиакомпанию")
            return
        self.refresh()
        self._on_changed()

    def delete(self) -> None:
        airline_id = self._selected_id()
        if airline_id is None:
            return
        if not messagebox.askyesno(
            "Подтверждение удаления",
            "Удалить выбранную авиакомпанию?",
        ):
            return
        try:
            delete_airline(airline_id)
        except DatabaseError as error:
            if error.is_integrity_error:
                messagebox.showerror("Ошибка удаления", "Авиакомпания используется в рейсах и не может быть удалена.", parent=self)
            else:
                show_database_error(self, error, "Не удалось удалить авиакомпанию")
            return
        self.refresh()
        self._on_changed()
