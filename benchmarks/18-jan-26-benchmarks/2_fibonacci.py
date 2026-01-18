import time
def fib(x):
    if x < 2: return 1
    return fib(x-1) + fib(x-2)
s = time.time()
print(fib(35))
print(f'Time: {time.time()-s:.6f}s')