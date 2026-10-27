import pytest
from src.lexer import Lexer
from src.errors import TranslationException


def test_simple_tokens():
    lx = Lexer("int x = 5;")
    codes = [t.code for t in lx.get_tokens()]
    assert 'I3' in codes   # int
    assert 'I1' in codes   # x
    assert 'N1' in codes   # 5
    assert 'D7' in codes   # ;


def test_float_before_int():
    lx = Lexer("float x = 3.14;")
    vals = [t.value for t in lx.get_tokens()]
    assert '3.14' in vals


def test_invalid_char_raises():
    with pytest.raises(TranslationException):
        Lexer("int x = 5 $ 3;")


def test_string_and_char():
    lx = Lexer('printf("%d", x); char c = \'a\';')
    cats = [t.category for t in lx.get_tokens()]
    assert 'STRING' in cats
    assert 'CHAR' in cats