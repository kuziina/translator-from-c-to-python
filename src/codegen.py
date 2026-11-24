from __future__ import annotations
from typing import List

from .ast_nodes import (
    Program, FuncDef, VarDecl, MultiVarDecl, ExprStmt, IfStmt, WhileStmt,
    DoWhileStmt, ForStmt, ReturnStmt, BreakStmt, ContinueStmt, SwitchStmt,
    IfdefStmt, CommentStmt, Assignment, BinOp, UnaryOp, TernaryOp, CallExpr,
    Ident, ArrayAccess, ArrayInit, Num, Str, Char, Bool, Expr,
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


class CodeGenerator:
    def __init__(self):
        self.lines: List[str] = []
        self.indent = 0
        self.defines_names: set = set()

    def generate(self, program: Program) -> str:
        self.lines = []
        self.indent = 0
        self.defines_names = {d.name for d in program.defines}

        for comment in program.header_comments:
            self._emit_comment(comment)
        if program.header_comments:
            self._emit("")

        imports = self._gen_imports(program)
        for imp in imports:
            self._emit(imp)
        if imports:
            self._emit("")

        defines = self._gen_defines(program)
        for line in defines:
            self._emit(line)
        if defines:
            self._emit("")

        for fn in program.funcs:
            self._gen_func(fn)
            self._emit("")

        main = next((f for f in program.funcs if f.name == 'main'), None)
        if main is not None:
            self._emit('if __name__ == "__main__":')
            self.indent += 1
            self._emit('main()')
            self.indent -= 1

        while self.lines and self.lines[-1] == "":
            self.lines.pop()
        return "\n".join(self.lines) + "\n"

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
                result.append(f'# TODO: import for <{h}> не поддерживается')
        return result

    def _gen_func(self, fn: FuncDef) -> None:
        for comment in fn.leading_comments:
            self._emit_comment(comment)
        params = ", ".join(p.name for p in fn.params)
        self._emit(f"def {fn.name}({params}):")
        self.indent += 1
        if not fn.body:
            self._emit("pass")
        else:
            for s in fn.body:
                self._gen_stmt(s)
        self.indent -= 1

    def _emit_comment(self, comment: CommentStmt) -> None:
        for line in self._comment_lines(comment.text):
            self._emit(line)

    @staticmethod
    def _comment_lines(text: str) -> List[str]:
        if text.startswith('//'):
            return ["# " + text[2:].strip()]
        if text.startswith('/*'):
            if text.endswith('*/'):
                inner = text[2:-2].strip()
            else:
                inner = text[2:].strip()
            lines = ["# " + line.strip() for line in inner.splitlines()]
            return lines or ["#"]
        return ["# " + text]

    def _gen_stmt(self, s) -> None:
        if isinstance(s, CommentStmt):
            self._emit_comment(s)
            return

        if isinstance(s, VarDecl):
            if s.dims:
                self._emit(f"{s.name} = {self._gen_array_value(s)}")
            elif s.init is not None:
                self._emit(f"{s.name} = {self.expr(s.init)}")
            else:
                self._emit(f"# {s.type_} {s.name}")
            return

        if isinstance(s, MultiVarDecl):
            for d in s.decls:
                self._gen_stmt(d)
            return

        if isinstance(s, ExprStmt):
            self._gen_expr_stmt(s.expr)
            return

        if isinstance(s, IfdefStmt):
            defined = s.macro in self.defines_names
            self._gen_body(s.body if (defined != s.negated) else s.else_body)
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

    def _gen_array_value(self, d: VarDecl) -> str:
        dims = self._effective_dims(d.dims, d.array_init)
        if d.array_init is not None:
            return self._gen_array_init(d.array_init, dims, 0)
        if d.init is not None:
            return self.expr(d.init)
        return self._gen_array_zeros(dims, 0)

    @staticmethod
    def _effective_dims(dims: List,
                        init: "ArrayInit | None") -> List:
        result = list(dims)
        node = init
        for i, dim in enumerate(result):
            if isinstance(dim, Num) and dim.val == 0:
                if isinstance(node, ArrayInit):
                    result[i] = Num(
                        CodeGenerator._infer_dimension(node, result, i))
                else:
                    result[i] = Num(1)
            if isinstance(node, ArrayInit):
                first = node.values[0] if node.values else None
                node = first if isinstance(first, ArrayInit) else None
            else:
                node = None
        return result

    @staticmethod
    def _infer_dimension(init: ArrayInit, dims: List, level: int) -> int:
        nested = any(isinstance(v, ArrayInit) for v in init.values)
        if not nested and level + 1 < len(dims):
            chunk = 1
            for d in dims[level + 1:]:
                if not isinstance(d, Num):
                    return len(init.values)
                chunk *= int(d.val)
            if chunk > 0:
                return (len(init.values) + chunk - 1) // chunk
        return len(init.values)

    def _gen_array_zeros(self, dims: List, level: int = 0) -> str:
        dim = self.expr(dims[level])
        if level == len(dims) - 1:
            return f"[0] * ({dim})"
        inner = self._gen_array_zeros(dims, level + 1)
        return f"[{inner} for _ in range({dim})]"

    def _gen_array_init(self, init: ArrayInit, dims: List,
                        level: int) -> str:
        # Плоский инициализатор для многомерного массива:
        # int a[2][3] = {1, 2, 3, 4, 5, 6};
        if level == 0 and len(dims) > 1 and self._is_flat_init(init):
            return self._gen_flat_init(init.values, dims, 0)

        parts: List[str] = []
        for value in init.values:
            if isinstance(value, ArrayInit):
                parts.append(self._gen_array_init(value, dims, level + 1))
            else:
                parts.append(self.expr(value))

        dim = dims[level] if level < len(dims) else None
        if isinstance(dim, Num):
            target = int(dim.val)
            while len(parts) < target:
                if level + 1 < len(dims):
                    parts.append(self._gen_array_zeros(dims, level + 1))
                else:
                    parts.append("0")
            parts = parts[:target]
        return "[" + ", ".join(parts) + "]"

    @staticmethod
    def _is_flat_init(init: ArrayInit) -> bool:
        return all(not isinstance(v, ArrayInit) for v in init.values)

    def _gen_flat_init(self, values: List, dims: List,
                       level: int) -> str:
        for d in dims[level:]:
            if not isinstance(d, Num):
                inner = ", ".join(self.expr(v) for v in values)
                return f"[{inner}]"
        if level == len(dims) - 1:
            target = int(dims[level].val)
            items = [self.expr(v) for v in values[:target]]
            items.extend(["0"] * (target - len(items)))
            return "[" + ", ".join(items) + "]"

        chunk = 1
        for d in dims[level + 1:]:
            if isinstance(d, Num):
                chunk *= int(d.val)
        target = int(dims[level].val)
        rows = [self._gen_flat_init(values[i * chunk:(i + 1) * chunk],
                                    dims, level + 1)
                for i in range(target)]
        return "[" + ", ".join(rows) + "]"

    def _gen_for(self, s: ForStmt) -> None:
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
        if body and isinstance(body[-1], BreakStmt):
            return body[:-1]
        return body

    def _gen_expr_stmt(self, e: Expr) -> None:
        if (isinstance(e, UnaryOp) and e.op in ('++', '--')
                and isinstance(e.operand, (Ident, ArrayAccess))):
            op = '+=' if e.op == '++' else '-='
            self._emit(f"{self.expr(e.operand)} {op} 1")
            return
        if isinstance(e, CallExpr) and e.func == 'printf':
            self._emit(self._fmt_printf(e.args))
            return
        if isinstance(e, CallExpr) and e.func == 'scanf':
            self._emit("# TODO: scanf не поддерживается транслятором")
            return
        if isinstance(e, Assignment):
            self._emit(f"{self.expr(e.left)} {e.op} {self.expr(e.right)}")
            return
        if isinstance(e, CallExpr):
            self._emit(self.expr(e))
            return
        self._emit(self.expr(e))

    def _gen_defines(self, program: Program) -> List[str]:
        result: List[str] = []
        for d in program.defines:
            if d.value is None:
                result.append(f"{d.name} = True")
                continue
            v = d.value.strip()
            num = None
            try:
                num = int(v, 0)
            except ValueError:
                try:
                    num = float(v)
                except ValueError:
                    num = None
            if num is not None:
                result.append(f"{d.name} = {num!r}")
                continue
            if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
                result.append(f"{d.name} = {v}")
                continue
            result.append(f"# #define {d.name} {v} (не подставлено)")
        return result

    def expr(self, e: Expr) -> str:
        if isinstance(e, Num):
            return repr(e.val)
        if isinstance(e, Str):
            return repr(e.val)
        if isinstance(e, Char):
            return repr(e.val)
        if isinstance(e, Bool):
            return 'True' if e.val else 'False'
        if isinstance(e, Ident):
            return e.name
        if isinstance(e, ArrayAccess):
            indices = "".join(f"[{self.expr(i)}]" for i in e.indices)
            return f"{e.name}{indices}"
        if isinstance(e, BinOp):
            op = BINOP_MAP.get(e.op, e.op)
            left = self._paren(e.left)
            right = self._paren(e.right)
            return f"{left} {op} {right}"
        if isinstance(e, UnaryOp):
            if e.op in ('++', '--'):
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
        parts: List[str] = []
        expr_list: List[str] = []
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
                parts.append("{")
                parts.append(expr_py)
                parts.append("}")
            elif spec in 'di':
                parts.append("{")
                parts.append(expr_py)
                parts.append("}")
            elif spec in 'fFeEgG':
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
        return f'print(f"{body}")'


def generate(program: Program) -> str:
    return CodeGenerator().generate(program)