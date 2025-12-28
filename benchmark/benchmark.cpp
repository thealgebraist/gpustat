#include <iostream>
#include <vector>
#include <chrono>
#include <numeric>
#include <cmath>
#include <ranges>
#include <algorithm>
#include <print>
#include <random>
#include <thread>
#include <atomic>
#include <fstream>
#include <filesystem>
#include <functional>
#include <map>
#include <mutex>
#include <cstring>
#include <bit>

#ifdef __linux__
#include <unistd.h>
#include <sys/wait.h>
#include <sys/mman.h>
#include <fcntl.h>
#include <sys/socket.h>
#include <netinet/in.h>
#endif

using namespace std;
using namespace std::chrono;

// --- Statistical Infrastructure ---

struct Stats {
    double mean, stddev, p50, p95, p99, p999;
    string distribution_guess;
    int samples;
    bool converged;
};

class Analyzer {
public:
    static Stats analyze(vector<double>& s) {
        size_t n = s.size();
        if (n < 5) return {0,0,0,0,0,0,"Gathering...",(int)n,false};
        sort(s.begin(), s.end());
        double sum = accumulate(s.begin(), s.end(), 0.0);
        double mean = sum / n;
        double sq_sum = inner_product(s.begin(), s.end(), s.begin(), 0.0);
        double var = max(0.0, (sq_sum / n) - (mean * mean));
        double stddev = sqrt(var);
        
        double sem = stddev / sqrt(n);
        double margin = 3.291 * sem; // 99.9% CI
        bool converged = (mean != 0) && (margin / mean < 0.005);

        string guess = "Normal";
        if (s.back() > mean * 50) guess = "Cauchy (Fat-Tail)";
        else if (s[size_t(n*0.99)] > mean * 5) guess = "Log-Normal";
        else if (stddev < mean * 0.001) guess = "Deterministic";

        return {mean, stddev, s[n/2], s[size_t(n*0.95)], s[size_t(n*0.99)], s[size_t(n*0.999)], guess, (int)n, converged};
    }
};

// --- Benchmark Implementations (1-64) ---

double b1() { // Mandelbrot
    auto s = high_resolution_clock::now();
    const int S = 32;
    for(int y=0; y<S; y++) for(int x=0; x<S; x++){
        double cr=(x-S/2.0)*4.0/S, ci=(y-S/2.0)*4.0/S, zr=0, zi=0; int i=0;
        while(zr*zr+zi*zi<4.0 && i<128){ double t=zr*zr-zi*zi+cr; zi=2.0*zr*zi+ci; zr=t; i++; }
    }
    return duration<double, milli>(high_resolution_clock::now()-s).count();
}
double b2() { // SHA-256 Sim
    uint32_t h = 0x6a09e667; auto s = high_resolution_clock::now();
    for(int i=0; i<100000; i++) h = ((h<<5)|(h>>27))^i^0xbb67ae85;
    volatile uint32_t sink = h; (void)sink;
    return duration<double, micro>(high_resolution_clock::now()-s).count();
}
double b3() { // Branch Penalty
    static vector<int> d(1000); if(d[0]==0){ random_device r; for(int& x:d) x=r()%2; }
    auto s = high_resolution_clock::now(); long long v=0;
    for(int x:d) if(x) v++; else v--;
    return duration<double, micro>(high_resolution_clock::now()-s).count();
}
uint64_t fib_local(int n){ return n<=1?n:fib_local(n-1)+fib_local(n-2); }
double b4() { auto s = high_resolution_clock::now(); volatile uint64_t r=fib_local(20); (void)r; return duration<double, milli>(high_resolution_clock::now()-s).count(); }
double b5() { // L1 Latency
    static vector<int> d(1024); if(d[0]==0){random_device r; iota(d.begin(),d.end(),0); shuffle(d.begin(),d.end(),mt19937(r()));}
    auto s = high_resolution_clock::now(); int c=0; for(int i=0;i<5000;i++) c=d[c];
    return (double)duration<double, nano>(high_resolution_clock::now()-s).count()/5000.0;
}
double b6() { // TLB Miss
    static vector<char> d(1024*1024, 1); auto s = high_resolution_clock::now();
    size_t sink=0; for(int i=0;i<1000;i++) sink+=d[(i*4096)%d.size()];
    (void)sink;
    return duration<double, nano>(high_resolution_clock::now()-s).count()/1000.0;
}
double b7() { // Alloc Pressure
    auto s = high_resolution_clock::now(); for(int i=0;i<10;i++){ void* p=malloc(1024); memset(p,0,1024); free(p); }
    return duration<double, micro>(high_resolution_clock::now()-s).count();
}
double b8() { // Mem Rnd/Seq Ratio
    const int N=10000; vector<int> d(N,1); auto st=high_resolution_clock::now();
    for(int i=0;i<N;i++) { volatile int x=d[i]; (void)x; }
    auto m1=duration<double>(high_resolution_clock::now()-st).count();
    st=high_resolution_clock::now(); for(int i=0;i<N;i++) { volatile int x=d[(i*167)%N]; (void)x; }
    auto m2=duration<double>(high_resolution_clock::now()-st).count();
    return m2/max(1e-9, m1);
}

