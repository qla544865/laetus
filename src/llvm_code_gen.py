from llvmlite import ir, binding
from const import *
from tokens import *

binding.initialize()
binding.initialize_native_target()
binding.initialize_native_asmprinter()

class LLVMGenerator:
    def __init__(self):
        self.module = ir.Module(name="main")
        self.module.triple = binding.get_default_triple()
        self.voidptr_ty = ir.IntType(8).as_pointer()
        self.double_ty = ir.DoubleType()
        self.int_ty = ir.IntType(32)
        self.var_struct = ir.LiteralStructType([self.int_ty, self.double_ty, self.voidptr_ty])
        self.functions, self.symbol_table, self.string_cache = {}, {}, {}
        
        printf_ty = ir.FunctionType(self.int_ty, [self.voidptr_ty], var_arg=True)
        self.printf = ir.Function(self.module, printf_ty, name="printf")
        
        func_ty = ir.FunctionType(self.int_ty, [])
        self.main_func = ir.Function(self.module, func_ty, name="main")
        self.builder = ir.IRBuilder(self.main_func.append_basic_block(name="entry"))

    def _get_str(self, s):
        if s not in self.string_cache:
            fmt = s.replace("\\n", "\n") + "\0"
            c = ir.Constant(ir.ArrayType(ir.IntType(8), len(fmt)), bytearray(fmt.encode("utf8")))
            v = ir.GlobalVariable(self.module, c.type, name=f"s{len(self.string_cache)}")
            v.linkage, v.global_constant, v.initializer = 'internal', True, c
            self.string_cache[s] = v.bitcast(self.voidptr_ty)
        return self.string_cache[s]

    def _box(self, val, is_str=False):
        ptr = self.builder.alloca(self.var_struct)
        self.builder.store(ir.Constant(self.int_ty, 1 if is_str else 0), self.builder.gep(ptr, [ir.Constant(self.int_ty, 0), ir.Constant(self.int_ty, 0)]))
        if is_str:
            self.builder.store(self._get_str(val), self.builder.gep(ptr, [ir.Constant(self.int_ty, 0), ir.Constant(self.int_ty, 2)]))
        else:
            v = val if isinstance(val, ir.Value) else ir.Constant(self.double_ty, float(val))
            self.builder.store(v, self.builder.gep(ptr, [ir.Constant(self.int_ty, 0), ir.Constant(self.int_ty, 1)]))
        return ptr

    def generate(self, root):
        self._reg_f(root)
        for c in root.children: self._visit(c)
        if not self.builder.block.is_terminated: self.builder.ret(ir.Constant(self.int_ty, 0))
        return self.module

    def _reg_f(self, node):
        if node.data.type == TokType.def_function:
            name = node.children[0].data.func
            ps = node.children[1].children
            self.functions[name] = ir.Function(self.module, ir.FunctionType(self.var_struct, [self.var_struct]*len(ps)), name=name)
        for c in node.children: self._reg_f(c)

    def _visit(self, node):
        if self.builder.block.is_terminated: return
        tok = node.data
        if tok.type == TokType.def_function:
            name = node.children[0].data.func
            f_obj = self.functions[name]
            old_b, old_s = self.builder, self.symbol_table.copy()
            self.builder = ir.IRBuilder(f_obj.append_basic_block(name="entry"))
            self.symbol_table = {}
            for i, arg in enumerate(f_obj.args):
                p_name = node.children[1].children[i].data.func
                ptr = self.builder.alloca(self.var_struct, name=p_name)
                self.builder.store(arg, ptr); self.symbol_table[p_name] = ptr
            for i in range(2, len(node.children)): self._visit(node.children[i])
            if not self.builder.block.is_terminated: self.builder.ret(self.builder.load(self._box(0.0)))
            self.builder, self.symbol_table = old_b, old_s
        elif tok.func == "if":
            cond = self.builder.load(self.builder.gep(self._expr(node.children[0].children[0]), [ir.Constant(self.int_ty, 0), ir.Constant(self.int_ty, 1)]))
            with self.builder.if_then(self.builder.fcmp_ordered("!=", cond, ir.Constant(self.double_ty, 0.0))):
                for i in range(1, len(node.children)): self._visit(node.children[i])
        elif tok.func == "return":
            v = self._expr(node.children[0])
            if self.builder.function.name == "main": self.builder.ret(ir.Constant(self.int_ty, 0))
            else: self.builder.ret(self.builder.load(v))
        elif tok.func in ["print", "println"]:
            is_ln = tok.func == "println"
            for arg in node.children:
                p = self._expr(arg)
                t = self.builder.load(self.builder.gep(p, [ir.Constant(self.int_ty, 0), ir.Constant(self.int_ty, 0)]))
                with self.builder.if_else(self.builder.icmp_signed("==", t, ir.Constant(self.int_ty, 1))) as (t_case, f_case):
                    with t_case:
                        v = self.builder.load(self.builder.gep(p, [ir.Constant(self.int_ty, 0), ir.Constant(self.int_ty, 2)]))
                        self.builder.call(self.printf, [self._get_str("%s\n" if is_ln else "%s"), v])
                    with f_case:
                        v = self.builder.load(self.builder.gep(p, [ir.Constant(self.int_ty, 0), ir.Constant(self.int_ty, 1)]))
                        self.builder.call(self.printf, [self._get_str("%.15g\n" if is_ln else "%.15g"), v])
        elif tok.type == TokType.assignment:
            name = node.children[0].data.func
            v = self._expr(node.children[0].children[0])
            if name not in self.symbol_table: self.symbol_table[name] = self.builder.alloca(self.var_struct, name=name)
            self.builder.store(self.builder.load(v), self.symbol_table[name])
        elif tok.type == TokType.function: self._expr(node)

    def _expr(self, node):
        t = node.data
        if t.type == TokType.number: return self._box(t.float_value if t.is_float else t.int_value)
        if t.type == TokType.string: return self._box(t.string_value, True)
        if t.type == TokType.identifier: return self.symbol_table.get(t.func, self._box(0.0))
        if t.type == TokType.function:
            f = self.functions[node.children[0].data.func]
            args = [self.builder.load(self._expr(p)) for p in node.children[1].children]
            res = self.builder.alloca(self.var_struct)
            self.builder.store(self.builder.call(f, args), res)
            return res
        if t.type == TokType.operator:
            l = self.builder.load(self.builder.gep(self._expr(node.children[0]), [ir.Constant(self.int_ty, 0), ir.Constant(self.int_ty, 1)]))
            r = self.builder.load(self.builder.gep(self._expr(node.children[1]), [ir.Constant(self.int_ty, 0), ir.Constant(self.int_ty, 1)]))
            op = t.operator
            if op == Operators.add: res = self.builder.fadd(l, r)
            elif op == Operators.subtract: res = self.builder.fsub(l, r)
            elif op == Operators.multiply: res = self.builder.fmul(l, r)
            elif op == Operators.divide: res = self.builder.fdiv(l, r)
            elif op == Operators.less: res = self.builder.uitofp(self.builder.fcmp_ordered("<", l, r), self.double_ty)
            else: res = ir.Constant(self.double_ty, 0.0)
            return self._box(res)
        return self._box(0.0)

def emit_llvm(ast): return LLVMGenerator().generate(ast)