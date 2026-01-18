import time
s = time.time()
a, b = 10, 20
for i in range(1, 10000001):
    a = (a * 2 + b) // 3 + 1
    b = a - 5
    if a > 1000: a = 10
print(a)
print(f'Time: {time.time()-s:.6f}s')