import sys
import threading
import time
import logging
import random
from xmlrpc.server import SimpleXMLRPCServer
from xmlrpc.client import ServerProxy
from collections import defaultdict, Counter

# ==============================================================================
# 
# UTILITY: LOGGING SETUP
# 
# ==============================================================================

def setup_logging(log_file_name):
    """Configures logging to write to both a file and the console."""
    
    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO) # Set the minimum level to log

    # Clear existing handlers (prevents duplicate logs if function is called again)
    if logger.hasHandlers():
        logger.handlers.clear()

    # Create file handler
    # 'w' mode overwrites the log file on each new run
    file_handler = logging.FileHandler(log_file_name, mode='w')
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    # Use a simpler format for the console
    console_formatter = logging.Formatter('%(message)s') 
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

# ==============================================================================
# 
# ASSIGNMENT 1: LAMPORT'S DISTRIBUTED MUTUAL EXCLUSION
# 
# ==============================================================================

class LamportNode:
    def __init__(self, node_id, total_nodes):
        self.id = node_id
        self.total_nodes = total_nodes
        self.clock = 0
        self.request_queue = []
        self.replies_received = set()
        self.state = 'RELEASED' # Can be RELEASED, WANTED, HELD
        
        # All nodes run on localhost but on different ports
        self.ports = [8000 + i for i in range(total_nodes)]
        self.node_uris = [f"http://localhost:{port}" for port in self.ports]
        
        logging.info(f"Node {self.id} initialized. State: {self.state}, Clock: {self.clock}")

    def _tick_clock(self, received_clock=None):
        """Increments the logical clock."""
        if received_clock:
            self.clock = max(self.clock, received_clock) + 1
        else:
            self.clock += 1
        logging.info(f"Node {self.id}: Clock ticked to {self.clock}")

    # --- RPC Exposed Methods ---
    def receive_request(self, timestamp, sender_id):
        """Handles an incoming CS request from another node."""
        self._tick_clock(timestamp)
        self.request_queue.append((timestamp, sender_id))
        self.request_queue.sort() # Keep queue sorted by timestamp, then by ID
        logging.info(f"Node {self.id}: Received REQUEST from Node {sender_id} with timestamp {timestamp}. Queue: {self.request_queue}")
        # Send a reply back immediately
        return "REPLY"

    def receive_release(self, sender_id):
        """Handles a release message from a node that has exited the CS."""
        self._tick_clock()
        # Find and remove the request from the sender
        self.request_queue = [req for req in self.request_queue if req[1] != sender_id]
        logging.info(f"Node {self.id}: Received RELEASE from Node {sender_id}. Queue: {self.request_queue}")
        return "OK"

    # --- Client-side Logic ---
    def _broadcast(self, method, *args):
        """Helper to send RPCs to all other nodes."""
        for i in range(self.total_nodes):
            if i == self.id:
                continue
            try:
                proxy = ServerProxy(self.node_uris[i])
                if method == 'request':
                    proxy.receive_request(*args)
                    # Successful request implies a reply was received
                    self.replies_received.add(i)
                    logging.info(f"Node {self.id}: Received REPLY from Node {i}")
                elif method == 'release':
                    proxy.receive_release(*args)
            except Exception as e:
                # This can happen if a server isn't up yet.
                # logging.warning(f"Node {self.id}: Could not connect to Node {i} to send {method}. Error: {e}")
                pass

    def request_cs(self):
        """Initiates the process of entering the critical section."""
        if self.state != 'RELEASED':
            logging.warning(f"Node {self.id}: Cannot request CS, current state is {self.state}")
            return

        self.state = 'WANTED'
        self._tick_clock()
        
        # Add self-request to queue
        request_timestamp = self.clock
        self.request_queue.append((request_timestamp, self.id))
        self.request_queue.sort()
        self.replies_received.clear()
        
        logging.info(f"Node {self.id}: State -> {self.state}. Broadcasting REQUEST with timestamp {request_timestamp}")
        
        # Broadcast request to all other nodes
        threading.Thread(target=self._broadcast, args=('request', request_timestamp, self.id)).start()

        # Periodically check if we can enter the CS
        while True:
            # Condition 1: Have we received replies from all other nodes?
            # We need N-1 replies.
            if len(self.replies_received) == self.total_nodes - 1:
                # Condition 2: Is our request at the top of our queue?
                if self.request_queue and self.request_queue[0][1] == self.id:
                    self.enter_cs()
                    break
            time.sleep(0.5)

    def enter_cs(self):
        """Enters the critical section."""
        self.state = 'HELD'
        logging.info(f"\n{'='*10} Node {self.id} has ENTERED the Critical Section! Clock: {self.clock} {'='*10}\n")
        time.sleep(random.randint(3, 5)) # Simulate work
        self.release_cs()

    def release_cs(self):
        """Exits the critical section and informs other nodes."""
        logging.info(f"\n{'='*10} Node {self.id} is EXITING the Critical Section. {'='*10}\n")
        self.state = 'RELEASED'
        
        # Remove own request from the queue
        self.request_queue = [req for req in self.request_queue if req[1] != self.id]
        
        logging.info(f"Node {self.id}: State -> {self.state}. Broadcasting RELEASE.")
        # Broadcast release message
        threading.Thread(target=self._broadcast, args=('release', self.id)).start()

