import socket
import threading
import json
import sys
import time


def _log(message):
    try:
        print(message, file=sys.stderr)
    except Exception:
        pass


class TCPSend:
    """TCP Client - Send messages to Node.js server on port 3000"""
    def __init__(self, host="127.0.0.1", port=3000):
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
        self.connect()
    
    def connect(self):
        """Connect to TCP server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            _log(f"Python client connected to {self.host}:{self.port}")
        except Exception as e:
            self.connected = False
    
    def send(self, message):
        """Send message to server"""
        if not self.connected:
            try:
                self.connect()
            except:
                return False
        
        try:
            if isinstance(message, dict):
                message = json.dumps(message)
            elif not isinstance(message, str):
                message = str(message)
            
            self.socket.send((message + '\n').encode('utf-8'))
            return True
        except Exception as e:
            self.connected = False
            return False
    
    def send_dict(self, data):
        """Send dictionary as JSON"""
        return self.send(json.dumps(data))
    
    def close(self):
        """Close connection"""
        if self.socket:
            self.socket.close()
            self.connected = False


class TCPServer:
    """TCP Server - Listen for connections from Max on port 3001"""
    def __init__(self, host="127.0.0.1", port=3001):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False
        self.clients = []
        self.handlers = {}
        self.default_handler = None
    
    def set_default_handler(self, handler):
        """Set default message handler"""
        self.default_handler = handler
    
    def map(self, prefix, handler):
        """Map message prefix to handler function"""
        self.handlers[prefix] = handler
    
    def start(self):
        """Start TCP server (threaded)"""
        thread = threading.Thread(target=self._run_server, daemon=True)
        thread.start()
    
    def _run_server(self):
        """Server loop"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            _log(f"Python server listening on {self.host}:{self.port}")
            
            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    _log(f"Max client connected from {address}")
                    
                    # Handle client in separate thread
                    thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, address),
                        daemon=True
                    )
                    thread.start()
                    self.clients.append(client_socket)
                    
                except Exception as e:
                    if self.running:
                        pass
        
        except Exception as e:
            pass
    
    def _handle_client(self, client_socket, address):
        """Handle individual client connection"""
        try:
            while self.running:
                data = client_socket.recv(4096).decode('utf-8')
                
                if not data:
                    break
                
                # Process each message (split by newlines if present)
                messages = data.strip().split('\n')
                for message in messages:
                    if message.strip():
                        self._process_message(message.strip(), address)
        
        except Exception as e:
            pass
        
        finally:
            client_socket.close()
            if client_socket in self.clients:
                self.clients.remove(client_socket)
            _log(f"Max client disconnected from {address}")
    
    def _process_message(self, message, address):
        """Process received message and route to handlers"""
        _log(message)
        
        # Try to parse as JSON
        try:
            data = json.loads(message)
            message_type = data.get('type', 'default')
        except:
            message_type = 'default'
            data = message
        
        # Route to handler if mapped
        if message_type in self.handlers:
            self.handlers[message_type](message)
        elif self.default_handler:
            self.default_handler(message)
    
    def broadcast(self, message):
        """Send message to all connected clients"""
        if isinstance(message, dict):
            message = json.dumps(message)
        
        message_bytes = (message + '\n').encode('utf-8')
        disconnected = []
        
        for client in self.clients:
            try:
                client.send(message_bytes)
            except:
                disconnected.append(client)
        
        # Remove dead connections
        for client in disconnected:
            self.clients.remove(client)
    
    def stop(self):
        """Stop server"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()


# Example usage
if __name__ == "__main__":
    # Python server on 3001 (Max connects here)
    server = TCPServer()
    server.set_default_handler(lambda msg: _log(f"From Max: {msg}"))
    server.start()
    
    # Sender to Node.js on 3000
    sender = TCPSend()
    
    time.sleep(1)
    
    # Send simple message
    sender.send("Hello from Python!")
    
    # Send dictionary
    sender.send_dict({"type": "sensor", "value": 42})
    
    # Keep alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        sender.close()
        server.stop()
