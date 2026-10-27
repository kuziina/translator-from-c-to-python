import pytest

from src.translator import translate
from src.parser import parse
from src.semantic import SemanticAnalyzer
from src.codegen import CodeGenerator


# ---------- helpers ----------

def gen(src: str) -> str:
    """Парсит, анализирует и генерирует Python-код. Ожидает успех."""
    ast = parse(src)
    SemanticAnalyzer().analyze(ast)
    return CodeGenerator().generate(ast)


def gen_err(src: str):
    """Ожидает, что генерация упадёт (например, неподдерживаемая конструкция)."""
    with pytest.raises(Exception) as exc_info:
        ast = parse(src)
        SemanticAnalyzer().analyze(ast)
        CodeGenerator().generate(ast)
    return exc_info.value


def assert_contains(code: str, *fragments: str) -> None:
    for frag in fragments:
        assert frag in code, f"Ожидался фрагмент {frag!r} в коде:\n{code}"


# ---------- структура программы ----------

def test_empty_program():
    code = gen("")
    assert isinstance(code, str)
    # Нет main — нет точки входа
    assert '__main__' not in code


def test_main_entry_point():
    code = gen("int main() { return 0; }")
    assert_contains(code, 'def main():', 'if __name__ == "__main__":', 'return 0')


def test_import_math():
    code = gen('#include <math.h>\nint main() { return 0; }')
    assert 'import math' in code


def test_import_stdio_ignored():
    """stdio.h не превращается в import — printf заменяется на print."""
    code = gen('#include <stdio.h>\nint main() { return 0; }')
    assert 'import stdio' not in code
    assert 'import math' not in code


def test_unknown_header_comment():
    code = gen('#include <myheader.h>\nint main() { return 0; }')
    assert '# TODO' in code
    assert 'myheader.h' in code


# ---------- переменные и присваивание ----------

def test_var_decl_with_init():
    code = gen("int main() { int x = 5; return x; }")
    assert_contains(code, 'x = 5')


def test_var_decl_without_init_comment():
    code = gen("int main() { int x; return 0; }")
    assert '# int x' in code


def test_multi_var_decl():
    code = gen("int main() { int a = 1, b = 2; return a + b; }")
    assert_contains(code, 'a = 1', 'b = 2')


def test_assignment():
    code = gen("int main() { int x = 1; x = 2; return x; }")
    assert_contains(code, 'x = 2')


def test_compound_assignment():
    code = gen("int main() { int x = 1; x += 3; return x; }")
    assert 'x += 3' in code


# ---------- арифметика и приоритеты ----------

def test_arithmetic():
    code = gen("int main() { int x = 1 + 2 * 3; return x; }")
    # Проверяем, что * обёрнут, чтобы приоритет сохранился
    assert_contains(code, '1 + (2 * 3)')


def test_parens_preserved():
    code = gen("int main() { int x = (1 + 2) * 3; return x; }")
    assert_contains(code, '(1 + 2) * 3')


def test_comparison():
    code = gen("int main() { int x = 1; if (x < 5) { return 1; } return 0; }")
    assert 'x < 5' in code


def test_logical_ops():
    code = gen("""
    int main() {
        int a = 1;
        int b = 0;
        if (a && b || a) { return 1; }
        return 0;
    }
    """)
    assert 'and' in code
    assert 'or' in code


def test_unary_not():
    code = gen("int main() { int a = 0; if (!a) { return 1; } return 0; }")
    assert 'not' in code


def test_ternary():
    code = gen("int main() { int a = 1; int b = a > 0 ? 10 : 20; return b; }")
    assert_contains(code, '10 if', 'else', '20')


# ---------- управляющие конструкции ----------

def test_if_only():
    code = gen("int main() { int x = 1; if (x > 0) { return 1; } return 0; }")
    assert_contains(code, 'if x > 0:', 'return 1')


def test_if_else():
    code = gen("""
    int main() {
        int x = 1;
        if (x > 0) { return 1; } else { return 2; }
    }
    """)
    assert_contains(code, 'if x > 0:', 'else:', 'return 1', 'return 2')


def test_while():
    code = gen("""
    int main() {
        int i = 0;
        while (i < 3) { i++; }
        return 0;
    }
    """)
    assert_contains(code, 'while i < 3:', 'i += 1')


