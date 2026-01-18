import time
s = time.time()
c=0
for i in range(2,10001):
    isP=1; j=2
    while j*j <= i:
        if i%j==0: isP=0; break
        j+=1
    if isP: c+=1
print(c)
print(f'Time: {time.time()-s:.6f}s')