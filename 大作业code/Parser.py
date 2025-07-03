from Lexical_analyzer import Lexer, Token, TokenType
from semantic_analyzer import SemanticAnalyzer
from typing import List, Optional, Dict, Any

def lex(code: str) -> List[Token]:
    lexer = Lexer(code)
    tokens: List[Token] = []
    while True:
        tok = lexer.get_next_token()
        if tok.type == TokenType.EOF:
            break
        if tok.type == TokenType.COMMENT:
            continue
        tokens.append(tok)
    return tokens

class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def peek(self, offset: int = 0) -> Optional[Token]:
        idx = self.pos + offset
        return self.tokens[idx] if idx < len(self.tokens) else None

    def advance(self) -> Token:
        tok = self.peek()
        if not tok:
            raise SyntaxError("Unexpected EOF")
        self.pos += 1
        return tok

    def match(self, type_: TokenType, value: Optional[str] = None) -> bool:
        tok = self.peek()
        if tok and tok.type == type_ and (value is None or tok.value == value):
            self.pos += 1
            return True
        return False

    def consume(self, type_: TokenType, value: Optional[str] = None) -> Token:
        tok = self.peek()
        if tok and tok.type == type_ and (value is None or tok.value == value):
            self.pos += 1
            return tok
        expected = f"{type_.name}{':' + value if value else ''}"
        got = f"{tok.type.name}:{tok.value}" if tok else "EOF"
        raise SyntaxError(f"Expected {expected}, got {got}")

    def parse(self) -> Dict[str, Any]:
        return self.parse_program()

    def is_at_end(self) -> bool:
        return self.peek() is None

    def parse_program(self) -> Dict[str, Any]:
        decls = []
        while not self.is_at_end():
            decls.append(self.parse_declaration())
        return {'type': 'Program', 'declarations': decls}

    def parse_declaration(self) -> Dict[str, Any]:
        self.consume(TokenType.KEYWORD, 'fn')
        name = self.consume(TokenType.IDENTIFIER).value
        self.consume(TokenType.DELIMITER, '(')
        params = self.parse_parameter_list()
        self.consume(TokenType.DELIMITER, ')')
        return_type = None
        if self.match(TokenType.ARROW, '->'):
            return_type = self.parse_type()
        body = self.parse_function_expression_block()
        return {'type': 'FunctionDecl', 'name': name, 'params': params, 'return_type': return_type, 'body': body}

    def parse_parameter_list(self) -> List[Dict[str, Any]]:
        params = []
        if self.peek() and self.peek().value != ')':
            params.append(self.parse_parameter())
            while self.match(TokenType.SEPARATOR, ','):
                params.append(self.parse_parameter())
        return params

    def parse_parameter(self) -> Dict[str, Any]:
        is_mut = self.match(TokenType.KEYWORD, 'mut')
        name = self.consume(TokenType.IDENTIFIER).value
        self.consume(TokenType.SEPARATOR, ':')
        ptype = self.parse_type()
        return {'mut': is_mut, 'name': name, 'type': ptype}

    def parse_type(self) -> Any:
        # Reference type
        if self.match(TokenType.OPERATOR, '&'):
            is_mut = self.match(TokenType.KEYWORD, 'mut')
            inner = self.parse_type()
            return {'type': 'ReferenceType', 'mut': is_mut, 'inner': inner}
        # Array type
        if self.match(TokenType.DELIMITER, '['):
            inner = self.parse_type()
            self.consume(TokenType.SEPARATOR, ';')
            size = self.consume(TokenType.LITERAL).value
            self.consume(TokenType.DELIMITER, ']')
            return {'type': 'ArrayType', 'inner': inner, 'size': size}
        # Tuple type
        if self.match(TokenType.DELIMITER, '('):
            # empty tuple (unit)
            if self.match(TokenType.DELIMITER, ')'):
                return {'type': 'TupleType', 'elements': []}
            # first type
            first = self.parse_type()
            # require comma for tuple
            self.consume(TokenType.SEPARATOR, ',')
            elements = [first]
            # parse remaining types
            while True:
                elements.append(self.parse_type())
                if not self.match(TokenType.SEPARATOR, ','):
                    break
            self.consume(TokenType.DELIMITER, ')')
            return {'type': 'TupleType', 'elements': elements}
        # Primitive type
        if self.match(TokenType.KEYWORD, 'i32'):
            return 'i32'
        raise SyntaxError(f"Unsupported type: {self.peek().value if self.peek() else 'EOF'}")

    def parse_statement(self) -> Dict[str, Any]:
        # --- 元组访问赋值：a.0 = expr; ---
        def is_dot(tok):
            return tok.type == TokenType.DOT or (tok.type == TokenType.DELIMITER and tok.value == '.')

        if (self.peek() and self.peek().type == TokenType.IDENTIFIER
                and self.peek(1) and is_dot(self.peek(1))
                and self.peek(2) and self.peek(2).type == TokenType.LITERAL
                and self.peek(3) and self.peek(3).type == TokenType.ASSIGN):
            tgt = self.parse_expression()
            self.consume(TokenType.ASSIGN, '=')
            val = self.parse_expression()
            self.consume(TokenType.SEPARATOR, ';')
            return {'type': 'Assignment', 'target': tgt, 'value': val}

        # break
        if self.match(TokenType.KEYWORD, 'break'):
            expr = None
            if not self.match(TokenType.SEPARATOR, ';'):
                expr = self.parse_expression()
                self.consume(TokenType.SEPARATOR, ';')
            return {'type': 'BreakStmt', 'expression': expr}

        # continue
        if self.match(TokenType.KEYWORD, 'continue'):
            self.consume(TokenType.SEPARATOR, ';')
            return {'type': 'ContinueStmt'}

        # return
        if self.match(TokenType.KEYWORD, 'return'):
            expr = None
            if not self.match(TokenType.SEPARATOR, ';'):
                expr = self.parse_expression()
                self.consume(TokenType.SEPARATOR, ';')
            return {'type': 'ReturnStmt', 'expression': expr}

        # let
        if self.match(TokenType.KEYWORD, 'let'):
            return self.parse_variable_decl()

        # if
        if self.match(TokenType.KEYWORD, 'if'):
            return self.parse_if()

        # while
        if self.match(TokenType.KEYWORD, 'while'):
            return self.parse_while()

        # for
        if self.match(TokenType.KEYWORD, 'for'):
            return self.parse_for()

        # loop
        if self.match(TokenType.KEYWORD, 'loop'):
            return self.parse_loop_stmt()

        # 数组/元组索引赋值: x[0] = expr; or a.0 = expr already handled above
        if self.peek() and self.peek().type == TokenType.IDENTIFIER and self.peek(1) and self.peek(
                1).type == TokenType.DELIMITER and self.peek(1).value == '[':
            tgt = self.parse_expression()
            self.consume(TokenType.ASSIGN, '=')
            val = self.parse_expression()
            self.consume(TokenType.SEPARATOR, ';')
            return {'type': 'Assignment', 'target': tgt, 'value': val}

        # 标识符直接赋值: x = expr;
        if self.peek() and self.peek().type == TokenType.IDENTIFIER and self.peek(1) and self.peek(
                1).type == TokenType.ASSIGN:
            tgt = {'type': 'Identifier', 'name': self.advance().value}
            self.consume(TokenType.ASSIGN, '=')
            val = self.parse_expression()
            self.consume(TokenType.SEPARATOR, ';')
            return {'type': 'Assignment', 'target': tgt, 'value': val}

        # 解引用赋值: *x = expr;
        if self.peek() and self.peek().type == TokenType.OPERATOR and self.peek().value == '*' and self.peek(
                2) and self.peek(2).type == TokenType.ASSIGN:
            self.advance()
            name = self.consume(TokenType.IDENTIFIER).value
            tgt = {'type': 'DerefExpr', 'operand': {'type': 'Identifier', 'name': name}}
            self.consume(TokenType.ASSIGN, '=')
            val = self.parse_expression()
            self.consume(TokenType.SEPARATOR, ';')
            return {'type': 'Assignment', 'target': tgt, 'value': val}

        # 空语句
        if self.match(TokenType.SEPARATOR, ';'):
            return {'type': 'EmptyStmt'}

        # 其他表达式语句
        expr = self.parse_expression()
        self.consume(TokenType.SEPARATOR, ';')
        return {'type': 'ExprStmt', 'expr': expr}

    def parse_expression(self) -> Dict[str, Any]:
        if self.match(TokenType.KEYWORD, 'if'):
            return self.parse_if_expression()
        if self.match(TokenType.KEYWORD, 'loop'):
            block = self.parse_function_expression_block()
            return {'type': 'LoopExpr', 'body': block}
        return self.parse_comparison()

    def parse_if_expression(self) -> Dict[str, Any]:
        cond = self.parse_expression()
        then_block = self.parse_function_expression_block()
        self.consume(TokenType.KEYWORD, 'else')
        else_block = self.parse_function_expression_block()
        return {'type': 'IfExpr', 'condition': cond, 'then': then_block, 'else': else_block}

    def parse_comparison(self) -> Dict[str, Any]:
        node = self.parse_additive()
        while self.peek() and self.peek().type == TokenType.OPERATOR and self.peek().value in ('<','<=','>','>=','==','!='):
            op = self.advance().value
            rhs = self.parse_additive()
            node = {'type': 'BinaryExpression', 'operator': op, 'left': node, 'right': rhs}
        return node

    def parse_additive(self) -> Dict[str, Any]:
        node = self.parse_term()
        while self.peek() and self.peek().type == TokenType.OPERATOR and self.peek().value in ('+','-'):
            op = self.advance().value
            rhs = self.parse_term()
            node = {'type': 'BinaryExpression', 'operator': op, 'left': node, 'right': rhs}
        return node

    def parse_term(self) -> Dict[str, Any]:
        node = self.parse_factor()
        while self.peek() and self.peek().type == TokenType.OPERATOR and self.peek().value in ('*','/'):
            op = self.advance().value
            rhs = self.parse_factor()
            node = {'type': 'BinaryExpression', 'operator': op, 'left': node, 'right': rhs}
        return node

    def parse_factor(self) -> Dict[str, Any]:
        tok = self.peek()
        if not tok:
            raise SyntaxError("Unexpected EOF in factor")

        # Block expression
        if tok.type == TokenType.DELIMITER and tok.value == '{':
            return self.parse_function_expression_block()

        # Array literal
        if tok.type == TokenType.DELIMITER and tok.value == '[':
            return self.parse_array_literal()

        # Tuple literal or grouping
        if tok.type == TokenType.DELIMITER and tok.value == '(':  # '('
            self.advance()
            # empty tuple
            if self.match(TokenType.DELIMITER, ')'):
                node = {'type': 'TupleLiteral', 'elements': []}
            else:
                first = self.parse_expression()
                if self.match(TokenType.SEPARATOR, ','):
                    elems = [first]
                    while True:
                        elems.append(self.parse_expression())
                        if not self.match(TokenType.SEPARATOR, ','):
                            break
                    self.consume(TokenType.DELIMITER, ')')
                    node = {'type': 'TupleLiteral', 'elements': elems}
                else:
                    self.consume(TokenType.DELIMITER, ')')
                    node = first
        # Deref
        elif tok.type == TokenType.OPERATOR and tok.value == '*':
            self.advance()
            node = {'type': 'DerefExpr', 'operand': self.parse_factor()}
        # Ref
        elif tok.type == TokenType.OPERATOR and tok.value == '&':
            self.advance()
            is_mut = self.match(TokenType.KEYWORD, 'mut')
            node = {'type': 'RefExpr', 'mut': is_mut, 'operand': self.parse_factor()}
        # Literal
        elif tok.type == TokenType.LITERAL:
            self.advance()
            node = {'type': 'Literal', 'value': tok.value}

        # ❗️防止将类型关键字误当作表达式
        elif tok.type == TokenType.KEYWORD:
            raise SyntaxError(f"Unexpected type keyword '{tok.value}' in expression")

        # Identifier or call
        elif tok.type == TokenType.IDENTIFIER:
            name = self.advance().value
            if self.peek() and self.peek().type == TokenType.DELIMITER and self.peek().value == '(':  # function call
                self.advance()
                args = self.parse_arg_list()
                self.consume(TokenType.DELIMITER, ')')
                node = {'type': 'CallExpression', 'callee': name, 'arguments': args}
            else:
                node = {'type': 'Identifier', 'name': name}

        else:
            raise SyntaxError(f"Unexpected token in parse_factor: {tok}")

        # Postfix: array indexing and tuple access
        while True:
            # Array indexing: node[expr]
            if self.peek() and self.peek().type == TokenType.DELIMITER and self.peek().value == '[':
                self.advance()
                idx = self.parse_expression()
                self.consume(TokenType.DELIMITER, ']')
                node = {'type': 'IndexExpr', 'target': node, 'index': idx}
                continue

            # Tuple access: a.0
            if self.peek() and (self.peek().type == TokenType.DOT or
                                (self.peek().type == TokenType.DELIMITER and self.peek().value == '.')):
                # consume dot
                self.advance()
                # expect a numeric literal
                index_tok = self.peek()
                if index_tok:
                    if index_tok.type == TokenType.LITERAL:
                        num = int(self.advance().value)
                        node = {'type': 'TupleAccess', 'target': node, 'index': num}
                    elif index_tok.type == TokenType.IDENTIFIER:
                        # 允许 identifier 作为字段，交给语义分析判断
                        ident = self.advance().value
                        node = {'type': 'TupleAccess', 'target': node, 'index': ident}
                    else:
                        raise SyntaxError(f"Expected tuple index after '.', got {index_tok}")
                else:
                    raise SyntaxError("Unexpected EOF after '.'")

            break

        return node

    def parse_array_literal(self) -> Dict[str, Any]:
        self.consume(TokenType.DELIMITER, '[')
        elements: List[Any] = []

        if self.peek() and self.peek().type == TokenType.DELIMITER and self.peek().value == ']':
            self.advance()
            return {'type': 'ArrayLiteral', 'elements': elements}

        # 🔍 提前检查是否误用了类型关键字（如 [i32; 3]）
        first = self.peek()
        if first and first.type == TokenType.KEYWORD:
            raise SyntaxError(f"Cannot use type keyword '{first.value}' as array element")

        elements.append(self.parse_expression())
        while self.match(TokenType.SEPARATOR, ','):
            elements.append(self.parse_expression())

        self.consume(TokenType.DELIMITER, ']')
        return {'type': 'ArrayLiteral', 'elements': elements}

    def parse_arg_list(self) -> List[Dict[str, Any]]:
        args: List[Dict[str, Any]] = []
        if self.peek() and self.peek().value != ')':
            args.append(self.parse_expression())
            while self.match(TokenType.SEPARATOR, ','):
                args.append(self.parse_expression())
        return args

    def parse_variable_decl(self) -> Dict[str, Any]:
        is_mut = self.match(TokenType.KEYWORD, 'mut')
        name = self.consume(TokenType.IDENTIFIER).value
        var_type = None
        init = None
        if self.match(TokenType.SEPARATOR, ':'):
            var_type = self.parse_type()
        if self.match(TokenType.ASSIGN, '='):
            init = self.parse_expression()
        self.consume(TokenType.SEPARATOR, ';')
        return {'type': 'VarDecl', 'mut': is_mut, 'name': name, 'var_type': var_type, 'init': init}

    def parse_if(self) -> Dict[str, Any]:
        cond = self.parse_expression()
        self.consume(TokenType.DELIMITER, '{')
        then = self.parse_block()
        else_part = None
        if self.match(TokenType.KEYWORD, 'else'):
            if self.match(TokenType.KEYWORD, 'if'):
                else_part = self.parse_if()
            else:
                self.consume(TokenType.DELIMITER, '{')
                else_part = self.parse_block()
        return {'type': 'IfStmt', 'condition': cond, 'then': then, 'else': else_part}

    def parse_while(self) -> Dict[str, Any]:
        cond = self.parse_expression()
        self.consume(TokenType.DELIMITER, '{')
        body = self.parse_block()
        return {'type': 'WhileStmt', 'condition': cond, 'body': body}

    def parse_for(self) -> Dict[str, Any]:
        is_mut = self.match(TokenType.KEYWORD, 'mut')
        var = self.consume(TokenType.IDENTIFIER).value
        var_type = None
        if self.match(TokenType.SEPARATOR, ':'):
            var_type = self.parse_type()
        self.consume(TokenType.KEYWORD, 'in')
        start = self.parse_expression()
        self.consume(TokenType.DOUBLE_DOT, '..')
        end = self.parse_expression()
        self.consume(TokenType.DELIMITER, '{')
        body = self.parse_block()
        return {'type': 'ForStmt', 'mut': is_mut, 'var': var, 'var_type': var_type, 'start': start, 'end': end, 'body': body}

    def parse_loop_stmt(self) -> Dict[str, Any]:
        self.consume(TokenType.DELIMITER, '{')
        body = self.parse_block()
        return {'type': 'LoopStmt', 'body': body}

    def parse_block(self) -> Dict[str, Any]:
        stmts = []
        while not self.match(TokenType.DELIMITER, '}'):
            stmts.append(self.parse_statement())
        return {'type': 'Block', 'statements': stmts}

    def parse_function_expression_block(self) -> Dict[str, Any]:
        self.consume(TokenType.DELIMITER, '{')
        elements = []
        while not self.match(TokenType.DELIMITER, '}'):
            # empty statement
            if self.match(TokenType.SEPARATOR, ';'):
                elements.append({'type': 'EmptyStmt'})
                continue

            tok = self.peek()
            # keyword-led statements
            if tok and tok.type == TokenType.KEYWORD and tok.value in (
                'let','if','while','for','loop','return','break','continue'
            ):
                elements.append(self.parse_statement())
                continue

            # assignment statements: array/tuple/index/deref
            # array index: x[...]=...;
            if tok and tok.type == TokenType.IDENTIFIER and self.peek(1) and self.peek(1).type == TokenType.DELIMITER and self.peek(1).value == '[':
                elements.append(self.parse_statement())
                continue
            # tuple access: a.0 = expr;
            if tok and tok.type == TokenType.IDENTIFIER and \
               (self.peek(1).type == TokenType.DOT or (self.peek(1).type == TokenType.DELIMITER and self.peek(1).value == '.')) and \
               self.peek(2) and self.peek(2).type == TokenType.LITERAL and \
               self.peek(3) and self.peek(3).type == TokenType.ASSIGN:
                elements.append(self.parse_statement())
                continue
            # identifier assignment: x = expr;
            if tok and tok.type == TokenType.IDENTIFIER and self.peek(1) and self.peek(1).type == TokenType.ASSIGN:
                elements.append(self.parse_statement())
                continue
            # deref assignment: *x = expr;
            if tok and tok.type == TokenType.OPERATOR and tok.value == '*' and self.peek(2) and self.peek(2).type == TokenType.ASSIGN:
                elements.append(self.parse_statement())
                continue

            # block expression
            if tok and tok.type == TokenType.DELIMITER and tok.value == '{':
                elements.append(self.parse_function_expression_block())
                continue

            # fallback to expression or expression statement
            expr = self.parse_expression()
            if self.match(TokenType.SEPARATOR, ';'):
                elements.append({'type': 'ExprStmt', 'expr': expr})
            else:
                elements.append(expr)
        return {'type': 'FunctionExprBlock', 'elements': elements}


