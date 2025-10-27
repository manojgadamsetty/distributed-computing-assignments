#!/usr/bin/env python3
"""
Simple commander script for Byzantine Agreement simulation.
Sends initial order to all lieutenants via XML-RPC.
"""
import json
import argparse
from xmlrpc.client import ServerProxy

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--order", default="ATTACK")
    args = parser.parse_args()

    cfg = json.load(open(args.config))
    lieuts = cfg['lieutenants']

    print(f"[Commander] Sending order='{args.order}' to lieutenants")
    for l in lieuts:
        addr = f"http://{l['host']}:{l['port']}"
        try:
            proxy = ServerProxy(addr, allow_none=True)
            proxy.receive_initial_order(args.order)
            print(f"[Commander] sent to lieutenant {l['id']}")
        except Exception as e:
            print(f"[Commander] failed to contact {l['id']}: {e}")

if __name__ == "__main__":
    main()
