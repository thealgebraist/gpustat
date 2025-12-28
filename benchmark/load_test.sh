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
echo "Timestamp,Delta_Steal,Delta_IOWait,CtxSwitch,PageFaults,Interrupts,L1_ns,TLB_ns" > $LOG

# Initial values
PREV_STAT=($(grep "cpu " /proc/stat))
PREV_STEAL=${PREV_STAT[8]}
PREV_IOWAIT=${PREV_STAT[5]}
PREV_CS=$(grep "ctxt" /proc/stat | awk '{print $2}')
PREV_INTR=$(grep "intr" /proc/stat | awk '{print $2}')
PREV_PF=$(awk '/pgmajfault/ {print $2}' /proc/vmstat)

START_TIME=$(date +%s)
[ -z "$DURATION" ] && DURATION=60

while [ $(($(date +%s) - START_TIME)) -lt $DURATION ]; do
    # Capture current stats
    CURR_STAT=($(grep "cpu " /proc/stat))
    CURR_STEAL=${CURR_STAT[8]}
    CURR_IOWAIT=${CURR_STAT[5]}
    CURR_CS=$(grep "ctxt" /proc/stat | awk '{print $2}')
    CURR_INTR=$(grep "intr" /proc/stat | awk '{print $2}')
    CURR_PF=$(awk '/pgmajfault/ {print $2}' /proc/vmstat)
    
    # Calculate Deltas
    D_STEAL=$((CURR_STEAL - PREV_STEAL))
    D_IOWAIT=$((CURR_IOWAIT - PREV_IOWAIT))
    D_CS=$((CURR_CS - PREV_CS))
    D_INTR=$((CURR_INTR - PREV_INTR))
    D_PF=$((CURR_PF - PREV_PF))
    
    # Update Previous
    PREV_STEAL=$CURR_STEAL; PREV_IOWAIT=$CURR_IOWAIT; PREV_CS=$CURR_CS; PREV_INTR=$CURR_INTR; PREV_PF=$CURR_PF

    # Pulse Test
    L1_LAT=$(./benchmark/bench "L1 Latency" | awk -F 'Avg:' '{print $2}' | awk '{print $1}')
    TLB_LAT=$(./benchmark/bench "TLB Miss" | awk -F 'Avg:' '{print $2}' | awk '{print $1}')

    TS=$(date +%H:%M:%S)
    echo "$TS,$D_STEAL,$D_IOWAIT,$D_CS,$D_PF,$D_INTR,$L1_LAT,$TLB_LAT" >> $LOG
    echo "[$TS] GCC Compiling... D_Steal: $D_STEAL | D_CS: $D_CS | L1: $L1_LAT ns"
    
    sleep 5
done

# 4. Cleanup
pkill -P $LOAD_PID
kill $LOAD_PID
rm -rf gcc_src

echo "=== Load Test Complete ==="
column -t -s, $LOG