const net = require('net');
const EventEmitter = require('events');
const path = require('path');
const Max = require('max-api');

const PORT = 3000;
const HOST = '0.0.0.0';  // Listen on all interfaces

// Print to Max console
Max.post(`Loaded ${path.basename(__filename)}`);

// Max MSP compatible TCP server
class MaxTCPServer extends EventEmitter {
  constructor(host = HOST, port = PORT) {
    super();
    this.host = host;
    this.port = port;
    this.server = null;
    this.clients = new Map();
    this.clientCounter = 0;
    this.listening = false;
    
    this.start();
  }

  start() {
    if (this.server) {
      return;
    }

    this.server = net.createServer((socket) => {
      this.clientCounter++;
      const clientId = this.clientCounter;
      const clientAddress = `${socket.remoteAddress}:${socket.remotePort}`;
      
      console.log(`Max server: client connected from ${clientAddress}`);
      
      this.clients.set(clientId, {
        socket: socket,
        address: clientAddress,
        id: clientId,
        connected: true
      });

      this.emit('clientConnected', { id: clientId, address: clientAddress });

      // Handle data received from client
      socket.on('data', (data) => {
        const message = data.toString('utf8').trim();
        if (message) {
          // Broadcast to all other connected clients (no echo)
          this.broadcast(`${message}\n`, clientId);

          this.emit('message', { 
            clientId: clientId, 
            address: clientAddress, 
            message: message 
          });
        }
      });

      // Handle client disconnect
      socket.on('end', () => {
        console.log(`Max server: client disconnected from ${clientAddress}`);
        this.clients.delete(clientId);
        this.emit('clientDisconnected', { id: clientId, address: clientAddress });
      });

      // Handle socket errors
      socket.on('error', (err) => {
        this.clients.delete(clientId);
      });
    });

    // Handle server errors
    this.server.on('error', (err) => {
      // Try to restart after a delay if port is in use
      if (err.code === 'EADDRINUSE') {
        setTimeout(() => this.start(), 5000);
      }
    });

    // Start listening
    this.server.listen(this.port, this.host, () => {
      console.log(`Max server listening on ${this.host}:${this.port}`);
      this.listening = true;
      this.emit('started');
    });
  }

  // Broadcast message to all clients except sender
  broadcast(message, excludeClientId = null) {
    this.clients.forEach((client, id) => {
      if (id !== excludeClientId && client.socket) {
        client.socket.write(message);
      }
    });
  }

  // Send message to specific client
  sendToClient(clientId, message) {
    const client = this.clients.get(clientId);
    if (client && client.socket) {
      client.socket.write(message);
      console.log(`[ServerTCP] Sent to client #${clientId}: ${message}`);
      return true;
    } else {
      console.warn(`[ServerTCP] Client #${clientId} not found`);
      return false;
    }
  }

  // Get connected clients info
  getClients() {
    const clientsList = [];
    this.clients.forEach((client, id) => {
      clientsList.push({
        id: id,
        address: client.address,
        connected: client.connected
      });
    });
    return clientsList;
  }

  // Get server status
  getStatus() {
    return {
      listening: this.listening,
      host: this.host,
      port: this.port,
      clientCount: this.clients.size,
      clients: this.getClients()
    };
  }

  // Stop the server
  stop() {
    if (this.server) {
      console.log('[ServerTCP] Stopping server...');
      
      // Close all client connections
      this.clients.forEach((client) => {
        if (client.socket) {
          client.socket.end();
        }
      });
      
      this.server.close(() => {
        console.log('[ServerTCP] Server stopped');
        this.listening = false;
        this.server = null;
        this.emit('stopped');
      });
    }
  }
}

// Create global server instance for Max MSP
global.maxTCPServer = new MaxTCPServer(HOST, PORT);

// Event listeners - output to Max console
global.maxTCPServer.on('started', () => {
  Max.post('[Bach TCP Server] Server started');
  Max.outlet(['status', 'started']);
});

global.maxTCPServer.on('clientConnected', (info) => {
  Max.post(`[Bach TCP Server] Client #${info.id} connected: ${info.address}`);
  Max.outlet(['client_connected', info.id]);
});

global.maxTCPServer.on('clientDisconnected', (info) => {
  Max.post(`[Bach TCP Server] Client #${info.id} disconnected`);
  Max.outlet(['client_disconnected', info.id]);
});

global.maxTCPServer.on('message', (info) => {
  Max.post(`[Bach TCP Server] Client #${info.clientId}: ${info.message}`);
  Max.outlet(['message', info.message]);
});

global.maxTCPServer.on('stopped', () => {
  Max.post('[Bach TCP Server] Server stopped');
  Max.outlet(['status', 'stopped']);
});

// Register handlers for Max messages
Max.addHandler("sendToClient", function(clientId, ...args) {
  let message = '';
  
  if (args.length === 0) {
    Max.post('[Bach TCP Server] sendToClient: No message provided');
    return false;
  } else if (args.length === 1) {
    message = String(args[0]);
  } else {
    message = args.map(arg => String(arg)).join(' ');
  }
  
  return global.maxTCPServer.sendToClient(clientId, message);
});

Max.addHandler("broadcastMessage", function(...args) {
  let message = '';
  
  if (args.length === 0) {
    Max.post('[Bach TCP Server] broadcastMessage: No message provided');
    return;
  } else if (args.length === 1) {
    message = String(args[0]);
  } else {
    message = args.map(arg => String(arg)).join(' ');
  }
  
  global.maxTCPServer.broadcast(message);
  Max.post(`[Bach TCP Server] Broadcasted: ${message}`);
  Max.outlet(['broadcast', message]);
});

Max.addHandler("getClients", () => {
  const clients = global.maxTCPServer.getClients();
  Max.post(`[Bach TCP Server] Connected clients: ${JSON.stringify(clients)}`);
  Max.outlet(['clients', clients.length, ...clients.map(c => `Client#${c.id}`)]);
});

Max.addHandler("getServerStatus", () => {
  const status = global.maxTCPServer.getStatus();
  Max.post(`[Bach TCP Server] Status: ${JSON.stringify(status)}`);
  Max.outlet(['server_status', status.listening ? 'listening' : 'stopped', status.clientCount]);
});

Max.addHandler("stopServer", () => {
  Max.post('[Bach TCP Server] Stopping server...');
  global.maxTCPServer.stop();
});

Max.addHandler("startServer", (host, port) => {
  const actualHost = host || HOST;
  const actualPort = port || PORT;
  if (global.maxTCPServer && global.maxTCPServer.listening) {
    Max.post('[Bach TCP Server] Server already running');
  } else {
    Max.post(`[Bach TCP Server] Starting server on ${actualHost}:${actualPort}`);
    global.maxTCPServer = new MaxTCPServer(actualHost, actualPort);
  }
});

Max.post('[Bach TCP Server] Ready for Max MSP communication');
