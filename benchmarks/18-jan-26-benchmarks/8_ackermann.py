import sys, time
sys.setrecursionlimit(10000)
def ack(m,n):
    if m==0: return n+1
    if n==0: return ack(m-1,1)
    return ack(m-1, ack(m, n-1))
s = time.time()
print(ack(3, 7))
print(f'Time: {time.time()-s:.6f}s')