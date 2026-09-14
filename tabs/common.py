import tkinter as tk
from tkinter import messagebox, ttk

from database import DatabaseError


class Tooltip:
    """Показывает краткую подсказку при наведении на элемент интерфейса."""

    _DELAY_MS = 500

    def __init__(self, widget: tk.Misc, text: str) -> None:
        self.widget = widget
        self.text = text
        self._after_id: str | None = None
        self._window: tk.Toplevel | None = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _event: tk.Event) -> None:
        self._cancel()
        self._after_id = self.widget.after(self._DELAY_MS, self._show)

    def _show(self) -> None:
        self._after_id = None
        if self._window is not None or not self.text:
            return
        self._window = tk.Toplevel(self.widget)
        self._window.wm_overrideredirect(True)
        self._window.attributes("-topmost", True)
        label = tk.Label(
            self._window,
            text=self.text,
            background="#fff8dc",
            foreground="#222222",
            relief=tk.SOLID,
            borderwidth=1,
            padx=7,
            pady=4,
        )
        label.pack()
        self._window.update_idletasks()
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self._window.geometry(f"+{x}+{y}")

    def _hide(self, _event: tk.Event) -> None:
        self._cancel()
        if self._window is not None:
            self._window.destroy()
            self._window = None

    def _cancel(self) -> None:
        if self._after_id is not None:
            self.widget.after_cancel(self._after_id)
            self._after_id = None


class NotebookTooltip:
    """Показывает подсказку для вкладки, на которую наведен курсор."""

    _DELAY_MS = 500

    def __init__(self, notebook: ttk.Notebook) -> None:
        self.notebook = notebook
        self._after_id: str | None = None
        self._window: tk.Toplevel | None = None
        self._text = ""
        notebook.bind("<Motion>", self._motion, add="+")
        notebook.bind("<Leave>", self._hide, add="+")
        notebook.bind("<ButtonPress>", self._hide, add="+")

    def _motion(self, event: tk.Event) -> None:
        if self.notebook.identify(event.x, event.y) != "label":
            self._hide(event)
            return
        try:
            tab_index = self.notebook.index(f"@{event.x},{event.y}")
        except tk.TclError:
            self._hide(event)
            return
        titles = {
            "Авиакомпании": "Справочник авиакомпаний и их IATA-кодов.",
            "Аэропорты": "Справочник аэропортов, городов и IATA-кодов.",
            "Самолёты": "Список самолётов и их регистрационных номеров.",
            "Рейсы": "Расписание рейсов и управление их статусами.",
            "Пассажиры": "Список пассажиров и их контактных данных.",
            "Сотрудники": "Список сотрудников аэропорта.",
            "Билеты": "Оформление и управление билетами.",
        }
        title = str(self.notebook.tab(tab_index, "text"))
        text = titles.get(title, title)
        if text == self._text and self._window is not None:
            return
        self._hide(event)
        self._text = text
        self._after_id = self.notebook.after(self._DELAY_MS, self._show)

    def _show(self) -> None:
        self._after_id = None
        if self._window is not None or not self._text:
            return
        self._window = tk.Toplevel(self.notebook)
        self._window.wm_overrideredirect(True)
        self._window.attributes("-topmost", True)
        label = tk.Label(
            self._window,
            text=self._text,
            background="#fff8dc",
            foreground="#222222",
            relief=tk.SOLID,
            borderwidth=1,
            padx=7,
            pady=4,
        )
        label.pack()
        self._window.update_idletasks()
        x = self.notebook.winfo_pointerx() + 12
        y = self.notebook.winfo_pointery() + 18
        self._window.geometry(f"+{x}+{y}")

    def _hide(self, _event: tk.Event) -> None:
        if self._after_id is not None:
            self.notebook.after_cancel(self._after_id)
            self._after_id = None
        self._text = ""
        if self._window is not None:
            self._window.destroy()
            self._window = None


