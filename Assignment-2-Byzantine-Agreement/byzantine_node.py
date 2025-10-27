# byzantine_node.py
import sys
import threading
from xmlrpc.server import SimpleXMLRPCServer
from xmlrpc.client import ServerProxy
from collections import Counter

class Lieutenant:
    def __init__(self, node_id, total_nodes, is_traitor=False):
        self.node_id = node_id
        self.total_nodes = total_nodes
        self.is_traitor = is_traitor
        self.node_addresses = {i: f"http://localhost:{9000 + i}" for i in range(total_nodes)}
        self.messages = {} # Stores messages for each round of OM algorithm
        self.final_decision = None
        self.lock = threading.Lock()

    def _log(self, message):
        traitor_status = "TRAITOR" if self.is_traitor else "LOYAL"
        print(f"[Lieutenant {self.node_id} ({traitor_status})] {message}")

    def receive_order(self, commander_id, order, path):
        """RPC method to receive an order from the commander or another lieutenant."""
        with self.lock:
            # If this lieutenant is a traitor, it might lie or do nothing.
            # Here, a traitorous lieutenant will try to forward a different value.
            if self.is_traitor:
                order = "RETREAT" if order == "ATTACK" else "ATTACK"
                self._log(f"Received order '{order}' via path {path}. As a traitor, I will forward the opposite.")
            else:
                self._log(f"Received order '{order}' via path {path}")
            
            # Store the message based on its path
            path_key = tuple(sorted(path))
            if path_key not in self.messages:
                self.messages[path_key] = []
            self.messages[path_key].append(order)

            # m is the number of traitors we are trying to tolerate.
            # The recursion depth is m. Path length tells us the recursion level.
            # len(path) = 1 means OM(m), len(path) = 2 means OM(m-1), etc.
            m = 1 # We are tolerating 1 traitor in this simulation.
            if len(path) <= m:
                # This lieutenant now acts as a commander for the next round
                new_path = path + [self.node_id]
                lieutenants_to_forward = [i for i in range(1, self.total_nodes) if i not in new_path]
                
                for lt_id in lieutenants_to_forward:
                    # Send order to other lieutenants in a new thread
                    threading.Thread(target=self._forward_order, args=(lt_id, order, new_path)).start()
        return True

    def _forward_order(self, target_id, order, path):
        """Forwards the order to another lieutenant."""
        try:
            proxy = ServerProxy(self.node_addresses[target_id])
            self._log(f"Forwarding order '{order}' to Lieutenant {target_id} with path {path}")
            proxy.receive_order(self.node_id, order, path)
        except Exception as e:
            self._log(f"Error forwarding order to {target_id}: {e}")

    def decide(self):
        """Makes a final decision based on the majority of received messages."""
        # The base value is what we received from the commander directly
        commander_path = tuple(sorted([0])) # Path from commander (ID 0)
        
        # In case the commander was a traitor and didn't send a message
        if commander_path not in self.messages:
             self._log("Did not receive a direct order from the Commander!")
             # In a real scenario, a default action like RETREAT would be chosen.
             self.final_decision = "RETREAT"
             return

        values_to_consider = [self.messages[commander_path][0]]

        # Now, consider values from other lieutenants
        for path, msg_list in self.messages.items():
            # path length of 2 corresponds to messages from OM(m-1) recursion
            if len(path) == 2: 
                values_to_consider.append(msg_list[0])

        self._log(f"Making final decision based on received values: {values_to_consider}")
        
        # Find the majority
        if not values_to_consider:
             self.final_decision = "RETREAT" # Default action
        else:
            most_common = Counter(values_to_consider).most_common(1)
            self.final_decision = most_common[0][0]
        
        self._log(f"-----------> My final decision is: {self.final_decision} <-----------")

def run_lieutenant_server(node):
    port = 9000 + node.node_id
    server = SimpleXMLRPCServer(("localhost", port), logRequests=False)
    server.register_instance(node)
    print(f"Lieutenant {node.node_id} listening on port {port}...")
    server.serve_forever()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python byzantine_node.py <node_id> <total_nodes> [is_traitor]")
        sys.exit(1)

    node_id = int(sys.argv[1])
    total_nodes = int(sys.argv[2])
    is_traitor = sys.argv[3] == 'traitor' if len(sys.argv) > 3 else False
    
    node = Lieutenant(node_id, total_nodes, is_traitor)
    run_lieutenant_server(node)