def run_lamport_node(node_id, total_nodes):
    """Initializes and runs the RPC server for a Lamport node."""
    
    # Setup logging to a unique file for this node
    setup_logging(f"lamport_node_{node_id}.log")
    
    node = LamportNode(node_id, total_nodes)
    port = node.ports[node_id]
    server = SimpleXMLRPCServer(("localhost", port), allow_none=True, logRequests=False)
    server.register_instance(node)
    
    logging.info(f"Node {node_id} listening on port {port}...")
    
    # Start the server in a separate thread
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    # Give servers time to start up before nodes start contending for the CS
    time.sleep(2) 
    
    # Simulate the node wanting to access the CS at a random time
    time.sleep(random.uniform(1, 5))
    node.request_cs()
    
    # Keep the main thread alive to allow the server thread to run
    try:
        server_thread.join()
    except KeyboardInterrupt:
        logging.info(f"Node {node_id} shutting down.")
        server.shutdown()

# ==============================================================================
# 
# ASSIGNMENT 2: BYZANTINE AGREEMENT PROTOCOL
# 
# ==============================================================================

class ByzantineNode:
    def __init__(self, node_id, total_nodes, is_traitor):
        self.id = node_id
        self.total_nodes = total_nodes
        self.is_traitor = is_traitor
        self.ports = [9000 + i for i in range(total_nodes)]
        self.node_uris = [f"http://localhost:{port}" for port in self.ports]
        self.messages = defaultdict(list)
        self.final_decision = None
        
        node_type = "TRAITOR" if self.is_traitor else "LOYAL"
        logging.info(f"Node {self.id} ({node_type}) initialized.")

    def _majority(self, values):
        """Finds the majority value. Returns 'DEFAULT_ORDER' if no majority."""
        if not values:
            return "RETREAT" # Default action
        
        counts = Counter(values)
        # Find the most common element and its count
        most_common = counts.most_common(1)
        if most_common:
            return most_common[0][0]
        return "RETREAT"

    # --- RPC Exposed Method ---
    def receive_message(self, commander_id_path, order):
        """Receives a message from another node as part of the OM algorithm."""
        path_str = "->".join(map(str, commander_id_path))
        logging.info(f"Node {self.id}: Received '{order}' via path {path_str}")
        self.messages[path_str].append(order)
        return "OK"

    # --- Client-side Logic (OM Algorithm) ---
    def execute_om(self, m, commander_id_path, order_to_send):
        """
        Executes the Oral Messages algorithm OM(m).
        m: Number of traitors the algorithm should tolerate.
        commander_id_path: A list tracking the chain of command, e.g., [Commander, L1, L2].
        order_to_send: The order this node is sending.
        """
        
        # If this node is a traitor, it may alter the message.
        if self.is_traitor:
            logging.info(f"Node {self.id} (Traitor): Deciding what to send for order '{order_to_send}'...")

        # Broadcast the order to all other Lieutenants
        lieutenants = [i for i in range(self.total_nodes) if i not in commander_id_path]
        
        for lt_id in lieutenants:
            current_order = order_to_send
            if self.is_traitor and lt_id % 2 == 0:
                current_order = "RETREAT" if order_to_send == "ATTACK" else "ATTACK"
                logging.info(f"Node {self.id} (Traitor): Sending MALICIOUS order '{current_order}' to Node {lt_id}")
            else:
                if self.is_traitor:
                    logging.info(f"Node {self.id} (Traitor): Sending order '{current_order}' to Node {lt_id}")

            try:
                proxy = ServerProxy(self.node_uris[lt_id])
                proxy.receive_message(commander_id_path, current_order)
            except Exception as e:
                # logging.warning(f"Node {self.id}: Could not connect to Node {lt_id}. Error: {e}")
                pass
        
    def decide(self, m, commander_id):
        """Makes a final decision based on received messages."""
        if self.id == commander_id:
            logging.info(f"Node {self.id} (Commander) does not decide.")
            return

        # Base case: OM(0) - trust the commander
        if m == 0:
            path_str = str(commander_id)
            self.final_decision = self.messages.get(path_str, ["RETREAT"])[0]
        else:
            # Recursive case OM(m):
            # 1. Value from commander
            v_commander = self.messages.get(str(commander_id), ["RETREAT"])[0]
            
            # 2. Values from other lieutenants
            all_values = [v_commander]
            other_lieutenants = [i for i in range(self.total_nodes) if i != self.id and i != commander_id]

            for lt_id in other_lieutenants:
                # The path for messages relayed by other lieutenants
                path_str = f"{commander_id}->{lt_id}"
                # Get the value they relayed, default to RETREAT if no message
                relayed_value = self.messages.get(path_str, ["RETREAT"])[0]
                all_values.append(relayed_value)
            
            logging.info(f"Node {self.id}: Deciding based on values: {all_values}")
            self.final_decision = self._majority(all_values)

        node_type = "(Traitor)" if self.is_traitor else "(Loyal)"
        logging.info(f"--- Node {self.id} {node_type} Final Decision: {self.final_decision} ---")


