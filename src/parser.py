from __future__ import annotations
from typing import List, Optional, Tuple

from .ast_nodes import (
    Num, Str, Char, Bool, Ident, ArrayAccess, ArrayInit, BinOp, UnaryOp,
    TernaryOp, CallExpr, Assignment, VarDecl, MultiVarDecl, ExprStmt, IfStmt,
    WhileStmt, DoWhileStmt, ForStmt, ReturnStmt, BreakStmt, ContinueStmt,
    CaseStmt, SwitchStmt, IncludeStmt, DefineStmt, IfdefStmt, CommentStmt,
    FuncDef, Program, Expr, Stmt,
)
from .errors import TranslationError, TranslationException
from .lexer import Lexer, Token


TYPE_KEYWORDS = {'int', 'char', 'float', 'double', 'void'}
TYPE_QUALIFIERS = {'short', 'long', 'unsigned', 'signed'}


def _norm_pp(value: str) -> str:
    return ''.join(value.split())


class Parser:
    def __init__(self, lexer: Lexer):
        self.lexer = lexer

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

    def _skip_to_eol(self, start_tok: Token) -> None:
        self.lexer.consume()
        while self._peek().code != 'EOF' and self._peek().line == start_tok.line:
            self.lexer.consume()

    def _skip_ifdef_block(self) -> None:
        depth = 0
        while self._peek().code != 'EOF':
            t = self._peek()
            if t.category == 'PREPROCESSOR':
                pp = _norm_pp(t.value)
                if pp in ('#ifdef', '#ifndef', '#if'):
                    depth += 1
                    self._skip_to_eol(t)
                    continue
                if pp == '#endif':
                    self.lexer.consume()
                    if depth == 0:
                        return
                    depth -= 1
                    continue
            self.lexer.consume()

    def parse_program(self) -> Program:
        includes: List[IncludeStmt] = []
        defines: List[DefineStmt] = []
        funcs: List[FuncDef] = []
        header_comments: List[CommentStmt] = []
        pending_comments: List[CommentStmt] = []
        seen_construct = False

        while self._peek().code != 'EOF':
            if self._is('PREPROCESSOR'):
                seen_construct = True
                pp = _norm_pp(self._peek().value)
                if pp == '#include':
                    includes.append(self.parse_include())
                elif pp == '#define':
                    defines.append(self.parse_define())
                elif pp in ('#ifdef', '#ifndef'):
                    self._skip_ifdef_block()
                else:
                    self._skip_to_eol(self._peek())
            elif self._is('COMMENT'):
                tok = self.lexer.consume()
                comment = CommentStmt(tok.value)
                if seen_construct:
                    pending_comments.append(comment)
                else:
                    header_comments.append(comment)
            else:
                seen_construct = True
                fn = self.parse_func()
                if pending_comments:
                    fn.leading_comments = pending_comments
                    pending_comments = []
                funcs.append(fn)

        if pending_comments and funcs:
            funcs[-1].body.extend(pending_comments)

        return Program(includes, defines, funcs, header_comments)

    def parse_include(self) -> IncludeStmt:
        self._expect('PREPROCESSOR')
        hdr = self._peek()
        if hdr.category == 'HEADER': 
            self.lexer.consume()
            return IncludeStmt(hdr.value[1:-1], is_system=True)
        if hdr.category == 'STRING': 
            self.lexer.consume()
            return IncludeStmt(hdr.value[1:-1], is_system=False)
        raise TranslationException(TranslationError(
            stage='parser',
            code='E_PARSE_INCLUDE',
            message=f"Ожидался заголовочный файл, получено {hdr.value!r}",
            line=hdr.line, col=hdr.col,
        ))

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
        parts: List[str] = []
        start_line = name_tok.line
        while self._peek().code != 'EOF' and self._peek().line == start_line:
            parts.append(self.lexer.consume().value)
        value = ' '.join(parts) if parts else None
        return DefineStmt(name_tok.value, value)

    def _parse_type_spec(self, error_code: str,
                         error_message: str) -> Tuple[str, Token]:
        first_tok = self._peek()
        quals: List[str] = []
        while (self._peek().category == 'KEYWORD'
               and self._peek().value in TYPE_QUALIFIERS):
            quals.append(self.lexer.consume().value)
        base_tok = self._peek()
        if base_tok.category == 'KEYWORD' and base_tok.value in TYPE_KEYWORDS:
            self.lexer.consume()
            base = base_tok.value
        elif quals:
            base = 'int'
        else:
            raise TranslationException(TranslationError(
                stage='parser', code=error_code,
                message=f"{error_message}, получено {first_tok.value!r}",
                line=first_tok.line, col=first_tok.col,
            ))
        return ' '.join(quals + [base]), first_tok

    def parse_func(self) -> FuncDef:
        ret_type, ret_type_tok = self._parse_type_spec(
            'E_PARSE_FUNC_RET', 'Ожидался тип возвращаемого значения')

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

        return FuncDef(ret_type, name_tok.value, params, body,
                       line=ret_type_tok.line, col=ret_type_tok.col)

    def _parse_param_list(self) -> List[VarDecl]:
        if self._is_delim(')'):
            return []
        if self._is_kw('void') and self.lexer.tokens[self.lexer.pos + 1].value == ')':
            self.lexer.consume()
            return []

        params = [self._parse_param()]
        while self._is_delim(','):
            self.lexer.consume()
            params.append(self._parse_param())
        return params

    def _parse_param(self) -> VarDecl:
        type_, type_tok = self._parse_type_spec(
            'E_PARSE_PARAM_TYPE', 'Ожидался тип параметра')
        name_tok = self._expect('IDENTIFIER')
        dims = self._parse_array_dims()
        return VarDecl(type_, name_tok.value,
                       line=type_tok.line, col=type_tok.col, dims=dims)

    def _parse_array_dims(self) -> List[Expr]:
        """Размерности массива: [2][3] -> [Num(2), Num(3)].

        Незаполненная размерность (``[]``) кодируется как ``Num(0)``
        и уточняется по инициализатору на этапе генерации кода.
        """
        dims: List[Expr] = []
        while self._is_delim('['):
            self.lexer.consume()
            if self._is_delim(']'):
                dims.append(Num(0))
            else:
                dims.append(self.parse_expr())
            self._expect('DELIMITER', ']')
        return dims

    def _parse_array_init(self) -> ArrayInit:
        """Рекурсивный инициализатор: {1, 2, {3, 4}}."""
        self._expect('DELIMITER', '{')
        values: List = []
        while not self._is_delim('}'):
            if self._is_delim('{'):
                values.append(self._parse_array_init())
            else:
                values.append(self.parse_expr())
            if self._is_delim(','):
                self.lexer.consume()
                continue
            break
        self._expect('DELIMITER', '}')
        return ArrayInit(values)

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

    def parse_stmt(self) -> Stmt:
        t = self._peek()

        if t.category == 'COMMENT':
            self.lexer.consume()
            return CommentStmt(t.value)

        if t.category == 'PREPROCESSOR':
            pp = _norm_pp(t.value)
            if pp in ('#ifdef', '#ifndef'):
                return self.parse_ifdef()
            self._skip_to_eol(t)
            return CommentStmt(f"// {pp} (пропущено транспилятором)")

        if t.category == 'KEYWORD':
            if t.value == 'return':
                return self.parse_return()
            if t.value == 'break':
                tok = self.lexer.consume()
                self._expect('DELIMITER', ';')
                return BreakStmt(line=tok.line, col=tok.col)
            if t.value == 'continue':
                tok = self.lexer.consume()
                self._expect('DELIMITER', ';')
                return ContinueStmt(line=tok.line, col=tok.col)
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
            if (t.value in ('int', 'char', 'float', 'double')
                    or t.value in TYPE_QUALIFIERS or t.value == 'const'):
                return self.parse_declaration()

        expr = self.parse_expr()
        self._expect('DELIMITER', ';')
        return ExprStmt(expr)

    def _at_type_decl(self) -> bool:
        t = self._peek()
        if t.category != 'KEYWORD':
            return False
        if (t.value in ('int', 'char', 'float', 'double')
                or t.value in TYPE_QUALIFIERS):
            return True
        if t.value == 'const':
            toks = self.lexer.tokens
            i = self.lexer.pos + 1
            if i < len(toks) and toks[i].category == 'KEYWORD':
                return (toks[i].value in ('int', 'char', 'float', 'double')
                        or toks[i].value in TYPE_QUALIFIERS)
        return False

    def parse_declaration(self) -> Stmt:
        is_const = False
        while self._is_kw('const'):
            self.lexer.consume()
            is_const = True
        type_, type_tok = self._parse_type_spec(
            'E_PARSE_DECL_TYPE', 'Ожидался тип переменной')
        decls: List[VarDecl] = []
        while True:
            name_tok = self._expect('IDENTIFIER')
            dims = self._parse_array_dims()
            init: Optional[Expr] = None
            array_init: Optional[ArrayInit] = None
            if self._is_op('='):
                self.lexer.consume()
                if self._is_delim('{'):
                    array_init = self._parse_array_init()
                else:
                    init = self.parse_expr()
            decls.append(VarDecl(type_, name_tok.value, init,
                                 is_const=is_const,
                                 line=type_tok.line, col=type_tok.col,
                                 dims=dims, array_init=array_init))
            if self._is_delim(','):
                self.lexer.consume()
                continue
            break
        self._expect('DELIMITER', ';')
        return decls[0] if len(decls) == 1 else MultiVarDecl(decls)

    def parse_ifdef(self) -> IfdefStmt:
        d = self.lexer.consume()
        negated = _norm_pp(d.value) == '#ifndef'
        name_tok = self._peek()
        if name_tok.category not in ('IDENTIFIER', 'MACRO') \
                or name_tok.line != d.line:
            raise TranslationException(TranslationError(
                stage='parser', code='E_PARSE_IFDEF',
                message=f"Ожидалось имя макроса после {d.value!r}, "
                        f"получено {name_tok.value!r}",
                line=name_tok.line, col=name_tok.col,
            ))
        self.lexer.consume()

        body: List[Stmt] = []
        else_body: List[Stmt] = []
        cur = body
        while True:
            t = self._peek()
            if t.code == 'EOF':
                raise TranslationException(TranslationError(
                    stage='parser', code='E_PARSE_IFDEF',
                    message=f"Для {d.value!r} не найдено #endif",
                    line=d.line, col=d.col,
                ))
            if t.category == 'PREPROCESSOR':
                pp = _norm_pp(t.value)
                if pp == '#endif':
                    self.lexer.consume()
                    break
                if pp == '#else':
                    self.lexer.consume()
                    cur = else_body
                    continue
                if pp in ('#ifdef', '#ifndef'):
                    cur.append(self.parse_ifdef())
                    continue
            cur.append(self.parse_stmt())
        return IfdefStmt(name_tok.value, body, else_body,
                         negated=negated, line=d.line, col=d.col)

    def parse_return(self) -> ReturnStmt:
        tok = self.lexer.consume()
        val: Optional[Expr] = None
        if not self._is_delim(';'):
            val = self.parse_expr()
        self._expect('DELIMITER', ';')
        return ReturnStmt(val, line=tok.line, col=tok.col)

    def parse_if(self) -> IfStmt:
        self.lexer.consume() 
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
        self.lexer.consume()
        self._expect('DELIMITER', '(')
        cond = self.parse_expr()
        self._expect('DELIMITER', ')')
        body = self._parse_statement_or_block()
        return WhileStmt(cond, body)

    def parse_do_while(self) -> DoWhileStmt:
        self.lexer.consume()
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
        self.lexer.consume()
        self._expect('DELIMITER', '(')
        init: Optional[Stmt] = None
        if self._at_type_decl():
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
        self.lexer.consume()
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

        expr = self.parse_primary()

        while self._peek().category == 'OPERATOR' and self._peek().value in ('++', '--'):
            op = self.lexer.consume().value
            expr = UnaryOp(op, expr)
        return expr

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

        if t.category == 'KEYWORD' and t.value in ('true', 'false'):
            self.lexer.consume()
            return Bool(t.value == 'true', line=t.line, col=t.col)

        if t.category in ('IDENTIFIER', 'MACRO'):
            self.lexer.consume()
            if self._is_delim('('):
                return self.parse_call(t)
            indices: List[Expr] = []
            while self._is_delim('['):
                self.lexer.consume()
                indices.append(self.parse_expr())
                self._expect('DELIMITER', ']')
            if indices:
                return ArrayAccess(t.value, indices,
                                   line=t.line, col=t.col)
            return Ident(t.value, line=t.line, col=t.col)

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

    def parse_call(self, name_tok: Token) -> CallExpr:
        self._expect('DELIMITER', '(')
        args: List[Expr] = []
        if not self._is_delim(')'):
            args.append(self.parse_expr())
            while self._is_delim(','):
                self.lexer.consume()
                args.append(self.parse_expr())
        self._expect('DELIMITER', ')')
        return CallExpr(name_tok.value, args,
                        line=name_tok.line, col=name_tok.col)


def parse(source: str) -> Program:
    return Parser(Lexer(source)).parse_program()