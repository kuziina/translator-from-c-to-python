from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional

from .lexer import Lexer, Token
from .parser import Parser
from .semantic import SemanticAnalyzer
from .codegen import CodeGenerator
from .ast_nodes import Program
from .errors import TranslationError, TranslationException


@dataclass
class TranslationResult:
    success: bool
    python_code: Optional[str]
    errors: List[TranslationError] = field(default_factory=list)
    tokens: Optional[List[Token]] = None
    ast: Optional[Program] = None


def translate(source: str, debug: bool = False) -> TranslationResult:
    tokens: Optional[List[Token]] = None
    ast: Optional[Program] = None
    try:
        lexer = Lexer(source)
        tokens = lexer.get_tokens()
        parser = Parser(lexer)
        ast = parser.parse_program()
        SemanticAnalyzer().analyze(ast)
        code = CodeGenerator().generate(ast)
        return TranslationResult(
            success=True, python_code=code,
            tokens=tokens if debug else None,
            ast=ast if debug else None,
        )
    except TranslationException as ex:
        return TranslationResult(
            success=False, python_code=None, errors=[ex.error],
            tokens=tokens if debug else None,
            ast=ast if debug else None,
        )
    except Exception as ex:  # непредвиденное
        return TranslationResult(
            success=False, python_code=None,
            errors=[TranslationError(
                stage='internal', code='E_INTERNAL',
                message=f"Внутренняя ошибка: {type(ex).__name__}: {ex}",
            )],
            tokens=tokens if debug else None,
            ast=ast if debug else None,
        )