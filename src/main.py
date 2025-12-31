import subprocess
import sys
from lexer import lexer
from parse import *
# from llvm_code_gen import emit_llvm, run_jit

def get_argv():
    flags = {}
    input_file = ""


    i = 0
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg[0] == "-":
            flags[arg] = {}
            if (arg == "-o"):
                flags[arg]["inp"] = sys.argv[i+1]
                i+=1

        else:
            input_file = arg
        i+=1

    input_file = "test\\main.txt"
    if input_file == "":
        print("ERROR:","No input file.")
    return [input_file, flags]


def laetus():

    file_name,flags = get_argv()

    file_content = ""

    try: 
        file_content = open(file_name, "r").read()
    except FileNotFoundError:
        print("Error:","File not found")
        return 1
    

    file_content += "\n"

    tokens = lexer(file_content)

    if "-dev" in flags:
        print("START_TOK")

        for token in tokens:
            print(token)

        print("END_TOK")

        if "-noparse" in flags:
            return

    ast = parse(tokens)

    print_tree(ast)
    

    # if "-dev" in flags:
    #     print_tree(ast)

    # ####### JIT #######

    # llvm_module = emit_llvm(ast.children)
    # run_llvm(llvm_module)
    

    # print(module)
    # run_jit(module)


    # ###### build exe #######

    # if not ("-nocompile" in flags):
    #     module = emit_llvm(ast)

    #     with open("temp.ll","w",encoding="utf-8") as f:
    #         f.write(str(module))


    #     output_file = "a.exe"

    #     if ("-o" in flags):
    #         output_file = flags["-o"]["inp"]

    #     subprocess.check_call([
    #         "clang",
    #         "temp.ll",
    #         "-O2",
    #         "-o",
    #         output_file
    #     ])
    # if "-jit" in flags:
    #     module = emit_llvm(ast)
    #     run_jit(module)



if __name__ == "__main__":
    laetus()

