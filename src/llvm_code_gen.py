from llvmlite import ir, binding
from const import TokType, Operators
from node import Node
import ctypes
binding.initialize()
binding.initialize_native_target()
binding.initialize_native_asmprinter()

class LLVMCodeGen:
    def __init__(self):
        self.module = ir.Module(name="laetus_module")
        self.builder = None
        self.func = None
        
        # Symbol Table: tên biến -> instruction (con trỏ bộ nhớ)
        self.variables = {}
        
        # --- KHAI BÁO HÀM PRINTF (từ libc) ---
        # i32 printf(i8*, ...)
        voidptr_ty = ir.IntType(8).as_pointer()
        printf_ty = ir.FunctionType(ir.IntType(32), [voidptr_ty], var_arg=True)
        self.printf = ir.Function(self.module, printf_ty, name="printf")

        # --- ĐỊNH DẠNG CHUỖI ---
        # %lld: Long Long Decimal (cho Int64)
        # %.8g: General format (tối đa 8 chữ số có nghĩa, tự bỏ số 0 thừa)
        
        # Định dạng không xuống dòng
        self.fmt_int     = self._global_string("%lld")    
        self.fmt_float   = self._global_string("%.8g")    
        self.fmt_str     = self._global_string("%s")
        
        # Định dạng có xuống dòng (cho println)
        self.fmt_int_nl   = self._global_string("%lld\n")
        self.fmt_float_nl = self._global_string("%.8g\n")
        self.fmt_str_nl   = self._global_string("%s\n")

    def _global_string(self, value):
        """Tạo hằng số chuỗi toàn cục để dùng trong printf"""
        name = "str_" + str(hash(value)).replace("-", "_")
        # Thêm null terminator \0 cho C string
        c_str_val = bytearray((value + '\0').encode('utf-8'))
        
        c_str = ir.Constant(ir.ArrayType(ir.IntType(8), len(c_str_val)), c_str_val)
        
        global_var = ir.GlobalVariable(self.module, c_str.type, name=name)
        global_var.linkage = 'internal'
        global_var.global_constant = True
        global_var.initializer = c_str
        return global_var

    def generate_ir(self, root_node: Node):
        """Hàm chính sinh mã"""
        # Tạo hàm main: i32 main()
        func_ty = ir.FunctionType(ir.IntType(32), [])
        self.func = ir.Function(self.module, func_ty, name="main")
        entry_block = self.func.append_basic_block(name="entry")
        self.builder = ir.IRBuilder(entry_block)

        # Duyệt qua các statement
        for child in root_node.children:
            self.visit(child)

        # return 0
        self.builder.ret(ir.Constant(ir.IntType(32), 0))
        return str(self.module)

    def visit(self, node: Node):
        if node is None: return None
        tok = node.data
        
        if tok.type == TokType.block:
            for child in node.children:
                self.visit(child)
            return

        elif tok.type == TokType.assignment:
            return self.visit_assignment(node)

        elif tok.type == TokType.identifier:
            if tok.func in ["print", "println"]:
                return self.visit_print(node, is_newline=(tok.func == "println"))
            elif tok.func == "if":
                return self.visit_if(node)
            elif tok.func == "while":
                return self.visit_while(node)
            elif tok.func == "for":
                return self.visit_for(node)
            else:
                return self.visit_variable_load(node)
        
        elif tok.type == TokType.operator:
            return self.visit_binary_op(node)

        elif tok.type == TokType.number:
            return self.visit_number(tok)
        
        elif tok.type == TokType.string:
            glob_str = self._global_string(tok.string_value)
            return self.builder.bitcast(glob_str, ir.IntType(8).as_pointer())
        
        elif tok.type in [TokType.value, TokType.condition, TokType.root]:
            if len(node.children) > 0:
                return self.visit(node.children[0])

        return None

    def visit_number(self, tok):
        # I64 cho số nguyên, Double cho số thực
        if tok.is_float:
            return ir.Constant(ir.DoubleType(), float(tok.float_value))
        else:
            val = int(tok.int_value if tok.int_value is not None else tok.float_value)
            return ir.Constant(ir.IntType(64), val)

    def visit_assignment(self, node: Node):
        var_name = node.children[0].data.func
        val_node = node.children[1]
        
        actual_val_node = val_node.children[0] if val_node.children else None
        value = self.visit(actual_val_node)
        
        if value is None: return

        if var_name not in self.variables:
            # Cấp phát vùng nhớ stack
            # Lưu ý: Cần xác định kiểu dựa trên giá trị gán vào
            typ = value.type
            ptr = self.builder.alloca(typ, name=var_name)
            self.variables[var_name] = ptr
        
        ptr = self.variables[var_name]
        
        # Nếu biến đã tồn tại nhưng kiểu mới khác kiểu cũ (ví dụ: a=1, sau đó a=1.5)
        # LLVM IR tĩnh không hỗ trợ đổi kiểu biến dynamic dễ dàng.
        # Ở đây ta giả định kiểu biến không đổi hoặc ta cast giá trị về kiểu biến.
        if value.type != ptr.type.pointee:
             # Logic đơn giản: Nếu biến là float, cast giá trị int sang float
             if ptr.type.pointee == ir.DoubleType() and value.type == ir.IntType(64):
                 value = self.builder.sitofp(value, ir.DoubleType())
             # Nếu biến là int, cast giá trị float sang int (mất dữ liệu)
             elif ptr.type.pointee == ir.IntType(64) and value.type == ir.DoubleType():
                 value = self.builder.fptosi(value, ir.IntType(64))

        self.builder.store(value, ptr)
        return value

    def visit_variable_load(self, node: Node):
        var_name = node.data.func
        if var_name in self.variables:
            ptr = self.variables[var_name]
            return self.builder.load(ptr, name=var_name)
        else:
            # Mặc định trả về 0 (Int64) nếu chưa khai báo
            return ir.Constant(ir.IntType(64), 0)

    def visit_print(self, node: Node, is_newline=False):
        for child in node.children:
            val = self.visit(child)
            
            fmt = None
            # Chọn format string dựa trên kiểu dữ liệu của val
            if val.type == ir.IntType(64):  # I64
                fmt = self.fmt_int_nl if is_newline else self.fmt_int
            elif val.type == ir.DoubleType(): # Double
                fmt = self.fmt_float_nl if is_newline else self.fmt_float
            elif val.type == ir.IntType(8).as_pointer(): # String
                fmt = self.fmt_str_nl if is_newline else self.fmt_str
            
            if fmt:
                void_ptr = self.builder.bitcast(fmt, ir.IntType(8).as_pointer())
                self.builder.call(self.printf, [void_ptr, val])

    def visit_binary_op(self, node: Node):
        lhs = self.visit(node.children[0])
        rhs = self.visit(node.children[1])
        op = node.data.operator

        # Tự động cast Int64 -> Double nếu phép toán hỗn hợp
        is_float_op = (lhs.type == ir.DoubleType() or rhs.type == ir.DoubleType())
        
        if is_float_op:
            if lhs.type == ir.IntType(64): 
                lhs = self.builder.sitofp(lhs, ir.DoubleType())
            if rhs.type == ir.IntType(64): 
                rhs = self.builder.sitofp(rhs, ir.DoubleType())

        # --- Tính toán ---
        if op == Operators.add:
            return self.builder.fadd(lhs, rhs) if is_float_op else self.builder.add(lhs, rhs)
        elif op == Operators.subtract:
            return self.builder.fsub(lhs, rhs) if is_float_op else self.builder.sub(lhs, rhs)
        elif op == Operators.multiply:
            return self.builder.fmul(lhs, rhs) if is_float_op else self.builder.mul(lhs, rhs)
        elif op == Operators.divide:
            # Chia số thực hoặc chia lấy phần nguyên
            if is_float_op:
                return self.builder.fdiv(lhs, rhs)
            else:
                return self.builder.sdiv(lhs, rhs)
        
        # --- So sánh ---
        pred = ""
        if op == Operators.equals or op == Operators.same: pred = '=='
        elif op == Operators.different: pred = '!='
        elif op == Operators.less: pred = '<'
        elif op == Operators.less_same: pred = '<='
        elif op == Operators.greater: pred = '>'
        elif op == Operators.greater_same: pred = '>='

        if pred:
            res = None
            if is_float_op:
                res = self.builder.fcmp_ordered(pred, lhs, rhs)
            else:
                res = self.builder.icmp_signed(pred, lhs, rhs)
            # Kết quả so sánh là 1 bit (i1), mở rộng ra Int64 để dùng tiếp
            return self.builder.zext(res, ir.IntType(64))
        
        return ir.Constant(ir.IntType(64), 0)

    # ================= LOGIC ĐIỀU KHIỂN =================

    def visit_if(self, node: Node):
        cond_val = self.visit(node.children[0]) # Condition
        # Convert sang bool (i1)
        if cond_val.type != ir.IntType(1):
            cond_val = self.builder.icmp_signed('!=', cond_val, ir.Constant(cond_val.type, 0))

        then_block = self.func.append_basic_block("if.then")
        merge_block = self.func.append_basic_block("if.end")
        
        # Kiểm tra xem có Else block không
        else_node = node.children[2] if len(node.children) > 2 else None
        else_block = self.func.append_basic_block("if.else") if else_node else None

        if else_block:
            self.builder.cbranch(cond_val, then_block, else_block)
        else:
            self.builder.cbranch(cond_val, then_block, merge_block)

        # -- Then --
        self.builder.position_at_end(then_block)
        self.visit(node.children[1]) # Block Then
        if not self.builder.block.is_terminated:
            self.builder.branch(merge_block)

        # -- Else --
        if else_block:
            self.builder.position_at_end(else_block)
            self.visit(else_node)
            if not self.builder.block.is_terminated:
                self.builder.branch(merge_block)

        self.builder.position_at_end(merge_block)

    def visit_while(self, node: Node):
        cond_expr_node = node.children[0].children[0]
        body_node = node.children[1]

        cond_block = self.func.append_basic_block("while.cond")
        body_block = self.func.append_basic_block("while.body")
        end_block = self.func.append_basic_block("while.end")

        self.builder.branch(cond_block)

        # -- Check Condition --
        self.builder.position_at_end(cond_block)
        cond_val = self.visit(cond_expr_node)
        if cond_val.type != ir.IntType(1):
             cond_val = self.builder.icmp_signed('!=', cond_val, ir.Constant(cond_val.type, 0))
        self.builder.cbranch(cond_val, body_block, end_block)

        # -- Body --
        self.builder.position_at_end(body_block)
        self.visit(body_node)
        self.builder.branch(cond_block)

        self.builder.position_at_end(end_block)

    def visit_for(self, node: Node):
        param_node = node.children[0] # Chứa init, end, step
        body_node = node.children[1]

        # 1. Init (ví dụ: i = 0)
        init_node = param_node.children[0]
        self.visit(init_node)
        
        # Lấy tên biến loop từ lệnh gán
        loop_var_name = init_node.children[0].data.func

        cond_block = self.func.append_basic_block("for.cond")
        body_block = self.func.append_basic_block("for.body")
        end_block = self.func.append_basic_block("for.end")

        self.builder.branch(cond_block)

        # -- Condition: i < end --
        self.builder.position_at_end(cond_block)
        curr_i = self.builder.load(self.variables[loop_var_name])
        end_val = self.visit(param_node.children[1])
        
        # Nếu end_val là int mà i là float (hoặc ngược lại), cần cast để so sánh
        if curr_i.type != end_val.type:
             if curr_i.type == ir.DoubleType(): end_val = self.builder.sitofp(end_val, ir.DoubleType())
             else: end_val = self.builder.fptosi(end_val, ir.IntType(64))

        # So sánh (dùng signed less than cho int, ordered less than cho float)
        if curr_i.type == ir.DoubleType():
            cmp = self.builder.fcmp_ordered('<', curr_i, end_val)
        else:
            cmp = self.builder.icmp_signed('<', curr_i, end_val)
            
        self.builder.cbranch(cmp, body_block, end_block)

        # -- Body --
        self.builder.position_at_end(body_block)
        self.visit(body_node)

        # -- Step: i = i + step --
        curr_i = self.builder.load(self.variables[loop_var_name])
        step_val = ir.Constant(curr_i.type, 1) # Mặc định step = 1 (cùng kiểu với i)
        
        # Nếu có step arg
        if len(param_node.children) > 2:
            raw_step = self.visit(param_node.children[2])
            # Cast step về kiểu của i
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
            
        self.builder.store(new_i, self.variables[loop_var_name])
        self.builder.branch(cond_block)

        self.builder.position_at_end(end_block)

def emit_llvm(ast):
    codegen = LLVMCodeGen()
    return codegen.generate_ir(ast)

def run_jit(llvm_ir):
    """Hàm thực thi mã IR trực tiếp bằng JIT"""
    # 1. Parse chuỗi IR
    llvm_module = binding.parse_assembly(llvm_ir)
    llvm_module.verify()

    # 2. Tạo máy đích (Target Machine)
    target = binding.Target.from_default_triple()
    target_machine = target.create_target_machine()

    # 3. Tạo Execution Engine
    # Sử dụng MCJIT để hỗ trợ các kiến trúc hiện đại
    with binding.create_mcjit_compiler(llvm_module, target_machine) as ee:
        ee.finalize_object()
        
        # Tìm địa chỉ hàm main
        func_ptr = ee.get_function_address("main")
        
        # Chuyển địa chỉ sang hàm Python có thể gọi thông qua ctypes
        # main không nhận tham số và trả về int 32-bit
        main_func = ctypes.CFUNCTYPE(ctypes.c_int32)(func_ptr)
        
        result = main_func()
        return result