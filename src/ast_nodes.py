from __future__ import annotations
from dataclasses import dataclass, field
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
class Bool:
    val: bool
    line: int = 0
    col: int = 0


@dataclass
class Ident:
    name: str
    line: int = 0
    col: int = 0


@dataclass
class ArrayAccess:
    name: str
    indices: List['Expr']
    line: int = 0
    col: int = 0


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
    line: int = 0
    col: int = 0


@dataclass
class Assignment:
    left: 'Expr'
    right: 'Expr'
    op: str = '='


@dataclass
class ArrayInit:
    values: List[Union['Expr', 'ArrayInit']]


@dataclass
class VarDecl:
    type_: str
    name: str
    init: Optional['Expr'] = None
    is_const: bool = False
    line: int = 0
    col: int = 0
    dims: List['Expr'] = field(default_factory=list)
    array_init: Optional['ArrayInit'] = None


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
    line: int = 0
    col: int = 0


@dataclass
class BreakStmt:
    line: int = 0
    col: int = 0


@dataclass
class ContinueStmt:
    line: int = 0
    col: int = 0


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
    line: int = 0
    col: int = 0


@dataclass
class IfdefStmt:
    macro: str
    body: List['Stmt']
    else_body: List['Stmt']
    negated: bool = False   # True для #ifndef
    line: int = 0
    col: int = 0


@dataclass
class CommentStmt:
    text: str


@dataclass
class FuncDef:
    ret_type: str
    name: str
    params: List[VarDecl]
    body: List['Stmt']
    line: int = 0
    col: int = 0
    leading_comments: List[CommentStmt] = field(default_factory=list)


@dataclass
class Program:
    includes: List[IncludeStmt]
    defines: List[DefineStmt]
    funcs: List[FuncDef]
    header_comments: List[CommentStmt] = field(default_factory=list)


Expr = Union[Num, Str, Char, Bool, Ident, ArrayAccess, BinOp, UnaryOp,
             TernaryOp, CallExpr, Assignment]
Stmt = Union[ExprStmt, VarDecl, MultiVarDecl, IfStmt, WhileStmt, DoWhileStmt,
             ForStmt, ReturnStmt, BreakStmt, ContinueStmt, SwitchStmt,
             IncludeStmt, DefineStmt, IfdefStmt, CommentStmt]