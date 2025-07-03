from enum import Enum


class TokenType(Enum):
    # 基础类型
    KEYWORD = "KEYWORD"            #关键字
    IDENTIFIER = "IDENTIFIER"      #标识符
    LITERAL = "LITERAL"            #数值
    OPERATOR = "OPERATOR"          #算符
    DELIMITER = "DELIMITER"        #界符
    SEPARATOR = "SEPARATOR"        #分隔符
    ASSIGN = "ASSIGN"              #赋值号
    ARROW = "ARROW"                #右键头
    DOT = "DOT"                    #.
    DOUBLE_DOT = "DOUBLE_DOT"      #..
    COMMENT = "COMMENT"            #注释
    EOF = "EOF"                    #结束符


class Token:
    def __init__(self, type, value=None):
        self.type = type
        self.value = value

    def __repr__(self):
        return f"<{self.type.name}: {self.value}>"


class Lexer:
    KEYWORDS = {
        'i32', 'let', 'if', 'else', 'while', 'return', 'mut', 'fn',
        'for', 'in', 'loop', 'break', 'continue'
    }
    OPERATORS = {'+', '-', '*', '/', '==', '>', '>=', '<', '<=', '!=', '&'}
    DELIMITERS = {'(', ')', '{', '}', '[', ']'}
    SEPARATORS = {';', ':', ','}
    SINGLE_CHAR_OPS = {'+', '-', '*', '/', '>', '<', '!', '&'}

    def __init__(self, text):
        self.text = text + '#'  # 添加结束符
        self.pos = 0
        self.current_char = self.text[self.pos] if self.text else None

    def advance(self):
        self.pos += 1
        if self.pos < len(self.text):
            self.current_char = self.text[self.pos]
        else:
            self.current_char = None

    def skip_whitespace(self):
        while self.current_char and self.current_char.isspace():
            self.advance()

    def peek(self, n=1):
        peek_pos = self.pos + n
        return self.text[peek_pos] if peek_pos < len(self.text) else None

    def get_next_token(self):
        while self.current_char:
            # 处理结束符
            if self.current_char == '#':
                self.advance()
                return Token(TokenType.EOF)

            # 跳过空白
            if self.current_char.isspace():
                self.skip_whitespace()
                continue

            # 处理标识符和关键字
            if self.current_char.isalpha() or self.current_char == '_':
                return self.read_identifier()

            # 处理数字字面量
            if self.current_char.isdigit():
                return self.read_number()

            # 处理字符串字面量（根据需求添加）

            # 处理注释
            if self.current_char == '/':
                if self.peek() == '/':
                    return self.read_line_comment()
                elif self.peek() == '*':
                    return self.read_block_comment()

            # 处理特殊符号
            if self.current_char == '-':
                if self.peek() == '>':
                    return self.read_arrow()

            if self.current_char == '.':
                if self.peek() == '.':
                    return self.read_double_dot()
                return self.read_dot()

            # 处理运算符
            if op_token := self.read_operator():
                return op_token

            # 处理分隔符
            if self.current_char in self.SEPARATORS:
                return self.read_separator()

            # 处理界定符
            if self.current_char in self.DELIMITERS:
                return self.read_delimiter()

            # 处理赋值符
            if self.current_char == '=':
                # 检查是否可能是==
                if self.peek() == '=':
                    self.advance()
                    self.advance()
                    return Token(TokenType.OPERATOR, '==')
                self.advance()
                return Token(TokenType.ASSIGN, '=')

            # 错误字符处理
            raise ValueError(f"Invalid character '{self.current_char}' ")

        return Token(TokenType.EOF)

    def read_identifier(self):
        buffer = []
        while self.current_char and (self.current_char.isalnum() or self.current_char == '_'):
            buffer.append(self.current_char)
            self.advance()

        identifier = ''.join(buffer)
        if identifier in self.KEYWORDS:
            return Token(TokenType.KEYWORD, identifier)
        return Token(TokenType.IDENTIFIER, identifier)

    def read_number(self):
        buffer = []
        while self.current_char and self.current_char.isdigit():
            buffer.append(self.current_char)
            self.advance()
        return Token(TokenType.LITERAL, int(''.join(buffer)))

    def read_operator(self):
        # 处理双字符运算符
        two_char = self.current_char + self.peek()
        if two_char in self.OPERATORS:
            token = Token(TokenType.OPERATOR, two_char)
            self.advance()
            self.advance()
            return token

        # 处理单字符运算符
        if self.current_char in self.SINGLE_CHAR_OPS:
            char = self.current_char
            self.advance()
            return Token(TokenType.OPERATOR, char)

        return None

    def read_separator(self):
        char = self.current_char
        self.advance()
        return Token(TokenType.SEPARATOR, char)

    def read_delimiter(self):
        char = self.current_char
        self.advance()
        return Token(TokenType.DELIMITER, char)

    def read_arrow(self):
        self.advance()  # 跳过-
        self.advance()  # 跳过>
        return Token(TokenType.ARROW, '->')

    def read_dot(self):
        self.advance()
        return Token(TokenType.DOT, '.')

    def read_double_dot(self):
        self.advance()  # 跳过第一个.
        self.advance()  # 跳过第二个.
        return Token(TokenType.DOUBLE_DOT, '..')

    def read_line_comment(self):
        self.advance()  # 跳过第一个/
        self.advance()  # 跳过第二个/
        buffer = []
        while self.current_char and self.current_char != '\n':
            buffer.append(self.current_char)
            self.advance()
        return Token(TokenType.COMMENT, ''.join(buffer))

    def read_block_comment(self):
        self.advance()  # 跳过/
        self.advance()  # 跳过*
        buffer = []
        while True:
            if self.current_char == '*' and self.peek() == '/':
                self.advance()
                self.advance()
                break
            if self.current_char is None:
                raise ValueError("Unclosed block comment")
            buffer.append(self.current_char)
            self.advance()
        return Token(TokenType.COMMENT, ''.join(buffer))