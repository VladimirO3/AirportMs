import tkinter as tk
from tkinter import messagebox, ttk

from config import COLORS, DEFAULT_LOGIN, DEFAULT_PASSWORD, LOGIN_GEOMETRY, LOGIN_TITLE


def validate_credentials(login: str, password: str) -> bool:
    return login.strip() == DEFAULT_LOGIN and password == DEFAULT_PASSWORD


class LoginWindow(tk.Tk):
    """Окно входа диспетчера в приложение."""

    DEFAULT_LOGIN = DEFAULT_LOGIN
    DEFAULT_PASSWORD = DEFAULT_PASSWORD

    def __init__(self) -> None:
        super().__init__()
        self.authenticated = False
        self.background_color = COLORS["background"]
        self.configure(bg=self.background_color)
        self.title(LOGIN_TITLE)
        self.geometry(LOGIN_GEOMETRY)
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._close)
        self._configure_style()
        self._build_interface()
        self.bind("<Return>", lambda _event: self._check_credentials())

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("TFrame", background=self.background_color)
        style.configure("TLabel", background=self.background_color)
        style.configure(
            "Login.TLabel",
            background=self.background_color,
            foreground=COLORS["text"],
            font=("Segoe UI", 16, "bold"),
        )
        style.configure(
            "Login.TButton",
            background=COLORS["button"],
            foreground=COLORS["text"],
            padding=(12, 6),
        )
        style.map(
            "Login.TButton",
            background=[
                ("active", COLORS["button_active"]),
                ("pressed", COLORS["button_pressed"]),
            ],
        )

    def _build_interface(self) -> None:
        frame = ttk.Frame(self, padding=24)
        frame.pack(fill=tk.BOTH, expand=True)
        frame.columnconfigure(1, weight=1)

        ttk.Label(
            frame,
            text="Вход в диспетчерскую службу",
            style="Login.TLabel",
        ).grid(row=0, column=0, columnspan=2, pady=(0, 18))
        ttk.Label(frame, text="Логин:").grid(
            row=1, column=0, sticky=tk.W, pady=6
        )
        self.login = tk.StringVar()
        login_entry = ttk.Entry(frame, textvariable=self.login, width=28)
        login_entry.grid(row=1, column=1, sticky=tk.EW, padx=(12, 0), pady=6)
        ttk.Label(frame, text="Пароль:").grid(
            row=2, column=0, sticky=tk.W, pady=6
        )
        self.password = tk.StringVar()
        password_entry = ttk.Entry(
            frame, textvariable=self.password, show="*", width=28
        )
        password_entry.grid(row=2, column=1, sticky=tk.EW, padx=(12, 0), pady=6)
        ttk.Label(
            frame,
            text=f"По умолчанию: {DEFAULT_LOGIN} / {DEFAULT_PASSWORD}",
            foreground=COLORS["muted_text"],
        ).grid(row=3, column=0, columnspan=2, pady=(4, 12))
        ttk.Button(
            frame,
            text="Войти",
            style="Login.TButton",
            command=self._check_credentials,
        ).grid(row=4, column=0, columnspan=2)
        login_entry.focus_set()

    def _check_credentials(self) -> None:
        if not self.login.get().strip() or not self.password.get():
            messagebox.showwarning(
                "Вход в систему",
                "Введите логин и пароль.",
                parent=self,
            )
            return
        if validate_credentials(self.login.get(), self.password.get()):
            self.authenticated = True
            self.destroy()
            return
        self.password.set("")
        messagebox.showerror(
            "Ошибка входа",
            "Неверный логин или пароль.",
            parent=self,
        )

    def _close(self) -> None:
        self.authenticated = False
        self.destroy()

    def run(self) -> bool:
        self.mainloop()
        return self.authenticated
