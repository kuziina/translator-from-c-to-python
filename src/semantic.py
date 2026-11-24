from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional

from .ast_nodes import (
    Program, FuncDef, VarDecl, MultiVarDecl, ExprStmt, IfStmt, WhileStmt,
    DoWhileStmt, ForStmt, ReturnStmt, BreakStmt, ContinueStmt, SwitchStmt,
    CaseStmt, CommentStmt, IfdefStmt, Assignment, BinOp, UnaryOp, TernaryOp,
    CallExpr, Ident, ArrayAccess, ArrayInit, Num, Str, Char, Bool,
)
from .errors import TranslationError, TranslationException


BUILTIN_FUNCS = {
    'printf': ('int', None),
    'scanf':  ('int', None),
}


def _define_type(value: Optional[str]) -> str:
    if value is None:
        return 'int' 
    v = value.strip()
    if v.startswith('"'):
        return 'string'
    try:
        int(v)
        return 'int'
    except ValueError:
        pass
    try:
        float(v)
        return 'float'
    except ValueError:
        return 'int'


@dataclass
class Symbol:
    name: str
    type_: str
    category: str
    scope: str
    ret_type: Optional[str] = None
    params: Optional[List[str]] = None
    dims: int = 0


class SymbolTable:
    def __init__(self):
        self.scopes: List[Dict[str, Symbol]] = [dict()]
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
        if sym.name in self.scopes[-1]:
            existing = self.scopes[-1][sym.name]
            kind = 'функции' if existing.category == 'func' \
                else 'идентификатора'
            raise TranslationException(TranslationError(
                stage='semantic', code='E_SEM_REDECLARED',
                message=f"Повторное объявление {kind} '{sym.name}'",
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
        self.func_returns: List[Optional[str]] = []
        self.loop_depth = 0
        self.switch_depth = 0
        self.defined_macros: set = set()

    def analyze(self, program: Program) -> Program:
        for d in program.defines:
            self.defined_macros.add(d.name)
            self.table.scopes[0][d.name] = Symbol(
                name=d.name, type_=_define_type(d.value), category='const',
                scope='global',
            )

        for fn in program.funcs:
            param_types = [p.type_ for p in fn.params]
            sym = Symbol(
                name=fn.name, type_=fn.ret_type, category='func',
                scope='global', ret_type=fn.ret_type, params=param_types,
            )
            self.table.declare(sym, line=fn.line, col=fn.col)

        for fn in program.funcs:
            self._visit_func(fn)

        return program

    def _visit_func(self, fn: FuncDef) -> None:
        self.table.push(f"func:{fn.name}")
        for p in fn.params:
            self.table.declare(Symbol(p.name, p.type_, 'param',
                                      self.table.current_scope_name(),
                                      dims=len(p.dims)),
                               line=p.line, col=p.col)
        self.func_returns.append(None if fn.ret_type == 'void' else fn.ret_type)
        try:
            for s in fn.body:
                self._visit_stmt(s)
        finally:
            self.func_returns.pop()
            self.table.pop()

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

        if isinstance(s, IfdefStmt):
            defined = s.macro in self.defined_macros
            branch = s.body if (defined != s.negated) else s.else_body
            for st in branch:
                self._visit_stmt(st)
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
            allowed = (self.loop_depth > 0
                       or (isinstance(s, BreakStmt)
                           and self.switch_depth > 0))
            if not allowed:
                what = "'break' вне цикла/switch" \
                    if isinstance(s, BreakStmt) else "'continue' вне цикла"
                raise TranslationException(TranslationError(
                    stage='semantic', code='E_SEM_LOOP_CTRL',
                    message=what,
                    line=s.line, col=s.col,
                ))
            return

        if isinstance(s, SwitchStmt):
            self._visit_expr(s.expr)
            self.switch_depth += 1
            try:
                for c in s.cases:
                    if c.value is not None:
                        self._visit_expr(c.value)
                    for st in c.body:
                        self._visit_stmt(st)
            finally:
                self.switch_depth -= 1
            return

        raise TranslationException(TranslationError(
            stage='semantic', code='E_SEM_UNKNOWN_STMT',
            message=f"Неизвестный тип инструкции: {type(s).__name__}",
        ))

    def _check_var_decl(self, d: VarDecl) -> None:
        for dim in d.dims:
            self._visit_expr(dim)
        if d.array_init is not None:
            self._visit_array_init(d.array_init)
        if d.init is not None:
            self._visit_expr(d.init)
        category = 'const' if d.is_const else 'var'
        self.table.declare(
            Symbol(d.name, d.type_, category,
                   self.table.current_scope_name(), dims=len(d.dims)),
            line=d.line, col=d.col,
        )

    def _visit_array_init(self, init: ArrayInit) -> None:
        for value in init.values:
            if isinstance(value, ArrayInit):
                self._visit_array_init(value)
            else:
                self._visit_expr(value)

    def _check_return(self, s: ReturnStmt) -> None:
        expected = self.func_returns[-1] if self.func_returns else None
        if s.value is not None:
            self._visit_expr(s.value)
        if expected is None:
            if s.value is not None:
                raise TranslationException(TranslationError(
                    stage='semantic', code='E_SEM_RET_VOID',
                    message="Функция void не должна возвращать значение",
                    line=s.line, col=s.col,
                ))
            return
        if s.value is None:
            raise TranslationException(TranslationError(
                stage='semantic', code='E_SEM_RET_MISSING',
                message=f"Ожидалось возвращаемое значение типа '{expected}'",
                line=s.line, col=s.col,
            ))

    def _visit_expr(self, e) -> None:
        if isinstance(e, (Num, Str, Char, Bool)):
            return
        if isinstance(e, Ident):
            sym = self.table.lookup(e.name)
            if sym is None:
                raise TranslationException(TranslationError(
                    stage='semantic', code='E_SEM_UNDECLARED',
                    message=f"Идентификатор '{e.name}' не объявлен",
                    line=e.line, col=e.col,
                ))
            return
        if isinstance(e, ArrayAccess):
            sym = self.table.lookup(e.name)
            if sym is None:
                raise TranslationException(TranslationError(
                    stage='semantic', code='E_SEM_UNDECLARED',
                    message=f"Идентификатор '{e.name}' не объявлен",
                    line=e.line, col=e.col,
                ))
            if sym.dims == 0:
                raise TranslationException(TranslationError(
                    stage='semantic', code='E_SEM_ARRAY_INDEX',
                    message=f"'{e.name}' не является массивом",
                    line=e.line, col=e.col,
                ))
            if len(e.indices) > sym.dims:
                raise TranslationException(TranslationError(
                    stage='semantic', code='E_SEM_ARRAY_INDEX',
                    message=f"Слишком много индексов для массива '{e.name}': "
                            f"объявлено {sym.dims}, использовано "
                            f"{len(e.indices)}",
                    line=e.line, col=e.col,
                ))
            for index in e.indices:
                self._visit_expr(index)
            return
        if isinstance(e, Assignment):
            if not isinstance(e.left, (Ident, ArrayAccess)):
                raise TranslationException(TranslationError(
                    stage='semantic', code='E_SEM_LVALUE',
                    message="Слева от присваивания должен быть идентификатор "
                            "или элемент массива",
                ))
            self._visit_expr(e.left)
            sym = self.table.lookup(e.left.name)
            if sym is not None and sym.category == 'const':
                raise TranslationException(TranslationError(
                    stage='semantic', code='E_SEM_CONST_MODIFY',
                    message=f"Нельзя изменять константу '{e.left.name}'",
                    line=e.left.line, col=e.left.col,
                ))
            self._visit_expr(e.right)
            return
        if isinstance(e, BinOp):
            self._visit_expr(e.left)
            self._visit_expr(e.right)
            return
        if isinstance(e, UnaryOp):
            if e.op in ('++', '--') and isinstance(
                    e.operand, (Ident, ArrayAccess)):
                sym = self.table.lookup(e.operand.name)
                if sym is not None and sym.category == 'const':
                    raise TranslationException(TranslationError(
                        stage='semantic', code='E_SEM_CONST_MODIFY',
                        message="Нельзя изменять константу "
                                f"'{e.operand.name}'",
                        line=e.operand.line, col=e.operand.col,
                    ))
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
                        line=e.line, col=e.col,
                    ))
                if sym.params is not None and len(sym.params) != len(e.args):
                    raise TranslationException(TranslationError(
                        stage='semantic', code='E_SEM_ARGS_COUNT',
                        message=f"Неверное количество аргументов функции '{e.func}': "
                                f"ожидалось {len(sym.params)}, передано {len(e.args)}",
                        line=e.line, col=e.col,
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