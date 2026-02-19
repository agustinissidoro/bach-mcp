const net = require('net');
const EventEmitter = require('events');
const path = require('path');
const Max = require('max-api');

const SERVER_HOST = '0.0.0.0';
const SERVER_PORT = 3000;
const CLIENT_HOST = '127.0.0.1';
const CLIENT_PORT = 3001;

Max.post(`Loaded ${path.basename(__filename)}`);

class MaxTCPServer extends EventEmitter {
  constructor(host = SERVER_HOST, port = SERVER_PORT) {
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
      this.clientCounter += 1;
      const clientId = this.clientCounter;
      const clientAddress = `${socket.remoteAddress}:${socket.remotePort}`;

      this.clients.set(clientId, {
        socket: socket,
        address: clientAddress,
        id: clientId,
        connected: true,
      });

      this.emit('clientConnected', { id: clientId, address: clientAddress });

      socket.on('data', (data) => {
        const message = data.toString('utf8').trim();
        if (!message) {
          return;
        }
        this.broadcast(`${message}\n`, clientId);
        this.emit('message', {
          clientId: clientId,
          address: clientAddress,
          message: message,
        });
      });

      socket.on('end', () => {
        this.clients.delete(clientId);
        this.emit('clientDisconnected', { id: clientId, address: clientAddress });
      });

      socket.on('error', () => {
        this.clients.delete(clientId);
      });
    });

    this.server.on('error', (err) => {
      if (err.code === 'EADDRINUSE') {
        setTimeout(() => this.start(), 5000);
      }
    });

    this.server.listen(this.port, this.host, () => {
      this.listening = true;
      this.emit('started');
    });
  }

  broadcast(message, excludeClientId = null) {
    this.clients.forEach((client, id) => {
      if (id !== excludeClientId && client.socket) {
        client.socket.write(message);
      }
    });
  }

  sendToClient(clientId, message) {
    const client = this.clients.get(clientId);
    if (!client || !client.socket) {
      Max.post(`[Bach TCP Server] Client #${clientId} not found`);
      return false;
    }
    client.socket.write(message);
    Max.post(`[Bach TCP Server] Sent to client #${clientId}: ${message}`);
    return true;
  }

  getClients() {
    const clientsList = [];
    this.clients.forEach((client, id) => {
      clientsList.push({
        id: id,
        address: client.address,
        connected: client.connected,
      });
    });
    return clientsList;
  }

  getStatus() {
    return {
      listening: this.listening,
      host: this.host,
      port: this.port,
      clientCount: this.clients.size,
      clients: this.getClients(),
    };
  }

  stop() {
    if (!this.server) {
      return;
    }
    this.clients.forEach((client) => {
      if (client.socket) {
        client.socket.end();
      }
    });
    this.server.close(() => {
      this.listening = false;
      this.server = null;
      this.emit('stopped');
    });
  }
}

class MaxTCPClient extends EventEmitter {
  constructor(host = CLIENT_HOST, port = CLIENT_PORT) {
    super();
    this.host = host;
    this.port = port;
    this.socket = null;
    this.connected = false;
    this.reconnectAttempts = 0;
    this.reconnectDelay = 2000;
    this.connect();
  }

  connect() {
    if (this.socket) {
      this.socket.destroy();
    }

    this.socket = net.createConnection(this.port, this.host, () => {
      this.connected = true;
      this.reconnectAttempts = 0;
      this.emit('connected');
    });

    this.socket.on('data', (data) => {
      const message = data.toString('utf8').trim();
      if (message) {
        this.emit('message', message);
      }
    });

    this.socket.on('end', () => {
      this.connected = false;
      this.emit('disconnected');
      this.attemptReconnect();
    });

    this.socket.on('error', (err) => {
      this.connected = false;
      this.emit('error', err);
      if (err.code === 'ECONNREFUSED') {
        this.attemptReconnect();
      }
    });
  }

  attemptReconnect() {
    this.reconnectAttempts += 1;
    const delayMs = Math.min(
      this.reconnectDelay * Math.pow(1.5, this.reconnectAttempts - 1),
      30000
    );
    setTimeout(() => this.connect(), delayMs);
  }

  send(message) {
    if (!this.connected || !this.socket) {
      Max.post(`[Bach TCP Client] Failed to send (connected=${this.connected}): ${message}`);
      return false;
    }
    const payload = message.endsWith('\n') ? message : `${message}\n`;
    this.socket.write(payload);
    Max.post(`[Bach TCP Client] Sent message: ${message}`);
    return true;
  }

  disconnect() {
    if (this.socket) {
      this.socket.end();
      this.connected = false;
    }
  }

  isConnected() {
    return this.connected;
  }
}

function formatMaxAtom(value) {
  if (Array.isArray(value)) {
    return `[ ${value.map(formatMaxAtom).join(' ')} ]`;
  }
  return String(value);
}

