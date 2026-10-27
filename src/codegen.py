from __future__ import annotations
from typing import List

from .ast_nodes import (
    Program, FuncDef, VarDecl, MultiVarDecl, ExprStmt, IfStmt, WhileStmt,
    DoWhileStmt, ForStmt, ReturnStmt, BreakStmt, ContinueStmt, SwitchStmt,
    CommentStmt, Assignment, BinOp, UnaryOp, TernaryOp, CallExpr,
    Ident, Num, Str, Char, Expr,
)
from .errors import TranslationError, TranslationException


INDENT = "    "


BINOP_MAP = {
    '&&': 'and',
    '||': 'or',
    '==': '==',
    '!=': '!=',
    '<': '<', '>': '>', '<=': '<=', '>=': '>=',
    '+': '+', '-': '-', '*': '*', '/': '/', '%': '%',
    '&': '&', '|': '|', '^': '^', '<<': '<<', '>>': '>>',
}

UNARY_MAP = {
    '!': 'not ',
    '-': '-',
    '+': '+',
    '~': '~',
}


def _fmt_printf(args: List[Expr]) -> str:
    """printf(fmt, a, b) -> print(f"...") с преобразованием спецификаторов."""
    if not args:
        return "print()"
    fmt_expr = args[0]
    if not isinstance(fmt_expr, Str):
        # Не строковый формат — просто выведем всё как print(args)
        inner = ", ".join(_expr_to_py(a) for a in args)
        return f"print({inner})"

    fmt = fmt_expr.val
    rest = args[1:]

    # Парсим спецификаторы %[флаги][ширина][.точность][длина]спец
    out_parts: List[str] = []
    arg_idx = 0
    i = 0
    while i < len(fmt):
        ch = fmt[i]
        if ch != '%':
            out_parts.append(ch)
            i += 1
            continue
        # %%
        if i + 1 < len(fmt) and fmt[i + 1] == '%':
            out_parts.append('%')
            i += 2
            continue
        # Спецификатор
        j = i + 1
        while j < len(fmt) and fmt[j] in '-+ 0#0123456789.':
            j += 1
        if j >= len(fmt):
            out_parts.append(fmt[i:])
            break
        spec_len = fmt[j]
        # Пропускаем длину (l, h)
        k = j
        while k < len(fmt) and fmt[k] in 'lh':
            k += 1
        if k < len(fmt):
            spec = fmt[k]
            j = k
        else:
            spec = spec_len

        if arg_idx >= len(rest):
            # Не хватает аргументов — оставим как есть
            out_parts.append(fmt[i:j + 1])
            i = j + 1
            continue

        arg = rest[arg_idx]
        arg_idx += 1
        expr = _expr_to_py(arg)
        if spec in 'di':
            out_parts.append('{')
            out_parts.append(expr)
            out_parts.append('}')
        elif spec in 'fFeEgG':
            out_parts.append('{')
            out_parts.append(expr)
            out_parts.append('}')
        elif spec == 'c':
            out_parts.append('{')
            out_parts.append(expr)
            out_parts.append('}')
        elif spec == 's':
            out_parts.append('{')
            out_parts.append(expr)
            out_parts.append('}')
        else:
            out_parts.append('{')
            out_parts.append(expr)
            out_parts.append('}')
        i = j + 1

    # Экранируем фигурные скобки в текстовой части (для f-строки)
    # Проще: собрать как f-строку через .format
    # Но у нас уже вставлены {expr}. Значит, экранируем только текст.
    # Пересоберём: пройдёмся и заэкранируем все `{`/`}`, которых мы не вставили.
    # Проще: собрать без f-строки, через .format(...)
    # Сделаем иначе: соберём строку с {} и отдельно список аргументов.
    # Тут мы уже потеряли структуру. Поэтому перепишем _fmt_printf ниже — см. v2.
    # Заглушка (не используется — вызов идёт в _fmt_printf_v2)
    raise RuntimeError("unreachable")


def _expr_to_py(e: Expr) -> str:
    return CodeGenerator().expr(e)


