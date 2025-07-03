from typing import Dict, Any, List, Tuple


class QuadrupleGenerator:
    def __init__(self, ast: Dict[str, Any]):
        self.ast = ast
        self.quadruples: List[Tuple] = []
        self.temp_counter = 0
        self.label_counter = 0
        self.loop_stack = []  # 用于跟踪循环上下文，处理break/continue语句
        self.current_function = None  # 当前处理的函数名称

    def generate(self) -> List[Tuple]:
        """生成四元式中间代码"""
        self._reset()
        self._process_program(self.ast)
        return self.quadruples

    def _reset(self):
        """重置生成器状态"""
        self.quadruples = []
        self.temp_counter = 0
        self.label_counter = 0
        self.loop_stack = []
        self.current_function = None

    def new_temp(self) -> str:
        """生成新的临时变量"""
        temp = f"t{self.temp_counter}"
        self.temp_counter += 1
        return temp

    def new_label(self) -> str:
        """生成新的标签"""
        label = f"L{self.label_counter}"
        self.label_counter += 1
        return label

    def _process_program(self, node: Dict[str, Any]):
        """处理程序节点"""
        if node.get('type') == 'Program':
            for decl in node.get('declarations', []):
                self._process_declaration(decl)

    def _process_declaration(self, decl: Dict[str, Any]):
        """处理声明"""
        decl_type = decl.get('type')
        if decl_type == 'FunctionDecl':
            self._process_function(decl)
        elif decl_type == 'VarDecl':
            self._process_variable_decl(decl)
        # 可以扩展其他声明类型

    def _process_function(self, func: Dict[str, Any]):
        """处理函数声明"""
        # 保存当前函数名称
        self.current_function = func.get('name', 'unknown_func')

        # 函数入口标签
        func_name = self.current_function
        self.quadruples.append((f"{func_name}:", None, None, None))

        # 处理参数
        for param in func.get('params', []):
            self._process_parameter(param)

        # 处理函数体
        if 'body' in func and func['body']:
            self._process_block(func['body'])
        # 如果函数体中没有显式的返回语句，添加一个默认返回
        if not any(quad[0] == 'return' for quad in self.quadruples):
            self.quadruples.append(('return', None, None, None))
        # 重置当前函数
        self.current_function = None

    def _process_parameter(self, param: Dict[str, Any]):
        """处理函数参数"""
        param_name = param.get('name', 'unknown_param')
        # 声明参数变量
        self.quadruples.append(('param', param_name, None, None))

    def _process_block(self, block: Dict[str, Any]):
        """处理代码块"""
        block_type = block.get('type')
        if block_type == 'FunctionExprBlock':
            for element in block.get('elements', []):
                self._process_elements(element)
        elif block_type == 'Block':
            for stmt in block.get('statements', []):
                self._process_statement(stmt)

    def _process_elements(self, element: Dict[str, Any]):
        """处理块中的元素"""
        element_type = element.get('type')
        if element_type == 'VariableDecl':
            self._process_variable_decl(element)
        elif element_type == 'ExprStmt':
            # 表达式语句只计算表达式，不保存结果
            self._process_expr(element.get('expr', {}))
        elif element_type == 'Assignment':
            self._process_assignment(element)
        elif element_type == 'IfStmt':
            self._process_if_stmt(element)
        elif element_type == 'WhileStmt':
            self._process_while_stmt(element)
        elif element_type == 'ForStmt':
            self._process_for_stmt(element)
        elif element_type == 'LoopStmt':
            self._process_loop_stmt(element)
        elif element_type == 'ReturnStmt':
            self._process_return_stmt(element)
        elif element_type == 'BreakStmt':
            self._process_break_stmt(element)
        elif element_type == 'ContinueStmt':
            self._process_continue_stmt(element)
        elif element_type == 'Block':
            # 修复：应该处理块中的每个语句，而不是递归调用自身
            for sub_element in element.get('statements', []):
                self._process_statement(sub_element)
        # 可以扩展其他元素类型

    def _process_statement(self, stmt: Dict[str, Any]):
        """处理语句"""
        stmt_type = stmt.get('type')
        if stmt_type == 'EmptyStmt':
            # 空语句不生成四元式
            pass
        elif stmt_type == 'ExprStmt':
            # 表达式语句只计算表达式，不保存结果
            self._process_expr(stmt.get('expr', {}))
        elif stmt_type == 'Assignment':
            self._process_assignment(stmt)
        elif stmt_type == 'IfStmt':
            self._process_if_stmt(stmt)
        elif stmt_type == 'WhileStmt':
            self._process_while_stmt(stmt)
        elif stmt_type == 'ForStmt':
            self._process_for_stmt(stmt)
        elif stmt_type == 'LoopStmt':
            self._process_loop_stmt(stmt)
        elif stmt_type == 'ReturnStmt':
            self._process_return_stmt(stmt)
        elif stmt_type == 'BreakStmt':
            self._process_break_stmt(stmt)
        elif stmt_type == 'ContinueStmt':
            self._process_continue_stmt(stmt)
        elif stmt_type == 'Block':
            self._process_block(stmt)

    def _process_variable_decl(self, decl: Dict[str, Any]):
        """处理变量声明"""
        var_name = decl.get('name', 'unknown_var')
        is_mut = decl.get('mut', False)

        # 声明变量
        self.quadruples.append(('declare', var_name, 'mut' if is_mut else 'const', None))

        if 'init' in decl and decl['init']:
            init_value = self._process_expr(decl['init'])
            self.quadruples.append(('=', init_value, None, var_name))

    def _process_assignment(self, stmt: Dict[str, Any]):
        """处理赋值语句"""
        target = stmt.get('target', {})
        value = self._process_expr(stmt.get('value', {}))

        if target.get('type') == 'Identifier':
            target_name = target.get('name', 'unknown_id')
            self.quadruples.append(('=', value, None, target_name))
        elif target.get('type') == 'IndexExpr':
            # 数组索引赋值
            array = self._process_expr(target.get('target', {}))
            index = self._process_expr(target.get('index', {}))
            self.quadruples.append(('[]=', array, index, value))
        elif target.get('type') == 'TupleAccess':
            # 元组访问赋值
            tuple_var = self._process_expr(target.get('target', {}))
            index = target.get('index', 0)
            self.quadruples.append(('tuple[]=', tuple_var, index, value))
        elif target.get('type') == 'DerefExpr':
            # 解引用赋值
            ptr = self._process_expr(target.get('operand', {}))
            self.quadruples.append(('*=', ptr, None, value))

    def _process_if_stmt(self, stmt: Dict[str, Any]):
        """处理if语句"""
        cond = self._process_expr(stmt.get('condition', {}))
        then_block = stmt.get('then', {})
        else_block = stmt.get('else', {})

        # 生成条件跳转
        else_label = self.new_label()
        end_label = self.new_label()

        self.quadruples.append(('ifz', cond, None, else_label))
        # 处理then分支
        self._process_block(then_block)
        # 无条件跳转到结束标签
        self.quadruples.append(('goto', None, None, end_label))
        # else标签
        self.quadruples.append((f"{else_label}:", None, None, None))
        # 处理else分支
        if else_block:
            self._process_block(else_block)
        # 结束标签
        self.quadruples.append((f"{end_label}:", None, None, None))

    def _process_while_stmt(self, stmt: Dict[str, Any]):
        """处理while循环"""
        start_label = self.new_label()
        end_label = self.new_label()

        # 记录循环上下文，用于break/continue语句
        self.loop_stack.append({
            'start_label': start_label,
            'end_label': end_label
        })

        # 循环开始标签
        self.quadruples.append((f"{start_label}:", None, None, None))
        # 处理循环条件
        cond = self._process_expr(stmt.get('condition', {}))
        # 条件不满足时跳转到循环结束
        self.quadruples.append(('ifz', cond, None, end_label))
        # 处理循环体
        self._process_block(stmt.get('body', {}))
        # 无条件跳转到循环开始
        self.quadruples.append(('goto', None, None, start_label))
        # 循环结束标签
        self.quadruples.append((f"{end_label}:", None, None, None))
        self.loop_stack.pop()

    def _process_for_stmt(self, stmt: Dict[str, Any]):
        """处理for循环"""
        is_mut = stmt.get('mut', False)
        var_name = stmt.get('var', 'unknown_var')
        var_type = stmt.get('var_type', 'unknown_type')
        start = self._process_expr(stmt.get('start', {}))
        end = self._process_expr(stmt.get('end', {}))
        body = stmt.get('body', {})

        start_label = self.new_label()
        end_label = self.new_label()

        # 记录循环上下文，用于break/continue语句
        self.loop_stack.append({
            'start_label': start_label,
            'end_label': end_label
        })

        # 声明循环变量
        self.quadruples.append(('declare', var_name, 'mut' if is_mut else 'const', var_type))
        # 初始化循环变量
        self.quadruples.append(('=', start, None, var_name))
        # 循环开始标签
        self.quadruples.append((f"{start_label}:", None, None, None))
        # 循环条件: var < end
        temp = self.new_temp()
        self.quadruples.append(('<', var_name, end, temp))
        # 条件不满足时跳转到循环结束
        self.quadruples.append(('ifz', temp, None, end_label))
        # 处理循环体
        self._process_block(body)
        # 递增循环变量
        inc_temp = self.new_temp()
        self.quadruples.append(('+', var_name, '1', inc_temp))
        self.quadruples.append(('=', inc_temp, None, var_name))
        # 无条件跳转到循环开始
        self.quadruples.append(('goto', None, None, start_label))
        # 循环结束标签
        self.quadruples.append((f"{end_label}:", None, None, None))
        self.loop_stack.pop()

    def _process_loop_stmt(self, stmt: Dict[str, Any]):
        """处理无限循环"""
        start_label = self.new_label()
        end_label = self.new_label()

        # 记录循环上下文，用于break/continue语句
        self.loop_stack.append({
            'start_label': start_label,
            'end_label': end_label
        })

        # 循环开始标签
        self.quadruples.append((f"{start_label}:", None, None, None))
        # 处理循环体
        self._process_block(stmt.get('body', {}))
        # 无条件跳转到循环开始
        self.quadruples.append(('goto', None, None, start_label))
        # 循环结束标签
        self.quadruples.append((f"{end_label}:", None, None, None))
        self.loop_stack.pop()

    def _process_return_stmt(self, stmt: Dict[str, Any]):
        """处理返回语句"""
        if 'expression' in stmt and stmt['expression']:
            expr = self._process_expr(stmt['expression'])
            self.quadruples.append(('return', expr, None, None))
        else:
            self.quadruples.append(('return', None, None, None))

    def _process_break_stmt(self, stmt: Dict[str, Any]):
        """处理break语句"""
        if not self.loop_stack:
            raise ValueError("break statement outside of loop")

        # 获取当前循环的结束标签
        loop_info = self.loop_stack[-1]
        end_label = loop_info['end_label']

        # 无条件跳转到循环结束
        self.quadruples.append(('goto', None, None, end_label))

    def _process_continue_stmt(self, stmt: Dict[str, Any]):
        """处理continue语句"""
        if not self.loop_stack:
            raise ValueError("continue statement outside of loop")

        # 获取当前循环的开始标签
        loop_info = self.loop_stack[-1]
        start_label = loop_info['start_label']

        # 无条件跳转到循环开始
        self.quadruples.append(('goto', None, None, start_label))

    def _process_expr(self, expr: Dict[str, Any]) -> str:
        """处理表达式并返回结果临时变量"""
        expr_type = expr.get('type')
        if expr_type == 'BinaryExpression':
            return self._process_binary_expr(expr)
        elif expr_type == 'CallExpression':
            return self._process_call_expr(expr)
        elif expr_type == 'Identifier':
            return expr.get('name', 'unknown_id')
        elif expr_type == 'Literal':
            return self._process_literal(expr)
        elif expr_type == 'IfExpr':
            return self._process_if_expr(expr)
        elif expr_type == 'LoopExpr':
            return self._process_loop_expr(expr)
        elif expr_type == 'UnaryExpr':
            return self._process_unary_expr(expr)
        elif expr_type == 'DerefExpr':
            return self._process_deref_expr(expr)
        elif expr_type == 'RefExpr':
            return self._process_ref_expr(expr)
        elif expr_type == 'IndexExpr':
            return self._process_index_expr(expr)
        elif expr_type == 'TupleAccess':
            return self._process_tuple_access(expr)
        elif expr_type == 'ArrayLiteral':
            return self._process_array_literal(expr)
        elif expr_type == 'TupleLiteral':
            return self._process_tuple_literal(expr)
        # 可以扩展其他表达式类型
        return None

    def _process_binary_expr(self, expr: Dict[str, Any]) -> str:
        """处理二元表达式"""
        left = self._process_expr(expr.get('left', {}))
        right = self._process_expr(expr.get('right', {}))
        op = expr.get('operator', '?')

        temp = self.new_temp()
        self.quadruples.append((op, left, right, temp))
        return temp

    def _process_unary_expr(self, expr: Dict[str, Any]) -> str:
        """处理一元表达式"""
        operand = self._process_expr(expr.get('argument', {}))
        op = expr.get('operator', '?')

        temp = self.new_temp()
        self.quadruples.append((op, operand, None, temp))
        return temp

    def _process_call_expr(self, expr: Dict[str, Any]) -> str:
        """处理函数调用表达式"""
        callee = expr.get('callee', 'unknown_func')
        args = expr.get('arguments', [])

        # 处理参数
        for arg in args:
            arg_value = self._process_expr(arg)
            self.quadruples.append(('param', arg_value, None, None))
        # 函数调用
        result = self.new_temp()
        self.quadruples.append(('call', callee, len(args), result))

        return result

    def _process_literal(self, literal: Dict[str, Any]) -> str:
        """处理字面量"""
        return str(literal.get('value', 'unknown_value'))

    def _process_if_expr(self, expr: Dict[str, Any]) -> str:
        """处理if表达式（有返回值的if语句）"""
        cond = self._process_expr(expr.get('condition', {}))
        then_expr = expr.get('then', {})
        else_expr = expr.get('else', {})

        # 生成条件跳转
        else_label = self.new_label()
        end_label = self.new_label()
        result_temp = self.new_temp()

        self.quadruples.append(('ifz', cond, None, else_label))

        # 处理then分支
        then_value = self._process_expr(then_expr)
        self.quadruples.append(('=', then_value, None, result_temp))

        # 无条件跳转到结束标签
        self.quadruples.append(('goto', None, None, end_label))

        # else标签
        self.quadruples.append((f"{else_label}:", None, None, None))

        # 处理else分支
        else_value = self._process_expr(else_expr)
        self.quadruples.append(('=', else_value, None, result_temp))

        # 结束标签
        self.quadruples.append((f"{end_label}:", None, None, None))

        return result_temp

    def _process_loop_expr(self, expr: Dict[str, Any]) -> str:
        """处理loop表达式（有返回值的无限循环）"""
        body = expr.get('body', {})

        start_label = self.new_label()
        end_label = self.new_label()
        result_temp = self.new_temp()

        # 记录循环上下文，用于break
        self.loop_stack.append({
            'start_label': start_label,
            'end_label': end_label,
            'result_temp': result_temp
        })
        # 循环开始
        self.quadruples.append((f"{start_label}:", None, None, None))
        # 处理循环体
        self._process_expr(body)
        # 无条件跳转到循环开始
        self.quadruples.append(('goto', None, None, start_label))

        # 循环结束
        self.quadruples.append((f"{end_label}:", None, None, None))
        self.loop_stack.pop()

        return result_temp

    def _process_deref_expr(self, expr: Dict[str, Any]) -> str:
        """处理解引用表达式"""
        operand = self._process_expr(expr.get('operand', {}))

        temp = self.new_temp()
        self.quadruples.append(('*', operand, None, temp))
        return temp

    def _process_ref_expr(self, expr: Dict[str, Any]) -> str:
        """处理取引用表达式"""
        is_mut = expr.get('mut', False)
        operand = self._process_expr(expr.get('operand', {}))

        temp = self.new_temp()
        self.quadruples.append(('&', operand, 'mut' if is_mut else 'const', temp))
        return temp

    def _process_index_expr(self, expr: Dict[str, Any]) -> str:
        """处理数组索引表达式"""
        target = self._process_expr(expr.get('target', {}))
        index = self._process_expr(expr.get('index', {}))

        temp = self.new_temp()
        self.quadruples.append(('[]', target, index, temp))
        return temp

    def _process_tuple_access(self, expr: Dict[str, Any]) -> str:
        """处理元组访问表达式"""
        target = self._process_expr(expr.get('target', {}))
        index = expr.get('index', 0)

        temp = self.new_temp()
        self.quadruples.append(('tuple[]', target, index, temp))
        return temp

    def _process_array_literal(self, expr: Dict[str, Any]) -> str:
        """处理数组字面量"""
        elements = expr.get('elements', [])

        array_temp = self.new_temp()
        self.quadruples.append(('new_array', len(elements), None, array_temp))

        # 初始化数组元素
        for i, element in enumerate(elements):
            element_value = self._process_expr(element)
            self.quadruples.append(('[]=', array_temp, i, element_value))

        return array_temp

    def _process_tuple_literal(self, expr: Dict[str, Any]) -> str:
        """处理元组字面量"""
        elements = expr.get('elements', [])

        tuple_temp = self.new_temp()
        self.quadruples.append(('new_tuple', len(elements), None, tuple_temp))

        for i, element in enumerate(elements):
            element_value = self._process_expr(element)
            self.quadruples.append(('tuple[]=', tuple_temp, i, element_value))

        return tuple_temp


def generate_quadruples(ast: Dict[str, Any]) -> List[Tuple]:
    """生成四元式中间代码的快捷函数"""
    generator = QuadrupleGenerator(ast)
    return generator.generate()
