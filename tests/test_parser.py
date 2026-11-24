import pytest
from src.parser import parse
from src.ast_nodes import (
    Program, FuncDef, ReturnStmt, Num, VarDecl, ArrayAccess, ArrayInit,
)
from src.errors import TranslationException


def test_empty_program():
    ast = parse("")
    assert isinstance(ast, Program)


def test_simple_main():
    ast = parse("int main() { return 0; }")
    assert len(ast.funcs) == 1
    fn = ast.funcs[0]
    assert fn.name == 'main'
    assert isinstance(fn.body[0], ReturnStmt)
    assert isinstance(fn.body[0].value, Num)


def test_undeclared_syntax_error():
    with pytest.raises(TranslationException):
        parse("int main() { return 0 }")  # нет ';'


# ---------- массивы ----------

def test_2d_array_declaration():
    ast = parse("int main() { int a[2][3]; return 0; }")
    decl = ast.funcs[0].body[0]
    assert isinstance(decl, VarDecl)
    assert decl.name == 'a'
    assert len(decl.dims) == 2
    assert isinstance(decl.dims[0], Num) and decl.dims[0].val == 2
    assert isinstance(decl.dims[1], Num) and decl.dims[1].val == 3


def test_unsized_array_declaration():
    ast = parse("int main() { int a[] = {1, 2}; return 0; }")
    decl = ast.funcs[0].body[0]
    assert isinstance(decl, VarDecl)
    assert isinstance(decl.dims[0], Num) and decl.dims[0].val == 0


def test_nested_array_initializer():
    ast = parse("int main() { int a[2][2] = {{1, 2}, {3, 4}}; return 0; }")
    decl = ast.funcs[0].body[0]
    assert isinstance(decl.array_init, ArrayInit)
    assert len(decl.array_init.values) == 2
    assert isinstance(decl.array_init.values[0], ArrayInit)


def test_2d_array_access():
    ast = parse("int main() { int a[2][3]; return a[1][2]; }")
    ret = ast.funcs[0].body[1]
    assert isinstance(ret, ReturnStmt)
    assert isinstance(ret.value, ArrayAccess)
    assert ret.value.name == 'a'
    assert len(ret.value.indices) == 2


def test_array_element_assignment():
    ast = parse("int main() { int a[2][3]; a[0][1] = 5; return 0; }")
    stmt = ast.funcs[0].body[1]
    assert isinstance(stmt.expr.left, ArrayAccess)
    assert stmt.expr.left.name == 'a'