class CodeGenerator:
    def __init__(self):
        self.lines: List[str] = []
        self.indent = 0

    # ---- public ----
    def generate(self, program: Program) -> str:
        self.lines = []
        self.indent = 0

        # Импорты
        imports = self._gen_imports(program)
        for imp in imports:
            self._emit(imp)
        if imports:
            self._emit("")

        # Функции
        for fn in program.funcs:
            self._gen_func(fn)
            self._emit("")

        # Точка входа
        main = next((f for f in program.funcs if f.name == 'main'), None)
        if main is not None:
            self._emit('if __name__ == "__main__":')
            self.indent += 1
            self._emit('main()')
            self.indent -= 1

        # Убираем trailing пустые строки
        while self.lines and self.lines[-1] == "":
            self.lines.pop()
        return "\n".join(self.lines) + "\n"

    # ---- helpers ----
    def _emit(self, line: str) -> None:
        if line == "":
            self.lines.append("")
        else:
            self.lines.append(INDENT * self.indent + line)

    def _gen_imports(self, program: Program) -> List[str]:
        result: List[str] = []
        seen = set()
        for inc in program.includes:
            h = inc.header
            if h in ('stdio.h', 'stdlib.h', 'string.h', 'ctype.h', 'stdbool.h'):
                continue
            if h == 'math.h':
                if 'import math' not in seen:
                    result.append('import math')
                    seen.add('import math')
            else:
                # Неизвестный заголовок — комментарий
                result.append(f'# TODO: import for <{h}> не поддерживается')
        return result

    # ---- functions ----
    def _gen_func(self, fn: FuncDef) -> None:
        params = ", ".join(p.name for p in fn.params)
        self._emit(f"def {fn.name}({params}):")
        self.indent += 1
        if not fn.body:
            self._emit("pass")
        else:
            for s in fn.body:
                self._gen_stmt(s)
        self.indent -= 1

    # ---- statements ----
    def _gen_stmt(self, s) -> None:
        if isinstance(s, CommentStmt):
            text = s.text
            if text.startswith('//'):
                self._emit("# " + text[2:].strip())
            elif text.startswith('/*'):
                inner = text[2:-2].strip() if text.endswith('*/') else text[2:].strip()
                for line in inner.splitlines():
                    self._emit("# " + line.strip())
            else:
                self._emit("# " + text)
            return

        if isinstance(s, VarDecl):
            if s.init is not None:
                self._emit(f"{s.name} = {self.expr(s.init)}")
            else:
                # Без инициализации — не эмитим (Python без объявлений)
                # но оставим комментарий для читаемости
                self._emit(f"# {s.type_} {s.name}")
            return

        if isinstance(s, MultiVarDecl):
            for d in s.decls:
                self._gen_stmt(d)
            return

        if isinstance(s, ExprStmt):
            self._gen_expr_stmt(s.expr)
            return

        if isinstance(s, IfStmt):
            self._emit(f"if {self.expr(s.cond)}:")
            self.indent += 1
            self._gen_body(s.then_body)
            self.indent -= 1
            if s.else_body:
                self._emit("else:")
                self.indent += 1
                self._gen_body(s.else_body)
                self.indent -= 1
            return

        if isinstance(s, WhileStmt):
            self._emit(f"while {self.expr(s.cond)}:")
            self.indent += 1
            self._gen_body(s.body)
            self.indent -= 1
            return

        if isinstance(s, DoWhileStmt):
            self._emit("while True:")
            self.indent += 1
            self._gen_body(s.body)
            self._emit(f"if not ({self.expr(s.cond)}):")
            self.indent += 1
            self._emit("break")
            self.indent -= 1
            self.indent -= 1
            return

        if isinstance(s, ForStmt):
            self._gen_for(s)
            return

        if isinstance(s, ReturnStmt):
            if s.value is None:
                self._emit("return")
            else:
                self._emit(f"return {self.expr(s.value)}")
            return

        if isinstance(s, BreakStmt):
            self._emit("break")
            return
        if isinstance(s, ContinueStmt):
            self._emit("continue")
            return

        if isinstance(s, SwitchStmt):
            self._gen_switch(s)
            return

        raise TranslationException(TranslationError(
            stage='codegen', code='E_CG_UNKNOWN_STMT',
            message=f"Генерация для {type(s).__name__} не реализована",
        ))

    def _gen_body(self, body: List) -> None:
        if not body:
            self._emit("pass")
            return
        for s in body:
            self._gen_stmt(s)

    def _gen_for(self, s: ForStmt) -> None:
        # Если init — VarDecl и update — UnaryOp/Assignment, можно range
        if (isinstance(s.init, VarDecl)
                and s.init.init is not None
                and s.cond is not None
                and isinstance(s.update, UnaryOp)
                and s.update.op in ('++', '--')
                and isinstance(s.update.operand, Ident)
                and isinstance(s.init, VarDecl)
                and s.init.name == s.update.operand.name):
            var = s.init.name
            start = self.expr(s.init.init)
            # cond: var < N  /  var <= N  /  var > N / var >= N
            if isinstance(s.cond, BinOp) and isinstance(s.cond.left, Ident) and s.cond.left.name == var:
                op = s.cond.op
                limit = self.expr(s.cond.right)
                if op in ('<', '<='):
                    if op == '<':
                        self._emit(f"for {var} in range({start}, {limit}):")
                    else:
                        self._emit(f"for {var} in range({start}, ({limit}) + 1):")
                    self.indent += 1
                    self._gen_body(s.body)
                    self.indent -= 1
                    return
                if op in ('>', '>='):
                    step = '-1'
                    if op == '>':
                        self._emit(f"for {var} in range({start}, {limit}, {step}):")
                    else:
                        self._emit(f"for {var} in range({start}, ({limit}) - 1, {step}):")
                    self.indent += 1
                    self._gen_body(s.body)
                    self.indent -= 1
                    return

        # Общий случай — while
        if s.init is not None:
            self._gen_stmt(s.init)
        cond = self.expr(s.cond) if s.cond is not None else "True"
        self._emit(f"while {cond}:")
        self.indent += 1
        self._gen_body(s.body)
        if s.update is not None:
            self._gen_expr_stmt(s.update)
        self.indent -= 1

    def _gen_switch(self, s: SwitchStmt) -> None:
        expr = self.expr(s.expr)
        # Используем if/elif
        first = True
        default_case = None
        for c in s.cases:
            if c.value is None:
                default_case = c
                continue
            kw = "if" if first else "elif"
            first = False
            self._emit(f"{kw} {expr} == {self.expr(c.value)}:")
            self.indent += 1
            self._gen_body(self._strip_break(c.body))
            self.indent -= 1
        if default_case is not None:
            self._emit("else:")
            self.indent += 1
            self._gen_body(self._strip_break(default_case.body))
            self.indent -= 1

    @staticmethod
    def _strip_break(body: List) -> List:
        # В switch break на конце ветки не нужен
        if body and isinstance(body[-1], BreakStmt):
            return body[:-1]
        return body

    def _gen_expr_stmt(self, e: Expr) -> None:
        # ++/-- как statement -> += 1 / -= 1
        if isinstance(e, UnaryOp) and e.op in ('++', '--') and isinstance(e.operand, Ident):
            op = '+=' if e.op == '++' else '-='
            self._emit(f"{e.operand.name} {op} 1")
            return
        if isinstance(e, CallExpr) and e.func == 'printf':
            self._emit(self._fmt_printf(e.args))
            return
        if isinstance(e, CallExpr) and e.func == 'scanf':
            # Осознанно не поддерживаем — генерируем заглушку
            self._emit("# TODO: scanf не поддерживается транспилятором")
            return
        if isinstance(e, Assignment):
            self._emit(f"{self.expr(e.left)} {e.op} {self.expr(e.right)}")
            return
        if isinstance(e, CallExpr):
            self._emit(self.expr(e))
            return
        # Просто выражение
        self._emit(self.expr(e))

    # ---- expressions ----
    def expr(self, e: Expr) -> str:
        if isinstance(e, Num):
            return repr(e.val)
        if isinstance(e, Str):
            return repr(e.val)
        if isinstance(e, Char):
            return repr(e.val)
        if isinstance(e, Ident):
            return e.name
        if isinstance(e, BinOp):
            op = BINOP_MAP.get(e.op, e.op)
            left = self._paren(e.left)
            right = self._paren(e.right)
            return f"{left} {op} {right}"
        if isinstance(e, UnaryOp):
            if e.op in ('++', '--'):
                # В выражении не поддерживаем — но попробуем как +1/-1
                # Лучше явно: (x + 1) или (x - 1)
                inner = self._paren(e.operand)
                return f"({inner} + 1)" if e.op == '++' else f"({inner} - 1)"
            op = UNARY_MAP.get(e.op, e.op)
            inner = self._paren(e.operand)
            return f"{op}{inner}"
        if isinstance(e, TernaryOp):
            return f"({self.expr(e.then_expr)} if {self.expr(e.cond)} else {self.expr(e.else_expr)})"
        if isinstance(e, Assignment):
            return f"{self.expr(e.left)} {e.op} {self.expr(e.right)}"
        if isinstance(e, CallExpr):
            if e.func == 'printf':
                return self._fmt_printf(e.args)
            args = ", ".join(self.expr(a) for a in e.args)
            return f"{e.func}({args})"
        raise TranslationException(TranslationError(
            stage='codegen', code='E_CG_UNKNOWN_EXPR',
            message=f"Генерация для выражения {type(e).__name__} не реализована",
        ))

    def _paren(self, e: Expr) -> str:
        s = self.expr(e)
        if isinstance(e, (BinOp, TernaryOp, Assignment)):
            return f"({s})"
        return s

    def _fmt_printf(self, args: List[Expr]) -> str:
        """printf(fmt, a, b) -> print(...) с f-строкой (v2)."""
        if not args:
            return "print()"
        fmt_expr = args[0]
        if not isinstance(fmt_expr, Str):
            inner = ", ".join(self.expr(a) for a in args)
            return f"print({inner})"

        fmt = fmt_expr.val
        rest = args[1:]

        # Собираем f-строку, экранируя литеральные { }
        parts: List[str] = []
        expr_list: List[str] = []  # не нужен при f-строке
        i = 0
        arg_idx = 0
        while i < len(fmt):
            ch = fmt[i]
            if ch == '{':
                parts.append('{{')
                i += 1
                continue
            if ch == '}':
                parts.append('}}')
                i += 1
                continue
            if ch != '%':
                parts.append(ch)
                i += 1
                continue
            if i + 1 < len(fmt) and fmt[i + 1] == '%':
                parts.append('%')
                i += 2
                continue

            j = i + 1
            while j < len(fmt) and fmt[j] in '-+ 0#0123456789.':
                j += 1
            if j >= len(fmt):
                parts.append(fmt[i:])
                break
            # length modifiers
            k = j
            while k < len(fmt) and fmt[k] in 'lh':
                k += 1
            spec = fmt[k] if k < len(fmt) else fmt[j]
            j = k

            if arg_idx >= len(rest):
                parts.append(fmt[i:j + 1])
                i = j + 1
                continue

            arg = rest[arg_idx]
            arg_idx += 1
            expr_py = self.expr(arg)
            if spec == 'c':
                # %c: в C — код символа или сам символ
                parts.append("{")
                parts.append(expr_py)
                parts.append("}")
            elif spec in 'di':
                parts.append("{")
                parts.append(expr_py)
                parts.append("}")
            elif spec in 'fFeEgG':
                # Оставим без форматирования точности (упрощённо)
                parts.append("{")
                parts.append(expr_py)
                parts.append("}")
            elif spec == 's':
                parts.append("{")
                parts.append(expr_py)
                parts.append("}")
            else:
                parts.append("{")
                parts.append(expr_py)
                parts.append("}")
            i = j + 1

        body = "".join(parts)
        # Разбираем body на литералы и {expr}
        # Для f-строки нужно экранировать только что уже заэкранировано.
        return f'print(f"{body}")'


def generate(program: Program) -> str:
    return CodeGenerator().generate(program)