def test_for_range():
    code = gen("""
    int main() {
        for (int i = 0; i < 3; i++) { }
        return 0;
    }
    """)
    assert 'for i in range(0, 3):' in code


def test_for_range_inclusive():
    code = gen("""
    int main() {
        for (int i = 0; i <= 3; i++) { }
        return 0;
    }
    """)
    assert_contains(code, 'range(0, (3) + 1)')


def test_for_fallback_to_while():
    """Если for нельзя свести к range — генерируется while."""
    code = gen("""
    int main() {
        int i = 0;
        for (i = 0; i < 5; i = i + 2) { }
        return 0;
    }
    """)
    assert 'while' in code


def test_do_while():
    code = gen("""
    int main() {
        int i = 0;
        do { i++; } while (i < 3);
        return 0;
    }
    """)
    assert_contains(code, 'while True:', 'break')


def test_break_continue():
    code = gen("""
    int main() {
        int i = 0;
        while (i < 10) {
            i++;
            if (i == 3) { continue; }
            if (i == 7) { break; }
        }
        return 0;
    }
    """)
    assert_contains(code, 'continue', 'break')


# ---------- switch ----------

def test_switch_if_elif_else():
    code = gen("""
    int main() {
        int x = 1;
        switch (x) {
            case 1: return 1;
            case 2: return 2;
            default: return 0;
        }
    }
    """)
    assert_contains(code, 'x == 1', 'elif x == 2', 'else:', 'return 0')


# ---------- функции ----------

def test_function_definition():
    code = gen("""
    int add(int a, int b) { return a + b; }
    int main() { return 0; }
    """)
    assert_contains(code, 'def add(a, b):', 'return a + b')


def test_void_function():
    code = gen("""
    void hello() { return; }
    int main() { hello(); return 0; }
    """)
    assert_contains(code, 'def hello():')


def test_function_call():
    code = gen("""
    int add(int a, int b) { return a + b; }
    int main() {
        int x = add(1, 2);
        return x;
    }
    """)
    assert 'add(1, 2)' in code


def test_recursive_call():
    code = gen("""
    int fact(int n) {
        if (n <= 1) { return 1; }
        return n * fact(n - 1);
    }
    int main() { return fact(5); }
    """)
    assert_contains(code, 'def fact(n):', 'fact(n - 1)')


# ---------- printf ----------

def test_printf_simple():
    code = gen('#include <stdio.h>\nint main() { printf("Hi\\n"); return 0; }')
    assert 'print(' in code
    assert 'Hi' in code


def test_printf_with_int():
    code = gen("""
    int main() {
        int x = 5;
        printf("x = %d\\n", x);
        return 0;
    }
    """)
    assert_contains(code, 'print(', 'x')


def test_printf_with_two_args():
    code = gen("""
    int main() {
        int a = 1;
        int b = 2;
        printf("%d + %d\\n", a, b);
        return 0;
    }
    """)
    assert 'print(' in code
    assert 'a' in code and 'b' in code


def test_printf_no_args():
    code = gen("int main() { printf(); return 0; }")
    assert 'print()' in code


# ---------- сквозные сценарии через translate() ----------

def test_translate_hello_world():
    src = '#include <stdio.h>\nint main() { printf("Hello\\n"); return 0; }'
    r = translate(src)
    assert r.success, r.errors
    assert 'print' in r.python_code
    assert '__main__' in r.python_code


def test_translate_arithmetic():
    src = """
    #include <stdio.h>
    int main() {
        int a = 10;
        int b = 20;
        printf("%d\\n", a + b);
        return 0;
    }
    """
    r = translate(src)
    assert r.success, r.errors


def test_translate_returns_error_on_semantic():
    src = 'int main() { return y; }'  # y не объявлена
    r = translate(src)
    assert not r.success
    assert r.errors
    assert r.errors[0].stage == 'semantic'
    assert r.errors[0].code == 'E_SEM_UNDECLARED'


def test_generated_code_is_valid_python():
    """Сгенерированный код должен компилироваться Python'ом."""
    src = """
    #include <stdio.h>
    int add(int a, int b) { return a + b; }
    int main() {
        int x = add(1, 2);
        if (x > 2) {
            printf("big\\n");
        } else {
            printf("small\\n");
        }
        return 0;
    }
    """
    r = translate(src)
    assert r.success, r.errors
    # Проверка: код синтаксически корректен для Python
    compile(r.python_code, '<generated>', 'exec')