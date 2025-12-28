#!/bin/bash

# GPUStat Sidecar Monitor & GCC Load Generator
echo "=== Initializing GCC Load Test & Sidecar Monitor ==="

# 1. Prepare GCC Source (Depth 1 for speed)
echo "Cloning GCC source (depth=1)..."
git clone --depth=1 https://github.com/gcc-mirror/gcc.git gcc_src > /dev/null 2>&1

# 2. Start GCC Load Generator
# We just run the configure and a partial make to maximize process fork and CPU load
cd gcc_src
./configure --disable-multilib > /dev/null 2>&1
make -j$(nproc) > /dev/null 2>&1 &
LOAD_PID=$!
cd ..

echo "GCC Compilation started (PID: $LOAD_PID) using $(nproc) cores."

# 3. Parallel Monitor Loop
LOG="load_test_results.log"
echo "Timestamp,Steal,IOWait,CtxSwitch,PageFaults,Interrupts,L1_ns,TLB_ns" > $LOG

START_TIME=$(date +%s)
# Use DURATION from env or default to 60s
[ -z "$DURATION" ] && DURATION=60

while [ $(($(date +%s) - START_TIME)) -lt $DURATION ]; do
    # Capture /proc/stat metrics
    STAT_LINE=$(grep "cpu " /proc/stat)
    # Fields: user nice system idle iowait irq softirq steal
    STEAL=$(echo $STAT_LINE | awk '{print $9}')
    IOWAIT=$(echo $STAT_LINE | awk '{print $6}')
    
    # Context Switches and Interrupts
    CS=$(grep "ctxt" /proc/stat | awk '{print $2}')
    INTR=$(grep "intr" /proc/stat | awk '{print $2}')
    
    # Page Faults (Major)
    PF=$(awk '/pgmajfault/ {print $2}' /proc/vmstat)
    
    # Pulse Test
    ./benchmark/bench "L1 Latency" > pulse.tmp
    L1_LAT=$(grep "Avg:" pulse.tmp | awk '{print $2}')
    
    ./benchmark/bench "TLB Miss" > pulse.tmp
    TLB_LAT=$(grep "Avg:" pulse.tmp | awk '{print $2}')

    # Log results
    TS=$(date +%H:%M:%S)
    echo "$TS,$STEAL,$IOWAIT,$CS,$PF,$INTR,$L1_LAT,$TLB_LAT" >> $LOG
    
    echo "[$TS] GCC Compiling... Steal: $STEAL | IOWait: $IOWAIT | L1: $L1_LAT ns"
    sleep 5
done

# 4. Cleanup
echo "Cleaning up load processes..."
pkill -P $LOAD_PID
kill $LOAD_PID
rm -rf gcc_src pulse.tmp

echo "=== Load Test Complete ==="
echo ""
echo "Summary of Infrastructure Degradation during GCC Compile:"
column -t -s, $LOG