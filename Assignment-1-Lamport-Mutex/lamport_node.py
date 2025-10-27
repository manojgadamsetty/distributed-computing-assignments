# lamport_node.py
import sys
import threading
import time
import random
from xmlrpc.server import SimpleXMLRPCServer
from xmlrpc.client import ServerProxy

# A Node in the distributed system
class LamportNode:
    def __init__(self, node_id, total_nodes):
        self.node_id = node_id
        self.total_nodes = total_nodes
        self.logical_clock = 0
        self.request_queue = [] # Stores tuples of (timestamp, node_id)
        self.replies_received = set()
        self.state = "RELEASED" # Can be RELEASED, WANTED, HELD
        
        # Node network addresses (e.g., node 0 is at localhost:8000)
        self.node_addresses = {i: f"http://localhost:{8000 + i}" for i in range(total_nodes)}
        
        # Lock for thread-safe operations on shared variables
        self.lock = threading.Lock()

    def _log(self, message):
        """Prints a log message with the node's current state."""
        print(f"[Node {self.node_id}] [Clock: {self.logical_clock}] [State: {self.state}] {message}")

    def _tick_clock(self):
        """Increments the logical clock."""
        self.logical_clock += 1

    # --- RPC Exposed Methods ---

    def receive_request(self, timestamp, requester_id):
        """Handles an incoming REQUEST message from another node."""
        with self.lock:
            self.logical_clock = max(self.logical_clock, timestamp) + 1
            self._log(f"Received REQUEST from Node {requester_id} with timestamp {timestamp}")
            self.request_queue.append((timestamp, requester_id))
            self.request_queue.sort() # Keep queue sorted by timestamp, then node ID
            
            self._tick_clock()
            self._log(f"Sending REPLY back to Node {requester_id}")
        return self.logical_clock # Return clock value for acknowledgement

    def receive_release(self, timestamp, releaser_id):
        """Handles an incoming RELEASE message."""
        with self.lock:
            self.logical_clock = max(self.logical_clock, timestamp) + 1
            self._log(f"Received RELEASE from Node {releaser_id}")
            # Remove the request from the node that just finished
            self.request_queue = [(ts, n_id) for ts, n_id in self.request_queue if n_id != releaser_id]
        return True

    # --- Main Algorithm Logic ---

    def request_cs(self):
        """Initiates the process of entering the Critical Section."""
        with self.lock:
            self.state = "WANTED"
            self._tick_clock()
            my_request = (self.logical_clock, self.node_id)
            self.request_queue.append(my_request)
            self.request_queue.sort()
            self._log(f"Wants to enter CS. Broadcasting REQUEST with timestamp {my_request[0]}.")
            
        # Broadcast request to all other nodes
        for i in range(self.total_nodes):
            if i != self.node_id:
                # Run network call in a separate thread to avoid blocking
                threading.Thread(target=self._send_request, args=(i, my_request)).start()
    
    def _send_request(self, target_node_id, my_request):
        """Sends a request message to a specific node."""
        try:
            proxy = ServerProxy(self.node_addresses[target_node_id])
            # The original algorithm gets replies. Here, the ack of the request serves as the reply.
            proxy.receive_request(my_request[0], my_request[1])
            with self.lock:
                self.replies_received.add(target_node_id)
                self._log(f"Got implicit REPLY from Node {target_node_id}")
        except Exception as e:
            self._log(f"Error connecting to Node {target_node_id}: {e}")
            # In a real system, you'd handle node failure here.

    def release_cs(self):
        """Exits the Critical Section and notifies other nodes."""
        with self.lock:
            self.state = "RELEASED"
            self._tick_clock()
            self.request_queue = [(ts, n_id) for ts, n_id in self.request_queue if n_id != self.node_id]
            self._log("Releasing CS. Broadcasting RELEASE.")

        # Broadcast release to all other nodes
        for i in range(self.total_nodes):
            if i != self.node_id:
                threading.Thread(target=self._send_release, args=(i,)).start()

    def _send_release(self, target_node_id):
        """Sends a release message to a specific node."""
        try:
            proxy = ServerProxy(self.node_addresses[target_node_id])
            proxy.receive_release(self.logical_clock, self.node_id)
        except Exception as e:
            self._log(f"Error sending RELEASE to Node {target_node_id}: {e}")

    def main_loop(self):
        """The main execution loop for the node."""
        while True:
            # Randomly decide to request the CS
            if self.state == "RELEASED" and random.random() < 0.3: # 30% chance each second
                self.request_cs()

            # Check if this node can enter the CS
            if self.state == "WANTED":
                # Condition 1: Have we received replies from all other nodes?
                all_replies_in = len(self.replies_received) == self.total_nodes - 1
                
                # Condition 2: Is our request at the top of the queue?
                is_head_of_queue = False
                if self.request_queue:
                    is_head_of_queue = self.request_queue[0][1] == self.node_id

                if all_replies_in and is_head_of_queue:
                    with self.lock:
                        self.state = "HELD"
                        self._log("🎉 --- Entered Critical Section --- 🎉")

                    # Simulate work in CS
                    time.sleep(random.randint(3, 6))
                    
                    self._log("✅ --- Exiting Critical Section --- ✅")
                    self.replies_received.clear()
                    self.release_cs()
            
            time.sleep(1)

def run_server(node):
    """Starts the RPC server for a node."""
    port = 8000 + node.node_id
    server = SimpleXMLRPCServer(("localhost", port), logRequests=False)
    server.register_instance(node)
    print(f"Node {node.node_id} listening on port {port}...")
    server.serve_forever()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python lamport_node.py <node_id> <total_nodes>")
        sys.exit(1)

    node_id = int(sys.argv[1])
    total_nodes = int(sys.argv[2])
    
    node = LamportNode(node_id, total_nodes)

    # Start the RPC server in a background thread
    server_thread = threading.Thread(target=run_server, args=(node,))
    server_thread.daemon = True
    server_thread.start()

    # Give the server a moment to start up
    time.sleep(2)

    # Start the main logic loop
    node.main_loop()