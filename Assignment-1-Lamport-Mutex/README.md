# Assignment 1 — Lamport's Distributed Mutual Exclusion using RPC

## Objective
Simulate N distributed nodes coordinating access to a shared Critical Section (CS) using Lamport's Distributed Mutual Exclusion Algorithm. Communication is via XML-RPC.

## How it works (provided code)
- Each node runs an XML-RPC server exposing `receive_request`, `receive_release`.
- Each node maintains a Lamport logical clock and a local request queue (sorted by timestamp, node id).
- To enter CS, a node:
  1. Increments its clock and broadcasts REQUEST(ts, id) to all nodes.
  2. Waits for ACKs from all other nodes and ensures its request is head of queue.
  3. Enters CS, then broadcasts RELEASE when done.

## Run (example)
1. Edit `code/config.json` if required.
2. Start nodes (three-node example) from separate terminals or use the `run_lamport_nodes.sh` script.

See `Assignment-1-Lamport-Mutex/code/` for scripts and run helpers.
