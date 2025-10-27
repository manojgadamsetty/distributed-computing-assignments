#!/usr/bin/env python3
"""
Lamport Distributed Mutual Exclusion - XML-RPC implementation.

Run:
  python node.py --id 1 --config config.json

Example to launch 3 nodes (in separate terminals):
  python node.py --id 1 --config config.json
  python node.py --id 2 --config config.json
  python node.py --id 3 --config config.json

This file implements:
- RPC handlers: receive_request(ts, node_id), receive_release(node_id)
- Client broadcast functions to send requests/releases and collect ACKs
- A simple CLI to request entering the Critical Section
"""
import argparse
import json
import threading
import time
from xmlrpc.server import SimpleXMLRPCServer
from xmlrpc.client import ServerProxy, Fault, ProtocolError

class LamportNode:
    def __init__(self, node_id, config_path):
        self.id = node_id
        with open(config_path, 'r') as f:
            cfg = json.load(f)
        self.nodes = {n['id']:(n['host'], n['port']) for n in cfg['nodes']}
        if self.id not in self.nodes:
            raise ValueError("Node id not in config")
        self.host, self.port = self.nodes[self.id]

        # Lamport clock and request queue
        self.clock = 0
        self.clock_lock = threading.Lock()
        # queue: list of (timestamp, node_id)
        self.request_queue = []
        self.queue_lock = threading.Lock()

        # For waiting on ACKs
        self.ack_event = threading.Event()
        self.ack_count_lock = threading.Lock()
        self.ack_count = 0

        # RPC server
        self.server = SimpleXMLRPCServer(("0.0.0.0", self.port), allow_none=True, logRequests=False)
        self.server.register_function(self.receive_request, 'receive_request')
        self.server.register_function(self.receive_release, 'receive_release')
        self.running = True

    def start(self):
        t = threading.Thread(target=self._serve, daemon=True)
        t.start()
        print(f"[Node {self.id}] RPC server started on {self.host}:{self.port}")

    def _serve(self):
        while self.running:
            try:
                self.server.handle_request()
            except Exception as e:
                print("Server handle error:", e)

    # RPC handlers
    def receive_request(self, ts, node_id):
        # Called by other nodes when they request the CS
        with self.clock_lock:
            self.clock = max(self.clock, ts) + 1
            cur = self.clock
        with self.queue_lock:
            # append and keep queue sorted by (ts, id)
            self.request_queue.append((ts, node_id))
            self.request_queue.sort()
        # Return ACK (True)
        print(f"[Node {self.id}] recv REQUEST from {node_id} (ts={ts}) -> clock={cur}")
        return True

    def receive_release(self, node_id):
        # Called when a node exits CS
        with self.clock_lock:
            self.clock += 1
            cur = self.clock
        with self.queue_lock:
            # remove any entries with node_id
            self.request_queue = [r for r in self.request_queue if r[1] != node_id]
        print(f"[Node {self.id}] recv RELEASE from {node_id} -> clock={cur}")
        return True

    # Utilities: broadcast request, release and collect ACKs
    def broadcast_request(self, ts):
        # reset ack counter
        with self.ack_count_lock:
            self.ack_count = 0
        self.ack_event.clear()

        for nid, (h, p) in self.nodes.items():
            if nid == self.id:
                continue
            try:
                proxy = ServerProxy(f'http://{h}:{p}', allow_none=True)
                proxy.receive_request(ts, self.id)
                with self.ack_count_lock:
                    self.ack_count += 1
            except Exception as e:
                print(f"[Node {self.id}] Request to {nid} failed: {e}")

        # local node also appends its own request (done by caller)
        # wait until ack_count == N-1
        total_needed = len(self.nodes) - 1
        # Note: we used synchronous calls and incremented ack_count immediately
        # For resilience, just check ack_count value:
        with self.ack_count_lock:
            got = self.ack_count
        if got >= total_needed:
            return True
        else:
            # Could wait with retries, but for this simple simulation return False if insufficient
            return False

    def broadcast_release(self):
        for nid, (h, p) in self.nodes.items():
            if nid == self.id:
                continue
            try:
                proxy = ServerProxy(f'http://{h}:{p}', allow_none=True)
                proxy.receive_release(self.id)
            except Exception as e:
                print(f"[Node {self.id}] Release to {nid} failed: {e}")

    # CLI interaction for requesting critical section
    def request_critical_section(self):
        # increment clock, create request timestamp
        with self.clock_lock:
            self.clock += 1
            ts = self.clock
        # append self request locally
        with self.queue_lock:
            self.request_queue.append((ts, self.id))
            self.request_queue.sort()
        print(f"[Node {self.id}] Broadcasting REQUEST ts={ts}")
        ok = self.broadcast_request(ts)
        if not ok:
            print(f"[Node {self.id}] WARN: Did not receive enough ACKs; continuing anyway")

        # wait until our request is head of queue
        while True:
            with self.queue_lock:
                head = self.request_queue[0] if self.request_queue else None
            if head == (ts, self.id):
                break
            time.sleep(0.1)

        # Enter critical section
        print(f"[Node {self.id}] >>> Entering Critical Section (ts={ts})")
        time.sleep(2)  # simulate CS work
        print(f"[Node {self.id}] <<< Exiting Critical Section (ts={ts})")

        # remove self request locally and broadcast release
        with self.queue_lock:
            self.request_queue = [r for r in self.request_queue if r[1] != self.id]
        self.broadcast_release()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", type=int, required=True)
    parser.add_argument("--config", default="config.json")
    args = parser.parse_args()

    node = LamportNode(args.id, args.config)
    node.start()

    # Simple CLI to request CS
    try:
        while True:
            cmd = input(f"\n[Node {args.id}] Type 'req' to request CS, 'q' to quit: ").strip()
            if cmd == "req":
                node.request_critical_section()
            elif cmd == "q":
                print("Shutting down...")
                node.running = False
                break
    except KeyboardInterrupt:
        print("KeyboardInterrupt, exiting...")

if __name__ == "__main__":
    main()
