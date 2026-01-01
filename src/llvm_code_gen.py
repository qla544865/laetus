from llvmlite import ir, binding
from const import TokType, Operators
from node import Node
import ctypes

# Khởi tạo môi trường JIT
binding.initialize()
binding.initialize_native_target()
binding.initialize_native_asmprinter()

class LLVMCodeGen:
    def __init__(self):
        self.module = ir.Module(name="laetus_module")
        self.builder = None
        self.func = None  # Hàm hiện tại đang generate code
        
        # Quản lý Scope: List[Dict[name, pointer]]
        # scopes[0] là global, scopes[-1] là local hiện tại
        self.scopes = [{}] 
        
        # --- Khai báo printf (C library) ---
        voidptr_ty = ir.IntType(8).as_pointer()
        printf_ty = ir.FunctionType(ir.IntType(32), [voidptr_ty], var_arg=True)
        self.printf = ir.Function(self.module, printf_ty, name="printf")

        # --- Các định dạng chuỗi ---
        self.fmt_int = self._global_string("%lld")
        self.fmt_float = self._global_string("%.8g")
        self.fmt_str = self._global_string("%s")
        self.fmt_int_nl = self._global_string("%lld\n")
        self.fmt_float_nl = self._global_string("%.8g\n")
        self.fmt_str_nl = self._global_string("%s\n")

    def _global_string(self, value):
        """Tạo chuỗi tĩnh global"""
        name = "str_" + str(hash(value)).replace("-", "_")
        c_str_val = bytearray((value + '\0').encode('utf-8'))
        c_str = ir.Constant(ir.ArrayType(ir.IntType(8), len(c_str_val)), c_str_val)
        global_var = ir.GlobalVariable(self.module, c_str.type, name=name)
        global_var.linkage = 'internal'
        global_var.global_constant = True
        global_var.initializer = c_str
        return global_var

    def _get_var_ptr(self, name):
        """Tìm biến trong scope từ trong ra ngoài"""
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def _create_var(self, name, typ):
        """Tạo biến mới trong scope hiện tại"""
        ptr = self.builder.alloca(typ, name=name)
        self.scopes[-1][name] = ptr
        return ptr

    def generate_ir(self, root_node: Node):
        # Tạo hàm main mặc định
        func_ty = ir.FunctionType(ir.IntType(32), [])
        self.func = ir.Function(self.module, func_ty, name="main")
        entry_block = self.func.append_basic_block(name="entry")
        self.builder = ir.IRBuilder(entry_block)

        # Vào scope của main
        self.scopes.append({}) 

        for child in root_node.children:
            self.visit(child)

        # Return 0 mặc định cho main nếu chưa return
        if not self.builder.block.is_terminated:
            self.builder.ret(ir.Constant(ir.IntType(32), 0))
        
        self.scopes.pop() # Thoát scope main
        return str(self.module)

    def visit(self, node: Node):
        if node is None: return None
        tok = node.data

        # --- CẤU TRÚC ---
        if tok.type == TokType.block:
            # Block chỉ là danh sách lệnh, không tạo scope mới ở đây 
            # (Scope được tạo ở If/While/Func/For)
            for child in node.children: self.visit(child)
            return

        elif tok.type == TokType.root:
            for child in node.children: self.visit(child)

        # --- HÀM & RETURN ---
        elif tok.type == TokType.def_function:
            return self.visit_def_function(node)
        
        elif tok.type == TokType.function: # Call Function
            return self.visit_call_function(node)

        elif tok.type == TokType.identifier and tok.func == "return":
            return self.visit_return(node)

        # --- CÁC LỆNH CƠ BẢN ---
        elif tok.type == TokType.assignment:
            return self.visit_assignment(node)

        elif tok.type == TokType.identifier:
            if tok.func in ["print", "println"]:
                return self.visit_print(node, is_newline=(tok.func == "println"))
            elif tok.func == "if": return self.visit_if(node)
            elif tok.func == "while": return self.visit_while(node)
            elif tok.func == "for": return self.visit_for(node)
            else: return self.visit_variable_load(node)
        
        elif tok.type == TokType.operator:
            return self.visit_binary_op(node)

        elif tok.type == TokType.number:
            if tok.is_float: return ir.Constant(ir.DoubleType(), float(tok.float_value))
            return ir.Constant(ir.IntType(64), int(tok.int_value if tok.int_value is not None else tok.float_value))
        
        elif tok.type == TokType.string:
            glob_str = self._global_string(tok.string_value)
            return self.builder.bitcast(glob_str, ir.IntType(8).as_pointer())

        elif tok.type in [TokType.value, TokType.condition, TokType.parameter]:
            # Đi xuống con (thường dùng cho node wrapper)
            if node.children: return self.visit(node.children[0])

        return None

    # ================= FUNCTION HANDLING =================

    def visit_def_function(self, node: Node):
        """
        Structure: DefFunc -> [NameNode, ParameterToken, BlockToken]
        """
        # 1. Lấy tên hàm
        func_name = node.children[0].data.func
        
        # 2. Lấy danh sách tham số
        # node.children[1] là ParameterToken, children của nó là các node ID (do parser build_expression_tree trả về)
        param_node = node.children[1]
        arg_names = []
        if param_node.children:
            for p_child in param_node.children:
                # p_child là Node chứa Token identifier
                arg_names.append(p_child.data.func)
        
        # 3. Định nghĩa kiểu hàm
        # Mặc định: input là Int64, return Int64 (do ngôn ngữ chưa định kiểu tường minh)
        arg_types = [ir.IntType(64)] * len(arg_names)
        func_type = ir.FunctionType(ir.IntType(64), arg_types)
        
        # Tạo Function trong Module
        new_func = ir.Function(self.module, func_type, name=func_name)
        
        # 4. Lưu builder hiện tại để khôi phục sau khi define xong hàm
        previous_builder = self.builder
        previous_func = self.func
        
        # 5. Tạo Entry Block cho hàm mới
        self.func = new_func
        entry_block = new_func.append_basic_block(name="entry")
        self.builder = ir.IRBuilder(entry_block)
        
        # Tạo scope mới cho hàm
        self.scopes.append({})

        # 6. Map tham số vào biến local (alloca)
        for i, arg_val in enumerate(new_func.args):
            arg_val.name = arg_names[i]
            # Cấp phát bộ nhớ cho tham số
            ptr = self.builder.alloca(ir.IntType(64), name=arg_names[i])
            self.builder.store(arg_val, ptr)
            # Lưu vào scope
            self.scopes[-1][arg_names[i]] = ptr

        # 7. Visit Body (BlockToken)
        body_node = node.children[2]
        self.visit(body_node)

        # 8. Đảm bảo hàm có return (nếu user quên return thì return 0)
        if not self.builder.block.is_terminated:
            self.builder.ret(ir.Constant(ir.IntType(64), 0))

        # 9. Khôi phục context cũ (quay về main hoặc hàm cha)
        self.scopes.pop()
        self.builder = previous_builder
        self.func = previous_func

    def visit_call_function(self, node: Node):
        """
        Structure: FunctionToken -> [NameNode, ParameterToken]
        """
        func_name = node.children[0].data.func
        
        # Tìm hàm trong module
        if func_name not in self.module.globals:
            print(f"Error: Function '{func_name}' not defined.")
            return ir.Constant(ir.IntType(64), 0)
        
        func_obj = self.module.globals[func_name]
        
        # Xử lý tham số truyền vào
        param_node = node.children[1]
        args = []
        if param_node.children:
            for p_child in param_node.children:
                val = self.visit(p_child)
                # Cast về Int64 nếu cần (vì định nghĩa hàm ta đang để default Int64)
                if val.type == ir.DoubleType():
                    val = self.builder.fptosi(val, ir.IntType(64))
                args.append(val)
        
        # Gọi hàm
        return self.builder.call(func_obj, args)

    def visit_return(self, node: Node):
        # Parse return giống print: children chứa expression
        if node.children:
            val = self.visit(node.children[0])
            # Cast về Int64 nếu hàm yêu cầu Int64 (giả định)
            if val.type == ir.DoubleType():
                val = self.builder.fptosi(val, ir.IntType(64))
            self.builder.ret(val)
        else:
            self.builder.ret(ir.Constant(ir.IntType(64), 0))
        return

    # ================= VARIABLE & LOGIC =================

    def visit_assignment(self, node: Node):
        var_name = node.children[0].data.func
        val_node = node.children[1]
        
        # Lấy giá trị bên phải
        actual_val_node = val_node.children[0] if val_node.children else None
        value = self.visit(actual_val_node)
        if value is None: return

        # Kiểm tra biến đã có trong scope chưa
        ptr = self._get_var_ptr(var_name)
        
        if not ptr:
            # Nếu chưa có, tạo mới trong scope hiện tại
            # Ưu tiên Int64 nếu int, Double nếu float
            typ = value.type
            ptr = self._create_var(var_name, typ)
        else:
            # Nếu đã có, kiểm tra type cast
            if ptr.type.pointee != value.type:
                # Cast đơn giản
                if ptr.type.pointee == ir.DoubleType() and value.type == ir.IntType(64):
                    value = self.builder.sitofp(value, ir.DoubleType())
                elif ptr.type.pointee == ir.IntType(64) and value.type == ir.DoubleType():
                    value = self.builder.fptosi(value, ir.IntType(64))

        self.builder.store(value, ptr)
        return value

    def visit_variable_load(self, node: Node):
        var_name = node.data.func
        ptr = self._get_var_ptr(var_name)
        if ptr:
            return self.builder.load(ptr, name=var_name)
        # print(f"Warning: Variable '{var_name}' not found.")
        return ir.Constant(ir.IntType(64), 0)

    def visit_print(self, node: Node, is_newline=False):
        for child in node.children:
            val = self.visit(child)
            fmt = None
            if val.type == ir.IntType(64): fmt = self.fmt_int_nl if is_newline else self.fmt_int
            elif val.type == ir.DoubleType(): fmt = self.fmt_float_nl if is_newline else self.fmt_float
            elif val.type == ir.IntType(8).as_pointer(): fmt = self.fmt_str_nl if is_newline else self.fmt_str
            
            if fmt:
                void_ptr = self.builder.bitcast(fmt, ir.IntType(8).as_pointer())
                self.builder.call(self.printf, [void_ptr, val])

    def visit_binary_op(self, node: Node):
        lhs = self.visit(node.children[0])
        rhs = self.visit(node.children[1])
        op = node.data.operator
        
        is_float = (lhs.type == ir.DoubleType() or rhs.type == ir.DoubleType())
        
        if is_float:
            if lhs.type == ir.IntType(64): lhs = self.builder.sitofp(lhs, ir.DoubleType())
            if rhs.type == ir.IntType(64): rhs = self.builder.sitofp(rhs, ir.DoubleType())

        if op == Operators.add: return self.builder.fadd(lhs, rhs) if is_float else self.builder.add(lhs, rhs)
        if op == Operators.subtract: return self.builder.fsub(lhs, rhs) if is_float else self.builder.sub(lhs, rhs)
        if op == Operators.multiply: return self.builder.fmul(lhs, rhs) if is_float else self.builder.mul(lhs, rhs)
        if op == Operators.divide: return self.builder.fdiv(lhs, rhs) if is_float else self.builder.sdiv(lhs, rhs)
        
        # So sánh
        preds = {Operators.equals: '==', Operators.same: '==', Operators.different: '!=', 
                 Operators.less: '<', Operators.less_same: '<=', Operators.greater: '>', Operators.greater_same: '>='}
        
        if op in preds:
            if is_float:
                res = self.builder.fcmp_ordered(preds[op], lhs, rhs)
            else:
                res = self.builder.icmp_signed(preds[op], lhs, rhs)
            return self.builder.zext(res, ir.IntType(64))
            
        return ir.Constant(ir.IntType(64), 0)

    # ================= CONTROL FLOW =================

    def visit_if(self, node: Node):
        cond_val = self.visit(node.children[0])
        if cond_val.type != ir.IntType(1):
            cond_val = self.builder.icmp_signed('!=', cond_val, ir.Constant(cond_val.type, 0))
        
        then_block = self.func.append_basic_block("if.then")
        merge_block = self.func.append_basic_block("if.end")
        else_node = node.children[2] if len(node.children) > 2 else None
        else_block = self.func.append_basic_block("if.else") if else_node else None

        if else_block: self.builder.cbranch(cond_val, then_block, else_block)
        else: self.builder.cbranch(cond_val, then_block, merge_block)

        # Then
        self.builder.position_at_end(then_block)
        self.visit(node.children[1])
        if not self.builder.block.is_terminated: self.builder.branch(merge_block)

        # Else
        if else_block:
            self.builder.position_at_end(else_block)
            self.visit(else_node)
            if not self.builder.block.is_terminated: self.builder.branch(merge_block)
            
        self.builder.position_at_end(merge_block)

    def visit_while(self, node: Node):
        cond_block = self.func.append_basic_block("while.cond")
        body_block = self.func.append_basic_block("while.body")
        end_block = self.func.append_basic_block("while.end")

        self.builder.branch(cond_block)
        
        self.builder.position_at_end(cond_block)
        cond_val = self.visit(node.children[0].children[0])
        if cond_val.type != ir.IntType(1):
            cond_val = self.builder.icmp_signed('!=', cond_val, ir.Constant(cond_val.type, 0))
        self.builder.cbranch(cond_val, body_block, end_block)

        self.builder.position_at_end(body_block)
        self.visit(node.children[1])
        if not self.builder.block.is_terminated: self.builder.branch(cond_block)

        self.builder.position_at_end(end_block)

    def visit_for(self, node: Node):
        # Node structure: For -> [Parameter(init, end, step), Block]
        param_node = node.children[0]
        
        # Init: i = start
        init_node = param_node.children[0] 
        self.visit(init_node)
        loop_var_name = init_node.children[0].data.func

        cond_block = self.func.append_basic_block("for.cond")
        body_block = self.func.append_basic_block("for.body")
        end_block = self.func.append_basic_block("for.end")

        self.builder.branch(cond_block)

        # Cond
        self.builder.position_at_end(cond_block)
        curr_i = self.builder.load(self._get_var_ptr(loop_var_name))
        end_val = self.visit(param_node.children[1])
        # Cast if needed
        if curr_i.type != end_val.type:
             if curr_i.type == ir.DoubleType(): end_val = self.builder.sitofp(end_val, ir.DoubleType())
             else: end_val = self.builder.fptosi(end_val, ir.IntType(64))

        if curr_i.type == ir.DoubleType():
            cmp = self.builder.fcmp_ordered('<', curr_i, end_val)
        else:
            cmp = self.builder.icmp_signed('<', curr_i, end_val)
        self.builder.cbranch(cmp, body_block, end_block)

        # Body
        self.builder.position_at_end(body_block)
        self.visit(node.children[1])
        
        # Increment
        curr_i = self.builder.load(self._get_var_ptr(loop_var_name))
        step_val = ir.Constant(curr_i.type, 1)
        if len(param_node.children) > 2:
            raw_step = self.visit(param_node.children[2])
            # Cast step
            if curr_i.type == ir.IntType(64) and raw_step.type == ir.DoubleType():
                step_val = self.builder.fptosi(raw_step, ir.IntType(64))
            elif curr_i.type == ir.DoubleType() and raw_step.type == ir.IntType(64):
                step_val = self.builder.sitofp(raw_step, ir.DoubleType())
            else:
                step_val = raw_step

        if curr_i.type == ir.DoubleType():
            new_i = self.builder.fadd(curr_i, step_val)
        else:
            new_i = self.builder.add(curr_i, step_val)
        
        self.builder.store(new_i, self._get_var_ptr(loop_var_name))
        if not self.builder.block.is_terminated: self.builder.branch(cond_block)

        self.builder.position_at_end(end_block)

# ================= PUBLIC API =================

def emit_llvm(ast):
    codegen = LLVMCodeGen()
    return codegen.generate_ir(ast)

def run_jit(llvm_ir):
    """JIT Runner với hỗ trợ gọi hàm main"""
    print("\n[JIT] Preparing execution...")
    
    # 1. Parse IR
    try:
        llvm_module = binding.parse_assembly(llvm_ir)
        llvm_module.verify()
    except Exception as e:
        print(f"[JIT Error] Parse Assembly failed: {e}")
        return

    # 2. Initialize Engine
    target = binding.Target.from_default_triple()
    target_machine = target.create_target_machine()
    
    # Dùng MCJIT để biên dịch
    with binding.create_mcjit_compiler(llvm_module, target_machine) as ee:
        ee.finalize_object()
        
        # 3. Tìm hàm 'main' và thực thi
        try:
            func_ptr = ee.get_function_address("main")
            # main trả về int32
            c_main = ctypes.CFUNCTYPE(ctypes.c_int32)(func_ptr)
            
            print("[JIT] Running code...\n" + "-"*20)
            res = c_main()
            print("-" * 20)
            print(f"[JIT] Program exited with code: {res}")
        except Exception as e:
            print(f"[JIT Error] Execution failed: {e}")