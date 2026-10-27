from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional

from .ast_nodes import (
    Program, FuncDef, VarDecl, MultiVarDecl, ExprStmt, IfStmt, WhileStmt,
    DoWhileStmt, ForStmt, ReturnStmt, BreakStmt, ContinueStmt, SwitchStmt,
    CaseStmt, CommentStmt, Assignment, BinOp, UnaryOp, TernaryOp, CallExpr,
    Ident, Num, Str, Char,
)
from .errors import TranslationError, TranslationException


BUILTIN_FUNCS = {
    'printf': ('int', None),     # (ret_type, params=None => любой)
    'scanf':  ('int', None),
}


@dataclass
class Symbol:
    name: str
    type_: str
    category: str             # 'var' | 'param' | 'func' | 'const'
    scope: str                # 'global' | 'local:<func>'
    ret_type: Optional[str] = None
    params: Optional[List[str]] = None   # список типов


class SymbolTable:
    def __init__(self):
        self.scopes: List[Dict[str, Symbol]] = [dict()]  # [0] — global
        self.scope_names: List[str] = ['global']

    def push(self, name: str) -> None:
        self.scopes.append({})
        self.scope_names.append(name)

    def pop(self) -> None:
        if len(self.scopes) == 1:
            raise RuntimeError("Нельзя выйти за пределы глобальной области")
        self.scopes.pop()
        self.scope_names.pop()

    def current_scope_name(self) -> str:
        return self.scope_names[-1]

    def declare(self, sym: Symbol, line: int, col: int) -> None:
        # В одной области — уникальное имя
        if sym.name in self.scopes[-1]:
            raise TranslationException(TranslationError(
                stage='semantic', code='E_SEM_REDECLARED',
                message=f"Повторное объявление идентификатора '{sym.name}'",
                line=line, col=col,
            ))
        self.scopes[-1][sym.name] = sym

    def lookup(self, name: str) -> Optional[Symbol]:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def lookup_func(self, name: str) -> Optional[Symbol]:
        return self.scopes[0].get(name)


