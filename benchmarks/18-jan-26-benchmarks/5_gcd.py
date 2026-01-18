def gcd(a,b):
    while b: 
        a, b = b, a % b
    return a
for _ in range(1,1000000,1): 
    r = gcd(987654321, 123456789)
print(r)
