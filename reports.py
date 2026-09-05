import base64
import os
import shutil
import subprocess
import tempfile
import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox, ttk

from config import (
    APP_TITLE,
    COLORS,
    PREVIEW_GEOMETRY,
    PREVIEW_MIN_HEIGHT,
    PREVIEW_MIN_WIDTH,
    REPORT_GEOMETRY,
    REPORT_MIN_HEIGHT,
    REPORT_MIN_WIDTH,
)
from database import (
    DatabaseError,
    report_airlines,
    report_airports,
    report_flight_statuses,
    report_schedule,
    fetch_all,
)


ReportLoader = Callable[[], list[object]]
ReportSource = ReportLoader | str
REPORTS: dict[str, tuple[tuple[str, ...], ReportSource]] = {
    "Расписание рейсов": (
        ("Рейс", "Авиакомпания", "Самолёт", "Откуда", "Куда", "Вылет", "Прилёт", "Статус"),
        report_schedule,
    ),
    "Авиакомпании": (("ID", "Название", "IATA-код"), report_airlines),
    "Аэропорты": (("ID", "Название", "Город", "IATA-код"), report_airports),
    "Распределение рейсов по статусам": (("Статус", "Количество рейсов"), report_flight_statuses),
}


def available_printers() -> list[str]:
    """Return installed Windows printer names without requiring extra packages."""
    if os.name != "nt":
        return []
    try:
        import win32print  # type: ignore[import-not-found]

        flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        return sorted({item[2] for item in win32print.EnumPrinters(flags)})
    except (ImportError, OSError):
        pass
    powershell = shutil.which("powershell") or shutil.which("pwsh")
    if not powershell:
        return []
    try:
        result = subprocess.run(
            [
                powershell,
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "Get-CimInstance Win32_Printer | Select-Object -ExpandProperty Name",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError):
        return []
    return sorted({line.strip() for line in result.stdout.splitlines() if line.strip()})


class PrintPreviewWindow:
    def __init__(self, parent: tk.Misc, title: str, report_text: str) -> None:
        self.parent = parent
        self.report_text = report_text
        self._process: subprocess.Popen[bytes] | None = None
        self._report_path: str | None = None
        self.window = tk.Toplevel(parent)
        self.window.title(f"Предварительный просмотр — {title}")
        self.window.geometry(PREVIEW_GEOMETRY)
        self.window.minsize(PREVIEW_MIN_WIDTH, PREVIEW_MIN_HEIGHT)
        self.window.transient(parent)
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self._build()

    def _build(self) -> None:
        content = ttk.Frame(self.window, padding=12)
        content.pack(fill=tk.BOTH, expand=True)
        content.rowconfigure(0, weight=1)
        content.columnconfigure(0, weight=1)
        self.text = tk.Text(content, wrap=tk.NONE, font=("Consolas", 10))
        scrollbar = ttk.Scrollbar(content, orient=tk.VERTICAL, command=self.text.yview)
        self.text.configure(yscrollcommand=scrollbar.set)
        self.text.grid(row=0, column=0, sticky=tk.NSEW)
        scrollbar.grid(row=0, column=1, sticky=tk.NS)
        self.text.insert("1.0", self.report_text)
        self.text.configure(state=tk.DISABLED)

        controls = ttk.Frame(content, padding=(0, 10, 0, 0))
        controls.grid(row=1, column=0, columnspan=2, sticky=tk.EW)
        ttk.Label(controls, text="Принтер:").pack(side=tk.LEFT)
        self.printers = available_printers()
        self.printer = tk.StringVar(value=self.printers[0] if self.printers else "")
        self.printer_combo = ttk.Combobox(
            controls,
            textvariable=self.printer,
            values=self.printers,
            state="readonly" if self.printers else "disabled",
            width=45,
        )
        self.printer_combo.pack(side=tk.LEFT, padx=(8, 12), fill=tk.X, expand=True)
        self.print_button = ttk.Button(controls, text="Печать", command=self.print)
        self.print_button.pack(side=tk.LEFT)
        ttk.Button(controls, text="Закрыть", command=self.close).pack(
            side=tk.LEFT, padx=(8, 0)
        )
        self.status = ttk.Label(content, text="")
        self.status.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(8, 0))
        if not self.printers:
            self.status.configure(text="Доступные принтеры не найдены.")
            self.print_button.configure(state=tk.DISABLED)

    def print(self) -> None:
        printer = self.printer.get().strip()
        if not printer:
            messagebox.showerror(
                "Печать отчета",
                "Выберите доступный принтер.",
                parent=self.window,
            )
            return
        try:
            report_file = tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8-sig",
                suffix=".txt",
                prefix="airport_report_",
                delete=False,
            )
            report_file.write(self.report_text)
            report_file.close()
            self._report_path = report_file.name
            self._process = self._start_print(report_file.name, printer)
        except OSError as error:
            self._cleanup_file()
            messagebox.showerror(
                "Печать отчета",
                f"Не удалось отправить отчет на печать:\n{error}",
                parent=self.window,
            )
            return
        self.print_button.configure(state=tk.DISABLED)
        self.status.configure(text=f"Отправка на печать: {printer}")
        self._wait_for_print()

    @staticmethod
    def _start_print(path: str, printer: str) -> subprocess.Popen[bytes]:
        if os.name != "nt":
            raise OSError("Печать через системный принтер доступна только в Windows.")
        powershell = shutil.which("powershell") or shutil.which("pwsh")
        if powershell:
            encoded_path = base64.b64encode(path.encode("utf-8")).decode("ascii")
            encoded_printer = base64.b64encode(printer.encode("utf-8")).decode("ascii")
            script = (
                f"$path = [Text.Encoding]::UTF8.GetString("
                f"[Convert]::FromBase64String('{encoded_path}')); "
                f"$printer = [Text.Encoding]::UTF8.GetString("
                f"[Convert]::FromBase64String('{encoded_printer}')); "
                "$content = Get-Content -LiteralPath $path -Raw; "
                "$content | Out-Printer -Name $printer"
            )
            encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
            return subprocess.Popen(
                [powershell, "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        return subprocess.Popen(
            ["notepad.exe", "/p", path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

    def _wait_for_print(self) -> None:
        if self._process is None:
            return
        if self._process.poll() is None:
            self.window.after(200, self._wait_for_print)
            return
        returncode = self._process.returncode
        self._cleanup_file()
        if returncode:
            self.status.configure(text="Печать не выполнена.")
            messagebox.showerror(
                "Печать отчета",
                "Принтер недоступен или не принял отчет.",
                parent=self.window,
            )
        else:
            self.status.configure(text="Отчет отправлен на печать.")
        self.print_button.configure(state="normal")

    def _cleanup_file(self) -> None:
        if self._report_path:
            try:
                os.unlink(self._report_path)
            except FileNotFoundError:
                pass
            except OSError:
                self.parent.after(1000, self._cleanup_file)
            else:
                self._report_path = None

    def close(self) -> None:
        if self._process is not None and self._process.poll() is None:
            self.parent.after(60000, self._cleanup_file)
        else:
            self._cleanup_file()
        self.window.destroy()


class ReportWindow:
    def __init__(self, parent: tk.Misc, reports: dict = REPORTS) -> None:
        self.parent = parent
        self.reports = reports
        self.window = tk.Toplevel(parent)
        self.window.title("Отчеты диспетчерской службы")
        self.window.geometry(REPORT_GEOMETRY)
        self.window.minsize(REPORT_MIN_WIDTH, REPORT_MIN_HEIGHT)
        self.window.transient(parent)
        self._headers: tuple[str, ...] = ()
        self._rows: list[tuple[object, ...]] = []
        self._sort_state: tuple[str | None, bool] = (None, False)
        self.preview: PrintPreviewWindow | None = None
        self._build()

    def _build(self) -> None:
        controls = ttk.Frame(self.window, padding=(12, 12, 12, 8))
        controls.pack(fill=tk.X)
        ttk.Label(controls, text="Тип отчета:").grid(row=0, column=0, sticky=tk.W, padx=(0, 8))
        self.report_name = tk.StringVar(value=next(iter(self.reports)))
        self.report_combo = ttk.Combobox(controls, textvariable=self.report_name, values=tuple(self.reports), state="readonly", width=32)
        self.report_combo.grid(row=0, column=1, sticky=tk.W)
        ttk.Button(controls, text="Сформировать", command=self.load_report).grid(row=0, column=2, padx=8)
        ttk.Button(controls, text="Предпросмотр и печать", command=self.print_report).grid(row=0, column=3)
        table_frame = ttk.Frame(self.window, padding=(12, 0, 12, 12))
        table_frame.pack(fill=tk.BOTH, expand=True)
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        self.tree = ttk.Treeview(table_frame, show="headings")
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.grid(row=0, column=0, sticky=tk.NSEW)
        scrollbar.grid(row=0, column=1, sticky=tk.NS)
        self.report_combo.bind("<<ComboboxSelected>>", lambda _event: self.load_report())
        self.load_report()

    def load_report(self) -> None:
        self._headers, loader = self.reports[self.report_name.get()]
        try:
            source_rows = loader() if callable(loader) else fetch_all(loader)
            self._rows = [tuple(row) for row in source_rows]
        except DatabaseError as error:
            messagebox.showerror("Отчеты", str(error), parent=self.window)
            return
        self._sort_state = (None, False)
        self.tree.delete(*self.tree.get_children())
        columns = tuple(f"column_{index}" for index in range(len(self._headers)))
        self.tree["columns"] = columns
        for column, heading in zip(columns, self._headers):
            self.tree.heading(column, text=heading, command=lambda column=column: self.sort_report(column))
            self.tree.column(column, width=140, minwidth=90, anchor=tk.CENTER)
        for row in self._rows:
            self.tree.insert("", tk.END, values=row)

    def sort_report(self, column: str) -> None:
        column_index = int(column.rsplit("_", 1)[1])
        previous_column, previous_descending = self._sort_state
        descending = not previous_descending if previous_column == column else False
        self._sort_state = (column, descending)
        rows = [tuple(self.tree.item(item, "values")) for item in self.tree.get_children()]

        def sort_key(row: tuple[str, ...]) -> tuple[int, object]:
            value = row[column_index]
            try:
                return (0, float(value))
            except (TypeError, ValueError):
                return (1, str(value).casefold())

        rows.sort(key=sort_key, reverse=descending)
        self.tree.delete(*self.tree.get_children())
        for row in rows:
            self.tree.insert("", tk.END, values=row)

    def print_report(self) -> None:
        if not self._headers:
            messagebox.showwarning("Печать отчета", "Сначала сформируйте отчет.", parent=self.window)
            return
        rows = [tuple(self.tree.item(item, "values")) for item in self.tree.get_children()]
        separator = "-+-".join("-" * max(12, len(header)) for header in self._headers)
        report_lines = [
            self.report_name.get(),
            APP_TITLE,
            "",
            " | ".join(self._headers),
            separator,
            *(" | ".join(str(value) for value in row) for row in rows),
        ]
        self.preview = PrintPreviewWindow(self.window, self.report_name.get(), "\n".join(report_lines))


def show_reports(parent: tk.Misc) -> ReportWindow:
    return ReportWindow(parent)
