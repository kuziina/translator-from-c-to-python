import pytest

from src.parser import parse
from src.semantic import SemanticAnalyzer
from src.ast_nodes import Program, FuncDef, VarDecl, ReturnStmt, Num
from src.errors import TranslationException


# ---------- helpers ----------

def analyze_ok(src: str) -> Program:
    """Парсит и анализирует; ожидает успех. Возвращает AST."""
    ast = parse(src)
    SemanticAnalyzer().analyze(ast)
    return ast


def analyze_err(src: str) -> TranslationException:
    """Парсит и анализирует; ожидает ошибку. Возвращает исключение."""
    with pytest.raises(TranslationException) as exc_info:
        ast = parse(src)
        SemanticAnalyzer().analyze(ast)
    return exc_info.value


def _err_code(exc: TranslationException) -> str:
    return exc.error.code


def _err_stage(exc: TranslationException) -> str:
    return exc.error.stage


# ---------- позитивные сценарии ----------

def test_empty_program_ok():
    analyze_ok("")


def test_simple_main_ok():
    analyze_ok("int main() { return 0; }")


def test_global_function_forward_use_ok():
    """Функция объявлена ниже — её вызов из main должен быть валиден."""
    src = """
    int main() {
        int x = add(1, 2);
        return x;
    }
    int add(int a, int b) {
        return a + b;
    }
    """
    analyze_ok(src)


def test_local_variables_ok():
    analyze_ok("""
    int main() {
        int x = 1;
        int y = 2;
        int z = x + y;
        return z;
    }
    """)


def test_multi_var_decl_ok():
    analyze_ok("""
    int main() {
        int a = 1, b = 2, c;
        c = a + b;
        return c;
    }
    """)


def test_shadowing_in_function_ok():
    """Параметр и локальная переменная с одним именем в одной функции запрещены,
    но разные функции могут иметь одинаковые имена локальных переменных."""
    analyze_ok("""
    int f(int x) { return x; }
    int g(int x) { return x; }
    """)


def test_void_function_ok():
    analyze_ok("""
    void p() {
        return;
    }
    int main() {
        p();
        return 0;
    }
    """)


def test_printf_builtin_ok():
    """printf — встроенная функция, объявлять не нужно."""
    analyze_ok("""
    int main() {
        printf("Hello %d\\n", 42);
        return 0;
    }
    """)


def test_printf_wrong_arg_count_ok():
    """Для builtin-функций (printf) количество аргументов не проверяем — оно
    переменное (формат + произвольное число подстановок)."""
    analyze_ok("""
    int main() {
        printf("x");
        return 0;
    }
    """)


def test_nested_loops_with_break_continue_ok():
    analyze_ok("""
    int main() {
        int i = 0;
        while (i < 10) {
            if (i == 3) { i++; continue; }
            if (i == 7) { break; }
            i++;
        }
        return 0;
    }
    """)


def test_switch_ok():
    analyze_ok("""
    int main() {
        int x = 1;
        switch (x) {
            case 1:
                return 1;
            case 2:
                return 2;
            default:
                return 0;
        }
    }
    """)


# ---------- ошибки объявления / использования ----------

def test_undeclared_identifier_in_expr():
    exc = analyze_err("""
    int main() {
        int x = y + 1;
        return x;
    }
    """)
    assert _err_stage(exc) == 'semantic'
    assert _err_code(exc) == 'E_SEM_UNDECLARED'


def test_undeclared_identifier_in_assignment_lhs():
    exc = analyze_err("""
    int main() {
        x = 10;
        return 0;
    }
    """)
    assert _err_code(exc) == 'E_SEM_UNDECLARED'


def test_use_before_declaration_in_same_block():
    """Использование до объявления в той же области — ошибка."""
    exc = analyze_err("""
    int main() {
        x = 1;
        int x = 2;
        return x;
    }
    """)
    assert _err_code(exc) == 'E_SEM_UNDECLARED'


def test_redeclaration_in_same_scope():
    exc = analyze_err("""
    int main() {
        int a = 1;
        int a = 2;
        return a;
    }
    """)
    assert _err_stage(exc) == 'semantic'
    assert _err_code(exc) == 'E_SEM_REDECLARED'


def test_redeclaration_param_and_local():
    exc = analyze_err("""
    int f(int a) {
        int a = 1;
        return a;
    }
    """)
    assert _err_code(exc) == 'E_SEM_REDECLARED'


def test_assignment_to_non_identifier():
    exc = analyze_err("""
    int main() {
        1 = 2;
        return 0;
    }
    """)
    assert _err_code(exc) == 'E_SEM_LVALUE'


# ---------- вызовы функций ----------

def test_call_undeclared_function():
    exc = analyze_err("""
    int main() {
        int r = foo(1, 2);
        return r;
    }
    """)
    assert _err_code(exc) == 'E_SEM_FUNC_UNDECLARED'


def test_wrong_arg_count():
    exc = analyze_err("""
    int add(int a, int b) { return a + b; }
    int main() {
        int r = add(1);
        return r;
    }
    """)
    assert _err_code(exc) == 'E_SEM_ARGS_COUNT'


def test_wrong_arg_count_three_instead_of_two():
    exc = analyze_err("""
    int add(int a, int b) { return a + b; }
    int main() {
        int r = add(1, 2, 3);
        return r;
    }
    """)
    assert _err_code(exc) == 'E_SEM_ARGS_COUNT'


def test_zero_args_to_void_param_func_ok():
    analyze_ok("""
    int g() { return 1; }
    int main() { return g(); }
    """)


# ---------- return ----------

def test_return_value_in_void_function():
    exc = analyze_err("""
    void p() {
        return 5;
    }
    int main() { p(); return 0; }
    """)
    assert _err_code(exc) == 'E_SEM_RET_VOID'


def test_missing_return_value_in_non_void():
    exc = analyze_err("""
    int f() {
        return;
    }
    int main() { return f(); }
    """)
    assert _err_code(exc) == 'E_SEM_RET_MISSING'


def test_void_function_with_plain_return_ok():
    analyze_ok("""
    void p() { return; }
    int main() { p(); return 0; }
    """)


# ---------- break/continue ----------

def test_break_outside_loop():
    exc = analyze_err("""
    int main() {
        break;
        return 0;
    }
    """)
    assert _err_code(exc) == 'E_SEM_LOOP_CTRL'


def test_continue_outside_loop():
    exc = analyze_err("""
    int main() {
        continue;
        return 0;
    }
    """)
    assert _err_code(exc) == 'E_SEM_LOOP_CTRL'


def test_break_inside_switch_only():
    """break в switch без цикла — по нашему правилу это ошибка
    (loop_depth == 0). Если хотите разрешить break только в switch —
    нужно отдельно отслеживать switch_depth. Сейчас — ошибка."""
    exc = analyze_err("""
    int main() {
        int x = 1;
        switch (x) {
            case 1:
                break;
            default:
                return 0;
        }
        return 1;
    }
    """)
    assert _err_code(exc) == 'E_SEM_LOOP_CTRL'


# ---------- вложенные области видимости ----------

def test_local_scope_does_not_leak_to_global():
    exc = analyze_err("""
    int f() {
        int inner = 1;
        return inner;
    }
    int main() {
        return inner;
    }
    """)
    assert _err_code(exc) == 'E_SEM_UNDECLARED'


def test_function_scopes_independent():
    """Одинаковые имена локальных переменных в разных функциях — ок."""
    analyze_ok("""
    int f() { int t = 1; return t; }
    int g() { int t = 2; return t; }
    int main() { return f() + g(); }
    """)