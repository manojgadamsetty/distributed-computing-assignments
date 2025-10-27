#!/usr/bin/env bash
# Start three lamport nodes in background (logs in files)
# Usage: ./run_lamport_nodes.sh
python3 node.py --id 1 --config config.json > node1.log 2>&1 &
sleep 0.5
python3 node.py --id 2 --config config.json > node2.log 2>&1 &
sleep 0.5
python3 node.py --id 3 --config config.json > node3.log 2>&1 &
echo "Started 3 nodes: logs -> node1.log node2.log node3.log"
