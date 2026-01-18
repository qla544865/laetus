import os
import subprocess
import time

# Cấu hình đường dẫn
BASE_DIR = "Laetus_Project_Benchmarks"
LAETUS_CMD = "laetus" # Giả định lệnh 'laetus' đã được thêm vào PATH

# 1. Định nghĩa nội dung 8 bài Benchmark theo đúng cú pháp báo cáo 
benchmarks = {
    "1_loop_sum": {
        "lae": "sum = 0\nfor i = 1, 10000000, 1 do\n    sum = sum + i\nend\nprintln sum",
        "py": "import time\ns = time.time()\ntotal = 0\nfor i in range(1, 10000001): total += i\nprint(total)\nprint(f'Time: {time.time()-s:.6f}s')",
        "cpp": "#include <iostream>\nint main(){ long long s=0; for(int i=1;i<=10000000;i++) s+=i; std::cout<<s<<std::endl; return 0; }"
    },
    "2_fibonacci": {
        "lae": "func fib(x)\n    if x < 2 then\n        return 1\n    end\n    return fib(x-1) + fib(x-2)\nend\nprintln fib(35)",
        "py": "import time\ndef fib(x):\n    if x < 2: return 1\n    return fib(x-1) + fib(x-2)\ns = time.time()\nprint(fib(35))\nprint(f'Time: {time.time()-s:.6f}s')",
        "cpp": "#include <iostream>\nint fib(int x){ if(x<2) return 1; return fib(x-1)+fib(x-2); }\nint main(){ std::cout<<fib(35)<<std::endl; return 0; }"
    },
    "3_primes": {
        "lae": "count = 0\nfor i = 2, 10000, 1 do\n    isP = 1\n    j = 2\n    while j * j <= i do\n        if (i - (i/j)*j) == 0 then\n            isP = 0\n        end\n        j = j + 1\n    end\n    if isP == 1 then count = count + 1 end\nend\nprintln count",
        "py": "import time\ns = time.time()\nc=0\nfor i in range(2,10001):\n    isP=1; j=2\n    while j*j <= i:\n        if i%j==0: isP=0; break\n        j+=1\n    if isP: c+=1\nprint(c)\nprint(f'Time: {time.time()-s:.6f}s')",
        "cpp": "#include <iostream>\nint main(){ int c=0; for(int i=2;i<=10000;i++){ bool p=1; for(int j=2;j*j<=i;j++) if(i%j==0){p=0;break;} if(p) c++; } std::cout<<c<<std::endl; return 0; }"
    },
    "4_collatz": {
        "lae": "max_s = 0\nfor i = 1, 100000, 1 do\n    s = 0\n    curr = i\n    while curr > 1 do\n        if (curr - (curr/2)*2) == 0 then curr = curr / 2\n        else curr = 3 * curr + 1\n        end\n        s = s + 1\n    end\n    if s > max_s then max_s = s end\nend\nprintln max_s",
        "py": "import time\ns_t = time.time()\nm_s = 0\nfor i in range(1, 100001):\n    s = 0; curr = i\n    while curr > 1:\n        if curr % 2 == 0: curr //= 2\n        else: curr = 3 * curr + 1\n        s += 1\n    if s > m_s: m_s = s\nprint(m_s)\nprint(f'Time: {time.time()-s_t:.6f}s')",
        "cpp": "#include <iostream>\nint main(){ int m_s=0; for(int i=1;i<=100000;i++){ long long c=i; int s=0; while(c>1){ if(c%2==0) c/=2; else c=3*c+1; s++; } if(s>m_s) m_s=s; } std::cout<<m_s<<std::endl; return 0; }"
    },
    "5_gcd": {
        "lae": "func gcd(a, b)\n    while b > 0 do\n        t = b\n        b = a - (a/b)*b\n        a = t\n    end\n    return a\nend\nres = 0\nfor i = 1, 1000000, 1 do\n    res = gcd(987654321, 123456789)\nend\nprintln res",
        "py": "import time\ndef gcd(a,b):\n    while b: a, b = b, a % b\n    return a\ns = time.time()\nfor _ in range(1000000): r = gcd(987654321, 123456789)\nprint(r)\nprint(f'Time: {time.time()-s:.6f}s')",
        "cpp": "#include <iostream>\nint gcd(int a, int b){ while(b){ int t=b; b=a%b; a=t; } return a; }\nint main(){ int r; for(int i=0;i<1000000;i++) r=gcd(987654321, 123456789); std::cout<<r<<std::endl; return 0; }"
    },
    "6_arithmetic": {
        "lae": "a = 10\nb = 20\nfor i = 1, 10000000, 1 do\n    a = (a * 2 + b) / 3 + 1\n    b = a - 5\n    if a > 1000 then a = 10 end\nend\nprintln a",
        "py": "import time\ns = time.time()\na, b = 10, 20\nfor i in range(1, 10000001):\n    a = (a * 2 + b) // 3 + 1\n    b = a - 5\n    if a > 1000: a = 10\nprint(a)\nprint(f'Time: {time.time()-s:.6f}s')",
        "cpp": "#include <iostream>\nint main(){ long long a=10, b=20; for(int i=1;i<=10000000;i++){ a=(a*2+b)/3+1; b=a-5; if(a>1000) a=10; } std::cout<<a<<std::endl; return 0; }"
    },
    "7_cond_sum": {
        "lae": "sum = 0\nfor i = 1, 10000000, 1 do\n    if (i - (i/3)*3) == 0 then sum = sum + i\n    else if (i - (i/5)*5) == 0 then sum = sum + i end end\nend\nprintln sum",
        "py": "import time\ns = time.time()\nt = 0\nfor i in range(1, 10000001):\n    if i%3==0: t+=i\n    elif i%5==0: t+=i\nprint(t)\nprint(f'Time: {time.time()-s:.6f}s')",
        "cpp": "#include <iostream>\nint main(){ long long t=0; for(int i=1;i<=10000000;i++){ if(i%3==0) t+=i; else if(i%5==0) t+=i; } std::cout<<t<<std::endl; return 0; }"
    },
    "8_ackermann": {
        "lae": "func ack(m, n)\n    if m == 0 then return n + 1 end\n    if n == 0 then return ack(m - 1, 1) end\n    return ack(m - 1, ack(m, n - 1))\nend\nprintln ack(3, 7)",
        "py": "import sys, time\nsys.setrecursionlimit(10000)\ndef ack(m,n):\n    if m==0: return n+1\n    if n==0: return ack(m-1,1)\n    return ack(m-1, ack(m, n-1))\ns = time.time()\nprint(ack(3, 7))\nprint(f'Time: {time.time()-s:.6f}s')",
        "cpp": "#include <iostream>\nint ack(int m, int n){ if(m==0) return n+1; if(n==0) return ack(m-1, 1); return ack(m-1, ack(m, n-1)); }\nint main(){ std::cout<<ack(3, 7)<<std::endl; return 0; }"
    }
}

