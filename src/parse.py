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
            return self.parse_for()
        if self.is_identifier("while"):
            return self.parse_while()
        if self.is_identifier("for"):
            return self.parse_for()
        elif tok.type == TokType.identifier and \
                self.pos+1 < self.size      and \
                self.tokens[self.pos+1].type == TokType.operator and self.tokens[self.pos+1].operator == Operators.equals:
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

    def parse_assignment(self):
        assignment_node = Node(AssignmentToken())
        name = Node(self.advance())
        assignment_node.add_children(name)

        value_node = Node(ValueToken())

        self.advance()

        expr_tokens = []

        while not self.current().type == TokType.end_line and self.pos < self.size:
            expr_tokens.append(self.advance())

        if expr_tokens:
            res = build_expression_tree(expr_tokens)
            value_node.children.extend(res)
        
        assignment_node.add_children(value_node)

        return assignment_node

    def parse_while(self):
        while_node = Node(self.advance())

        expr =  []

        op_node = Node(Token())
        
        while not self.is_identifier("do") and self.pos < self.size:
            if self.is_type(TokType.operator) and self.current().operator in compare_operators:
                expr = build_expression_tree(expr)
                op_node = Node(self.advance())
                op_node.children.extend(expr)
                expr = []

            expr.append(self.advance())

            if self.is_identifier("then"):
                expr = build_expression_tree(expr)
                op_node.children.extend(expr)

                condition_node = Node(ConditionToken())
                condition_node.add_children(op_node)
                while_node.add_children(condition_node)

        block_node = Node(BlockToken("WhileBlock"))
        block_child =  self.get_block(end_keyword=["end"])
        block_node.children = block_child
        while_node.add_children(block_node)

        if self.is_identifier("end"):
            self.advance()


        return while_node

    def parse_for(self):
        for_node = Node(self.advance())
        parameter = Node(ParameterToken())
        expr =  []        
        while not self.is_identifier("do") and self.pos < self.size:
            if self.is_identifier("Comma"):
                expr = build_expression_tree(expr)
                parameter.children.extend(expr)
                expr = []
                self.advance()
            elif self.is_type(TokType.operator) and self.current().operator == Operators.equals:
                self.advance()

            expr.append(self.advance())

            if self.is_identifier("do"):
                expr = build_expression_tree(expr)
                parameter.children.extend(expr)

                for_node.add_children(parameter)

        block_node = Node(BlockToken("ForBlock"))
        block_child =  self.get_block(end_keyword=["end"])
        block_node.children = block_child
        for_node.add_children(block_node)

        if self.is_identifier("end"):
            self.advance()


        return for_node



def parse(tokens:list[Token]):
    root = Node(RootToken())
    parser = Parser(tokens)
    root.children = parser.get_block([])

    return root