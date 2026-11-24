"""Быстрый ручной прогон всех C-тестов из examples/ через транслятор.

Использование:
    python run_examples.py            # сводка по всем файлам
    python run_examples.py --save     # сохранять .py в examples/out/
    python run_examples.py --file examples/07_loops.c   # показать код
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.translator import translate  # noqa: E402

ROOT = Path(__file__).resolve().parent
EXAMPLES = ROOT / "examples"
ERRORS = EXAMPLES / "errors"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Прогон C-тестов через транслятор")
    parser.add_argument("--save", action="store_true",
                        help="сохранять Python в examples/out/")
    parser.add_argument(
        "--file", help="транслировать один файл и показать результат")
    args = parser.parse_args()

    if args.file:
        path = Path(args.file)
        result = translate(path.read_text(encoding="utf-8"))
        if result.success:
            print(result.python_code)
            return 0
        print(result.errors[0], file=sys.stderr)
        return 1

    out_dir = EXAMPLES / "out"
    if args.save:
        out_dir.mkdir(exist_ok=True)

    files = sorted(EXAMPLES.glob("*.c")) + sorted(ERRORS.glob("*.c"))
    passed = 0
    print(f"{'Файл':<38} {'Ожидание':<22} Результат")
    print("-" * 80)
    for path in files:
        result = translate(path.read_text(encoding="utf-8"))
        expect_error = path.parent == ERRORS
        if not expect_error:
            ok = result.success
            status = "OK" if ok else f"FAIL: {result.errors[0].code}"
        else:
            expected = path.read_text(encoding="utf-8").splitlines()[0]
            code = (expected.split("EXPECT:")[-1].strip()
                    if "EXPECT:" in expected else "?")
            ok = (not result.success) and result.errors \
                and result.errors[0].code.startswith(code)
            status = f"ошибка ожидаемо: {result.errors[0].code}" if ok \
                else ("FAIL: получено "
                      f"{result.errors[0].code if result.errors else 'успех'}")

        if ok:
            passed += 1
            if args.save and result.python_code:
                (out_dir / (path.stem + ".py")).write_text(
                    result.python_code, encoding="utf-8")
        mark = "OK  " if ok else "FAIL"
        print(f"{mark} {path.relative_to(ROOT)!s:<33} "
              f"{'трансляция' if not expect_error else code:<22} {status}")

    print("-" * 80)
    print(f"Итого: {passed}/{len(files)} тестов пройдено")
    return 0 if passed == len(files) else 1


if __name__ == "__main__":
    raise SystemExit(main())
