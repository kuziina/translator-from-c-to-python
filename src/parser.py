from __future__ import annotations
from typing import List, Optional

from .ast_nodes import (
    Num, Str, Char, Ident, BinOp, UnaryOp, TernaryOp, CallExpr, Assignment,
    VarDecl, MultiVarDecl, ExprStmt, IfStmt, WhileStmt, DoWhileStmt, ForStmt,
    ReturnStmt, BreakStmt, ContinueStmt, CaseStmt, SwitchStmt,
    IncludeStmt, DefineStmt, CommentStmt, FuncDef, Program,
    Expr, Stmt,
)
from .errors import TranslationError, TranslationException
from .lexer import Lexer, Token


TYPE_KEYWORDS = {'int', 'char', 'float', 'double', 'void'}


class Parser:
    def __init__(self, lexer: Lexer):
        self.lexer = lexer

    # ---- helpers ----
    def _peek(self) -> Token:
        return self.lexer.peek()

    def _is(self, category: str, value: Optional[str] = None) -> bool:
        t = self._peek()
        if t.category != category:
            return False
        if value is not None and t.value != value:
            return False
        return True

    def _is_kw(self, kw: str) -> bool:
        return self._is('KEYWORD', kw)

    def _is_delim(self, val: str) -> bool:
        return self._is('DELIMITER', val)

    def _is_op(self, val: str) -> bool:
        return self._is('OPERATOR', val)

    def _expect(self, category: str, value: Optional[str] = None) -> Token:
        t = self._peek()
        if t.category != category or (value is not None and t.value != value):
            raise TranslationException(TranslationError(
                stage='parser',
                code='E_PARSE_EXPECTED',
                message=f"Ожидалось {value or category}, получено {t.value or t.category!r}",
                line=t.line, col=t.col,
            ))
        return self.lexer.consume()

    # ---- program ----
    def parse_program(self) -> Program:
        includes: List[IncludeStmt] = []
        defines: List[DefineStmt] = []
        funcs: List[FuncDef] = []

        while self._peek().code != 'EOF':
            if self._is('PREPROCESSOR'):
                pp = self._peek().value
                if pp == '#include':
                    includes.append(self.parse_include())
                elif pp == '#define':
                    defines.append(self.parse_define())
                else:
                    # Неподдерживаемые директивы пропускаем до конца строки
                    self.lexer.consume()
                    while self._peek().code != 'EOF' and self._peek().value != '\n':
                        self.lexer.consume()
                    # SKIP для \n уже отработан лексером
            elif self._is('COMMENT'):
                self.lexer.consume()  # комментарии между функциями пропускаем
            else:
                funcs.append(self.parse_func())

        return Program(includes, defines, funcs)

    def parse_include(self) -> IncludeStmt:
        self._expect('PREPROCESSOR')
        hdr = self._peek()
        if hdr.category != 'HEADER':
            raise TranslationException(TranslationError(
                stage='parser',
                code='E_PARSE_INCLUDE',
                message=f"Ожидался заголовочный файл, получено {hdr.value!r}",
                line=hdr.line, col=hdr.col,
            ))
        self.lexer.consume()
        is_system = hdr.value.startswith('<')
        name = hdr.value[1:-1]
        return IncludeStmt(name, is_system)

    def parse_define(self) -> DefineStmt:
        self._expect('PREPROCESSOR')
        name_tok = self._peek()
        if name_tok.category not in ('IDENTIFIER', 'MACRO', 'KEYWORD'):
            raise TranslationException(TranslationError(
                stage='parser',
                code='E_PARSE_DEFINE',
                message=f"Ожидалось имя макроса, получено {name_tok.value!r}",
                line=name_tok.line, col=name_tok.col,
            ))
        self.lexer.consume()
        # Собираем всё до конца строки как «значение»
        parts: List[str] = []
        # У нас SKIP уже съел \n, поэтому просто собираем токены,
        # пока не встретим 'EOI' (следующий # или объявление) — упрощённо
        # читаем токены, пока они на той же строке
        start_line = name_tok.line
        while self._peek().code != 'EOF' and self._peek().line == start_line:
            parts.append(self.lexer.consume().value)
        value = ' '.join(parts) if parts else None
        return DefineStmt(name_tok.value, value)

    def parse_func(self) -> FuncDef:
        ret_type_tok = self._peek()
        if ret_type_tok.category != 'KEYWORD' or ret_type_tok.value not in TYPE_KEYWORDS:
            raise TranslationException(TranslationError(
                stage='parser',
                code='E_PARSE_FUNC_RET',
                message=f"Ожидался тип возвращаемого значения, получено {ret_type_tok.value!r}",
                line=ret_type_tok.line, col=ret_type_tok.col,
            ))
        self.lexer.consume()

        name_tok = self._peek()
        if name_tok.category != 'IDENTIFIER':
            raise TranslationException(TranslationError(
                stage='parser',
                code='E_PARSE_FUNC_NAME',
                message=f"Ожидалось имя функции, получено {name_tok.value!r}",
                line=name_tok.line, col=name_tok.col,
            ))
        self.lexer.consume()

        self._expect('DELIMITER', '(')
        params = self._parse_param_list()
        self._expect('DELIMITER', ')')

        self._expect('DELIMITER', '{')
        body = self._parse_block()
        self._expect('DELIMITER', '}')

        return FuncDef(ret_type_tok.value, name_tok.value, params, body)

    def _parse_param_list(self) -> List[VarDecl]:
        if self._is_delim(')'):
            return []
        # void в списке параметров = пустой список
        if self._is_kw('void') and self.lexer.tokens[self.lexer.pos + 1].value == ')':
            self.lexer.consume()
            return []

        params = [self._parse_param()]
        while self._is_delim(','):
            self.lexer.consume()
            params.append(self._parse_param())
        return params

    def _parse_param(self) -> VarDecl:
        type_tok = self._peek()
        if type_tok.category != 'KEYWORD' or type_tok.value not in TYPE_KEYWORDS:
            raise TranslationException(TranslationError(
                stage='parser',
                code='E_PARSE_PARAM_TYPE',
                message=f"Ожидался тип параметра, получено {type_tok.value!r}",
                line=type_tok.line, col=type_tok.col,
            ))
        self.lexer.consume()
        name_tok = self._expect('IDENTIFIER')
        return VarDecl(type_tok.value, name_tok.value)

    def _parse_block(self) -> List[Stmt]:
        stmts: List[Stmt] = []
        while not self._is_delim('}') and self._peek().code != 'EOF':
            stmts.append(self.parse_stmt())
        return stmts

    def _parse_statement_or_block(self) -> List[Stmt]:
        if self._is_delim('{'):
            self.lexer.consume()
            body = self._parse_block()
            self._expect('DELIMITER', '}')
            return body
        return [self.parse_stmt()]

    # ---- statements ----
    def parse_stmt(self) -> Stmt:
        t = self._peek()

        if t.category == 'COMMENT':
            self.lexer.consume()
            return CommentStmt(t.value)
        if t.category == 'KEYWORD':
            if t.value == 'return':
                return self.parse_return()
            if t.value == 'break':
                self.lexer.consume()
                self._expect('DELIMITER', ';')
                return BreakStmt()
            if t.value == 'continue':
                self.lexer.consume()
                self._expect('DELIMITER', ';')
                return ContinueStmt()
            if t.value == 'if':
                return self.parse_if()
            if t.value == 'while':
                return self.parse_while()
            if t.value == 'do':
                return self.parse_do_while()
            if t.value == 'for':
                return self.parse_for()
            if t.value == 'switch':
                return self.parse_switch()
            if t.value in ('int', 'char', 'float', 'double'):
                return self.parse_declaration()

        expr = self.parse_expr()
        self._expect('DELIMITER', ';')
        return ExprStmt(expr)

    def parse_declaration(self) -> Stmt:
        type_tok = self.lexer.consume()  # KEYWORD
        decls: List[VarDecl] = []
        while True:
            name_tok = self._expect('IDENTIFIER')
            init: Optional[Expr] = None
            if self._is_op('='):
                self.lexer.consume()
                init = self.parse_expr()
            decls.append(VarDecl(type_tok.value, name_tok.value, init))
            if self._is_delim(','):
                self.lexer.consume()
                continue
            break
        self._expect('DELIMITER', ';')
        return decls[0] if len(decls) == 1 else MultiVarDecl(decls)

    def parse_return(self) -> ReturnStmt:
        self.lexer.consume()  # return
        val: Optional[Expr] = None
        if not self._is_delim(';'):
            val = self.parse_expr()
        self._expect('DELIMITER', ';')
        return ReturnStmt(val)

    def parse_if(self) -> IfStmt:
        self.lexer.consume()  # if
        self._expect('DELIMITER', '(')
        cond = self.parse_expr()
        self._expect('DELIMITER', ')')
        then_body = self._parse_statement_or_block()

        else_body: List[Stmt] = []
        if self._is_kw('else'):
            self.lexer.consume()
            else_body = self._parse_statement_or_block()
        return IfStmt(cond, then_body, else_body)

    def parse_while(self) -> WhileStmt:
        self.lexer.consume()  # while
        self._expect('DELIMITER', '(')
        cond = self.parse_expr()
        self._expect('DELIMITER', ')')
        body = self._parse_statement_or_block()
        return WhileStmt(cond, body)

    def parse_do_while(self) -> DoWhileStmt:
        self.lexer.consume()  # do
        body = self._parse_statement_or_block()
        if not self._is_kw('while'):
            raise TranslationException(TranslationError(
                stage='parser', code='E_PARSE_DOWHILE',
                message="Ожидалось 'while' после тела do",
                line=self._peek().line, col=self._peek().col,
            ))
        self.lexer.consume()
        self._expect('DELIMITER', '(')
        cond = self.parse_expr()
        self._expect('DELIMITER', ')')
        self._expect('DELIMITER', ';')
        return DoWhileStmt(body, cond)

    def parse_for(self) -> ForStmt:
        self.lexer.consume()  # for
        self._expect('DELIMITER', '(')

        # init: либо объявление, либо выражение, либо пусто
        init: Optional[Stmt] = None
        if self._is_kw('int') or self._is_kw('char') or self._is_kw('float') or self._is_kw('double'):
            init = self.parse_declaration()
        elif not self._is_delim(';'):
            e = self.parse_expr()
            self._expect('DELIMITER', ';')
            init = ExprStmt(e)
        else:
            self._expect('DELIMITER', ';')

        cond: Optional[Expr] = None
        if not self._is_delim(';'):
            cond = self.parse_expr()
        self._expect('DELIMITER', ';')

        update: Optional[Expr] = None
        if not self._is_delim(')'):
            update = self.parse_expr()
        self._expect('DELIMITER', ')')

        body = self._parse_statement_or_block()
        return ForStmt(init, cond, update, body)

    def parse_switch(self) -> SwitchStmt:
        self.lexer.consume()  # switch
        self._expect('DELIMITER', '(')
        expr = self.parse_expr()
        self._expect('DELIMITER', ')')
        self._expect('DELIMITER', '{')

        cases: List[CaseStmt] = []
        while not self._is_delim('}') and self._peek().code != 'EOF':
            if self._is_kw('case'):
                self.lexer.consume()
                val = self.parse_expr()
                self._expect('OPERATOR', ':')
                body = self._parse_case_body()
                cases.append(CaseStmt(val, body))
            elif self._is_kw('default'):
                self.lexer.consume()
                self._expect('OPERATOR', ':')
                body = self._parse_case_body()
                cases.append(CaseStmt(None, body))
            elif self._peek().category == 'COMMENT':
                self.lexer.consume()
            else:
                tok = self._peek()
                raise TranslationException(TranslationError(
                    stage='parser', code='E_PARSE_SWITCH',
                    message=f"Ожидался 'case'/'default', получено {tok.value!r}",
                    line=tok.line, col=tok.col,
                ))
        self._expect('DELIMITER', '}')
        return SwitchStmt(expr, cases)

    def _parse_case_body(self) -> List[Stmt]:
        body: List[Stmt] = []
        while self._peek().code != 'EOF':
            if self._is_kw('case') or self._is_kw('default') or self._is_delim('}'):
                break
            body.append(self.parse_stmt())
        return body

    # ---- expressions ----
    def parse_expr(self) -> Expr:
        return self.parse_assignment()

    def parse_assignment(self) -> Expr:
        left = self.parse_ternary()
        if self._peek().category == 'OPERATOR' and self._peek().value in ('=', '+=', '-=', '*=', '/=', '%='):
            op = self.lexer.consume().value
            right = self.parse_assignment()
            return Assignment(left, right, op)
        return left

    def parse_ternary(self) -> Expr:
        cond = self.parse_logical_or()
        if self._is_op('?'):
            self.lexer.consume()
            then_e = self.parse_expr()
            self._expect('OPERATOR', ':')
            else_e = self.parse_ternary()
            return TernaryOp(cond, then_e, else_e)
        return cond

    def parse_logical_or(self) -> Expr:
        left = self.parse_logical_and()
        while self._is_op('||'):
            op = self.lexer.consume().value
            right = self.parse_logical_and()
            left = BinOp(left, op, right)
        return left

    def parse_logical_and(self) -> Expr:
        left = self.parse_bitwise_or()
        while self._is_op('&&'):
            op = self.lexer.consume().value
            right = self.parse_bitwise_or()
            left = BinOp(left, op, right)
        return left

    def parse_bitwise_or(self) -> Expr:
        left = self.parse_bitwise_xor()
        while self._is_op('|'):
            op = self.lexer.consume().value
            right = self.parse_bitwise_xor()
            left = BinOp(left, op, right)
        return left

    def parse_bitwise_xor(self) -> Expr:
        left = self.parse_bitwise_and()
        while self._is_op('^'):
            op = self.lexer.consume().value
            right = self.parse_bitwise_and()
            left = BinOp(left, op, right)
        return left

    def parse_bitwise_and(self) -> Expr:
        left = self.parse_equality()
        while self._is_op('&'):
            op = self.lexer.consume().value
            right = self.parse_equality()
            left = BinOp(left, op, right)
        return left

    def parse_equality(self) -> Expr:
        left = self.parse_comparison()
        while self._peek().category == 'OPERATOR' and self._peek().value in ('==', '!='):
            op = self.lexer.consume().value
            right = self.parse_comparison()
            left = BinOp(left, op, right)
        return left

    def parse_comparison(self) -> Expr:
        left = self.parse_shift()
        while self._peek().category == 'OPERATOR' and self._peek().value in ('>', '<', '>=', '<='):
            op = self.lexer.consume().value
            right = self.parse_shift()
            left = BinOp(left, op, right)
        return left

    def parse_shift(self) -> Expr:
        left = self.parse_additive()
        while self._peek().category == 'OPERATOR' and self._peek().value in ('<<', '>>'):
            op = self.lexer.consume().value
            right = self.parse_additive()
            left = BinOp(left, op, right)
        return left

    def parse_additive(self) -> Expr:
        left = self.parse_multiplicative()
        while self._peek().category == 'OPERATOR' and self._peek().value in ('+', '-'):
            op = self.lexer.consume().value
            right = self.parse_multiplicative()
            left = BinOp(left, op, right)
        return left

    def parse_multiplicative(self) -> Expr:
        left = self.parse_unary()
        while self._peek().category == 'OPERATOR' and self._peek().value in ('*', '/', '%'):
            op = self.lexer.consume().value
            right = self.parse_unary()
            left = BinOp(left, op, right)
        return left

    def parse_unary(self) -> Expr:
        if self._peek().category == 'OPERATOR' and self._peek().value in ('+', '-', '!', '~', '++', '--', '&', '*'):
            op = self.lexer.consume().value
            operand = self.parse_unary()
            return UnaryOp(op, operand)
        return self.parse_primary()

    def parse_primary(self) -> Expr:
        t = self._peek()

        if t.category == 'NUMBER':
            self.lexer.consume()
            v = t.value
            if v.lower().startswith('0x'):
                return Num(int(v, 16))
            if '.' in v:
                return Num(float(v))
            return Num(int(v))

        if t.category == 'STRING':
            self.lexer.consume()
            return Str(t.value[1:-1])

        if t.category == 'CHAR':
            self.lexer.consume()
            return Char(t.value[1:-1])

        if t.category in ('IDENTIFIER', 'MACRO'):
            self.lexer.consume()
            if self._is_delim('('):
                return self.parse_call(t.value)
            return Ident(t.value)

        if self._is_delim('('):
            self.lexer.consume()
            e = self.parse_expr()
            self._expect('DELIMITER', ')')
            return e

        raise TranslationException(TranslationError(
            stage='parser', code='E_PARSE_PRIMARY',
            message=f"Неожиданный токен: {t.value!r}",
            line=t.line, col=t.col,
        ))

    def parse_call(self, func_name: str) -> CallExpr:
        self._expect('DELIMITER', '(')
        args: List[Expr] = []
        if not self._is_delim(')'):
            args.append(self.parse_expr())
            while self._is_delim(','):
                self.lexer.consume()
                args.append(self.parse_expr())
        self._expect('DELIMITER', ')')
        return CallExpr(func_name, args)


def parse(source: str) -> Program:
    return Parser(Lexer(source)).parse_program()