# Combined Distributed Systems Assignments

This project contains a single Python script, `combined_assignments.py`, used to run simulations for two classic distributed systems algorithms:
1.  **Lamport's Distributed Mutual Exclusion**
2.  **Byzantine Agreement Protocol (Oral Messages)**

All inter-node communication is implemented using Remote Procedure Calls (RPC) via Python's `xmlrpc` library. All output is saved to dedicated `.log` files.

## ⚙️ Prerequisites

* **Python 3.x**

All required modules (`xmlrpc.server`, `xmlrpc.client`, `logging`, `sys`, `threading`, `random`, `collections`) are part of the standard Python library. No external packages are needed.

## 📁 Project Structure

The project is organized into two separate folders, with the main script placed inside each.
├── Assignment-1-Lamport-Mutex/ │ 
├── combined_assignments.py 
│ └── ... (logs will be created here) │ 
├── Assignment-2-Byzantine-Agreement/ │ 
├ └── ... (logs will be created here) │ 
├── combined_assignments.py 
│ └── ... (log will be created here) 
│ └── README.md


##  How to Run

You must `cd` into the specific assignment's folder *before* running any commands.

### Assignment 1: Lamport's Mutual Exclusion

This simulation requires running **multiple instances** of the script, one for each node in the distributed system.

1.  **Navigate** to the Lamport folder:
    ```bash
    cd Assignment-1-Lamport-Mutex
    ```
2.  **Open multiple terminals** (e.g., 3 terminals for a 3-node simulation).
3.  In each terminal, run the script with a unique `<node_id>`.

**Syntax:**
```bash
python combined_assignments.py lamport <node_id> <total_nodes>

Example (3-Node System):
python combined_assignments.py lamport 0 3
python combined_assignments.py lamport 1 3
python combined_assignments.py lamport 2 3
