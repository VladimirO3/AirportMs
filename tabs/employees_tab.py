import tkinter as tk
from tkinter import messagebox, ttk

from database import (
    DatabaseError,
    add_employee,
    delete_employee,
    list_employees,
    update_employee,
)
from .common import SortableTreeMixin, show_database_error


class EmployeesTab(ttk.Frame, SortableTreeMixin):
    def __init__(self, parent: ttk.Notebook) -> None:
        ttk.Frame.__init__(self, parent, padding=12)
        SortableTreeMixin.__init__(self)
        parent.add(self, text="Сотрудники")

        form = ttk.LabelFrame(self, text="Сотрудник", padding=10)
        form.pack(fill=tk.X, pady=(0, 10))
        self.full_name = tk.StringVar()
        self.position = tk.StringVar()
        self.phone = tk.StringVar()
        for column, (label, variable, width) in enumerate(
            (("ФИО:", self.full_name, 28), ("Должность:", self.position, 24),
             ("Телефон:", self.phone, 18))
        ):
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
            self, ("id", "full_name", "position", "phone"),
            ("ID", "ФИО", "Должность", "Телефон"),
        )
        self.tree.bind("<<TreeviewSelect>>", self._load_selected)

    def refresh(self) -> None:
        try:
            rows = list_employees()
        except DatabaseError as error:
            show_database_error(self, error, "Не удалось обновить список сотрудников")
            return
        self.tree.delete(*self.tree.get_children())
        for row in rows:
            self.tree.insert(
                "", tk.END, iid=str(row["id"]),
                values=(row["id"], row["full_name"], row["position"], row["phone"] or ""),
            )

    def _values(self) -> tuple[str, str, str] | None:
        values = tuple(variable.get().strip() for variable in (
            self.full_name, self.position, self.phone
        ))
        if not values[0] or not values[1]:
            messagebox.showwarning(
                "Проверка данных", "Укажите ФИО и должность сотрудника."
            )
            return None
        return values

    def _selected_id(self) -> int | None:
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Выбор записи", "Выберите сотрудника в таблице.")
            return None
        return int(selection[0])

    def add(self) -> None:
        values = self._values()
        if values is None:
            return
        try:
            add_employee(*values)
        except DatabaseError as error:
            show_database_error(self, error, "Не удалось добавить сотрудника")
            return
        self._clear()
        self.refresh()

    def edit(self) -> None:
        employee_id = self._selected_id()
        values = self._values() if employee_id is not None else None
        if employee_id is None or values is None:
            return
        try:
            update_employee(employee_id, *values)
        except DatabaseError as error:
            show_database_error(self, error, "Не удалось изменить сотрудника")
            return
        self.refresh()

    def delete(self) -> None:
        employee_id = self._selected_id()
        if employee_id is None or not messagebox.askyesno(
            "Подтверждение удаления", "Удалить выбранного сотрудника?"
        ):
            return
        try:
            delete_employee(employee_id)
        except DatabaseError as error:
            show_database_error(self, error, "Не удалось удалить сотрудника")
            return
        self._clear()
        self.refresh()

    def _load_selected(self, _event: tk.Event) -> None:
        selection = self.tree.selection()
        if selection:
            values = self.tree.item(selection[0], "values")
            self.full_name.set(values[1])
            self.position.set(values[2])
            self.phone.set(values[3])

    def _clear(self) -> None:
        for variable in (self.full_name, self.position, self.phone):
            variable.set("")
