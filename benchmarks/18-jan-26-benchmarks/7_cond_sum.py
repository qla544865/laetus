import time
s = time.time()
t = 0
for i in range(1, 10000001):
    if i%3==0: t+=i
    elif i%5==0: t+=i
print(t)
print(f'Time: {time.time()-s:.6f}s')