# --- 测试 --- #
if __name__ == '__main__':
    code = []
    code.append('''
    fn program_1_1() {
    }
    ''')
    code.append('''
        fn program_1_2() {
;;;;;;
}
        ''')
    code.append('''
fn program_1_3() {
return ;
}
            ''')
    code.append('''
fn program_1_4(mut a:i32) {
}
            ''')
    code.append('''
        fn program_1_5() -> i32 {
     return 1;
     }
                                ''')
    code.append('''
fn program_2_1() {
let mut a:i32;
let mut b;
}
                ''')
    code.append('''
fn program_3_1__1() {
0;
(1);
((2));
(((3)));
}
                    ''')
    code.append('''
fn program_3_1__2(mut a:i32) {
a;
(a);
((a));
(((a)));
}
                    ''')
    code.append('''
fn program_3_2() {
1*2/3;
4+5/6;
7<8;
1*2+3*4<4/2-3/1;
}
                        ''')
    code.append('''
fn program_3_3__1() {
}
                        ''')
    code.append('''
fn program_3_3__2() {
program_3_3__1();
}
                        ''')
    code.append('''
    fn program_2_2(mut a:i32) {
 a=32;
 }
                                ''')
    code.append('''
    fn program_2_3() {
 let mut a:i32=1;
 let mut b=1;
 }
                                    ''')
    code.append('''
        fn program_4_1(a:i32) -> i32 {
 if a>0 {
 return 1;
 } else {
 return 0;
 }
 }
                        ''')
    code.append('''
fn program_4_2(a:i32) -> i32 {
 if a>0 {
 return a+1;
 } else if a<0 {
 return a-1;
 } else {
 return 0;
 }
 }
                            ''')
    code.append('''
fn program_5_1(mut n:i32) {
 while n>0 {
 n=n-1;
 }
 }
                            ''')
    code.append('''
 fn program_5_2(mut n:i32) {
 for mut i in 1..n+1 {
 n=n-1;
 }
 }
                            ''')
    code.append('''
 fn program_5_3() {
 loop {
 }
 }
                            ''')
    code.append('''
    fn program_5_4__1() {
 while 1==0 {
 continue;
 }
 }
                            ''')
    code.append('''
fn program_5_4__2() {
 while 1==1 {
 break;
 }
 }
                                ''')
    code.append('''
fn program_6_1() {
 let a:i32;
 let b;
 let c:i32=1;
 let d=2;
 }
                                ''')
    code.append('''
fn program_6_2__1() {
 let mut a:i32=1;
 let mut b:&mut i32=&mut a;
 let mut c:i32=*b;
 *b=2;
 }
                                ''')
    code.append('''
fn program_6_2__2() {
 let a:i32=1;
 let b:& i32=&a;
 let c:i32=*b;
 }
                                ''')
    code.append('''
 fn program_7_1(mut x:i32,mut y:i32) {
 let mut z={
 let mut t=x*x+x;
 t=t+x*y;
 t
 };
 }
                                ''')
    code.append('''
 fn program_7_2(mut x:i32,mut y:i32) -> i32 {
 let mut t=x*x+x;
 t=t+x*y;
 t
 }
                                ''')
    code.append('''
    fn program_7_3(mut a:i32) {
let mut b=if a>0 {
1
} else {
0
};
}
                        ''')
    code.append('''
    fn program_7_4() {
let mut a=loop {
break 2;
};
}
                            ''')
    code.append('''
fn program_8_1() {
let mut a:[i32;3];
a=[1,2,3];
}
                            ''')
    code.append('''
    fn program_8_2(mut a:[i32;3]) {
let mut b:i32=a[0];
a[0]=1;
}
                            ''')
    code.append('''
fn program_9_1() {
let a:(i32,i32,i32);
a=(1,2,3);
}
                                ''')
    code.append('''
fn program_9_2(mut a:(i32,i32)) {
let mut b:i32=a.0;
a.0=1;
}
                                ''')



    for cod in code:
        tokens = lex(cod)
        # for tok in tokens:
        #     print(tok)
        parser = Parser(tokens)
        import pprint
        pprint.pprint(parser.parse())

