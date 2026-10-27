from src.translator import translate


def test_hello_world():
    src = '#include <stdio.h>\nint main() { printf("Hello\\n"); return 0; }'
    r = translate(src)
    assert r.success, r.errors
    assert 'print' in r.python_code
    assert '__main__' in r.python_code


def test_syntax_error_returned():
    r = translate("int main() { return 0 }")
    assert not r.success
    assert len(r.errors) == 1
    assert r.errors[0].stage == 'parser'