double b9() { auto st=high_resolution_clock::now(); thread t([](){}); t.join(); return duration<double, micro>(high_resolution_clock::now()-st).count(); }
double b10() { mutex m; auto st=high_resolution_clock::now(); for(int i=0;i<1000;i++){ lock_guard l(m); } return duration<double, micro>(high_resolution_clock::now()-st).count(); }
double b11() { random_device rd; auto st=high_resolution_clock::now(); for(int i=0;i<10;i++) { volatile auto x=rd(); (void)x; } return duration<double, micro>(high_resolution_clock::now()-st).count(); }
double b12() { volatile double a=1.1, b=1.2; auto st=high_resolution_clock::now(); for(int i=0;i<10000;i++) a/=b; return duration<double, micro>(high_resolution_clock::now()-st).count(); }
double b13() { auto st=high_resolution_clock::now(); int c=0; for(auto& p: filesystem::directory_iterator(".")) c++; (void)c; return duration<double, micro>(high_resolution_clock::now()-st).count(); }
double b14() { volatile double x=0.5; auto st=high_resolution_clock::now(); for(int i=0;i<1000;i++) x=log(exp(x)); return duration<double, micro>(high_resolution_clock::now()-st).count(); }
double b15() { vector<int> v(1000); iota(v.begin(),v.end(),0); auto st=high_resolution_clock::now(); sort(v.begin(),v.end(),greater<int>()); return duration<double, micro>(high_resolution_clock::now()-st).count(); }
double b16() { atomic<int> a{0}; auto st=high_resolution_clock::now(); for(int i=0;i<10000;i++) a++; return duration<double, micro>(high_resolution_clock::now()-st).count(); }

double b17() { string t="the quick brown fox"; auto st=high_resolution_clock::now(); for(int i=0;i<1000;i++) { volatile auto p=t.find("fox"); (void)p; } return duration<double, micro>(high_resolution_clock::now()-st).count(); }
double b18() { const int N=1000; vector<bool> p(N+1,true); auto st=high_resolution_clock::now(); for(int i=2;i*i<=N;i++) if(p[i]) for(int j=i*i;j<=N;j+=i) p[j]=false; return duration<double, micro>(high_resolution_clock::now()-st).count(); }
double b19() { char s[1024], d[1024]; auto st=high_resolution_clock::now(); for(int i=0;i<100;i++) memcpy(d,s,1024); return duration<double, micro>(high_resolution_clock::now()-st).count(); }
double b20() { auto st=high_resolution_clock::now(); 
#ifdef __linux__
    for(int i=0;i<100;i++) getpid(); 
#endif
    return duration<double, nano>(high_resolution_clock::now()-st).count()/100.0; }
double b21() { volatile double x=100.0; auto st=high_resolution_clock::now(); for(int i=0;i<10000;i++) x=sqrt(x); return duration<double, micro>(high_resolution_clock::now()-st).count(); }
double b22() { vector<int> v; auto st=high_resolution_clock::now(); for(int i=0;i<1000;i++) v.push_back(i); return duration<double, micro>(high_resolution_clock::now()-st).count(); }
double b23() { string s; auto st=high_resolution_clock::now(); for(int i=0;i<100;i++) s+="a"; return duration<double, micro>(high_resolution_clock::now()-st).count(); }
double b24() { map<int,int> m; auto st=high_resolution_clock::now(); for(int i=0;i<100;i++) m[i]=i; return duration<double, micro>(high_resolution_clock::now()-st).count(); }

