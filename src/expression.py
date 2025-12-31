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

        # 1. Xử lý Số
        if tk.type == TokType.number:
            node_stack.append(Node(tk))
            expecting_operand = False 
        
        # 2. Xử lý Chuỗi (String)
        elif tk.type == TokType.string:
            node_stack.append(Node(tk))
            expecting_operand = False

        # 3. Xử lý Identifier: Có thể là Biến hoặc Gọi Hàm
        elif tk.type == TokType.identifier:
            # KIỂM TRA: Có phải là hàm không? (Identifier + '(')
            if i + 1 < size and tokens[i+1].type == TokType.operator and tokens[i+1].operator == Operators.left_paren:
                
                # --- LOGIC GỌI HÀM ---
                func_tok = FunctionToken()
                func_node = Node(func_tok)
                
                # Token tên hàm (ví dụ: 'a')
                func_name_node = Node(tk)
                func_node.add_children(func_name_node)
                
                para_node = Node(ParameterToken())
                
                # Tách các đối số trong ngoặc: ( arg1, arg2, ... )
                # Bắt đầu từ sau dấu '('
                arg_tokens = []
                current_arg = []
                balance = 1 
                k = i + 2   
                
                while k < size:
                    t = tokens[k]
                    
                    if t.type == TokType.operator and t.operator == Operators.left_paren:
                        balance += 1
                        current_arg.append(t)
                    elif t.type == TokType.operator and t.operator == Operators.right_paren:
                        balance -= 1
                        if balance == 0:
                            # Đóng ngoặc cuối cùng của hàm -> Kết thúc
                            if current_arg:
                                arg_tokens.append(current_arg)
                            break
                        else:
                            current_arg.append(t)
                    # Kiểm tra dấu phẩy (Dựa trên Lexer của bạn: CommaToken là Identifier có func="Comma")
                    elif t.type == TokType.identifier and t.func == "Comma": 
                        if balance == 1: # Chỉ tách phẩy ở cấp cao nhất
                            if current_arg:
                                arg_tokens.append(current_arg)
                                current_arg = []
                        else:
                            current_arg.append(t)
                    else:
                        current_arg.append(t)
                    
                    k += 1
                
                # Xây dựng tree cho từng đối số
                for arg_list in arg_tokens:
                    # Đệ quy: Mỗi đối số là một biểu thức (ví dụ: x + 1)
                    # build_expression_tree trả về list node (thường là 1 root), ta lấy node đầu
                    arg_roots = build_expression_tree(arg_list)
                    if arg_roots:
                        para_node.add_children(arg_roots[0])

                func_node.add_children(para_node)
                node_stack.append(func_node)
                
                expecting_operand = False
                i = k # Nhảy cóc qua toàn bộ phần gọi hàm
                # --- KẾT THÚC LOGIC HÀM ---

            else:
                # Là biến bình thường
                node_stack.append(Node(tk))
                expecting_operand = False 

        # 4. Xử lý Dấu ngoặc mở '(' (Chỉ dùng để gom nhóm, không phải hàm)
        elif tk.type == TokType.operator and tk.operator == Operators.left_paren:
            op_stack.append(tk)
            expecting_operand = True 

        # 5. Xử lý Dấu ngoặc đóng ')'
        elif tk.type == TokType.operator and tk.operator == Operators.right_paren:
            while op_stack and not (op_stack[-1].type == TokType.operator and op_stack[-1].operator == Operators.left_paren):
                apply_operator(node_stack, op_stack)
            if op_stack:
                op_stack.pop() # Lấy dấu '(' ra
            expecting_operand = False 

        # 6. Xử lý Toán tử (+, -, *, /)
        elif tk.type == TokType.operator:
            # XỬ LÝ SỐ ÂM: Biến -x thành 0 - x
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

# def build_expression_tree(tokens):
#     node_stack = []
#     op_stack = []
    
#     expecting_operand = True 

#     def apply_operator():
#         if len(node_stack) < 2: return
#         op = op_stack.pop()
#         right = node_stack.pop()
#         left = node_stack.pop()

#         op_node = Node(op)
#         op_node.add_children(left)
#         op_node.add_children(right)
#         node_stack.append(op_node)


#     for tk in tokens:
#         if tk.type in (TokType.number, TokType.identifier):
#             node_stack.append(Node(tk))
#             expecting_operand = False 

#         elif tk.type == TokType.operator and tk.operator == Operators.left_paren:
#             op_stack.append(tk)
#             expecting_operand = True

#         elif tk.type == TokType.operator and tk.operator == Operators.right_paren:
#             while op_stack and not (op_stack[-1].type == TokType.operator and op_stack[-1].operator == Operators.left_paren):
#                 apply_operator()
#             op_stack.pop()
#             expecting_operand = False

#         elif tk.type == TokType.operator:
#             if tk.operator == Operators.subtract and expecting_operand:
#                 node_stack.append(create_zero_node())
            
#             while (op_stack and 
#                    op_stack[-1].type == TokType.operator and 
#                    precedence(op_stack[-1]) >= precedence(tk)):
#                 apply_operator()
            
#             op_stack.append(tk)
#             expecting_operand = True

#     while op_stack:
#         apply_operator()

#     return node_stack

def build_expression_tree_old(tokens):
    node_stack = []
    op_stack = []

    def apply_operator():
        op = op_stack.pop()
        right = node_stack.pop()
        left = node_stack.pop()

        op_node = Node(op)
        op_node.add_children(left)
        op_node.add_children(right)

        node_stack.append(op_node)

    for tk in tokens:
        if tk.type in (TokType.number,TokType.identifier):
            node_stack.append(Node(tk))

        # # (
        # elif tk.type == TOKEN_PAREN and tk.string_value == '(':
        #     op_stack.append(tk)

        # # )
        # elif tk.type == TOKEN_PAREN and tk.string_value == ')':
        #     while op_stack and op_stack[-1].string_value != '(':
        #         apply_operator()
        #     op_stack.pop()

        # toán tử
        elif tk.type == TokType.operator:
            while (op_stack and
                   op_stack[-1].type == TokType.operator and
                   precedence(op_stack[-1]) >= precedence(tk)):
                apply_operator()
            op_stack.append(tk)

    while op_stack:
        apply_operator()

    return node_stack