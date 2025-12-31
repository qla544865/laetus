from llvmlite import ir, binding
import subprocess
import os

# ============================
# 1. Tạo LLVM IR (Hello World)
# ============================
binding.initialize()
binding.initialize_native_target()
binding.initialize_native_asmprinter()

module = ir.Module("hello")
module.triple = binding.get_default_triple()

i8 = ir.IntType(8)
i8ptr = i8.as_pointer()

# khai báo printf
printf_ty = ir.FunctionType(ir.IntType(32), [i8ptr], var_arg=True)
printf = ir.Function(module, printf_ty, name="printf")

# main()
fn_ty = ir.FunctionType(ir.IntType(32), [])
main = ir.Function(module, fn_ty, name="main")
block = main.append_basic_block("entry")
builder = ir.IRBuilder(block)

msg = "Hello World!\n"
arr_ty = ir.ArrayType(i8, len(msg) + 1)
g = ir.GlobalVariable(module, arr_ty, "msg")
g.initializer = ir.Constant(arr_ty, bytearray(msg.encode() + b"\x00"))
g.global_constant = True

ptr = builder.bitcast(g, i8ptr)
builder.call(printf, [ptr])
builder.ret(ir.Constant(ir.IntType(32), 0))

llvm_ir = str(module)

# ============================
# 2. Convert IR => object file
# ============================

target = binding.Target.from_default_triple()
target_machine = target.create_target_machine(opt=2)

llvm_mod = binding.parse_assembly(llvm_ir)
llvm_mod.verify()

obj_filename = "hello.obj"
obj = target_machine.emit_object(llvm_mod)

with open(obj_filename, "wb") as f:
    f.write(obj)

print("Created:", obj_filename)

# ============================
# 3. Link .obj => .exe bằng gcc
# ============================

exe_file = "hello.exe"

cmd = [
    "gcc",
    "hello.obj",
    "-o" + exe_file,
]

print("Linking...")
subprocess.check_call(cmd)

print("DONE: created", exe_file)
