import time
s_t = time.time()
m_s = 0
for i in range(1, 100001):
    s = 0; curr = i
    while curr > 1:
        if curr % 2 == 0: curr //= 2
        else: curr = 3 * curr + 1
        s += 1
    if s > m_s: m_s = s
print(m_s)
print(f'Time: {time.time()-s_t:.6f}s')