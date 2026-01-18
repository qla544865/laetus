from llvmlite import ir, binding
from const import TokType, Operators
from node import Node
import ctypes

# Initialize JIT environment
binding.initialize()
binding.initialize_native_target()
binding.initialize_native_asmprinter()

# === CONSTANTS ===
TYPE_NONE = 0
TYPE_INT = 1
TYPE_FLOAT = 2
TYPE_STR = 3

class LLVMCodeGen:
    def __init__(self):
        self.module = ir.Module(name="laetus_module")
        self.builder = None
        self.func = None
        
        # Scopes: Dictionary mapping variable_name -> pointer_to_struct
        # scopes[-1] is the current local scope
        self.scopes = [] 

        # --- DYNAMIC VARIABLE STRUCT DEFINITION ---
        # Structure: { i8 type, i64 int_val, double float_val, i8* str_val }
        self.var_struct_ty = ir.LiteralStructType([
            ir.IntType(8),               # Type ID
            ir.IntType(64),              # Int Value
            ir.DoubleType(),             # Float Value
            ir.IntType(8).as_pointer()   # String Value
        ])
        
        # --- C LIBRARY FUNCTIONS ---
        voidptr_ty = ir.IntType(8).as_pointer()
        
        # printf(format, ...)
        printf_ty = ir.FunctionType(ir.IntType(32), [voidptr_ty], var_arg=True)
        self.printf = ir.Function(self.module, printf_ty, name="printf")

        # scanf(format, ...)
        scanf_ty = ir.FunctionType(ir.IntType(32), [voidptr_ty], var_arg=True)
        self.scanf = ir.Function(self.module, scanf_ty, name="scanf")
        
        # malloc(size)
        malloc_ty = ir.FunctionType(voidptr_ty, [ir.IntType(64)])
        self.malloc = ir.Function(self.module, malloc_ty, name="malloc")

        # fflush(stream)
        fflush_ty = ir.FunctionType(ir.IntType(32), [voidptr_ty])
        self.fflush = ir.Function(self.module, fflush_ty, name="fflush")

        # --- FORMAT STRINGS ---
        self.fmt_int = self._global_string("%lld")
        self.fmt_float = self._global_string("%.8g")
        self.fmt_str = self._global_string("%s")
        
        self.fmt_int_nl = self._global_string("%lld\n")
        self.fmt_float_nl = self._global_string("%.8g\n")
        self.fmt_str_nl = self._global_string("%s\n")
        
        self.scan_int = self._global_string("%lld") 
        self.scan_float = self._global_string("%lf")
        self.scan_str = self._global_string("%s")

        self.current_func_ret_ptr = None

    def _global_string(self, value):
        """Creates a global static string and returns i8*"""
        name = "str_" + str(hash(value)).replace("-", "_")
        if name in self.module.globals:
            var = self.module.globals[name]
        else:
            c_str_val = bytearray((value + '\0').encode('utf-8'))
            c_str_ty = ir.ArrayType(ir.IntType(8), len(c_str_val))
            c_str = ir.Constant(c_str_ty, c_str_val)
            
            var = ir.GlobalVariable(self.module, c_str.type, name=name)
            var.linkage = 'internal'
            var.global_constant = True
            var.initializer = c_str
            
        return var.bitcast(ir.IntType(8).as_pointer())

    def _get_var_ptr(self, name):
        """Finds variable pointer in scopes (Local -> Global)"""
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def _create_var(self, name):
        """Allocates a new Dynamic Variable Struct in the current scope"""
        ptr = self.builder.alloca(self.var_struct_ty, name=name)
        
        # Initialize Type = NONE (0)
        zero = ir.Constant(ir.IntType(8), 0)
        type_ptr = self.builder.gep(ptr, [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), 0)])
        self.builder.store(zero, type_ptr)
        
        self.scopes[-1][name] = ptr
        return ptr

    # ================= MAIN GENERATION =================

    def generate_ir(self, root_node: Node):
        # 1. First Pass: Define User Functions (Global Scope)
        # We process function definitions BEFORE creating main
        for child in root_node.children:
            if child.data.type == TokType.def_function:
                self.visit_def_function(child)

        # 2. Define Main Function
        func_ty = ir.FunctionType(ir.IntType(32), [])
        self.func = ir.Function(self.module, func_ty, name="main")
        entry_block = self.func.append_basic_block(name="entry")
        self.builder = ir.IRBuilder(entry_block)

        self.scopes.append({}) # Push Main Scope

        # 3. Second Pass: Process Main Body (Skip def_function nodes)
        for child in root_node.children:
            if child.data.type != TokType.def_function:
                self.visit(child)

        # 4. Terminate Main
        if not self.builder.block.is_terminated:
            self.builder.ret(ir.Constant(ir.IntType(32), 0))
        
        self.scopes.pop()
        return self.module

    def visit(self, node: Node):
        if node is None: return None
        tok = node.data

        # --- BLOCKS & ROOT ---
        if tok.type in [TokType.block, TokType.root]:
            for child in node.children: self.visit(child)
            return

        # --- FUNCTIONS ---
        elif tok.type == TokType.def_function:
            # Should have been handled in generate_ir pass 1, 
            # but if nested (not supported logic but safety check), ignore or handle.
            return self.visit_def_function(node)
        elif tok.type == TokType.function:
            return self.visit_call_func(node)
        if tok.type == TokType.return_stmt: # <--- Thêm xử lý Return
            return self.visit_return(node)

        # --- BUILT-INS ---
        elif tok.func == "input":
            return self.visit_input(node)
        elif tok.type == TokType.identifier and tok.func in ["print", "println"]:
            return self.visit_print(node, is_newline=(tok.func == "println"))
        
        # --- CONTROL FLOW ---
        elif tok.func == "if": return self.visit_if(node)
        elif tok.func == "while": return self.visit_while(node)
        elif tok.func == "for": return self.visit_for(node)

        # --- ASSIGNMENT & VARS ---
        elif tok.type == TokType.assignment:
            return self.visit_assignment(node)
        elif tok.type == TokType.identifier:
            return self.visit_variable_load(node)
        
        # --- OPERATORS & LITERALS ---
        elif tok.type == TokType.operator:
            return self.visit_binary_op(node)

        elif tok.type == TokType.number:
            if tok.is_float: 
                return (TYPE_FLOAT, ir.Constant(ir.DoubleType(), float(tok.float_value)))
            return (TYPE_INT, ir.Constant(ir.IntType(64), int(tok.int_value if tok.int_value is not None else tok.float_value)))
        
        elif tok.type == TokType.string:
            str_ptr = self._global_string(tok.string_value)
            return (TYPE_STR, str_ptr)

        elif tok.type in [TokType.value, TokType.condition, TokType.parameter]:
            if node.children: return self.visit(node.children[0])

        return None

    # ================= FUNCTION DEFINITION & CALL =================

    def visit_def_function(self, node: Node):
        func_name = node.children[0].data.func
        param_node = node.children[1]
        body_node = node.children[2]
        
        param_names = []
        for p in param_node.children:
            # Parse mới đảm bảo children của param là ID node
            param_names.append(p.data.func)

        # Signature mới: (RetPtr*, Arg1*, Arg2*...) -> Void
        # Tham số đầu tiên luôn là pointer để chứa giá trị return
        arg_types = [self.var_struct_ty.as_pointer()] * (len(param_names) + 1)
        
        # Return type là Void (vì trả về qua tham số đầu tiên)
        func_ty = ir.FunctionType(ir.VoidType(), arg_types)
        
        func = ir.Function(self.module, func_ty, name=func_name)
        
        # Save context
        old_builder = self.builder
        old_func = self.func
        old_ret_ptr = self.current_func_ret_ptr # Save old return ptr (cho nested func nếu có)
        
        entry = func.append_basic_block("entry")
        self.builder = ir.IRBuilder(entry)
        self.func = func
        
        # Setup Local Scope
        func_scope = {}
        
        # Arg 0 là Return Slot
        func.args[0].name = "ret_slot"
        self.current_func_ret_ptr = func.args[0] # Lưu lại để dùng trong visit_return
        
        # Các Arg còn lại là tham số hàm
        for i, arg in enumerate(func.args[1:]): 
            name = param_names[i]
            arg.name = f"arg_{name}"
            func_scope[name] = arg 
            
        self.scopes.append(func_scope)
        
        self.visit(body_node)
        
        # Đảm bảo block kết thúc
        if not self.builder.block.is_terminated:
            self.builder.ret_void()
            
        # Restore context
        self.scopes.pop()
        self.builder = old_builder
        self.func = old_func
        self.current_func_ret_ptr = old_ret_ptr

        

    def visit_return(self, node: Node):
        # 1. Tính toán giá trị trả về
        val_raw = None
        if len(node.children) > 0:
            val_raw = self.visit(node.children[0])
        
        # Extract giá trị (Type, Int, Float)
        typ, i_val, f_val = self._extract_val(val_raw)
        str_val = val_raw.get("str") if isinstance(val_raw, dict) else None
        
        # 2. Ghi vào pointer trả về (self.current_func_ret_ptr)
        ptr = self.current_func_ret_ptr
        if ptr:
            idx0 = ir.Constant(ir.IntType(32), 0)
            p_type = self.builder.gep(ptr, [idx0, ir.Constant(ir.IntType(32), 0)])
            p_int  = self.builder.gep(ptr, [idx0, ir.Constant(ir.IntType(32), 1)])
            p_flt  = self.builder.gep(ptr, [idx0, ir.Constant(ir.IntType(32), 2)])
            p_str  = self.builder.gep(ptr, [idx0, ir.Constant(ir.IntType(32), 3)])
            
            self.builder.store(typ, p_type)
            self.builder.store(i_val, p_int)
            self.builder.store(f_val, p_flt)
            
            if isinstance(val_raw, tuple) and val_raw[0] == TYPE_STR:
                 self.builder.store(val_raw[1], p_str)
            elif str_val:
                 self.builder.store(str_val, p_str)
        
        # 3. Kết thúc hàm
        self.builder.ret_void()

    # ================= LOGIC MỚI: CALL FUNCTION =================

    def visit_call_func(self, node: Node):
        func_name = node.children[0].data.func
        param_node = node.children[1]
        
        if func_name not in self.module.globals:
            print(f"Error: Function '{func_name}' not defined.")
            return None 
        
        func_obj = self.module.globals[func_name]
        
        # 1. Tạo biến tạm để chứa giá trị trả về (Allocation trên Stack)
        ret_val_ptr = self.builder.alloca(self.var_struct_ty, name="call_ret_val")
        
        # Khởi tạo giá trị 0 cho biến tạm
        zero = ir.Constant(ir.IntType(8), 0)
        t_ptr = self.builder.gep(ret_val_ptr, [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), 0)])
        self.builder.store(zero, t_ptr)

        # 2. Chuẩn bị danh sách đối số: [ret_ptr, arg1, arg2...]
        call_args = [ret_val_ptr] 

        for arg_expr in param_node.children:
            val_raw = self.visit(arg_expr)
            if val_raw is None: 
                # Handle null/error case -> create dummy
                tmp_dummy = self.builder.alloca(self.var_struct_ty)
                call_args.append(tmp_dummy)
                continue

            typ, i_val, f_val = self._extract_val(val_raw)
            str_val = val_raw.get("str") if isinstance(val_raw, dict) else None
            
            tmp_ptr = self.builder.alloca(self.var_struct_ty)
            idx0 = ir.Constant(ir.IntType(32), 0)
            p_type = self.builder.gep(tmp_ptr, [idx0, ir.Constant(ir.IntType(32), 0)])
            p_int  = self.builder.gep(tmp_ptr, [idx0, ir.Constant(ir.IntType(32), 1)])
            p_flt  = self.builder.gep(tmp_ptr, [idx0, ir.Constant(ir.IntType(32), 2)])
            p_str  = self.builder.gep(tmp_ptr, [idx0, ir.Constant(ir.IntType(32), 3)])
            
            self.builder.store(typ, p_type)
            if i_val: self.builder.store(i_val, p_int)
            if f_val: self.builder.store(f_val, p_flt)
            
            if isinstance(val_raw, tuple) and val_raw[0] == TYPE_STR:
                 self.builder.store(val_raw[1], p_str)
            elif str_val:
                 self.builder.store(str_val, p_str)
            
            call_args.append(tmp_ptr)

        # 3. Gọi hàm (trả về Void, nhưng ghi kết quả vào ret_val_ptr)
        self.builder.call(func_obj, call_args)
        
        # 4. Load kết quả từ ret_val_ptr để trả về cho Expression
        idx0 = ir.Constant(ir.IntType(32), 0)
        res_type_ptr = self.builder.gep(ret_val_ptr, [idx0, ir.Constant(ir.IntType(32), 0)])
        res_int_ptr  = self.builder.gep(ret_val_ptr, [idx0, ir.Constant(ir.IntType(32), 1)])
        res_flt_ptr  = self.builder.gep(ret_val_ptr, [idx0, ir.Constant(ir.IntType(32), 2)])
        res_str_ptr  = self.builder.gep(ret_val_ptr, [idx0, ir.Constant(ir.IntType(32), 3)])

        return {
            "is_var": True,
            "type": self.builder.load(res_type_ptr),
            "int": self.builder.load(res_int_ptr),
            "flt": self.builder.load(res_flt_ptr),
            "str": self.builder.load(res_str_ptr)
        }

    # ================= LOGIC: INPUT =================

    def visit_input(self, node: Node):
        type_node = node.children[0]
        var_node = node.children[1]
        
        target_type = type_node.data.func 
        var_name = var_node.data.func

        # Prompt
        if len(node.children) > 2:
            prompt_str = node.children[2].data.string_value
            prompt_ptr = self._global_string(prompt_str)
            self.builder.call(self.printf, [self.fmt_str, prompt_ptr])
            null_ptr = ir.Constant(ir.IntType(64), 0).inttoptr(ir.IntType(8).as_pointer())
            self.builder.call(self.fflush, [null_ptr])

        # Get/Create Variable
        ptr = self._get_var_ptr(var_name)
        if not ptr:
            ptr = self._create_var(var_name)

        idx0 = ir.Constant(ir.IntType(32), 0)
        type_ptr = self.builder.gep(ptr, [idx0, ir.Constant(ir.IntType(32), 0)])
        int_ptr  = self.builder.gep(ptr, [idx0, ir.Constant(ir.IntType(32), 1)])
        flt_ptr  = self.builder.gep(ptr, [idx0, ir.Constant(ir.IntType(32), 2)])
        str_ptr  = self.builder.gep(ptr, [idx0, ir.Constant(ir.IntType(32), 3)])

        if target_type == "int":
            self.builder.call(self.scanf, [self.scan_int, int_ptr])
            self.builder.store(ir.Constant(ir.IntType(8), TYPE_INT), type_ptr)
            
        elif target_type == "float":
            self.builder.call(self.scanf, [self.scan_float, flt_ptr])
            self.builder.store(ir.Constant(ir.IntType(8), TYPE_FLOAT), type_ptr)

        elif target_type == "str":
            size = ir.Constant(ir.IntType(64), 256)
            mem = self.builder.call(self.malloc, [size])
            self.builder.call(self.scanf, [self.scan_str, mem])
            self.builder.store(mem, str_ptr)
            self.builder.store(ir.Constant(ir.IntType(8), TYPE_STR), type_ptr)

    # ================= LOGIC: ASSIGNMENT =================

    def visit_assignment(self, node: Node):
        # Cấu trúc: [0]: Name, [1]: ValueNode, [2]: TypeNode (Optional)
        var_name = node.children[0].data.func
        val_node = node.children[1]
        
        # 1. Tính toán giá trị vế phải
        result = self.visit(val_node.children[0])
        if result is None: return
        
        rhs_type, rhs_int, rhs_flt = self._extract_val(result)

        # 2. Kiểm tra xem có ép kiểu "int" không (dựa vào AST child 2)
        forced_type = ""
        if len(node.children) > 2:
            forced_type = node.children[2].data.func
            
        if forced_type == "int":
            # Ép kiểu vế phải sang Int
            new_int = self._val_to_int((rhs_type, rhs_int, rhs_flt))
            rhs_type = ir.Constant(ir.IntType(8), TYPE_INT)
            rhs_int = new_int
            # rhs_flt không quan trọng, nhưng để an toàn có thể set về 0.0
            rhs_flt = ir.Constant(ir.DoubleType(), 0.0)

        # 3. Lưu vào biến
        ptr = self._get_var_ptr(var_name)
        if not ptr:
            ptr = self._create_var(var_name)

        idx0 = ir.Constant(ir.IntType(32), 0)
        type_ptr = self.builder.gep(ptr, [idx0, ir.Constant(ir.IntType(32), 0)])
        int_ptr  = self.builder.gep(ptr, [idx0, ir.Constant(ir.IntType(32), 1)])
        flt_ptr  = self.builder.gep(ptr, [idx0, ir.Constant(ir.IntType(32), 2)])
        str_ptr  = self.builder.gep(ptr, [idx0, ir.Constant(ir.IntType(32), 3)])

        self.builder.store(rhs_type, type_ptr) 
        self.builder.store(rhs_int, int_ptr)
        self.builder.store(rhs_flt, flt_ptr)

        if isinstance(result, tuple) and result[0] == TYPE_STR:
             self.builder.store(result[1], str_ptr)
        elif isinstance(result, dict) and result.get("str"):
             self.builder.store(result["str"], str_ptr)

    def visit_variable_load(self, node: Node):
        var_name = node.data.func
        ptr = self._get_var_ptr(var_name)
        
        # If variable not found, return 0 (safe fallback)
        if not ptr:
            return (TYPE_INT, ir.Constant(ir.IntType(64), 0))

        idx0 = ir.Constant(ir.IntType(32), 0)
        type_ptr = self.builder.gep(ptr, [idx0, ir.Constant(ir.IntType(32), 0)])
        int_ptr  = self.builder.gep(ptr, [idx0, ir.Constant(ir.IntType(32), 1)])
        flt_ptr  = self.builder.gep(ptr, [idx0, ir.Constant(ir.IntType(32), 2)])
        str_ptr  = self.builder.gep(ptr, [idx0, ir.Constant(ir.IntType(32), 3)])

        return {
            "is_var": True,
            "type": self.builder.load(type_ptr),
            "int": self.builder.load(int_ptr),
            "flt": self.builder.load(flt_ptr),
            "str": self.builder.load(str_ptr)
        }

    # ================= UTILS & OPS =================
    
    def _extract_val(self, operand):
        """Standardizes return values into (Type, Int, Float)"""
        if operand is None:
            # Fallback for null
            return (ir.Constant(ir.IntType(8), TYPE_INT), ir.Constant(ir.IntType(64), 0), ir.Constant(ir.DoubleType(), 0.0))
            
        if isinstance(operand, tuple): # Literal (TYPE, Value)
            typ, val = operand
            if typ == TYPE_INT:
                return (ir.Constant(ir.IntType(8), TYPE_INT), val, ir.Constant(ir.DoubleType(), 0.0))
            elif typ == TYPE_FLOAT:
                return (ir.Constant(ir.IntType(8), TYPE_FLOAT), ir.Constant(ir.IntType(64), 0), val)
            elif typ == TYPE_STR:
                return (ir.Constant(ir.IntType(8), TYPE_STR), None, None) 
        elif isinstance(operand, dict) and operand.get("is_var"): # Dynamic Var
            return (operand["type"], operand["int"], operand["flt"])
            
        return (ir.Constant(ir.IntType(8), TYPE_INT), ir.Constant(ir.IntType(64), 0), ir.Constant(ir.DoubleType(), 0.0))

    def visit_binary_op(self, node: Node):
        lhs_raw = self.visit(node.children[0])
        rhs_raw = self.visit(node.children[1])
        op = node.data.operator

        l_type, l_int, l_flt = self._extract_val(lhs_raw)
        r_type, r_int, r_flt = self._extract_val(rhs_raw)

        # Type Coercion: If either is float, operation is float
        is_l_float = self.builder.icmp_signed('==', l_type, ir.Constant(ir.IntType(8), TYPE_FLOAT))
        is_r_float = self.builder.icmp_signed('==', r_type, ir.Constant(ir.IntType(8), TYPE_FLOAT))
        is_any_float = self.builder.or_(is_l_float, is_r_float)

        l_val_f = self.builder.select(is_l_float, l_flt, self.builder.sitofp(l_int, ir.DoubleType()))
        r_val_f = self.builder.select(is_r_float, r_flt, self.builder.sitofp(r_int, ir.DoubleType()))

        l_val_i = l_int
        r_val_i = r_int

        res_i = ir.Constant(ir.IntType(64), 0)
        res_f = ir.Constant(ir.DoubleType(), 0.0)

        # Arithmetic
        if op == Operators.add:
            res_i = self.builder.add(l_val_i, r_val_i)
            res_f = self.builder.fadd(l_val_f, r_val_f)
        elif op == Operators.subtract:
            res_i = self.builder.sub(l_val_i, r_val_i)
            res_f = self.builder.fsub(l_val_f, r_val_f)
        elif op == Operators.multiply:
            res_i = self.builder.mul(l_val_i, r_val_i)
            res_f = self.builder.fmul(l_val_f, r_val_f)
        elif op == Operators.divide:
            res_i = self.builder.sdiv(l_val_i, r_val_i)
            res_f = self.builder.fdiv(l_val_f, r_val_f)
        
        # Comparision
        preds = {Operators.equals: '==', Operators.same: '==', Operators.different: '!=', 
                 Operators.less: '<', Operators.less_same: '<=', Operators.greater: '>', Operators.greater_same: '>='}
        
        if op in preds:
            cmp_f = self.builder.fcmp_ordered(preds[op], l_val_f, r_val_f)
            cmp_i = self.builder.icmp_signed(preds[op], l_val_i, r_val_i)
            
            final_bool = self.builder.select(is_any_float, cmp_f, cmp_i)
            res_val = self.builder.zext(final_bool, ir.IntType(64))
            return (TYPE_INT, res_val)

        final_type = self.builder.select(is_any_float, ir.Constant(ir.IntType(8), TYPE_FLOAT), ir.Constant(ir.IntType(8), TYPE_INT))
        
        return {
            "is_var": True,
            "type": final_type,
            "int": res_i,
            "flt": res_f,
            "str": None
        }
    
    def _val_to_int(self, val_data):
        """
        Chuyển đổi dữ liệu (Type, Int, Float) sang giá trị Int 64-bit duy nhất.
        Nếu Type là Float, dùng lệnh fptosi để ép kiểu.
        """
        typ, i_val, f_val = val_data
        
        # Kiểm tra xem type có phải là FLOAT không
        is_float = self.builder.icmp_signed('==', typ, ir.Constant(ir.IntType(8), TYPE_FLOAT))
        
        # Tạo lệnh ép kiểu Float -> Int
        cast_val = self.builder.fptosi(f_val, ir.IntType(64))
        
        # Dùng lệnh Select: Nếu là Float thì lấy cast_val, ngược lại lấy i_val
        final_int = self.builder.select(is_float, cast_val, i_val)
        
        return final_int

    # ================= PRINT =================

    def visit_print(self, node: Node, is_newline=False):
        for child in node.children:
            val_raw = self.visit(child)
            if val_raw is None: continue

            # --- Xử lý String Literal ---
            if isinstance(val_raw, tuple) and val_raw[0] == TYPE_STR:
                fmt = self.fmt_str_nl if is_newline else self.fmt_str
                self.builder.call(self.printf, [fmt, val_raw[1]])
                # FIX: Flush stdout sau khi in string
                null_ptr = ir.Constant(ir.IntType(64), 0).inttoptr(ir.IntType(8).as_pointer())
                self.builder.call(self.fflush, [null_ptr])
                continue

            # --- Xử lý Variable / Expression ---
            data = self._extract_val(val_raw)
            typ, i_val, f_val = data
            str_val = val_raw.get("str") if isinstance(val_raw, dict) else None

            # 1. Case INT
            is_int = self.builder.icmp_signed('==', typ, ir.Constant(ir.IntType(8), TYPE_INT))
            with self.builder.if_then(is_int):
                fmt = self.fmt_int_nl if is_newline else self.fmt_int
                self.builder.call(self.printf, [fmt, i_val])

            # 2. Case FLOAT
            is_flt = self.builder.icmp_signed('==', typ, ir.Constant(ir.IntType(8), TYPE_FLOAT))
            with self.builder.if_then(is_flt):
                fmt = self.fmt_float_nl if is_newline else self.fmt_float
                self.builder.call(self.printf, [fmt, f_val])
                
            # 3. Case STR (Var)
            if str_val:
                is_str = self.builder.icmp_signed('==', typ, ir.Constant(ir.IntType(8), TYPE_STR))
                with self.builder.if_then(is_str):
                    fmt = self.fmt_str_nl if is_newline else self.fmt_str
                    self.builder.call(self.printf, [fmt, str_val])

            # FIX: Luôn Flush stdout sau lệnh print
            null_ptr = ir.Constant(ir.IntType(64), 0).inttoptr(ir.IntType(8).as_pointer())
            self.builder.call(self.fflush, [null_ptr])

    # ================= CONTROL FLOW =================
    
    def visit_if(self, node: Node):
        cond_raw = self.visit(node.children[0])
        data = self._extract_val(cond_raw)
        
        # Check != 0
        bool_val = self.builder.icmp_signed('!=', data[1], ir.Constant(ir.IntType(64), 0))
        
        then_block = self.func.append_basic_block("if.then")
        merge_block = self.func.append_basic_block("if.end")
        else_node = node.children[2] if len(node.children) > 2 else None
        else_block = self.func.append_basic_block("if.else") if else_node else None

        if else_block: self.builder.cbranch(bool_val, then_block, else_block)
        else: self.builder.cbranch(bool_val, then_block, merge_block)

        self.builder.position_at_end(then_block)
        self.visit(node.children[1])
        if not self.builder.block.is_terminated: self.builder.branch(merge_block)

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
        
        cond_raw = self.visit(node.children[0].children[0])
        data = self._extract_val(cond_raw)
        bool_val = self.builder.icmp_signed('!=', data[1], ir.Constant(ir.IntType(64), 0))
        
        self.builder.cbranch(bool_val, body_block, end_block)

        self.builder.position_at_end(body_block)
        self.visit(node.children[1])
        if not self.builder.block.is_terminated: self.builder.branch(cond_block)

        self.builder.position_at_end(end_block)

    def visit_for(self, node: Node):
        param = node.children[0]
        init_node = param.children[0] 

        # 1. Chạy Assignment (i = 1). 
        # Nhờ hàm visit_assignment mới, i sẽ được lưu là INT (Type=1)
        self.visit(init_node) 
        
        var_name = init_node.children[0].data.func
        
        # 2. Lấy giá trị End (Xử lý ép kiểu an toàn)
        end_raw = self.visit(param.children[1])
        end_data = self._extract_val(end_raw)
        end_val = self._val_to_int(end_data) # Ép 10.0 -> 10

        # 3. Lấy giá trị Step (Xử lý ép kiểu an toàn)
        step_val = ir.Constant(ir.IntType(64), 1)
        if len(param.children) > 2:
            step_raw = self.visit(param.children[2])
            step_data = self._extract_val(step_raw)
            step_val = self._val_to_int(step_data) # Ép 1.0 -> 1 (Fix lỗi step=0)

        cond_block = self.func.append_basic_block("for.cond")
        body_block = self.func.append_basic_block("for.body")
        end_block = self.func.append_basic_block("for.end")
        
        self.builder.branch(cond_block)
        
        # --- COND BLOCK ---
        self.builder.position_at_end(cond_block)
        
        # Load i từ bộ nhớ
        ptr = self._get_var_ptr(var_name)
        # Load đủ 3 thành phần để dùng _val_to_int cho an toàn
        idx0 = ir.Constant(ir.IntType(32), 0)
        t_ptr = self.builder.gep(ptr, [idx0, ir.Constant(ir.IntType(32), 0)])
        i_ptr = self.builder.gep(ptr, [idx0, ir.Constant(ir.IntType(32), 1)])
        f_ptr = self.builder.gep(ptr, [idx0, ir.Constant(ir.IntType(32), 2)])
        
        cur_type = self.builder.load(t_ptr)
        cur_int = self.builder.load(i_ptr)
        cur_flt = self.builder.load(f_ptr)
        
        # Chuyển i hiện tại về int để so sánh
        curr_i = self._val_to_int((cur_type, cur_int, cur_flt))
        
        cmp = self.builder.icmp_signed('<=', curr_i, end_val)
        self.builder.cbranch(cmp, body_block, end_block)
        
        # --- BODY BLOCK ---
        self.builder.position_at_end(body_block)
        self.visit(node.children[1]) 
        
        # --- UPDATE STEP ---
        # Tính i mới
        new_i = self.builder.add(curr_i, step_val)
        
        # Store lại vào i_ptr
        self.builder.store(new_i, i_ptr)
        # QUAN TRỌNG: Update luôn Type về INT để các lệnh print sau đó nhận diện đúng
        self.builder.store(ir.Constant(ir.IntType(8), TYPE_INT), t_ptr)
        
        self.builder.branch(cond_block)
        
        # --- END BLOCK ---
        self.builder.position_at_end(end_block)

def emit_llvm(ast):
    codegen = LLVMCodeGen()
    return codegen.generate_ir(ast)

def run_jit(llvm_ir):
    try:
        llvm_module = binding.parse_assembly(str(llvm_ir))
        llvm_module.verify()
    except Exception as e:
        print(f"LLVM Parse Error: {e}")
        return

    target = binding.Target.from_default_triple()
    target_machine = target.create_target_machine()
    with binding.create_mcjit_compiler(llvm_module, target_machine) as ee:
        ee.finalize_object()
        func_ptr = ee.get_function_address("main")
        c_main = ctypes.CFUNCTYPE(ctypes.c_int32)(func_ptr)
        c_main()