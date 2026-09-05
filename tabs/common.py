import tkinter as tk
from tkinter import messagebox, ttk

from database import DatabaseError


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
                command=lambda column=column: self._sort_tree(tree, column),
            )
            tree.column(column, width=130, minwidth=80, anchor=tk.CENTER)
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
