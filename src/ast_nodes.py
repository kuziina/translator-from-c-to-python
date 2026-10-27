from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Union


@dataclass
class Num:
    val: Union[int, float]


@dataclass
class Str:
    val: str


@dataclass
class Char:
    val: str


@dataclass
class Ident:
    name: str


@dataclass
class BinOp:
    left: 'Expr'
    op: str
    right: 'Expr'


@dataclass
class UnaryOp:
    op: str
    operand: 'Expr'


@dataclass
class TernaryOp:
    cond: 'Expr'
    then_expr: 'Expr'
    else_expr: 'Expr'


@dataclass
class CallExpr:
    func: str
    args: List['Expr']


@dataclass
class Assignment:
    left: 'Expr'
    right: 'Expr'
    op: str = '='


@dataclass
class VarDecl:
    type_: str
    name: str
    init: Optional['Expr'] = None


@dataclass
class MultiVarDecl:
    decls: List[VarDecl]


@dataclass
class ExprStmt:
    expr: 'Expr'


@dataclass
class IfStmt:
    cond: 'Expr'
    then_body: List['Stmt']
    else_body: List['Stmt']


@dataclass
class WhileStmt:
    cond: 'Expr'
    body: List['Stmt']


@dataclass
class DoWhileStmt:
    body: List['Stmt']
    cond: 'Expr'


@dataclass
class ForStmt:
    init: Optional['Stmt']
    cond: Optional['Expr']
    update: Optional['Expr']
    body: List['Stmt']


@dataclass
class ReturnStmt:
    value: Optional['Expr']


@dataclass
class BreakStmt:
    pass


@dataclass
class ContinueStmt:
    pass


@dataclass
class CaseStmt:
    value: Optional['Expr']
    body: List['Stmt']


@dataclass
class SwitchStmt:
    expr: 'Expr'
    cases: List[CaseStmt]


@dataclass
class IncludeStmt:
    header: str
    is_system: bool


@dataclass
class DefineStmt:
    name: str
    value: Optional[str]


@dataclass
class IfdefStmt:
    macro: str
    body: List['Stmt']
    else_body: List['Stmt']


@dataclass
class CommentStmt:
    text: str


@dataclass
class FuncDef:
    ret_type: str
    name: str
    params: List[VarDecl]
    body: List['Stmt']


@dataclass
class Program:
    includes: List[IncludeStmt]
    defines: List[DefineStmt]
    funcs: List[FuncDef]


Expr = Union[Num, Str, Char, Ident, BinOp, UnaryOp, TernaryOp, CallExpr, Assignment]
Stmt = Union[ExprStmt, VarDecl, MultiVarDecl, IfStmt, WhileStmt, DoWhileStmt, ForStmt,
             ReturnStmt, BreakStmt, ContinueStmt, SwitchStmt, IncludeStmt,
             DefineStmt, IfdefStmt, CommentStmt]