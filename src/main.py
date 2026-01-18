import subprocess
import sys
import os
from lexer import lexer
from parse import *
from llvm_code_gen import emit_llvm, run_jit

dev = False

def get_argv():
    flags = {}
    input_file = ""

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg[0] == "-":
            flags[arg] = {}
            if (arg == "-o"):
                flags[arg]["inp"] = sys.argv[i+1]
                i+=1
        else:
            if input_file == "":
                if arg != "src\\main.py":
                    input_file = arg
        i+=1

    if "-help" in flags:
        print(
"""Use laetus [input_file] [flag1] [flag2] ... 
-help               Display this information
-version            Display the version
-s                  Compile only; do not assemble or link
-c                  Compile and assemble, but do not link
-p                  Parse only; do not assemble or link or compile
-temp               Keep the temp files
-o <file>           Place the output into <file>""")
        return -1, flags
    if input_file == "":
        print("ERROR:","No input file.")
        return -1,flags
    return [input_file, flags]

def resource_path(relative_path):
    if dev:
        if hasattr(sys, "_MEIPASS"):
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.path.abspath("."), relative_path)
    else:
        return "clang"
clang_path = resource_path("clang/bin/clang.exe")

def laetus():
    file_name,flags = get_argv()

    if "-help" in flags:return

    if file_name == -1:
        return
    
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

    if "-dev" in flags:
        print_tree(ast)

    # ###### build exe #######

    if not ("-p" in flags):
        module = emit_llvm(ast)

        with open("temp.ll","w",encoding="utf-8") as f:
            f.write(str(module))


        output_file = "a.exe"
        build_cmd = [
            clang_path,
            "temp.ll",
            "-O2",
            "-o",
            output_file
        ]

        if ("-o" in flags):
            output_file = flags["-o"]["inp"]

        if os.name == 'nt': 
            build_cmd.append("-llegacy_stdio_definitions")
            build_cmd.append("-lmsvcrt")

        subprocess.check_call(build_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if not("-temp" in flags):
            os.remove("temp.ll")
    if "-jit" in flags:
        module = emit_llvm(ast)
        run_jit(module)



if __name__ == "__main__":
    laetus()

