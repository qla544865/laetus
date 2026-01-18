from tokens import *
from const import *

data_types = [
    "int",
    "float",
    "str",
]

def add_identifier(tokens:list[Token], id_type: str):
    if id_type in data_types:
        new_tok  = TypeToken(id_type)
        new_tok.set_id(id_type)
        tokens.append(new_tok)
    else:
        new_tok  = IdToken(id_type)
        new_tok.set_id(id_type)
        new_tok.func = id_type
        tokens.append(new_tok)
    return tokens

def add_number(tokens:list[Token], value: int|float):
    new_tok  = NumToken(value)
    tokens.append(new_tok)
    return tokens

def add_operator(tokens:list[Token], op: str):
    new_tok  = OperatorToken(operators_[op])
    tokens.append(new_tok)
    return tokens

def lexer(code:str):
    tokens:list[Token] = []
    tok = ""

    state = TokType.identifier
    curr_char = ""

    pre_tok = ""
    is_command = False

    for c in code:
        curr_char = c
        if state == TokType.string:
            if (c == "\""):
                new_tok = StrToken(tok)
                tokens.append(new_tok)
                state = TokType.identifier
                tok = ""
                curr_char = ""
        elif is_command == True:
            if c == "\n":
                curr_char = ""
                tok = ""
                is_command = False
        else:
            if (c == "\""):
                if tok != "":
                    if state == TokType.identifier:
                        tokens = add_identifier(tokens,tok)
                    elif state == TokType.number:
                        tokens = add_number(tokens,tok)
                curr_char = ""
                tok = ""
                state = TokType.string
            if (c == ","):
                if tok != "":
                    if state == TokType.identifier:
                        tokens = add_identifier(tokens,tok)
                    elif state == TokType.number:
                        tokens = add_number(tokens,tok)
                curr_char = ""
                tok = ""
                new_tok = CommaToken()
                tokens.append(new_tok)

                state = TokType.identifier
            if (c == "#"):
                if tok != "":
                    if state == TokType.identifier:
                        tokens = add_identifier(tokens,tok)
                    elif state == TokType.number:
                        tokens = add_number(tokens,tok)
                tok = ""
                state = TokType.identifier
            if c == "(":
                if tok != "":
                    if state == TokType.identifier:
                        tokens = add_identifier(tokens,tok)
                    elif state == TokType.number:
                        tokens = add_number(tokens,tok)
                curr_char = ""
                tok = ""

                new_tok = OperatorToken(Operators.left_paren)
                tokens.append(new_tok)
                state = TokType.identifier
            if c == ")":
                if tok != "":
                    if state == TokType.identifier:
                        tokens = add_identifier(tokens,tok)
                    elif state == TokType.number:
                        tokens = add_number(tokens,tok)
                curr_char = ""
                tok = ""

                new_tok = OperatorToken(Operators.right_paren)
                tokens.append(new_tok)
                state = TokType.identifier
            if (c == "\n" or c == " "):
                if tok != "":
                    if state == TokType.identifier:
                        tokens = add_identifier(tokens,tok)
                    elif state == TokType.number:
                        tokens = add_number(tokens,tok)
                
                if c == "\n":
                    tokens.append(EndLineToken())
                tok = ""
                curr_char = ""
                state = TokType.identifier
            elif (
                    c == "+" or c == "-" or c == "*" or \
                    c == "/" or c == "=" or c == "<" or \
                    c == ">" or c == "%" or c == "^"
                ):
                if tok != "":
                    if state == TokType.identifier:
                        tokens = add_identifier(tokens,tok)
                    elif state == TokType.number:
                        tokens = add_number(tokens,tok)

                if c == "=" and pre_tok == "=":
                    tokens.pop(-1)

                    same_tok = OperatorToken(Operators.same)

                    tokens.append(same_tok)
                elif c == "=" and pre_tok == "<":
                    tokens.pop(-1)

                    same_tok = OperatorToken(Operators.less_same)

                    tokens.append(same_tok)
                elif c == "=" and pre_tok == ">":
                    tokens.pop(-1)

                    same_tok = OperatorToken(Operators.greater_same)

                    tokens.append(same_tok)
                else:
                    tokens = add_operator(tokens, c)
                
                tok = ""
                curr_char = ""
                state = TokType.identifier

            elif (
                    c == "1" or c == "2" or c == "3" or \
                    c == "4" or c == "5" or c == "6" or \
                    c == "7" or c == "8" or c == "9" or \
                    c == "0"
                ) and tok == "":
                state = TokType.number

            elif c == "#" and tok == "":
                is_command = True

    
        tok += curr_char

        pre_tok = c
    return tokens