def run_byzantine_simulation(total_nodes, num_traitors, commander_order):
    """Sets up nodes and runs the full Byzantine agreement simulation."""
    
    # Setup logging to a single file for the whole simulation
    setup_logging("byzantine.log")
    
    if total_nodes <= 3 * num_traitors:
        logging.error(f"Error: Condition N > 3m not met. N={total_nodes}, m={num_traitors}")
        return

    # Assign traitors (e.g., the highest indexed nodes)
    traitor_ids = {total_nodes - 1 - i for i in range(num_traitors)}
    
    # Initialize all nodes
    nodes = [ByzantineNode(i, total_nodes, i in traitor_ids) for i in range(total_nodes)]
    
    server_threads = []
    # Start RPC servers for each node
    for node in nodes:
        try:
            server = SimpleXMLRPCServer(("localhost", node.ports[node.id]), allow_none=True, logRequests=False)
            server.register_instance(node)
            server_thread = threading.Thread(target=server.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            server_threads.append((server, server_thread))
        except Exception as e:
            logging.error(f"Failed to start server for Node {node.id}: {e}")
            return
            
    time.sleep(1) # Wait for servers to be ready
    
    # --- Start the Algorithm ---
    commander_id = 0
    m = num_traitors
    
    logging.info(f"\n--- STARTING SIMULATION: OM({m}) ---")
    logging.info(f"Commander: Node {commander_id}, Order: '{commander_order}', Traitors: {traitor_ids}\n")
    
    # This simulates the recursive calls of the algorithm
    path_history = [[commander_id]]
    
    for i in range(m + 1):
        current_paths = list(path_history)
        for path in current_paths:
            current_commander_id = path[-1]
            
            # Get the order to send.
            order_to_send = commander_order
            if len(path) > 1:
                prev_path_str = "->".join(map(str, path[:-1]))
                current_commander_node = next((n for n in nodes if n.id == current_commander_id), None)
                if current_commander_node:
                    order_to_send = current_commander_node.messages.get(prev_path_str, ["RETREAT"])[0]

            commander_node = nodes[current_commander_id]
            commander_node.execute_om(m - i, path, order_to_send)
            
            # Generate next set of paths for recursion
            if m - i > 0:
                lieutenants = [n for n in range(total_nodes) if n not in path]
                for lt_id in lieutenants:
                    path_history.append(path + [lt_id])
    
    time.sleep(2) # Allow final messages to be processed
    
    # --- All loyal nodes make their decision ---
    logging.info("\n--- FINAL DECISIONS ---")
    for node in nodes:
        if node.id != commander_id: # Lieutenants decide
            node.decide(m, commander_id)
            
    # Shutdown all servers
    for server, _ in server_threads:
        server.shutdown()
    logging.info("Simulation complete. Servers shutting down.")


# ==============================================================================
# 
# MAIN EXECUTION BLOCK
# 
# ==============================================================================

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Error: Missing assignment name.")
        print("Usage:")
        print("  For Lamport:   python combined_assignments.py lamport <node_id> <total_nodes>")
        print("  For Byzantine: python combined_assignments.py byzantine <total_nodes> <num_traitors> <order>")
        print("\nExample (Lamport Node 0 of 3):")
        print("  python combined_assignments.py lamport 0 3")
        print("\nExample (Byzantine 4 nodes, 1 traitor, 'ATTACK' order):")
        print("  python combined_assignments.py byzantine 4 1 ATTACK")
        sys.exit(1)

    assignment = sys.argv[1]

    try:
        if assignment == 'lamport':
            if len(sys.argv) != 4:
                print("Usage: python combined_assignments.py lamport <node_id> <total_nodes>")
                sys.exit(1)
            node_id = int(sys.argv[2])
            total_nodes = int(sys.argv[3])
            run_lamport_node(node_id, total_nodes)
        
        elif assignment == 'byzantine':
            if len(sys.argv) != 5:
                print("Usage: python combined_assignments.py byzantine <total_nodes> <num_traitors> <order>")
                print("Example: python combined_assignments.py byzantine 4 1 ATTACK")
                sys.exit(1)
            total_nodes = int(sys.argv[2])
            num_traitors = int(sys.argv[3])
            commander_order = sys.argv[4].upper()
            if commander_order not in ["ATTACK", "RETREAT"]:
                print("Error: Order must be 'ATTACK' or 'RETREAT'")
                sys.exit(1)
            run_byzantine_simulation(total_nodes, num_traitors, commander_order)
            
        else:
            print(f"Error: Unknown assignment '{assignment}'. Use 'lamport' or 'byzantine'.")
            sys.exit(1)
            
    except ValueError:
        print("Error: Invalid number provided for arguments.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nShutting down.")