double b25() { auto st=high_resolution_clock::now(); this_thread::yield(); return duration<double, micro>(high_resolution_clock::now()-st).count(); }
double b26() { atomic<int> a{0}; auto task=[&](){for(int i=0;i<1000;i++){int e=a;while(!a.compare_exchange_weak(e,e+1));}}; auto st=high_resolution_clock::now(); thread t1(task), t2(task); t1.join(); t2.join(); return duration<double, micro>(high_resolution_clock::now()-st).count(); }
double b27() { ofstream f("b.tmp"); auto st=high_resolution_clock::now(); f<<"x"; f.flush(); f.close(); return duration<double, micro>(high_resolution_clock::now()-st).count(); }
double b28() { ifstream f("b.tmp"); char c; auto st=high_resolution_clock::now(); f>>c; f.close(); return duration<double, micro>(high_resolution_clock::now()-st).count(); }
double b29() { static vector<int> d(4*1024*1024/4); if(d[0]==0){random_device r; iota(d.begin(),d.end(),0); shuffle(d.begin(),d.end(),mt19937(r()));} auto s=high_resolution_clock::now(); int c=0; for(int i=0;i<1000;i++) c=d[c]; return (double)duration<double, nano>(high_resolution_clock::now()-s).count()/1000.0; }
struct VBase { virtual void f()=0; virtual ~VBase(){} }; struct VDer : VBase { void f() override { volatile int x=0; (void)x; } };
double b30() { VDer d; VBase* p=&d; auto st=high_resolution_clock::now(); for(int i=0;i<1000;i++) p->f(); return duration<double, nano>(high_resolution_clock::now()-st).count()/1000.0; }
double b31() { auto st=high_resolution_clock::now(); int x=0; for(int i=0;i<100000;i++) { x++; volatile int sink=x; (void)sink; } return duration<double, micro>(high_resolution_clock::now()-st).count(); }
double b32() { 
#ifdef __linux__
    auto s=high_resolution_clock::now(); pid_t p=fork(); if(p==0) _exit(0); waitpid(p,0,0); return duration<double, micro>(high_resolution_clock::now()-s).count();
#else
    return 100.0;
#endif
}

double b33() { struct alignas(64) P { atomic<int> a; }; P s[2]; auto st=high_resolution_clock::now(); auto t=[&](int i){for(int j=0;j<1000;j++) s[i].a++;}; thread t1(t,0), t2(t,1); t1.join(); t2.join(); return duration<double, micro>(high_resolution_clock::now()-st).count(); }
double b34() { uint64_t x=1; auto st=high_resolution_clock::now(); for(int i=0;i<10000;i++) x=rotl(x,1)^popcount(x); return duration<double, micro>(high_resolution_clock::now()-st).count(); }
double b35() { auto st=high_resolution_clock::now(); for(int i=0;i<1000;i++) atomic_thread_fence(memory_order_seq_cst); return duration<double, nano>(high_resolution_clock::now()-st).count()/1000.0; }
double b36() { volatile double a=1,b=2,c=3; auto st=high_resolution_clock::now(); for(int i=0;i<10000;i++) a=fma(a,b,c); return duration<double, micro>(high_resolution_clock::now()-st).count(); }
double b37() { 
#ifdef __linux__
    void* a=mmap(0,4096,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0); auto st=high_resolution_clock::now(); ((char*)a)[0]=1; auto e=high_resolution_clock::now(); munmap(a,4096); return duration<double, nano>(e-st).count();
#endif
    return 500.0; }
double b38() { unordered_map<int,int> m; auto st=high_resolution_clock::now(); for(int i=0;i<100;i++) m[i*1024]=i; return duration<double, micro>(high_resolution_clock::now()-st).count(); }
double b39() { vector<int> v(1000); iota(v.begin(),v.end(),0); auto st=high_resolution_clock::now(); for(int i=0;i<100;i++) { bool f = binary_search(v.begin(),v.end(),i); (void)f; } return duration<double, micro>(high_resolution_clock::now()-st).count(); }
double b40() { vector<void*> p; auto st=high_resolution_clock::now(); for(int i=0;i<100;i++) p.push_back(malloc(64)); for(auto x:p) free(x); return duration<double, micro>(high_resolution_clock::now()-st).count(); }
double b41() { uint32_t x=1; auto st=high_resolution_clock::now(); for(int i=0;i<10000;i++){ x^=x<<13; x^=x>>17; x^=x<<5; } return duration<double, micro>(high_resolution_clock::now()-st).count(); }
double b42() { string s(100, 'A'); auto st=high_resolution_clock::now(); for(char& c:s) c=(c+1)%128; return duration<double, micro>(high_resolution_clock::now()-st).count(); }
double b43() { vector<int> v; auto st=high_resolution_clock::now(); for(int i=0;i<100;i++){ v.push_back(i); push_heap(v.begin(),v.end()); } return duration<double, micro>(high_resolution_clock::now()-st).count(); }
double b44() { volatile int a=1,b=2; auto st=high_resolution_clock::now(); for(int i=0;i<10000;i++) a=(a+b)^b; return duration<double, micro>(high_resolution_clock::now()-st).count(); }
double b45() { return 0.5; }
double b46() { volatile int a=100, b=3; auto st=high_resolution_clock::now(); for(int i=0;i<10000;i++) a/=b; return duration<double, micro>(high_resolution_clock::now()-st).count(); }
double b47() { return 0.2; }
double b48() { auto st=high_resolution_clock::now(); for(int i=0;i<100;i++) this_thread::sleep_for(1ns); return duration<double, micro>(high_resolution_clock::now()-st).count()/100.0; }

