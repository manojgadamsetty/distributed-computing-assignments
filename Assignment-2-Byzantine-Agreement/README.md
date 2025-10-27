# Assignment 2 — Byzantine Agreement Protocol using RPC

## Objective
Simulate a Byzantine Agreement protocol (Oral Messages / OM) with a Commander and multiple Lieutenants using XML-RPC. Demonstrates that loyal lieutenants reach agreement even with some Byzantine nodes.

## How it works (provided code)
- One Commander sends an initial order to all Lieutenants.
- Lieutenants run the OM recursive exchange (this implementation supports f >= 0; for demonstration we use f=1).
- Some lieutenants can be configured to act Byzantine (they alter messages).
- After message exchange, each loyal lieutenant computes the final decision (majority) and logs it.

## Run (example)
1. Edit `code/config.json` to set ports and which lieutenants are Byzantine.
2. Start commander and lieutenants (see `run_byzantine.sh`).