def install_tooltips(root: tk.Misc) -> None:
    """Подключает подсказки к полям ввода, спискам и кнопкам окна."""
    button_hints = {
        "Добавить": "Добавить новую запись.",
        "Изменить": "Сохранить изменения выбранной записи.",
        "Удалить": "Удалить выбранную запись.",
        "Обновить статус": "Изменить статус выбранного рейса.",
        "Обновить список": "Обновить список с учетом заданных фильтров.",
        "Отчеты": "Открыть формирование отчетов.",
        "Справка": "Открыть справку по текущей вкладке.",
    }

    def label_for(widget: tk.Misc) -> str | None:
        parent = widget.master
        labels: list[tuple[int, str]] = []
        try:
            widget_column = int(widget.grid_info().get("column", 0))
            widget_row = int(widget.grid_info().get("row", 0))
            for sibling in parent.winfo_children():
                if not isinstance(sibling, ttk.Label):
                    continue
                info = sibling.grid_info()
                if int(info.get("row", 0)) != widget_row:
                    continue
                column = int(info.get("column", 0))
                if column < widget_column:
                    text = str(sibling.cget("text")).rstrip(":")
                    if text:
                        labels.append((column, text))
        except (tk.TclError, ValueError):
            return None
        if labels:
            return max(labels)[1]
        return None

    def visit(widget: tk.Misc) -> None:
        if isinstance(widget, ttk.Notebook):
            NotebookTooltip(widget)
        if isinstance(widget, (tk.Button, ttk.Button)):
            text = str(widget.cget("text"))
            if text in button_hints:
                Tooltip(widget, button_hints[text])
        elif isinstance(widget, (ttk.Entry, ttk.Combobox)):
            label = label_for(widget)
            Tooltip(
                widget,
                f"Введите значение: {label.lower()}." if label else "Введите или выберите значение.",
            )
        for child in widget.winfo_children():
            visit(child)

    visit(root)


def _sort_key(value: object) -> tuple[int, object]:
    try:
        return (0, float(value))
    except (TypeError, ValueError):
        return (1, str(value).casefold())


def sort_rows(
    rows: list[tuple[object, ...]],
    column_index: int,
    descending: bool = False,
) -> list[tuple[object, ...]]:
    return sorted(
        rows,
        key=lambda row: _sort_key(row[column_index]),
        reverse=descending,
    )


class SortableTreeMixin:
    """Shared treeview creation and header sorting for application tabs."""

    def __init__(self) -> None:
        self._tree_sort_state: dict[int, tuple[str | None, bool]] = {}

    def _create_tree(
        self,
        parent: ttk.Widget,
        columns: tuple[str, ...],
        headings: tuple[str, ...],
    ) -> ttk.Treeview:
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True)
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        for column, heading in zip(columns, headings):
            tree.heading(
                column,
                text=heading,
                anchor=tk.W,
                command=lambda column=column: self._sort_tree(tree, column),
            )
            tree.column(column, width=130, minwidth=80, anchor=tk.W)
        tree.column(columns[0], width=70)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        return tree

    def _sort_tree(self, tree: ttk.Treeview, column: str) -> None:
        tree_id = id(tree)
        previous_column, previous_descending = self._tree_sort_state.get(
            tree_id, (None, False)
        )
        descending = (
            not previous_descending if previous_column == column else False
        )
        self._tree_sort_state[tree_id] = (column, descending)

        items = list(tree.get_children())

        items.sort(
            key=lambda item: _sort_key(tree.set(item, column)),
            reverse=descending,
        )
        for index, item in enumerate(items):
            tree.move(item, "", index)


def replace_rows(tree: ttk.Treeview, rows: list[object]) -> None:
    tree.delete(*tree.get_children())
    for row in rows:
        tree.insert("", tk.END, values=tuple(row))


def show_database_error(parent: tk.Misc, error: DatabaseError, action: str) -> None:
    messagebox.showerror(
        "Ошибка базы данных",
        f"{action}:\n{error}",
        parent=parent,
    )