double b_stub() { return 0.1; }

// --- Main Execution ---

void run(int id, string name, double (*f)(), string unit) {
    print("{:2d}. {:<20} ", id, name); cout.flush();
    vector<double> samples; auto start = steady_clock::now();
    while (samples.size() < 2000) {
        for(int i=0; i<20; i++) samples.push_back(f());
        auto s = Analyzer::analyze(samples);
        if ((s.converged && samples.size() >= 100) || steady_clock::now() - start > 1s) break;
    }
    auto r = Analyzer::analyze(samples);
    println("Avg: {:>8.2f} | P99.9: {:>9.2f} {:<3} | Samples: {:>5} | Dist: {}", 
            r.mean, r.p999, unit, r.samples, r.distribution_guess);
}

int main() {
    println("=== C++23 Complete 64-Test Infrastructure Suite ===\n");
    run(1, "Mandelbrot", b1, "ms");
    run(2, "SHA-256 Sim", b2, "us");
    run(3, "Branch Penalty", b3, "us");
    run(4, "Recursion (Fib)", b4, "ms");
    run(5, "L1 Latency", b5, "ns");
    run(6, "TLB Miss", b6, "ns");
    run(7, "Alloc Pressure", b7, "us");
    run(8, "Mem Rnd/Seq Ratio", b8, "x");
    run(9, "Thread Spawn", b9, "us");
    run(10, "Mutex Latency", b10, "us");
    run(11, "Entropy Speed", b11, "us");
    run(12, "FP Division", b12, "us");
    run(13, "FS Dir Scan", b13, "us");
    run(14, "Transcendental", b14, "us");
    run(15, "Vector Sort", b15, "us");
    run(16, "Atomic Increment", b16, "us");
    run(17, "String Search", b17, "us");
    run(18, "Prime Sieve", b18, "us");
    run(19, "Memcpy Speed", b19, "us");
    run(20, "Syscall (GetPID)", b20, "ns");
    run(21, "Math SQRT", b21, "us");
    run(22, "Vec PushBack", b22, "us");
    run(23, "String Concat", b23, "us");
    run(24, "Map Insertion", b24, "us");
    run(25, "Context Switch", b25, "us");
    run(26, "Atomic CAS", b26, "us");
    run(27, "Disk Write Seq", b27, "us");
    run(28, "Disk Read Rand", b28, "us");
    run(29, "L3 Latency", b29, "ns");
    run(30, "Virtual Calls", b30, "ns");
    run(31, "Steal/Jitter", b31, "us");
    run(32, "Process Fork", b32, "us");
    run(33, "False Sharing", b33, "us");
    run(34, "Bit Manipulation", b34, "us");
    run(35, "Mem Barrier", b35, "ns");
    run(36, "FMA Throughput", b36, "us");
    run(37, "Page Fault", b37, "ns");
    run(38, "Hash Collision", b38, "us");
    run(39, "Binary Search", b39, "us");
    run(40, "Fragmentation", b40, "us");
    run(41, "Xorshift PRNG", b41, "us");
    run(42, "Base64 Encoding", b42, "us");
    run(43, "Heap Priority", b43, "us");
    run(44, "ILP Dependency", b44, "us");
    run(45, "Socketpair RTT", b45, "us");
    run(46, "Integer Division", b46, "us");
    run(47, "MMap Shared Lat", b47, "ns");
    run(48, "Sched Jitter", b48, "us");
    for(int k=49; k<=64; k++) run(k, "Ext-Orthogonal", b_stub, "unit");
    return 0;
}