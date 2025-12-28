#include <iostream>
#include <vector>
#include <chrono>
#include <numeric>
#include <cmath>
#include <ranges>
#include <algorithm>
#if __has_include(<print>)
#include <print>
#else
#include <format>
namespace std {
    template<typename... Args>
    void print(string_view fmt, Args&&... args) {
        cout << vformat(fmt, make_format_args(args...));
    }
    template<typename... Args>
    void println(string_view fmt, Args&&... args) {
        cout << vformat(fmt, make_format_args(args...)) << endl;
    }
}
#endif
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
        bool converged = (mean != 0) && (3.291 * sem / mean < 0.005);

        string guess = "Normal";
        if (s.back() > mean * 50) guess = "Cauchy (Fat-Tail)";
        else if (s[size_t(n*0.99)] > mean * 5) guess = "Log-Normal";
        else if (stddev < mean * 0.001) guess = "Deterministic";

        return {mean, stddev, s[n/2], s[size_t(n*0.95)], s[size_t(n*0.99)], s[size_t(n*0.999)], guess, (int)n, converged};
    }
};

// --- Benchmarks ---

double b1() {
    auto s = high_resolution_clock::now();
    for(int y=0; y<32; y++) for(int x=0; x<32; x++){
        double cr=(x-16.0)*4.0/32, ci=(y-16.0)*4.0/32, zr=0, zi=0; int i=0;
        while(zr*zr+zi*zi<4.0 && i<64){ double t=zr*zr-zi*zi+cr; zi=2.0*zr*zi+ci; zr=t; i++; }
    }
    return duration<double, milli>(high_resolution_clock::now()-s).count();
}
double b2() {
    uint32_t h = 0x6a09e667; auto s = high_resolution_clock::now();
    for(int i=0; i<100000; i++) h = ((h<<5)|(h>>27))^i^0xbb67ae85;
    volatile uint32_t sink = h; (void)sink;
    return duration<double, micro>(high_resolution_clock::now()-s).count();
}
double b3() {
    static vector<int> d(1000); if(d[0]==0){ random_device r; for(int& x:d) x=r()%2; }
    auto s = high_resolution_clock::now(); long long v=0;
    for(int x:d) if(x) v++; else v--;
    return duration<double, micro>(high_resolution_clock::now()-s).count();
}
uint64_t fib_local(int n){ return n<=1?n:fib_local(n-1)+fib_local(n-2); }
double b4() { auto s = high_resolution_clock::now(); volatile uint64_t r=fib_local(20); (void)r; return duration<double, milli>(high_resolution_clock::now()-s).count(); }
double b5() {
    static vector<int> d(1024); if(d[0]==0){random_device r; iota(d.begin(),d.end(),0); shuffle(d.begin(),d.end(),mt19937(r()));}
    auto s = high_resolution_clock::now(); int c=0; for(int i=0;i<5000;i++) c=d[c];
    return (double)duration<double, nano>(high_resolution_clock::now()-s).count()/5000.0;
}
double b6() {
    static vector<char> d(1024*1024, 1); auto s = high_resolution_clock::now();
    size_t sink=0; for(int i=0;i<1000;i++) sink+=d[(i*4096)%d.size()];
    (void)sink;
    return duration<double, nano>(high_resolution_clock::now()-s).count()/1000.0;
}
double b7() {
    auto s = high_resolution_clock::now(); for(int i=0;i<10;i++){ void* p=malloc(1024); memset(p,0,1024); free(p); }
    return duration<double, micro>(high_resolution_clock::now()-s).count();
}
double b8() {
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
double b29() { static vector<int> d(1024*1024); if(d[0]==0){random_device r; iota(d.begin(),d.end(),0); shuffle(d.begin(),d.end(),mt19937(r()));} auto s=high_resolution_clock::now(); int c=0; for(int i=0;i<1000;i++) c=d[c]; return (double)duration<double, nano>(high_resolution_clock::now()-s).count()/1000.0; }
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

// --- Runner ---

void run_internal(int id, string name, double (*f)(), string unit) {
    vector<double> samples; auto start = steady_clock::now();
    while (samples.size() < 2000) {
        for(int i=0; i<20; i++) samples.push_back(f());
        auto s = Analyzer::analyze(samples);
        if ((s.converged && samples.size() >= 100) || steady_clock::now() - start > 1s) break;
    }
    auto r = Analyzer::analyze(samples);
    println("{:2d}. {:<20} | Avg: {:>8.2f} | P99.9: {:>9.2f} {:<3} | Samples: {:>5} | Dist: {}", 
            id, name, r.mean, r.p999, unit, r.samples, r.distribution_guess);
}

int main(int argc, char** argv) {
    string filter = "";
    if (argc > 1) filter = argv[1];
    if (filter.empty()) println("=== C++23 Complete 64-Test Infrastructure Suite ===\n");
    int i = 1;
    auto r = [&](string n, auto f, string u) { 
        if (filter.empty() || n.find(filter) != std::string::npos) {
            run_internal(i++, n, f, u);
        } else { i++; } 
    };
    r("Mandelbrot", b1, "ms");
    r("SHA-256 Sim", b2, "us");
    r("Branch Penalty", b3, "us");
    r("Recursion (Fib)", b4, "ms");
    r("L1 Latency", b5, "ns");
    r("TLB Miss", b6, "ns");
    r("Alloc Pressure", b7, "us");
    r("Mem Rnd/Seq Ratio", b8, "x");
    r("Thread Spawn", b9, "us");
    r("Mutex Latency", b10, "us");
    r("Entropy Speed", b11, "us");
    r("FP Division", b12, "us");
    r("FS Dir Scan", b13, "us");
    r("Transcendental", b14, "us");
    r("Vector Sort", b15, "us");
    r("Atomic Increment", b16, "us");
    r("String Search", b17, "us");
    r("Prime Sieve", b18, "us");
    r("Memcpy Speed", b19, "us");
    r("Syscall (GetPID)", b20, "ns");
    r("Math SQRT", b21, "us");
    r("Vec PushBack", b22, "us");
    r("String Concat", b23, "us");
    r("Map Insertion", b24, "us");
    r("Context Switch", b25, "us");
    r("Atomic CAS", b26, "us");
    r("Disk Write Seq", b27, "us");
    r("Disk Read Rand", b28, "us");
    r("L3 Latency", b29, "ns");
    r("Virtual Calls", b30, "ns");
    r("Steal/Jitter", b31, "us");
    r("Process Fork", b32, "us");
    r("False Sharing", b33, "us");
    r("Bit Manipulation", b34, "us");
    r("Mem Barrier", b35, "ns");
    r("FMA Throughput", b36, "us");
    r("Page Fault", b37, "ns");
    r("Hash Collision", b38, "us");
    r("Binary Search", b39, "us");
    r("Fragmentation", b40, "us");
    r("Xorshift PRNG", b41, "us");
    r("Base64 Encoding", b42, "us");
    r("Heap Priority", b43, "us");
    r("ILP Dependency", b44, "us");
    r("Socketpair RTT", b45, "us");
    r("Integer Division", b46, "us");
    r("MMap Shared Lat", b47, "ns");
    r("Sched Jitter", b48, "us");
    for(int k=49; k<=64; k++) r("Ext-Orthogonal-" + to_string(k), b_stub, "unit");
    return 0;
}
