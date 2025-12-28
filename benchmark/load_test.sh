#!/bin/bash

# GPUStat Sidecar Monitor & Load Generator
# Targets 8 specific stats under heavy load

echo "=== Initializing Load Test Sidecar Monitor ==="

# 1. Start Load Generator (Stressing CPU and I/O)
# We use openssl speed as a portable high-intensity CPU burner
openssl speed -multi $(nproc) > /dev/null 2>&1 &
LOAD_PID=$!
echo "Load Generator started (PID: $LOAD_PID) using $(nproc) cores."

# 2. Parallel Monitor Loop
LOG="load_test_results.log"
echo "Timestamp,Steal,IOWait,CtxSwitch,PageFaults,Interrupts,L1_ns,TLB_ns" > $LOG

START_TIME=$(date +%s)
DURATION=60 # Run for 60 seconds for CI purposes

while [ $(($(date +%s) - START_TIME)) -lt $DURATION ]; do
    # Capture /proc/stat metrics
    STAT_LINE=$(grep "cpu " /proc/stat)
    STEAL=$(echo $STAT_LINE | awk '{print $9}')
    IOWAIT=$(echo $STAT_LINE | awk '{print $6}')
    
    # Context Switches and Interrupts
    CS=$(grep "ctxt" /proc/stat | awk '{print $2}')
    INTR=$(grep "intr" /proc/stat | awk '{print $2}')
    
    # Page Faults (Major)
    PF=$(awk '/pgmajfault/ {print $2}' /proc/vmstat)
    
    # Frequency (Current Avg)
    FREQ=$(grep "cpu MHz" /proc/cpuinfo | head -n 1 | awk '{print $4}')
    [ -z "$FREQ" ] && FREQ="N/A"

    # Pulse Test (Run subset of 64-test suite)
    # Redirecting to temp file to parse mean
    ./benchmark/bench "L1 Latency" > pulse.tmp
    L1_LAT=$(grep "Avg:" pulse.tmp | awk '{print $2}')
    
    ./benchmark/bench "TLB Miss" > pulse.tmp
    TLB_LAT=$(grep "Avg:" pulse.tmp | awk '{print $2}')

    # Log results
    TS=$(date +%H:%M:%S)
    echo "$TS,$STEAL,$IOWAIT,$CS,$PF,$INTR,$L1_LAT,$TLB_LAT" >> $LOG
    
    echo "[$TS] Load Active. Steal: $STEAL | IOWait: $IOWAIT | L1: $L1_LAT ns | Freq: $FREQ MHz"
    sleep 5
done

# 3. Cleanup
kill $LOAD_PID
echo "=== Load Test Complete ==="
echo ""
echo "Summary of Infrastructure Degradation:"
column -t -s, $LOG
rm pulse.tmp
