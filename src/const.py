import enum


class TokType(enum.Enum):
    identifier      = 10
    number          = 11
    string          = 12
    operator        = 13
    variable        = 14
    assignment      = 15
    condition       = 16
    parameter       = 17
    function        = 18
    def_function    = 19
    
    block           = 20
    value           = 21
    Type            = 22
    return_stmt     = 23
    
    root            = 101
    end_line        = 102


class Operators(enum.Enum):
    add             = 110
    subtract        = 111
    multiply        = 112
    divide          = 113
    remainder       = 114
    power           = 115

    equals          = 116

    same            = 117
    different       = 118

    less            = 119
    greater         = 120
    less_same       = 121
    greater_same    = 122

    left_paren      = 123
    right_paren     = 124



class Identifier(enum.Enum):
    print_tok      = "print"
    

operators_ = {
    "+": Operators.add,
    "-": Operators.subtract,
    "*": Operators.multiply,
    "/": Operators.divide,
    "%": Operators.remainder,
    "^": Operators.power,
    "=": Operators.equals,
    "==": Operators.same,
    "!=": Operators.different,
    ">": Operators.greater,
    "<": Operators.less,
    ">=": Operators.greater_same,
    "<=": Operators.less_same,
    
    ">=": Operators.left_paren,
    "<=": Operators.right_paren,
}

operators_vis = {
    Operators.add:          "add",
    Operators.subtract:     "sub",
    Operators.multiply:     "mul",
    Operators.divide:       "div",
    Operators.remainder:    "remainder",
    Operators.power:        "pow",
    Operators.equals:       "equal",
    Operators.same:         "==",
    Operators.different:    "!=",
    Operators.greater:      ">",
    Operators.less:         "<",
    Operators.greater_same: ">=",
    Operators.less_same:    "<=",
    
    Operators.left_paren:   "(",
    Operators.right_paren:  ")",
}

compare_operators = [
    Operators.same,
    Operators.less,
    Operators.less_same,
    Operators.greater,
    Operators.greater_same,
    Operators.different,
]