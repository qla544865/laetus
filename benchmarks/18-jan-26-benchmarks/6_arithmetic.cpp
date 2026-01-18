#include <iostream>
int main(){ long long a=10, b=20; for(int i=1;i<=10000000;i++){ a=(a*2+b)/3+1; b=a-5; if(a>1000) a=10; } std::cout<<a<<std::endl; return 0; }