class SemanticAnalyzer:
    def __init__(self):
        self.table = SymbolTable()
        self.func_returns: List[Optional[str]] = []  # стек возвращаемых типов
        self.loop_depth = 0

    def analyze(self, program: Program) -> Program:
        # 1) Регистрируем все функции глобально (позволяет forward usage)
        for fn in program.funcs:
            param_types = [p.type_ for p in fn.params]
            sym = Symbol(
                name=fn.name, type_=fn.ret_type, category='func',
                scope='global', ret_type=fn.ret_type, params=param_types,
            )
            self.table.scopes[0][fn.name] = sym  # без проверки дубликатов на этом шаге

        # 2) Обрабатываем тела
        for fn in program.funcs:
            self._visit_func(fn)

        return program

    # ---- func ----
    def _visit_func(self, fn: FuncDef) -> None:
        self.table.push(f"func:{fn.name}")
        for p in fn.params:
            self.table.declare(Symbol(p.name, p.type_, 'param', self.table.current_scope_name()),
                               line=0, col=0)
        self.func_returns.append(None if fn.ret_type == 'void' else fn.ret_type)
        try:
            for s in fn.body:
                self._visit_stmt(s)
        finally:
            self.func_returns.pop()
            self.table.pop()

    # ---- statements ----
    def _visit_stmt(self, s) -> None:
        if isinstance(s, CommentStmt):
            return

        if isinstance(s, VarDecl):
            self._check_var_decl(s)
            return

        if isinstance(s, MultiVarDecl):
            for d in s.decls:
                self._check_var_decl(d)
            return

        if isinstance(s, ExprStmt):
            self._visit_expr(s.expr)
            return

        if isinstance(s, IfStmt):
            self._visit_expr(s.cond)
            for st in s.then_body:
                self._visit_stmt(st)
            for st in s.else_body:
                self._visit_stmt(st)
            return

        if isinstance(s, WhileStmt):
            self._visit_expr(s.cond)
            self.loop_depth += 1
            try:
                for st in s.body:
                    self._visit_stmt(st)
            finally:
                self.loop_depth -= 1
            return

        if isinstance(s, DoWhileStmt):
            self.loop_depth += 1
            try:
                for st in s.body:
                    self._visit_stmt(st)
            finally:
                self.loop_depth -= 1
            self._visit_expr(s.cond)
            return

        if isinstance(s, ForStmt):
            if s.init is not None:
                self._visit_stmt(s.init)
            if s.cond is not None:
                self._visit_expr(s.cond)
            if s.update is not None:
                self._visit_expr(s.update)
            self.loop_depth += 1
            try:
                for st in s.body:
                    self._visit_stmt(st)
            finally:
                self.loop_depth -= 1
            return

        if isinstance(s, ReturnStmt):
            self._check_return(s)
            return

        if isinstance(s, (BreakStmt, ContinueStmt)):
            if self.loop_depth == 0:
                raise TranslationException(TranslationError(
                    stage='semantic', code='E_SEM_LOOP_CTRL',
                    message="'break'/'continue' вне цикла",
                ))
            return

        if isinstance(s, SwitchStmt):
            self._visit_expr(s.expr)
            for c in s.cases:
                if c.value is not None:
                    self._visit_expr(c.value)
                for st in c.body:
                    self._visit_stmt(st)
            return

        raise TranslationException(TranslationError(
            stage='semantic', code='E_SEM_UNKNOWN_STMT',
            message=f"Неизвестный тип инструкции: {type(s).__name__}",
        ))

    def _check_var_decl(self, d: VarDecl) -> None:
        if d.init is not None:
            self._visit_expr(d.init)
        self.table.declare(
            Symbol(d.name, d.type_, 'var', self.table.current_scope_name()),
            line=0, col=0,
        )

    def _check_return(self, s: ReturnStmt) -> None:
        expected = self.func_returns[-1] if self.func_returns else None
        if s.value is not None:
            self._visit_expr(s.value)
        if expected is None:
            if s.value is not None:
                raise TranslationException(TranslationError(
                    stage='semantic', code='E_SEM_RET_VOID',
                    message="Функция void не должна возвращать значение",
                ))
            return
        if s.value is None:
            raise TranslationException(TranslationError(
                stage='semantic', code='E_SEM_RET_MISSING',
                message=f"Ожидалось возвращаемое значение типа '{expected}'",
            ))

    # ---- expressions ----
    def _visit_expr(self, e) -> None:
        if isinstance(e, (Num, Str, Char)):
            return
        if isinstance(e, Ident):
            sym = self.table.lookup(e.name)
            if sym is None:
                raise TranslationException(TranslationError(
                    stage='semantic', code='E_SEM_UNDECLARED',
                    message=f"Идентификатор '{e.name}' не объявлен",
                ))
            return
        if isinstance(e, Assignment):
            if not isinstance(e.left, Ident):
                raise TranslationException(TranslationError(
                    stage='semantic', code='E_SEM_LVALUE',
                    message="Слева от присваивания должен быть идентификатор",
                ))
            sym = self.table.lookup(e.left.name)
            if sym is None:
                raise TranslationException(TranslationError(
                    stage='semantic', code='E_SEM_UNDECLARED',
                    message=f"Идентификатор '{e.left.name}' не объявлен",
                ))
            self._visit_expr(e.right)
            return
        if isinstance(e, BinOp):
            self._visit_expr(e.left)
            self._visit_expr(e.right)
            return
        if isinstance(e, UnaryOp):
            self._visit_expr(e.operand)
            return
        if isinstance(e, TernaryOp):
            self._visit_expr(e.cond)
            self._visit_expr(e.then_expr)
            self._visit_expr(e.else_expr)
            return
        if isinstance(e, CallExpr):
            if e.func not in BUILTIN_FUNCS:
                sym = self.table.lookup_func(e.func)
                if sym is None:
                    raise TranslationException(TranslationError(
                        stage='semantic', code='E_SEM_FUNC_UNDECLARED',
                        message=f"Функция '{e.func}' не объявлена",
                    ))
                if sym.params is not None and len(sym.params) != len(e.args):
                    raise TranslationException(TranslationError(
                        stage='semantic', code='E_SEM_ARGS_COUNT',
                        message=f"Неверное количество аргументов функции '{e.func}': "
                                f"ожидалось {len(sym.params)}, передано {len(e.args)}",
                    ))
            for a in e.args:
                self._visit_expr(a)
            return
        raise TranslationException(TranslationError(
            stage='semantic', code='E_SEM_UNKNOWN_EXPR',
            message=f"Неизвестный тип выражения: {type(e).__name__}",
        ))


def analyze(program: Program) -> Program:
    SemanticAnalyzer().analyze(program)
    return program