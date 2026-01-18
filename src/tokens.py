from const import *


class Token:
    def __init__(self):
        self.type: int = None
        self.func: str = None
        self.int_value: int = None
        self.float_value: float = None
        self.string_value: str = None
        self.is_unary:bool = False

        self.operator: int = None

        self.is_float = False

    def __str__(self):
        if self.type == TokType.identifier:
            return "ID: "+self.func
        elif self.type == TokType.number:
            return ("NUM: "+self.float_value if self.is_float else "NUM: "+self.int_value) 
        elif self.type == TokType.end_line:
            return "ENDLINE"
        elif self.type == TokType.operator:
            return ("OP: "+operators_vis[self.operator])
        elif self.type == TokType.string:
            return ("STR: "+self.string_value)
        elif self.type == TokType.assignment:
            return "Assignment"
        elif self.type == TokType.condition:
            return "Condition"
        elif self.type == TokType.parameter:
            return "Parameter"
        elif self.type == TokType.function:
            return "Func"
        elif self.type == TokType.def_function:
            return "Def_Func"
        elif self.type == TokType.root:
            return "Root"
        elif self.type == TokType.block:
            return self.func
        elif self.type == TokType.return_stmt:
            return "Return"
        elif self.type == TokType.Type:
            return ("Type: " + self.func)
        elif self.type == TokType.value:
            return "Value"
        else:
            return ""

    def set_id(self, id:str): 
        self.func = id
        
    def set_num(self, num: int | float): 
        if isinstance(num, float):
            self.float_value = num
            self.is_float = True
        else:
            self.int_value = num
            self.is_float = False
            self.float_value = float(num)

    def set_op(self, op:int):
        self.operator = op

    def set_str(self, str_: str):
        self.string_value = str_

class IdToken(Token):
    def __init__(self, id:str):
        super().__init__()
        self.type = TokType.identifier
        self.set_id(id)

class NumToken(Token):
    def __init__(self, num: int|float):
        super().__init__()
        self.type = TokType.number
        self.set_num(num)

class StrToken(Token):
    def __init__(self, id:str):
        super().__init__()
        self.type = TokType.string
        self.set_str(id)

class CommaToken(Token):
    def __init__(self):
        super().__init__()
        self.type = TokType.identifier
        self.set_id("Comma")

class ValueToken(Token):
    def __init__(self):
        super().__init__()
        self.type = TokType.value

class BlockToken(Token):
    def __init__(self,block:str):
        super().__init__()
        self.type = TokType.block
        self.set_id(block)

class TypeToken(Token):
    def __init__(self,type:str):
        super().__init__()
        self.type = TokType.Type
        self.set_id(type)

class RootToken(Token):
    def __init__(self):
        super().__init__()
        self.type = TokType.root

class OperatorToken(Token):
    def __init__(self, op: int):
        super().__init__()
        self.type = TokType.operator
        self.set_op(op)


class ParameterToken(Token):
    def __init__(self):
        super().__init__()
        self.type = TokType.parameter

class DefFunctionToken(Token):
    def __init__(self):
        super().__init__()
        self.type = TokType.def_function

class FunctionToken(Token):
    def __init__(self):
        super().__init__()
        self.type = TokType.function


class EndLineToken(Token):
    def __init__(self):
        super().__init__()
        self.type = TokType.end_line


class AssignmentToken(Token):
    def __init__(self):
        super().__init__()
        self.type = TokType.assignment


class ConditionToken(Token):
    def __init__(self):
        super().__init__()
        self.type = TokType.condition

class ReturnToken(Token):
    def __init__(self):
        super().__init__()
        self.type = TokType.return_stmt
        self.set_id("return")