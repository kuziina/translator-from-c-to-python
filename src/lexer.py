from __future__ import annotations
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .errors import TranslationError, TranslationException


@dataclass
class Token:
    code: str
    value: str
    line: int
    col: int
    category: str


# Порядок важен: длинные/специфичные — раньше.
# Ключевые слова — через (?<!\w) ... (?!\w), т.к. \b в комбинированном regex
# ведёт себя не всегда предсказуемо.
_TOKEN_SPEC: List[Tuple[str, str, str]] = [
    # --- препроцессор ---
    ('PP1', r'#\s*include', 'PREPROCESSOR'),
    ('PP2', r'#\s*define', 'PREPROCESSOR'),
    ('PP3', r'#\s*ifdef', 'PREPROCESSOR'),
    ('PP4', r'#\s*ifndef', 'PREPROCESSOR'),
    ('PP7', r'#\s*if', 'PREPROCESSOR'),
    ('PP5', r'#\s*else', 'PREPROCESSOR'),
    ('PP6', r'#\s*endif', 'PREPROCESSOR'),

    # --- заголовки ---
    ('H1', r'<[a-zA-Z0-9_/\.]+>', 'HEADER'),
    ('H2', r'"[a-zA-Z0-9_/\.]+"', 'HEADER'),

    # --- ключевые слова ---
    ('I3', r'(?<!\w)int(?!\w)', 'KEYWORD'),
    ('I3', r'(?<!\w)char(?!\w)', 'KEYWORD'),
    ('I3', r'(?<!\w)float(?!\w)', 'KEYWORD'),
    ('I3', r'(?<!\w)double(?!\w)', 'KEYWORD'),
    ('I3', r'(?<!\w)void(?!\w)', 'KEYWORD'),
    ('I3', r'(?<!\w)if(?!\w)', 'KEYWORD'),
    ('I3', r'(?<!\w)else(?!\w)', 'KEYWORD'),
    ('I3', r'(?<!\w)while(?!\w)', 'KEYWORD'),
    ('I3', r'(?<!\w)for(?!\w)', 'KEYWORD'),
    ('I3', r'(?<!\w)do(?!\w)', 'KEYWORD'),
    ('I3', r'(?<!\w)return(?!\w)', 'KEYWORD'),
    ('I3', r'(?<!\w)break(?!\w)', 'KEYWORD'),
    ('I3', r'(?<!\w)continue(?!\w)', 'KEYWORD'),
    ('I3', r'(?<!\w)switch(?!\w)', 'KEYWORD'),
    ('I3', r'(?<!\w)case(?!\w)', 'KEYWORD'),
    ('I3', r'(?<!\w)default(?!\w)', 'KEYWORD'),
    ('I3', r'(?<!\w)const(?!\w)', 'KEYWORD'),

        # --- идентификаторы и макросы ---
    ('I2', r'[A-Z_][A-Z0-9_]*', 'MACRO'),
    ('I1', r'[a-zA-Z_][a-zA-Z0-9_]*', 'IDENTIFIER'),

    # --- комментарии ---
    ('COMMENT', r'//[^\n]*|/\*[\s\S]*?\*/', 'COMMENT'),

    # --- строки/символы ---
    ('S2', r'"[^"\\]*(?:\\.[^"\\]*)*"', 'STRING'),
    ('S1', r"'[^'\\]*(?:\\.[^'\\]*)*'", 'CHAR'),

    # --- числа: сначала float/hex, потом int ---
    ('N2', r'\d+\.\d+', 'NUMBER'),
    ('N3', r'0[xX][0-9a-fA-F]+', 'NUMBER'),
    ('N1', r'\d+', 'NUMBER'),

    # --- операторы: длинные раньше коротких ---
    ('O1',  r'<=',  'OPERATOR'),
    ('O2',  r'>=',  'OPERATOR'),
    ('O3',  r'==',  'OPERATOR'),
    ('O4',  r'!=',  'OPERATOR'),
    ('O5',  r'&&',  'OPERATOR'),
    ('O6',  r'\|\|', 'OPERATOR'),
    ('O7',  r'\+\+', 'OPERATOR'),
    ('O8',  r'--',  'OPERATOR'),
    ('O9',  r'<<',  'OPERATOR'),
    ('O10', r'>>',  'OPERATOR'),
    ('O11', r'\+=', 'OPERATOR'),
    ('O12', r'-=', 'OPERATOR'),
    ('O13', r'\*=', 'OPERATOR'),
    ('O14', r'/=', 'OPERATOR'),
    ('O31', r'%=', 'OPERATOR'),

    ('O16', r'<', 'OPERATOR'),
    ('O17', r'>', 'OPERATOR'),
    ('O18', r'!', 'OPERATOR'),
    ('O19', r'&', 'OPERATOR'),
    ('O20', r'\|', 'OPERATOR'),
    ('O21', r'\^', 'OPERATOR'),
    ('O22', r'~', 'OPERATOR'),
    ('O23', r'\+', 'OPERATOR'),
    ('O24', r'[-–]', 'OPERATOR'),
    ('O25', r'\*', 'OPERATOR'),
    ('O26', r'/', 'OPERATOR'),
    ('O27', r'%', 'OPERATOR'),
    ('O28', r'=', 'OPERATOR'),
    ('O29', r'\?', 'OPERATOR'),
    ('O30', r':', 'OPERATOR'),

    # --- разделители ---
    ('D1', r'\(', 'DELIMITER'),
    ('D2', r'\)', 'DELIMITER'),
    ('D3', r'\{', 'DELIMITER'),
    ('D4', r'\}', 'DELIMITER'),
    ('D5', r'\[', 'DELIMITER'),
    ('D6', r'\]', 'DELIMITER'),
    ('D7', r';', 'DELIMITER'),
    ('D8', r',', 'DELIMITER'),
    ('D9', r'\.', 'DELIMITER'),

    # --- пробелы/переносы — в самом конце ---
    ('SKIP', r'[ \t\r\n]+', 'SKIP'),
]


