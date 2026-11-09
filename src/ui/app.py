import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from dataclasses import is_dataclass, fields

from src.translator import translate


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Транспилятор C → Python")
        self.geometry("1200x800")
        self.minsize(800, 600)

        self._debug_var = tk.BooleanVar(value=True)  # показывать отладку по умолчанию
        self._build_ui()

    # ==========================================
    # ПОСТРОЕНИЕ ИНТЕРФЕЙСА
    # ==========================================
    def _build_ui(self):
        # --- Верхняя панель кнопок ---
        top = tk.Frame(self)
        top.pack(side=tk.TOP, fill=tk.X, padx=8, pady=8)

        tk.Button(top, text="▶ Транслировать (Ctrl+Enter)", command=self.on_translate).pack(side=tk.LEFT)
        tk.Button(top, text="📂 Загрузить .c", command=self.on_load).pack(side=tk.LEFT, padx=4)
        tk.Button(top, text="💾 Сохранить .py", command=self.on_save).pack(side=tk.LEFT)
        
        tk.Checkbutton(top, text="Показать отладку", variable=self._debug_var).pack(side=tk.LEFT, padx=12)

        # --- Основная область: два поля ввода/вывода ---
        body = tk.Frame(self)
        body.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        # Левое поле (C)
        left = tk.Frame(body)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tk.Label(left, text="C (вход)", font=('Arial', 10, 'bold')).pack(anchor='w')
        self.txt_in = scrolledtext.ScrolledText(left, wrap=tk.NONE, font=('Consolas', 11))
        self.txt_in.pack(fill=tk.BOTH, expand=True)
        self._setup_clipboard(self.txt_in)

        # Правое поле (Python)
        right = tk.Frame(body)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0))
        tk.Label(right, text="Python (выход)", font=('Arial', 10, 'bold')).pack(anchor='w')
        self.txt_out = scrolledtext.ScrolledText(right, wrap=tk.NONE, font=('Consolas', 11))
        self.txt_out.pack(fill=tk.BOTH, expand=True)
        self._setup_clipboard(self.txt_out)

        # --- Нижняя панель (Вкладки) ---
        self.bottom = ttk.Notebook(self)
        self.bottom.pack(fill=tk.BOTH, expand=False, padx=8, pady=(0, 8))

        # Вкладка 1: Ошибки
        self.tab_errors = scrolledtext.ScrolledText(self.bottom, height=8, font=('Consolas', 10), fg="red")
        self.bottom.add(self.tab_errors, text="Ошибки")

        # Вкладка 2: Токены
        self.tab_tokens = scrolledtext.ScrolledText(self.bottom, height=8, font=('Consolas', 10))
        self.bottom.add(self.tab_tokens, text="Токены")

        # Вкладка 3: AST (Дерево)
        self.tab_ast = scrolledtext.ScrolledText(self.bottom, height=8, font=('Consolas', 10))
        self.bottom.add(self.tab_ast, text="AST")

        # Вкладка 4: Этапы / Отладка
        self.tab_stages = scrolledtext.ScrolledText(self.bottom, height=8, font=('Consolas', 10))
        self.bottom.add(self.tab_stages, text="Этапы / Отладка")

        # --- Статусная строка ---
        self.status = tk.StringVar(value="Готов к работе")
        tk.Label(self, textvariable=self.status, anchor='w', relief='sunken', padx=8).pack(
            side=tk.BOTTOM, fill=tk.X)

        # Привязка Ctrl+Enter к трансляции
        self.bind('<Control-Return>', lambda e: self.on_translate())

    # ==========================================
    # КОПИРОВАНИЕ / ВСТАВКА (Буфер обмена)
    # ==========================================
    def _setup_clipboard(self, widget):
        for seq, h in (
            ('<Control-c>', lambda e: self._copy(widget)), ('<Control-C>', lambda e: self._copy(widget)),
            ('<Control-v>', lambda e: self._paste(widget)), ('<Control-V>', lambda e: self._paste(widget)),
            ('<Control-x>', lambda e: self._cut(widget)), ('<Control-X>', lambda e: self._cut(widget)),
            ('<Control-a>', lambda e: self._select_all(widget)), ('<Control-A>', lambda e: self._select_all(widget)),
        ):
            widget.bind(seq, h)

        menu = tk.Menu(widget, tearoff=0)
        menu.add_command(label="Вырезать", command=lambda: self._cut(widget))
        menu.add_command(label="Копировать", command=lambda: self._copy(widget))
        menu.add_command(label="Вставить", command=lambda: self._paste(widget))
        menu.add_separator()
        menu.add_command(label="Выделить всё", command=lambda: self._select_all(widget))

        def show_menu(event):
            widget.mark_set(tk.INSERT, f"@{event.x},{event.y}")
            widget.focus_set()
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()

        widget.bind('<Button-3>', show_menu)
        widget._context_menu = menu

    def _copy(self, w):
        try:
            t = w.get(tk.SEL_FIRST, tk.SEL_LAST)
        except tk.TclError:
            return "break"
        self.clipboard_clear()
        self.clipboard_append(t)
        return "break"

    def _cut(self, w):
        try:
            t = w.get(tk.SEL_FIRST, tk.SEL_LAST)
        except tk.TclError:
            return "break"
        self.clipboard_clear()
        self.clipboard_append(t)
        w.delete(tk.SEL_FIRST, tk.SEL_LAST)
        return "break"

    def _paste(self, w):
        try:
            t = self.clipboard_get()
        except tk.TclError:
            return "break"
        try:
            w.delete(tk.SEL_FIRST, tk.SEL_LAST)
        except tk.TclError:
            pass
        w.insert(tk.INSERT, t)
        w.see(tk.INSERT)
        return "break"

    def _select_all(self, w):
        w.tag_add(tk.SEL, "1.0", tk.END)
        w.mark_set(tk.INSERT, "1.0")
        w.see(tk.INSERT)
        return "break"

    # ==========================================
    # ОБРАБОТЧИКИ СОБЫТИЙ
    # ==========================================
    def on_translate(self):
        src = self.txt_in.get("1.0", tk.END)
        debug = self._debug_var.get()

        # Очищаем панели перед новым запуском
        self.txt_out.delete("1.0", tk.END)
        self.tab_errors.delete("1.0", tk.END)
        self.tab_tokens.delete("1.0", tk.END)
        self.tab_ast.delete("1.0", tk.END)
        self.tab_stages.delete("1.0", tk.END)

        # Запуск трансляции (с флагом debug)
        result = translate(src, debug=debug)

        # 1. Вывод Python-кода
        if result.success:
            self.txt_out.insert("1.0", result.python_code)
            self.status.set("✅ Трансляция успешна")
        else:
            self.status.set(f"❌ Ошибок: {len(result.errors)}")

        # 2. Ошибки
        if result.errors:
            for err in result.errors:
                self.tab_errors.insert(tk.END, str(err) + "\n")
        else:
            self.tab_errors.insert(tk.END, "Ошибок нет.\n")

        # 3. Токены
        if debug and result.tokens is not None:
            self.tab_tokens.insert(tk.END, self._format_tokens(result.tokens))
        elif debug:
            self.tab_tokens.insert(tk.END, "(токены недоступны — ошибка на этапе лексера)\n")
        else:
            self.tab_tokens.insert(tk.END, "Отладка выключена\n")

        # 4. AST
        if debug and result.ast is not None:
            self.tab_ast.insert(tk.END, self._format_ast(result.ast))
        elif debug:
            self.tab_ast.insert(tk.END, "(AST недоступен — ошибка на этапе парсера)\n")
        else:
            self.tab_ast.insert(tk.END, "Отладка выключена\n")

        # 5. Этапы
        if debug:
            self.tab_stages.insert(tk.END, self._format_stages(result))
        else:
            self.tab_stages.insert(tk.END, "Отладка выключена\n")

    def on_load(self):
        path = filedialog.askopenfilename(filetypes=[("C files", "*.c"), ("All", "*.*")])
        if not path:
            return
        with open(path, encoding='utf-8') as f:
            self.txt_in.delete("1.0", tk.END)
            self.txt_in.insert("1.0", f.read())
        self.status.set(f"Загружено: {path}")

    def on_save(self):
        path = filedialog.asksaveasfilename(defaultextension=".py", filetypes=[("Python files", "*.py")])
        if not path:
            return
        with open(path, 'w', encoding='utf-8') as f:
            f.write(self.txt_out.get("1.0", tk.END))
        messagebox.showinfo("Сохранено", f"Файл сохранён: {path}")
        self.status.set(f"Сохранено в {path}")

    # ==========================================
    # ФОРМАТИРОВАНИЕ ДЛЯ ОТЛАДКИ
    # ==========================================
    @staticmethod
    def _format_tokens(tokens):
        lines = []
        lines.append(f"{'№':>4} | {'Код':<10} | {'Категория':<13} | {'Строка:Стлб':<12} | Значение")
        lines.append("-" * 78)
        for i, t in enumerate(tokens):
            val = t.value if len(t.value) <= 40 else t.value[:37] + '...'
            lines.append(f"{i:>4} | {t.code:<10} | {t.category:<13} | {t.line:>4}:{t.col:<7} | {val}")
        lines.append("-" * 78)
        lines.append(f"Всего токенов: {len(tokens)}")
        return "\n".join(lines) + "\n"

    @staticmethod
    def _format_ast(node, indent=0):
        """Рекурсивный pretty-print dataclass-дерева без шума."""
        pad = "  " * indent
        if node is None:
            return f"{pad}None\n"
        if isinstance(node, (int, float, str, bool)):
            return f"{pad}{node!r}\n"
        if isinstance(node, list):
            if not node:
                return f"{pad}[]\n"
            out = f"{pad}[\n"
            for item in node:
                out += App._format_ast(item, indent + 1)
            out += f"{pad}]\n"
            return out

        if is_dataclass(node) and not isinstance(node, type):
            cls = type(node).__name__
            out = f"{pad}{cls}(\n"
            for f in fields(node):
                val = getattr(node, f.name)
                out += f"{pad}  {f.name}:\n"
                out += App._format_ast(val, indent + 2)
            out += f"{pad})\n"
            return out

        return f"{pad}{repr(node)}\n"

    def _format_stages(self, result):
        lines = []
        lines.append("=== СВОДКА ===")
        lines.append(f"success: {result.success}")
        lines.append(f"ошибок: {len(result.errors)}")
        if result.python_code is not None:
            lines.append(f"длина Python-кода: {len(result.python_code)} символов")
        lines.append("")

        lines.append("=== ОШИБКИ ПО ЭТАПАМ ===")
        by_stage = {}
        for e in result.errors:
            by_stage.setdefault(e.stage, []).append(e)
        if not by_stage:
            lines.append("(нет)")
        else:
            for stage, errs in by_stage.items():
                lines.append(f"{stage}: {len(errs)}")
                for e in errs:
                    lines.append(f"  - {e}")
        lines.append("")

        lines.append("=== PYTHON (сырой, как есть) ===")
        lines.append(result.python_code or "(пусто)")
        return "\n".join(lines) + "\n"


def main():
    App().mainloop()


if __name__ == '__main__':
    main()
