#!/bin/bash

# GPUStat Sidecar Monitor & GCC Load Generator
echo "=== Initializing GCC Load Test & Sidecar Monitor ==="

# 1. Prepare GCC Source
[ ! -d "gcc_src" ] && git clone --depth=1 https://github.com/gcc-mirror/gcc.git gcc_src > /dev/null 2>&1

# 2. Start GCC Load Generator
cd gcc_src
./configure --disable-multilib > /dev/null 2>&1
make -j$(nproc) > /dev/null 2>&1 &
LOAD_PID=$!
cd ..
echo "GCC Compilation started (PID: $LOAD_PID) using $(nproc) cores."

# 3. Parallel Monitor Loop
LOG="load_test_results.log"
echo "Timestamp,Delta_Steal,Delta_IOWait,CtxSwitch,L1_ns,TLB_ns" > $LOG

# Initial values for delta calculation
PREV_STAT=($(grep "cpu " /proc/stat))
PREV_STEAL=${PREV_STAT[8]}
PREV_IOWAIT=${PREV_STAT[5]}

START_TIME=$(date +%s)
[ -z "$DURATION" ] && DURATION=60

while [ $(($(date +%s) - START_TIME)) -lt $DURATION ]; do
    # Capture /proc/stat
    CURR_STAT=($(grep "cpu " /proc/stat))
    CURR_STEAL=${CURR_STAT[8]}
    CURR_IOWAIT=${CURR_STAT[5]}
    
    # Calculate Deltas
    D_STEAL=$((CURR_STEAL - PREV_STEAL))
    D_IOWAIT=$((CURR_IOWAIT - PREV_IOWAIT))
    
    # Update Prev
    PREV_STEAL=$CURR_STEAL
    PREV_IOWAIT=$CURR_IOWAIT
    
    # Context Switches
    CS=$(grep "ctxt" /proc/stat | awk '{print $2}')

    # Pulse Test (High-fidelity parsing)
    # Binary now outputs: "ID. Name | Avg: X.XX | ..."
    L1_OUT=$(./benchmark/bench "L1 Latency")
    L1_LAT=$(echo "$L1_OUT" | awk -F 'Avg:' '{print $2}' | awk '{print $1}')
    
    TLB_OUT=$(./benchmark/bench "TLB Miss")
    TLB_LAT=$(echo "$TLB_OUT" | awk -F 'Avg:' '{print $2}' | awk '{print $1}')

    TS=$(date +%H:%M:%S)
    echo "$TS,$D_STEAL,$D_IOWAIT,$CS,$L1_LAT,$TLB_LAT" >> $LOG
    echo "[$TS] GCC Compiling... D_Steal: $D_STEAL | D_IOWait: $D_IOWAIT | L1: $L1_LAT ns"
    
    sleep 5
done

# 4. Cleanup
pkill -P $LOAD_PID
kill $LOAD_PID
rm -rf gcc_src pulse.tmp

echo "=== Load Test Complete ==="
column -t -s, $LOG