# Собираем master-regex один раз на уровне модуля.
_parts = []
_group_to_spec = {}
for _i, (_code, _pat, _cat) in enumerate(_TOKEN_SPEC):
    _gname = f'g{_i}'
    _parts.append(f'(?P<{_gname}>{_pat})')
    _group_to_spec[_gname] = (_code, _cat)

_MASTER_RE = re.compile('|'.join(_parts), re.DOTALL)


class Lexer:
    def __init__(self, text: str):
        self.text = text
        self.tokens: List[Token] = []
        self.pos = 0
        self._line = 1
        self._col = 1
        self._tokenize()

    def _advance(self, s: str) -> None:
        for ch in s:
            if ch == '\n':
                self._line += 1
                self._col = 1
            else:
                self._col += 1

    def _tokenize(self) -> None:
        i = 0
        n = len(self.text)
        while i < n:
            m = _MASTER_RE.match(self.text, i)
            if not m:
                ch = self.text[i]
                raise TranslationException(TranslationError(
                    stage='lexer',
                    code='E_LEX_INVALID_CHAR',
                    message=f"Недопустимый символ: {ch!r}",
                    line=self._line, col=self._col,
                ))
            gname = m.lastgroup
            value = m.group()
            code, category = _group_to_spec[gname]

            if category != 'SKIP':
                if value == '–':
                    value = '-'
                self.tokens.append(Token(code, value, self._line, self._col, category))

            self._advance(value)
            i = m.end()

        self.tokens.append(Token('EOF', '', self._line, self._col, 'EOF'))

    # --- API ---
    def peek(self) -> Token:
        return self.tokens[self.pos]

    def consume(self, category: Optional[str] = None) -> Token:
        tok = self.peek()
        if category is not None and tok.category != category:
            raise TranslationException(TranslationError(
                stage='parser',
                code='E_PARSE_UNEXPECTED_TOKEN',
                message=f"Ожидался токен категории {category}, получен {tok.category} ({tok.value!r})",
                line=tok.line, col=tok.col,
            ))
        self.pos += 1
        return tok

    def get_tokens(self) -> List[Token]:
        return [t for t in self.tokens if t.code != 'EOF']

    def print_tokens_table(self) -> None:
        print("\n" + "-" * 78)
        print("ТАБЛИЦА ТОКЕНОВ")
        print("-" * 78)
        print(f"{'№':>4} | {'Код':<10} | {'Категория':<13} | {'Строка:Стлб':<12} | Значение")
        print("-" * 78)
        for idx, t in enumerate(self.tokens):
            if t.code == 'EOF':
                continue
            val = t.value if len(t.value) <= 30 else t.value[:27] + '...'
            print(f"{idx:>4} | {t.code:<10} | {t.category:<13} | {t.line:>4}:{t.col:<7} | {val}")
        print("-" * 78)
        print(f"Всего токенов: {len(self.get_tokens())}")