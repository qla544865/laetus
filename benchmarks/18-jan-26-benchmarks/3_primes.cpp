#include <iostream>
int main(){ int c=0; for(int i=2;i<=10000;i++){ bool p=1; for(int j=2;j*j<=i;j++) if(i%j==0){p=0;break;} if(p) c++; } std::cout<<c<<std::endl; return 0; }