def run_test():
    if not os.path.exists(BASE_DIR):
        os.makedirs(BASE_DIR)
    
    results = []
    
    for name, code in benchmarks.items():
        print(f"\n--- Testing: {name} ---")
        # # 1. Ghi file
        # for ext in ["lae", "py", "cpp"]:
        #     with open(os.path.join(BASE_DIR, f"{name}.{ext}"), "w") as f:
        #         f.write(code[ext])
        
        # 2. Biên dịch C++
        cpp_file = os.path.join(BASE_DIR, f"{name}.cpp")
        exe_file = os.path.join(BASE_DIR, f"{name}.exe")
        subprocess.run(["g++", cpp_file, "-o", exe_file])

        # 3. Chạy và đo thời gian
        # Laetus JIT
        try:
            start = time.time()
            subprocess.run([LAETUS_CMD, os.path.join(BASE_DIR, f"{name}.lae"), "-jit"], capture_output=True)
            t_laetus = time.time() - start
        except: t_laetus = -1
        
        # Python
        start = time.time()
        subprocess.run(["python", os.path.join(BASE_DIR, f"{name}.py")], capture_output=True)
        t_python = time.time() - start
        
        # C++
        start = time.time()
        subprocess.run([exe_file], capture_output=True)
        t_cpp = time.time() - start
        
        results.append((name, t_laetus, t_python, t_cpp))
        print(f"Laetus: {t_laetus:.4f}s | Python: {t_python:.4f}s | C++: {t_cpp:.4f}s")

    # In bảng tổng kết
    print("\n" + "="*50)
    print(f"{'Benchmark':<15} | {'Laetus (s)':<10} | {'Python (s)':<10} | {'C++ (s)':<10}")
    print("-" * 50)
    for res in results:
        print(f"{res[0]:<15} | {res[1]:<10.4f} | {res[2]:<10.4f} | {res[3]:<10.4f}")

if __name__ == "__main__":
    run_test()