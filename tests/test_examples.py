"""Интеграционные тесты транслятора: прогон C-примеров из examples/.

Позитивные файлы (examples/*.c) обязаны транслироваться успешно, а
сгенерированный Python обязан быть синтаксически корректным (compile()).

Негативные файлы (examples/errors/*.c) обязаны завершаться ошибкой, причём
код ошибки указан в первой строке файла как ``// EXPECT: <код>``. Код может
быть точным (``E_SEM_UNDECLARED``) или префиксом этапа (``E_PARSE``),
если точный код парсера не фиксирован.

Запуск: python -m pytest tests/test_examples.py -v
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from src.translator import translate

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = ROOT / "examples"
ERRORS_DIR = EXAMPLES_DIR / "errors"

POSITIVE_CASES = sorted(EXAMPLES_DIR.glob("*.c"))
NEGATIVE_CASES = sorted(ERRORS_DIR.glob("*.c"))


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _expected_code(path: Path) -> str:
    """Извлекает ожидаемый код ошибки из строки '// EXPECT: <код>'."""
    match = re.search(r"EXPECT:\s*([A-Z_0-9]+)", _source(path))
    assert match, f"{path.name}: нет строки '// EXPECT:' с кодом ошибки"
    return match.group(1)


@pytest.mark.parametrize("path", POSITIVE_CASES, ids=lambda p: p.name)
class TestPositiveExamples:
    """Каждый корректный C-файл транслируется в корректный Python."""

    def test_translation_succeeds(self, path: Path) -> None:
        result = translate(_source(path))
        assert result.success, f"{path.name}: {result.errors[0]}"

    def test_generated_python_compiles(self, path: Path) -> None:
        result = translate(_source(path))
        assert result.success, f"{path.name}: {result.errors[0]}"
        assert result.python_code is not None and result.python_code.strip()
        compile(result.python_code, path.name, "exec")


@pytest.mark.parametrize("path", NEGATIVE_CASES, ids=lambda p: p.name)
class TestNegativeExamples:
    """Каждый ошибочный C-файл даёт ошибку ожидаемого типа."""

    def test_translation_fails_with_expected_code(self, path: Path) -> None:
        result = translate(_source(path))
        assert not result.success, (
            f"{path.name}: трансляция прошла, ожидалась ошибка")
        assert result.errors, f"{path.name}: нет ни одной ошибки"
        expected = _expected_code(path)
        actual = result.errors[0].code
        assert actual == expected or actual.startswith(expected), (
            f"{path.name}: ожидался код {expected!r}, получен {actual!r} "
            f"({result.errors[0]})"
        )


def test_suite_not_empty() -> None:
    """Страховка: наборы тестов не должны опустеть при переименовании папок."""
    assert len(POSITIVE_CASES) >= 10
    assert len(NEGATIVE_CASES) >= 10
