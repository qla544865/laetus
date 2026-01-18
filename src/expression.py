from const import *
from node import Node
from tokens import *

def precedence(op):
    if op.operator in (Operators.multiply, Operators.divide):
        return 2
    if op.operator in (Operators.add, Operators.subtract):
        return 1
    return 0

def create_zero_node():
    return Node(NumToken("0"))

from const import *
from node import Node
from tokens import *

def precedence(op):
    if op.operator in (Operators.multiply, Operators.divide):
        return 2
    if op.operator in (Operators.add, Operators.subtract):
        return 1
    return 0

def create_zero_node():
    return Node(NumToken("0"))

def build_expression_tree(tokens):
    node_stack = []
    op_stack = []
    
    expecting_operand = True 

    i = 0
    size = len(tokens)

    while i < size:
        tk = tokens[i]

        if tk.type == TokType.number:
            node_stack.append(Node(tk))
            expecting_operand = False 
        
        elif tk.type == TokType.string:
            node_stack.append(Node(tk))
            expecting_operand = False

        elif tk.type == TokType.identifier:
            if i + 1 < size and tokens[i+1].type == TokType.operator and tokens[i+1].operator == Operators.left_paren:
                # Bắt đầu parse hàm gọi
                fn_call_node = Node(FunctionToken())
                fn_call_node.add_children(Node(tk)) # Tên hàm
                
                params_node = Node(ParameterToken())
                i += 2 # Bỏ qua ID và '('
                
                paren_count = 1
                inner_tokens = []
                while i < size and paren_count > 0:
                    t = tokens[i]
                    if t.type == TokType.operator and t.operator == Operators.left_paren: paren_count += 1
                    if t.type == TokType.operator and t.operator == Operators.right_paren: paren_count -= 1
                    
                    if paren_count > 0:
                        if t.type == TokType.identifier and t.func == "Comma":
                            if inner_tokens:
                                params_node.children.extend(build_expression_tree(inner_tokens))
                            inner_tokens = []
                        else:
                            inner_tokens.append(t)
                        i += 1
                
                if inner_tokens:
                    params_node.children.extend(build_expression_tree(inner_tokens))
                
                fn_call_node.add_children(params_node)
                node_stack.append(fn_call_node)
                expecting_operand = False
                # i bây giờ đang ở vị trí dấu ')', vòng lặp chính sẽ i += 1 tiếp
            else:
                node_stack.append(Node(tk))
                expecting_operand = False

        elif tk.type == TokType.operator and tk.operator == Operators.left_paren:
            op_stack.append(tk)
            expecting_operand = True 

        elif tk.type == TokType.operator and tk.operator == Operators.right_paren:
            while op_stack and not (op_stack[-1].type == TokType.operator and op_stack[-1].operator == Operators.left_paren):
                apply_operator(node_stack, op_stack)
            if op_stack:
                op_stack.pop()
            expecting_operand = False 

        elif tk.type == TokType.operator:
            if tk.operator == Operators.subtract and expecting_operand:
                node_stack.append(create_zero_node())
            
            while (op_stack and 
                   op_stack[-1].type == TokType.operator and 
                   precedence(op_stack[-1]) >= precedence(tk)):
                apply_operator(node_stack, op_stack)
            
            op_stack.append(tk)
            expecting_operand = True
            
        i += 1

    while op_stack:
        apply_operator(node_stack, op_stack)

    return node_stack

def apply_operator(node_stack, op_stack):
    if len(node_stack) < 2: return
    op = op_stack.pop()
    right = node_stack.pop()
    left = node_stack.pop()

    op_node = Node(op)
    op_node.add_children(left)
    op_node.add_children(right)
    node_stack.append(op_node)

