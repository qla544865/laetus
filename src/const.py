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
    
    root            = 101
    end_line        = 102


class Operators(enum.Enum):
    add             = 110
    subtract        = 111
    multiply        = 112
    divide          = 113
    remainder       = 114

    equals          = 115

    same            = 116
    different       = 117

    less            = 118
    greater         = 119
    less_same       = 120
    greater_same    = 121

    left_paren    = 122
    right_paren    = 123



class Identifier(enum.Enum):
    print_tok      = "print"
    

operators_ = {
    "+": Operators.add,
    "-": Operators.subtract,
    "*": Operators.multiply,
    "/": Operators.divide,
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