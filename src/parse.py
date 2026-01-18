from tokens import *
from const import *
from node import Node
from expression import build_expression_tree

def print_tree(node, depth=0):
    indent = "   " * depth
    tok = node.data
    print(f"{indent}-{depth}->{tok}")
    for c in node.children:
        # print(c.data.type)
        print_tree(c, depth + 1)

class Parser:
    def __init__(self, tokens:list[Token]):
        self.tokens = tokens
        self.pos = 0
        self.size = len(self.tokens)

    def current(self):
        return self.tokens[self.pos]

    def is_type(self, _type):
        return self.current().type == _type
    
    def is_identifier(self, func):
        return self.is_type(TokType.identifier) and self.current().func == func
    
    def is_next_identifier(self, func):
        return self.tokens[self.pos+1].type == TokType.identifier and self.tokens[self.pos+1].func == func
    
    
    def advance(self):
        self.pos += 1
        return self.tokens[self.pos-1] if self.pos < self.size else self.tokens[self.size-1]
    
    def back(self):
        self.pos -= 1
        return self.tokens[self.pos] if self.pos < self.size else self.tokens[self.size-1]

    def get_block(self, end_keyword=[], ops=[]):
        statements = []

        while self.pos < self.size:
            current_tok = self.current()
            if current_tok.type == TokType.identifier and current_tok.func in end_keyword:
                break

            stmt = self.parse_statement()

            if stmt:
                statements.append(stmt)
            else:
                self.advance()
        return statements

    def parse_statement(self):
        tok = self.current()



        if self.is_identifier("print") or self.is_identifier("println"):
            return self.parse_print()
        if self.is_identifier("if"):
            return self.parse_if()
        if self.is_identifier("input"):
            return self.parse_input()
        if self.is_identifier("while"):
            return self.parse_while()
        if self.is_identifier("for"):
            return self.parse_for()
        if self.is_identifier("func"):
            return self.parse_function()
        if self.is_identifier("return"):
            return self.parse_return()
        if tok.type == TokType.identifier and self.pos+1 < self.size:
            if self.tokens[self.pos+1].type == TokType.operator:
                if self.tokens[self.pos+1].operator == Operators.equals:
                    return self.parse_assignment()
                if self.tokens[self.pos+1].operator == Operators.left_paren:
                    return self.parse_call_func()
        if tok.type == TokType.Type and self.pos+2 < self.size:
            if self.tokens[self.pos+2].type == TokType.operator:
                if self.tokens[self.pos+1].operator == Operators.equals:
                    return self.parse_assignment()
        
        return None

    def parse_print(self):
        print_node = Node(self.advance())

        expr_tokens = []

        while not self.current().type == TokType.end_line and self.pos < self.size:
            expr_tokens.append(self.advance())

        if expr_tokens:
            res = build_expression_tree(expr_tokens)
            print_node.children.extend(res)
            
        return print_node

    def parse_return(self):
        ret_node = Node(ReturnToken())
        self.advance()

        expr_tokens = []
        while not self.current().type == TokType.end_line and self.pos < self.size:
            expr_tokens.append(self.advance())

        if expr_tokens:
            res = build_expression_tree(expr_tokens)
            ret_node.children.extend(res)
            
        return ret_node

    def parse_assignment(self):
        assignment_node = Node(AssignmentToken())
        type_node = Node(TypeToken(""))
        var_type = ""
        if self.tokens[self.pos-1].type == TokType.Type:
            type_node.data.func = self.tokens[self.pos-1].func
            var_type = type_node.data.func
        name = Node(self.advance())
        assignment_node.add_children(name)

        value_node = Node(ValueToken())

        self.advance()

        expr_tokens = []

        while not self.current().type == TokType.end_line and self.pos < self.size:
            if self.current().type == TokType.number:
                var_type = "float" if var_type == "" else var_type
            if self.current().type == TokType.string:
                var_type = "str" if var_type == "" else var_type
            if self.current().type == TokType.identifier:
                if self.tokens[self.pos+1].type == TokType.operator and \
                    self.tokens[self.pos+1].operator == Operators.right_paren:
                    self.advance()
            expr_tokens.append(self.advance())
        
        type_node.data.func = var_type
        if expr_tokens:
            res = build_expression_tree(expr_tokens)
            value_node.children.extend(res)
        
        assignment_node.add_children(value_node)
        assignment_node.add_children(type_node)

        return assignment_node

    def parse_while(self):
        while_node = Node(self.advance())

        expr =  []

        condition_node = Node(ConditionToken())
        op_node = Node(Token())
        
        while not self.is_identifier("do") and self.pos < self.size:
            if self.is_type(TokType.operator) and self.current().operator in compare_operators:
                expr = build_expression_tree(expr)
                op_node.data = self.advance()
                op_node.children.extend(expr)
                expr = []

            expr.append(self.advance())

            if self.is_identifier("do"):
                expr = build_expression_tree(expr)
                op_node.children.extend(expr)
                print
        
        condition_node.add_children(op_node)
        while_node.add_children(condition_node)

        block_node = Node(BlockToken("WhileBlock"))
        block_child =  self.get_block(end_keyword=["end"])
        block_node.children = block_child
        while_node.add_children(block_node)

        if self.is_identifier("end"):
            self.advance()


        return while_node

    def parse_if(self):
        if_node = Node(self.advance())

        expr =  []

        condition_node = Node(ConditionToken())
        op_node = Node(Token())
        
        while not self.is_identifier("then") and self.pos < self.size:
            if self.is_type(TokType.operator) and self.current().operator in compare_operators:
                expr = build_expression_tree(expr)
                op_node.data = self.advance()
                op_node.children.extend(expr)
                expr = []

            expr.append(self.advance())

            if self.is_identifier("then"):
                expr = build_expression_tree(expr)
                op_node.children.extend(expr)
                print
        
        condition_node.add_children(op_node)
        if_node.add_children(condition_node)

        block_node = Node(BlockToken("IfBlock"))
        block_child =  self.get_block(end_keyword=["else","end"])
        block_node.children = block_child
        if_node.add_children(block_node)
        
        if self.is_identifier("else"):
            self.advance()
            block_node = Node(BlockToken("ElseBlock"))
            block_child =  self.get_block(end_keyword=["end"])
            block_node.children = block_child
            if_node.add_children(block_node)


        if self.is_identifier("end"):
            self.advance()


        return if_node

    def parse_input(self):
        input_node = Node(self.advance())

        type_node = Node(self.advance())
        input_node.add_children(type_node)
        var_node = Node(self.advance())
        input_node.add_children(var_node)

        if self.pos < self.size and self.current().type == TokType.string:
            prompt_node = Node(self.advance())
            input_node.add_children(prompt_node)

        return input_node

    def parse_for(self):
        for_node = Node(self.advance())  # 'for'
        param_node = Node(ParameterToken())

        # 1. Xử lý biến đếm và giá trị khởi đầu (i = 1)
        var_tok = self.advance() # Lấy 'i'
        if self.current().type == TokType.operator and self.current().operator == Operators.equals:
            self.advance() # Bỏ qua dấu '='
        
        # Lấy expression cho giá trị bắt đầu (đến dấu phẩy)
        start_expr_tokens = []
        while not self.is_identifier("Comma") and self.pos < self.size:
            start_expr_tokens.append(self.advance())
        
        # Tạo node Assignment: i = start_expr
        assign_node = Node(AssignmentToken())
        assign_node.add_children(Node(var_tok))
        val_node = Node(ValueToken())
        val_node.children.extend(build_expression_tree(start_expr_tokens))
        assign_node.add_children(val_node)
        assign_node.add_children(Node(TypeToken("int"))) # Mặc định là int cho loop
        
        param_node.add_children(assign_node) # Child 0 của Parameter là Assignment

        # 2. Xử lý giá trị kết thúc (10)
        if self.is_identifier("Comma"): self.advance()
        end_expr_tokens = []
        while not self.is_identifier("Comma") and not self.is_identifier("do") and self.pos < self.size:
            end_expr_tokens.append(self.advance())
        param_node.add_children(build_expression_tree(end_expr_tokens)[0])

        # 3. Xử lý bước nhảy (1)
        if self.is_identifier("Comma"):
            self.advance()
            step_tokens = []
            while not self.is_identifier("do") and self.pos < self.size:
                step_tokens.append(self.advance())
            param_node.add_children(build_expression_tree(step_tokens)[0])
        else:
            # Mặc định step = 1 nếu không ghi
            step_node = Node(NumToken(1))
            step_node.data.set_num(1)
            param_node.add_children(step_node)

        for_node.add_children(param_node)

        # 4. Block xử lý
        if self.is_identifier("do"):
            self.advance()
            block_node = Node(BlockToken("ForBlock"))
            block_node.children = self.get_block(end_keyword=["end"])
            for_node.add_children(block_node)
            if self.is_identifier("end"): self.advance()

        return for_node

    def parse_function(self):
        self.advance() # Bỏ qua 'func'
        def_func_node = Node(DefFunctionToken())
        
        # Tên hàm
        func_node = Node(self.advance()) 
        def_func_node.add_children(func_node)
        
        parameter = Node(ParameterToken())
        
        # Bắt buộc phải có dấu '('
        if self.current().operator == Operators.left_paren:
            self.advance()
        
        # Parse tham số: Chỉ chấp nhận ID, cách nhau bởi dấu phẩy
        while self.pos < self.size:
            if self.current().operator == Operators.right_paren:
                self.advance() # Bỏ qua ')'
                break
            
            if self.current().type == TokType.identifier:
                # Thêm ID vào parameter node
                # Lưu ý: Không dùng build_expression_tree ở đây vì đây là định nghĩa
                param_id = Node(self.current())
                parameter.add_children(param_id)
                self.advance()
                
            if self.is_identifier("Comma"): # Nếu gặp dấu phẩy thì bỏ qua
                self.advance()
                
        def_func_node.add_children(parameter)

        block_node = Node(BlockToken("FuncBlock"))
        block_child = self.get_block(end_keyword=["end"])
        block_node.children = block_child
        def_func_node.add_children(block_node)

        if self.is_identifier("end"):
            self.advance()

        return def_func_node

    def parse_call_func(self):
        call_node = Node(FunctionToken())
        func_name_node = Node(self.advance()) # Lấy tên hàm
        call_node.add_children(func_name_node)
        
        parameter_node = Node(ParameterToken())
        self.advance() # Bỏ qua '('

        expr_tokens = []
        paren_count = 0

        while self.pos < self.size:
            curr = self.current()
            
            # Xử lý đóng ngoặc của hàm, lưu ý nested ngoặc (vd: fib( (1+2) ))
            if curr.type == TokType.operator and curr.operator == Operators.left_paren:
                paren_count += 1
            elif curr.type == TokType.operator and curr.operator == Operators.right_paren:
                if paren_count == 0:
                    if expr_tokens:
                        parameter_node.children.extend(build_expression_tree(expr_tokens))
                    self.advance() # Bỏ qua ')'
                    break
                paren_count -= 1
            
            # Xử lý dấu phẩy ngăn cách tham số
            if self.is_identifier("Comma") and paren_count == 0:
                if expr_tokens:
                    parameter_node.children.extend(build_expression_tree(expr_tokens))
                expr_tokens = []
                self.advance() # Bỏ qua ','
                continue

            expr_tokens.append(self.advance())

        call_node.add_children(parameter_node)
        return call_node



def parse(tokens:list[Token]):
    root = Node(RootToken())
    parser = Parser(tokens)
    root.children = parser.get_block([])

    return root