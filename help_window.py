import tkinter as tk
from tkinter import ttk

from config import HELP_GEOMETRY, HELP_MIN_HEIGHT, HELP_MIN_WIDTH


HELP_TOPICS = {
    "Обзор системы": (
        "Диспетчерская служба предназначена для ведения справочников и "
        "оперативного управления расписанием рейсов.\n\n"
        "Диспетчер может просматривать справочники и рейсы, а также добавлять, "
        "изменять и удалять записи. Выберите нужную вкладку и нажмите нужную "
        "кнопку."
    ),
    "Авиакомпании": (
        "На вкладке «Авиакомпании» можно просматривать, добавлять, изменять "
        "и удалять авиакомпании.\n\n"
        "Укажите название и уникальный двухсимвольный IATA-код. Код автоматически "
        "переводится в верхний регистр."
    ),
    "Аэропорты": (
        "На вкладке «Аэропорты» можно просматривать, добавлять, изменять и "
        "удалять аэропорты.\n\n"
        "Для новой записи укажите название, город и уникальный трёхсимвольный "
        "IATA-код. Выберите строку для изменения или удаления. Города "
        "сохраняются как отдельные справочные данные."
    ),
    "Самолёты": (
        "На вкладке «Самолёты» ведётся справочник воздушных судов.\n\n"
        "Укажите модель, уникальный регистрационный номер и положительное "
        "количество мест. Выберите строку для изменения или удаления. "
        "Самолёт, назначенный рейсу, удалить нельзя."
    ),
    "Рейсы": (
        "На вкладке «Рейсы» создаются маршруты между аэропортами.\n\n"
        "Выберите авиакомпанию, самолёт, аэропорты вылета и прилёта, статус и "
        "укажите время в формате ГГГГ-ММ-ДД ЧЧ:ММ. Связанные справочники "
        "заполняются автоматически из базы данных. Используйте поиск и фильтр "
        "статуса, а выбранный рейс можно изменить, удалить или обновить ему "
        "статус. Номера рейсов уникальны."
    ),
    "Проверка данных": (
        "Приложение проверяет обязательные поля, формат IATA-кодов, уникальность "
        "записей, положительное число мест и корректность времени рейса.\n\n"
        "Аэропорты вылета и прилёта должны отличаться, а время прилёта должно "
        "быть позже времени вылета. Ошибки отображаются в отдельном сообщении."
    ),
    "Горячие клавиши": (
        "F1 — открыть справку.\n"
        "Esc — закрыть окно справки.\n\n"
        "В окне справки выберите тему слева или введите слово в поле поиска. "
        "Результаты фильтруются по названию и содержанию темы."
    ),
    "Отчеты и печать": (
        "Нажмите кнопку «Отчеты». Доступны "
        "расписание рейсов, списки авиакомпаний и аэропортов, а также сводка "
        "рейсов по статусам.\n\n"
        "Нажатие на заголовок столбца сортирует данные. Кнопка "
        "«Предпросмотр и печать» сначала показывает текст отчета, затем позволяет "
        "выбрать установленный принтер Windows. Если принтеры недоступны, "
        "кнопка печати отключена."
    ),
}


class HelpWindow:
    def __init__(
        self,
        parent: tk.Misc,
        topics: dict[str, str] = HELP_TOPICS,
        initial_topic: str | None = None,
    ) -> None:
        self.topics = topics
        self.initial_topic = initial_topic
        self.window = tk.Toplevel(parent)
        self.window.title("Справка по системе")
        self.window.geometry(HELP_GEOMETRY)
        self.window.minsize(HELP_MIN_WIDTH, HELP_MIN_HEIGHT)
        self.window.transient(parent)
        self.window.protocol("WM_DELETE_WINDOW", self.window.destroy)
        self.window.bind("<Escape>", lambda _event: self.window.destroy())
        self._build()

    def _build(self) -> None:
        content = ttk.Frame(self.window, padding=12)
        content.pack(fill=tk.BOTH, expand=True)
        content.columnconfigure(1, weight=1)
        content.rowconfigure(1, weight=1)
        ttk.Label(content, text="Поиск по справке:").grid(
            row=0, column=0, sticky=tk.W, padx=(0, 10)
        )
        self.search = tk.StringVar()
        search_entry = ttk.Entry(content, textvariable=self.search)
        search_entry.grid(row=0, column=1, columnspan=2, sticky=tk.EW, pady=(0, 10))

        topics_frame = ttk.Frame(content)
        topics_frame.grid(row=1, column=0, sticky=tk.NSEW, padx=(0, 10))
        topics_frame.rowconfigure(0, weight=1)
        self.topic_list = tk.Listbox(topics_frame, exportselection=False, width=24)
        topic_scrollbar = ttk.Scrollbar(
            topics_frame, orient=tk.VERTICAL, command=self.topic_list.yview
        )
        self.topic_list.configure(yscrollcommand=topic_scrollbar.set)
        self.topic_list.grid(row=0, column=0, sticky=tk.NSEW)
        topic_scrollbar.grid(row=0, column=1, sticky=tk.NS)

        text_frame = ttk.Frame(content)
        text_frame.grid(row=1, column=1, columnspan=2, sticky=tk.NSEW)
        text_frame.rowconfigure(0, weight=1)
        text_frame.columnconfigure(0, weight=1)
        self.help_text = tk.Text(
            text_frame, wrap=tk.WORD, padx=12, pady=10, state=tk.DISABLED
        )
        text_scrollbar = ttk.Scrollbar(
            text_frame, orient=tk.VERTICAL, command=self.help_text.yview
        )
        self.help_text.configure(yscrollcommand=text_scrollbar.set)
        self.help_text.grid(row=0, column=0, sticky=tk.NSEW)
        text_scrollbar.grid(row=0, column=1, sticky=tk.NS)

        self.visible_topics: list[str] = []
        self.topic_list.bind("<<ListboxSelect>>", self._select_topic)
        self.search.trace_add("write", self.refresh_topics)
        self.refresh_topics()
        search_entry.focus_set()

    def display_topic(self, topic: str) -> None:
        self.help_text.configure(state=tk.NORMAL)
        self.help_text.delete("1.0", tk.END)
        self.help_text.insert("1.0", self.topics[topic])
        self.help_text.configure(state=tk.DISABLED)

    def refresh_topics(self, *_args: object) -> None:
        query = self.search.get().strip().casefold()
        self.visible_topics = [
            name
            for name, description in self.topics.items()
            if not query
            or query in name.casefold()
            or query in description.casefold()
        ]
        self.topic_list.delete(0, tk.END)
        for name in self.visible_topics:
            self.topic_list.insert(tk.END, name)
        if self.visible_topics:
            selected = (
                self.initial_topic
                if self.initial_topic in self.visible_topics
                else self.visible_topics[0]
            )
            index = self.visible_topics.index(selected)
            self.topic_list.selection_set(index)
            self.topic_list.activate(index)
            self.topic_list.see(index)
            self.display_topic(selected)
        else:
            self.help_text.configure(state=tk.NORMAL)
            self.help_text.delete("1.0", tk.END)
            self.help_text.insert("1.0", "По вашему запросу темы не найдены.")
            self.help_text.configure(state=tk.DISABLED)

    def _select_topic(self, _event: tk.Event) -> None:
        selection = self.topic_list.curselection()
        if selection:
            self.display_topic(self.visible_topics[selection[0]])


def show_help(
    parent: tk.Misc,
    initial_topic: str | None = None,
) -> HelpWindow:
    return HelpWindow(parent, initial_topic=initial_topic)