global.maxTCPServer = new MaxTCPServer(SERVER_HOST, SERVER_PORT);
global.maxTCPClient = new MaxTCPClient(CLIENT_HOST, CLIENT_PORT);

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

global.maxTCPClient.on('connected', () => {
  Max.post('[Bach TCP Client] Connected');
});

global.maxTCPClient.on('message', (msg) => {
  Max.outlet(msg);
});

global.maxTCPClient.on('error', (err) => {
  Max.post(`[Bach TCP Client] Error: ${err.message}`);
});

global.maxTCPClient.on('disconnected', () => {
  Max.post('[Bach TCP Client] Disconnected');
});

if (Max.MESSAGE_TYPES && Max.MESSAGE_TYPES.ALL) {
  Max.addHandler(Max.MESSAGE_TYPES.ALL, (...args) => {
    Max.post(`[Bach TCP] ALL handler args: ${JSON.stringify(args)}`);
  });
}

Max.addHandler('list', (...args) => {
  Max.post(`[Bach TCP] list handler args: ${JSON.stringify(args)}`);
});

Max.addHandler('bang', () => {
  Max.post('[Bach TCP] bang received');
});

Max.addHandler('sendMessage', (...args) => {
  let message = '';
  Max.post(`[Bach TCP Client] sendMessage raw args: ${JSON.stringify(args)}`);

  if (args.length === 0) {
    return false;
  }
  if (args.length === 1) {
    message = formatMaxAtom(args[0]);
  } else {
    message = args.map((arg) => formatMaxAtom(arg)).join(' ');
  }

  const result = global.maxTCPClient.send(message);
  Max.post(`[Bach TCP Client] sendMessage result=${result ? 'ok' : 'failed'} payload="${message}"`);
  Max.outlet(['sent', message]);
  return result;
});

Max.addHandler('disconnect', () => {
  global.maxTCPClient.disconnect();
});

Max.addHandler('getStatus', () => {
  const status = {
    connected: global.maxTCPClient.isConnected(),
    host: global.maxTCPClient.host,
    port: global.maxTCPClient.port,
  };
  Max.outlet(['status', status.connected ? 'connected' : 'disconnected']);
});

Max.addHandler('reconnectTo', (host, port) => {
  const actualHost = host || CLIENT_HOST;
  const actualPort = port || CLIENT_PORT;
  global.maxTCPClient.host = actualHost;
  global.maxTCPClient.port = actualPort;
  global.maxTCPClient.reconnectAttempts = 0;
  global.maxTCPClient.connect();
});

Max.addHandler('sendToClient', (clientId, ...args) => {
  let message = '';
  if (args.length === 0) {
    Max.post('[Bach TCP Server] sendToClient: No message provided');
    return false;
  }
  if (args.length === 1) {
    message = String(args[0]);
  } else {
    message = args.map((arg) => String(arg)).join(' ');
  }
  return global.maxTCPServer.sendToClient(clientId, message);
});

Max.addHandler('broadcastMessage', (...args) => {
  let message = '';
  if (args.length === 0) {
    Max.post('[Bach TCP Server] broadcastMessage: No message provided');
    return;
  }
  if (args.length === 1) {
    message = String(args[0]);
  } else {
    message = args.map((arg) => String(arg)).join(' ');
  }
  global.maxTCPServer.broadcast(message);
  Max.post(`[Bach TCP Server] Broadcasted: ${message}`);
  Max.outlet(['broadcast', message]);
});

Max.addHandler('getClients', () => {
  const clients = global.maxTCPServer.getClients();
  Max.post(`[Bach TCP Server] Connected clients: ${JSON.stringify(clients)}`);
  Max.outlet(['clients', clients.length, ...clients.map((c) => `Client#${c.id}`)]);
});

Max.addHandler('getServerStatus', () => {
  const status = global.maxTCPServer.getStatus();
  Max.post(`[Bach TCP Server] Status: ${JSON.stringify(status)}`);
  Max.outlet(['server_status', status.listening ? 'listening' : 'stopped', status.clientCount]);
});

Max.addHandler('stopServer', () => {
  Max.post('[Bach TCP Server] Stopping server...');
  global.maxTCPServer.stop();
});

Max.addHandler('startServer', (host, port) => {
  const actualHost = host || SERVER_HOST;
  const actualPort = port || SERVER_PORT;
  if (global.maxTCPServer && global.maxTCPServer.listening) {
    Max.post('[Bach TCP Server] Server already running');
    return;
  }
  Max.post(`[Bach TCP Server] Starting server on ${actualHost}:${actualPort}`);
  global.maxTCPServer = new MaxTCPServer(actualHost, actualPort);
});

Max.post('[Bach TCP] Combined server/client ready for Max MSP communication');
