import pytest
from src.parser import parse
from src.ast_nodes import Program, FuncDef, ReturnStmt, Num
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