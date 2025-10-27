#!/usr/bin/env python3
"""
Lieutenant implementation for Byzantine Agreement (Oral Messages OM(m)).

Run:
  python lieutenant.py --id 1 --config config.json

Each lieutenant starts an RPC server exposing:
- receive_initial_order(order) : called by commander
- receive_message(order, path)  : called recursively by other lieutenants

We implement a simple OM(m) where m = f from config. For demonstration and clarity:
- Each lieutenant collects messages into a tree structure (dictionary).
- If marked Byzantine, a lieutenant may flip/alter messages when forwarding.
- Final decision is majority of collected values.

This is a didactic simulation (suitable for small N).
"""
import argparse
import json
import threading
import time
from xmlrpc.server import SimpleXMLRPCServer
from xmlrpc.client import ServerProxy
from collections import defaultdict, Counter

class Lieutenant:
    def __init__(self, node_id, config_path):
        self.id = node_id
        with open(config_path) as f:
            cfg = json.load(f)
        self.cfg = cfg
        self.lieuts = {l['id']:(l['host'], l['port'], l.get('byzantine', False)) for l in cfg['lieutenants']}
        if self.id not in self.lieuts:
            raise ValueError("Lieutenant id not found in config")
        self.host, self.port, self.byzantine = self.lieuts[self.id]
        self.f = cfg.get('f', 1)

        # message tree: mapping from path tuple -> value
        self.msgs = {}  # e.g. ('C', 2, 3) -> "ATTACK"
        self.msgs_lock = threading.Lock()

        # RPC server
        self.server = SimpleXMLRPCServer(("0.0.0.0", self.port), allow_none=True, logRequests=False)
        self.server.register_function(self.receive_initial_order, 'receive_initial_order')
        self.server.register_function(self.receive_message, 'receive_message')
        self.running = True

    def start(self):
        t = threading.Thread(target=self._serve, daemon=True)
        t.start()
        print(f"[Lieutenant {self.id}] RPC server running at {self.host}:{self.port} (byzantine={self.byzantine})")

    def _serve(self):
        while self.running:
            try:
                self.server.handle_request()
            except Exception as e:
                print("Server handle error:", e)

    # Called by commander
    def receive_initial_order(self, order):
        print(f"[Lieutenant {self.id}] Received INITIAL order from Commander: {order}")
        # store under path ('C', self.id)
        with self.msgs_lock:
            self.msgs[('C', self.id)] = order
        # start OM recursion with m = f
        threading.Thread(target=self._om_recursive, args=(order, [], self.f), daemon=True).start()
        return True

    # Called by other lieutenants during recursion
    def receive_message(self, value, path):
        # path is list of sender ids (path from commander to here)
        path_t = tuple(path)
        with self.msgs_lock:
            # store first message for that path
            if path_t not in self.msgs:
                self.msgs[path_t] = value
                print(f"[Lieutenant {self.id}] Received message for path {path_t}: {value}")
                # if further recursion needed, forward with m-1
                m_remaining = self.f - (len(path)) + 0  # initial call had 0 path length
                # We will not compute m_remaining exactly here; we forward until path length == f
                if len(path) < self.f:
                    threading.Thread(target=self._forward_message, args=(value, path), daemon=True).start()
        return True

    def _maybe_corrupt(self, val):
        # Byzantine behavior: flip between ATTACK and RETREAT (or add suffix)
        if not self.byzantine:
            return val
        # corrupt deterministically for reproducibility
        if val == "ATTACK":
            return "RETREAT"
        elif val == "RETREAT":
            return "ATTACK"
        else:
            return val + "_BYZ"

    def _forward_message(self, value, path):
        # forward to all lieutenants except those already in path and except self
        new_path = list(path) + [self.id]
        for lid, (h, p, byz) in self.lieuts.items():
            if lid == self.id:
                continue
            if lid in path:
                continue
            try:
                # corrupt value if this lieutenant is Byzantine when forwarding
                forward_val = self._maybe_corrupt(value)
                proxy = ServerProxy(f'http://{h}:{p}', allow_none=True)
                proxy.receive_message(forward_val, new_path)
                print(f"[Lieutenant {self.id}] forwarded {forward_val} to {lid} via path {new_path}")
            except Exception as e:
                print(f"[Lieutenant {self.id}] forward to {lid} failed: {e}")

    def _om_recursive(self, value, path, m):
        # Called to initiate OM(m) forwarding from this node.
        # value: value received (from commander or another lieutenant)
        # path: list of ids already in the path
        # m: remaining recursion depth
        if m <= 0:
            return
        # forward to each lieutenant not in path and not self
        new_path = list(path) + [self.id]
        for lid, (h, p, byz) in self.lieuts.items():
            if lid == self.id or lid in path:
                continue
            try:
                forward_val = self._maybe_corrupt(value)
                proxy = ServerProxy(f'http://{h}:{p}', allow_none=True)
                proxy.receive_message(forward_val, new_path)
                print(f"[Lieutenant {self.id}] OM forward {forward_val} to {lid} via {new_path} (m={m-1})")
            except Exception as e:
                print(f"[Lieutenant {self.id}] OM forward to {lid} failed: {e}")
            # do not block; remote nodes will continue recursion when they receive messages

    # Start OM algorithm local termination / decision (called manually after some wait)
    def decide(self):
        # Wait a while for messages to propagate
        print(f"[Lieutenant {self.id}] Waiting for messages to propagate...")
        time.sleep(2 + self.f)  # simple wait; in robust version use synchronization
        with self.msgs_lock:
            values = list(self.msgs.values())
        # majority decision among collected values (simple heuristic)
        if not values:
            print(f"[Lieutenant {self.id}] No messages received.")
            return None
        c = Counter(values)
        decision, count = c.most_common(1)[0]
        print(f"[Lieutenant {self.id}] Collected messages: {self.msgs}")
        print(f"[Lieutenant {self.id}] DECISION = {decision} (count={count})")
        return decision

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", type=int, required=True)
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--decide-after", type=int, default=5)
    args = parser.parse_args()

    lt = Lieutenant(args.id, args.config)
    lt.start()

    # simple REPL to decide after some time
    try:
        while True:
            cmd = input(f"\n[Lieutenant {args.id}] Type 'decide' to compute final decision, 'q' to quit: ").strip()
            if cmd == "decide":
                lt.decide()
            elif cmd == "q":
                lt.running = False
                break
    except KeyboardInterrupt:
        print("Exiting...")

if __name__ == "__main__":
    main()
