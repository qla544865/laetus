#include <iostream>
int gcd(int a, int b){ 
    while(b) { 
        int t=b; 
        b=a%b; 
        a=t; 
    } 
    return a; 
}
int main(){ 
    int r; 
    for(int i=0;i<1000000;i++) {
        r=gcd(987654321, 123456789); 
        std::cout<<r<<std::endl;
    } 
    return 0; 
}