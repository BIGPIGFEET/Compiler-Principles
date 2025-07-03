from typing import Any, Dict, List, Optional, Union

class SemanticError(Exception): pass
class UndeclaredVariableError(SemanticError): pass
class ImmutableAssignmentError(SemanticError): pass
class TypeMismatchError(SemanticError): pass
class ReturnTypeError(SemanticError): pass
class InvalidControlFlowError(SemanticError): pass
class UninitializedVariableError(SemanticError): pass
class BorrowCheckError(SemanticError): pass

class Symbol:
    def __init__(self, name, type_, mut=False, initialized=False):
        self.name = name
        self.type = type_
        self.mut = mut
        self.initialized = initialized
        self.borrowed_mut = False  # 是否被可变借用
        self.borrowed_immut = False  # 是否被不可变借用


class SemanticAnalyzer:
    def __init__(self, ast: Dict[str, Any]):
        self.ast = ast
        self.env_stack: List[Dict[str, Symbol]] = [{}]
        self.loop_depth = 0
        self.functions: Dict[str, Dict] = {}

    def current_env(self):
        return self.env_stack[-1]

    def push_env(self):
        self.env_stack.append({})

    def pop_env(self):
        self.env_stack.pop()

    def declare_variable(self, name, type_, mut=False, initialized=False):
        self.current_env()[name] = Symbol(name, type_, mut, initialized)

    def lookup_variable(self, name) -> Symbol:
        for env in reversed(self.env_stack):
            if name in env:
                return env[name]
        raise UndeclaredVariableError(f"Variable '{name}' is not declared")

    def analyze(self):
        assert self.ast["type"] == "Program"
        # ✅ 第一遍收集所有函数声明
        for decl in self.ast["declarations"]:
            self.functions[decl["name"]] = decl
        # ✅ 第二遍执行语义检查
        for decl in self.ast["declarations"]:
            self.visit_function(decl)

    def visit_function(self, node):
        self.push_env()
        for param in node["params"]:
            self.declare_variable(param["name"], param["type"], param["mut"], initialized=True)
        self.visit_block(node["body"]["elements"], node["return_type"])
        self.pop_env()

    def visit_block(self, stmts: List[Dict[str, Any]], expected_return_type=None):
        for stmt in stmts:
            if stmt["type"] in {"EmptyStmt", "Block"}: continue
            if stmt["type"] == "ReturnStmt":
                self.check_return(stmt, expected_return_type)
            elif stmt["type"] == "BreakStmt":
                if self.loop_depth == 0:
                    raise InvalidControlFlowError("break used outside of loop")
            elif stmt["type"] == "ContinueStmt":
                if self.loop_depth == 0:
                    raise InvalidControlFlowError("continue used outside of loop")
            elif stmt["type"] == "VarDecl":
                self.check_var_decl(stmt)
            elif stmt["type"] == "Assignment":
                self.check_assignment(stmt)
            elif stmt["type"] == "ExprStmt":
                self.infer_expr_type(stmt["expr"])
            elif stmt["type"] == "IfStmt":
                self.check_if(stmt, expected_return_type)
            elif stmt["type"] == "WhileStmt":
                self.loop_depth += 1
                self.visit_block(stmt["body"]["statements"], expected_return_type)
                self.loop_depth -= 1
            elif stmt["type"] == "ForStmt":
                self.loop_depth += 1
                self.push_env()
                self.declare_variable(stmt["var"], "i32", stmt["mut"], initialized=True)
                self.visit_block(stmt["body"]["statements"], expected_return_type)
                self.pop_env()
                self.loop_depth -= 1
            elif stmt["type"] == "LoopStmt":
                self.loop_depth += 1
                self.visit_block(stmt["body"]["statements"], expected_return_type)
                self.loop_depth -= 1
            else:
                inferred = self.infer_expr_type(stmt)
                if expected_return_type and inferred != expected_return_type:
                    raise ReturnTypeError(f"Expected return type {expected_return_type}, got {inferred}")

    def check_return(self, stmt, expected_type):
        expr = stmt.get("expression")
        if not expected_type and expr:
            raise ReturnTypeError("Function declared void but returned value")
        if expected_type and not expr:
            raise ReturnTypeError("Function expected return value but returned nothing")
        if expr:
            expr_type = self.infer_expr_type(expr)
            if expr_type != expected_type:
                raise ReturnTypeError(f"Return type mismatch: expected {expected_type}, got {expr_type}")

    def check_var_decl(self, stmt):
        name = stmt["name"]
        var_type = stmt["var_type"]
        init = stmt["init"]
        mut = stmt["mut"]
        if var_type:
            initialized = bool(init)
            self.declare_variable(name, var_type, mut, initialized)
            if init:
                expr_type = self.infer_expr_type(init)
                if expr_type != var_type:
                    raise TypeMismatchError(f"Declared type {var_type}, got {expr_type}")
        elif init:
            # no type, but has initializer — type inference
            expr_type = self.infer_expr_type(init)
            self.declare_variable(name, expr_type, mut, initialized=True)
        else:
            # 检查是否允许不写类型也不初始化（如 shadowing）
            if name in self.current_env():
                # 允许 shadowing：当前作用域已有同名变量
                self.declare_variable(name, None, mut, initialized=False)
            else:
                # 否则不允许声明不初始化、且无法推导类型
                raise TypeMismatchError(f"Cannot infer type for '{name}' without initializer")

    def check_assignment(self, stmt):
        target = stmt["target"]
        val = stmt["value"]
        if target["type"] == "Identifier":
            sym = self.lookup_variable(target["name"])
            if not sym.mut:
                raise ImmutableAssignmentError(f"Cannot assign to immutable variable '{sym.name}'")
            rhs_type = self.infer_expr_type(val)
            if rhs_type != sym.type:
                raise TypeMismatchError(f"Assigning {rhs_type} to {sym.type}")
            sym.initialized = True
        elif target["type"] == "IndexAccess":
            # 数组索引赋值
            array_type = self.infer_expr_type(target["target"])
            if not isinstance(array_type, dict) or array_type["type"] != "ArrayType":
                raise TypeMismatchError("Can only index into arrays")

            # 检查数组是否可变
            if target["target"]["type"] == "Identifier":
                array_sym = self.lookup_variable(target["target"]["name"])
                if not array_sym.mut:
                    raise ImmutableAssignmentError(f"Cannot assign to immutable array '{array_sym.name}'")

            index_type = self.infer_expr_type(target["index"])
            if index_type != "i32":
                raise TypeMismatchError("Array index must be i32")

            rhs_type = self.infer_expr_type(val)
            if rhs_type != array_type["inner"]:
                raise TypeMismatchError(f"Array element type mismatch: expected {array_type['inner']}, got {rhs_type}")

        elif target["type"] == "TupleAccess":
            # 元组字段赋值
            tuple_type = self.infer_expr_type(target["target"])
            if not isinstance(tuple_type, dict) or tuple_type["type"] != "Tuple":
                raise TypeMismatchError("Can only access field on tuple")

            # 检查元组是否可变
            if target["target"]["type"] == "Identifier":
                tuple_sym = self.lookup_variable(target["target"]["name"])
                if not tuple_sym.mut:
                    raise ImmutableAssignmentError(f"Cannot assign to immutable tuple '{tuple_sym.name}'")

            idx = target["index"]
            if idx >= len(tuple_type["elements"]):
                raise SemanticError("Tuple index out of bounds")

            rhs_type = self.infer_expr_type(val)
            expected_type = tuple_type["elements"][idx]
            if rhs_type != expected_type:
                raise TypeMismatchError(f"Tuple element type mismatch: expected {expected_type}, got {rhs_type}")
        else:
            self.infer_expr_type(target)
            self.infer_expr_type(val)

    def check_if(self, stmt, expected_return_type):
        cond_type = self.infer_expr_type(stmt["condition"])
        if cond_type != "i32":
            raise TypeMismatchError("Condition must be i32")
        self.visit_block(stmt["then"]["statements"], expected_return_type)
        if stmt["else"]:
            if stmt["else"]["type"] == "IfStmt":
                self.check_if(stmt["else"], expected_return_type)
            else:
                self.visit_block(stmt["else"]["statements"], expected_return_type)

    def infer_expr_type(self, expr) -> Union[str, Dict[str, Any]]:
        t = expr["type"]
        if t == "Literal": return "i32"
        if t == "Identifier":
            sym = self.lookup_variable(expr["name"])
            if sym.type is None:
                raise TypeMismatchError(f"Cannot use variable '{sym.name}' with unknown type")
            if not sym.initialized:
                raise UninitializedVariableError(f"Variable '{sym.name}' is used before initialization")
            return sym.type
        if t == "BinaryExpression":
            lhs = self.infer_expr_type(expr["left"])
            rhs = self.infer_expr_type(expr["right"])
            if lhs != rhs:
                raise TypeMismatchError(f"Binary operands must match, got {lhs} and {rhs}")
            return "i32"
        if t == "CallExpression":
            func = self.functions.get(expr["callee"])
            if not func:
                raise SemanticError(f"Function {expr['callee']} not defined")
            if len(expr["arguments"]) != len(func["params"]):
                raise SemanticError(f"Function {expr['callee']} expects {len(func['params'])} arguments")
            for arg_expr, param in zip(expr["arguments"], func["params"]):
                arg_type = self.infer_expr_type(arg_expr)
                if arg_type != param["type"]:
                    raise TypeMismatchError(
                        f"Function argument type mismatch: expected {param['type']}, got {arg_type}")
            return func["return_type"]
        if t == "TupleLiteral":
            return {"type": "Tuple", "elements": [self.infer_expr_type(e) for e in expr["elements"]]}
        if t == "ArrayLiteral":
            types = [self.infer_expr_type(e) for e in expr["elements"]]
            if len(set(map(str, types))) > 1:
                raise TypeMismatchError("Array elements must be of same type")
            return {"type": "ArrayType", "inner": types[0], "size": len(types)}
        if t == "RefExpr":
            base_expr = expr["operand"]
            base_type = self.infer_expr_type(base_expr)
            ref_mut = expr["mut"]

            # 借用检查
            if base_expr["type"] == "Identifier":
                sym = self.lookup_variable(base_expr["name"])

                # 检查是否可以创建可变引用
                if ref_mut and not sym.mut:
                    raise BorrowCheckError(f"Cannot create mutable reference to immutable variable '{sym.name}'")

                # 检查借用冲突
                if ref_mut:
                    if sym.borrowed_mut or sym.borrowed_immut:
                        raise BorrowCheckError(f"Cannot borrow '{sym.name}' as mutable because it is already borrowed")
                    sym.borrowed_mut = True
                else:
                    if sym.borrowed_mut:
                        raise BorrowCheckError(
                            f"Cannot borrow '{sym.name}' as immutable because it is already borrowed as mutable")
                    sym.borrowed_immut = True

            return {"type": "ReferenceType", "mut": ref_mut, "inner": base_type}
        if t == "DerefExpr":
            ref = self.infer_expr_type(expr["operand"])
            if not isinstance(ref, dict) or ref["type"] != "ReferenceType":
                raise TypeMismatchError("Can only deref a reference")
            return ref["inner"]
        if t == "TupleAccess":
            tup = self.infer_expr_type(expr["target"])
            if not isinstance(tup, dict) or tup["type"] != "Tuple":
                raise TypeMismatchError("Can only access field on tuple")
            idx = expr["index"]
            if idx >= len(tup["elements"]):
                raise SemanticError("Tuple index out of bounds")
            return tup["elements"][idx]
        if t == "IndexAccess":
            # 数组索引访问
            array_type = self.infer_expr_type(expr["target"])
            if not isinstance(array_type, dict) or array_type["type"] != "ArrayType":
                raise TypeMismatchError("Can only index into arrays")

            index_type = self.infer_expr_type(expr["index"])
            if index_type != "i32":
                raise TypeMismatchError("Array index must be i32")

            # 简单的边界检查（只能检查字面量）
            if expr["index"]["type"] == "Literal":
                index_val = expr["index"]["value"]
                array_size = array_type["size"]
                if index_val >= array_size:
                    raise SemanticError("Array index out of bounds")

            return array_type["inner"]
        if t == "IfExpr":
            c = self.infer_expr_type(expr["condition"])
            if c != "i32":
                raise TypeMismatchError("Condition must be i32")
            then = self.infer_expr_type(expr["then"])
            else_ = self.infer_expr_type(expr["else"])
            if then != else_:
                raise TypeMismatchError("Branches of if expression must return same type")
            return then
        if t == "LoopExpr":
            for e in expr["body"]["elements"]:
                if e["type"] == "BreakStmt":
                    return self.infer_expr_type(e["expression"])
            raise SemanticError("Loop expression has no break with value")
        if t == "FunctionExprBlock":
            # 处理块表达式，创建新的作用域
            self.push_env()
            try:
                # 处理块中除最后一个元素外的所有语句
                for elem in expr["elements"][:-1]:
                    if elem["type"] == "VarDecl":
                        self.check_var_decl(elem)
                    elif elem["type"] == "Assignment":
                        self.check_assignment(elem)
                    elif elem["type"] == "ExprStmt":
                        self.infer_expr_type(elem["expr"])
                    else:
                        self.infer_expr_type(elem)

                # 最后一个元素是表达式，返回其类型
                last = expr["elements"][-1]
                if last["type"] == "ExprStmt":
                    return self.infer_expr_type(last["expr"])
                else:
                    return self.infer_expr_type(last)
            finally:
                self.pop_env()
        return "i32"