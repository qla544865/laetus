#include <iostream>
int main(){ 
    long long t=0; 
    for(int i=1;i<=10000000;i++){ 
        if(i%3==0) 
            t+=i; 
        else if(i%5==0) 
            t+=i; 
    } 
    std::cout<<t<<std::endl; 
    return 0; 
}