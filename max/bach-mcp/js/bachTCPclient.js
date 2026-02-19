const net = require('net');
const EventEmitter = require('events');
const path = require('path');
const Max = require('max-api');

const PORT = 3001;
const HOST = '127.0.0.1';  // Use explicit IP instead of localhost

// Print to Max console
Max.post(`Loaded ${path.basename(__filename)}`);

// Max MSP compatible TCP client
class MaxTCPClient extends EventEmitter {
  constructor(host = HOST, port = PORT) {
    super();
    this.host = host;
    this.port = port;
    this.socket = null;
    this.connected = false;
    this.reconnectAttempts = 0;
    this.reconnectDelay = 2000; // 2 seconds
    
    this.connect();
  }

  connect() {
    if (this.socket) {
      this.socket.destroy();
    }
    
    this.socket = net.createConnection(this.port, this.host, () => {
      this.connected = true;
      this.reconnectAttempts = 0;
      console.log(`Max client connected to ${this.host}:${this.port}`);
      this.emit('connected');
    });

    // Handle data received from server
    this.socket.on('data', (data) => {
      const message = data.toString('utf8').trim();
      this.emit('message', message);
    });

    // Handle connection closed
    this.socket.on('end', () => {
      this.connected = false;
      console.log('Max client disconnected from server');
      this.emit('disconnected');
      this.attemptReconnect();
    });

    // Handle socket errors
    this.socket.on('error', (err) => {
      this.connected = false;
      this.emit('error', err);
      
      if (err.code === 'ECONNREFUSED') {
        this.attemptReconnect();
      }
    });
  }

  attemptReconnect() {
    this.reconnectAttempts++;
    const delayMs = Math.min(this.reconnectDelay * Math.pow(1.5, this.reconnectAttempts - 1), 30000);
    setTimeout(() => this.connect(), delayMs);
  }

  // Send message to server
  send(message) {
    if (this.connected && this.socket) {
      const payload = message.endsWith('\n') ? message : `${message}\n`;
      this.socket.write(payload);
      Max.post(`[Bach TCP Client] Sent message: ${message}`);
      return true;
    } else {
      Max.post(
        `[Bach TCP Client] Failed to send message (connected=${this.connected}): ${message}`
      );
      return false;
    }
  }

  // Disconnect gracefully
  disconnect() {
    if (this.socket) {
      this.socket.end();
      this.connected = false;
    }
  }

  // Check connection status
  isConnected() {
    return this.connected;
  }
}

// Create global client instance for Max MSP
global.maxTCPClient = new MaxTCPClient(HOST, PORT);

// Event listeners
global.maxTCPClient.on('connected', () => {
  Max.post('[Bach TCP Client] Connected');
});

global.maxTCPClient.on('message', (msg) => {
  Max.outlet(msg);
});

global.maxTCPClient.on('error', (err) => {
  Max.post(`Error: ${err.message}`);
});

global.maxTCPClient.on('disconnected', () => {
  Max.post('[Bach TCP Client] Disconnected');
});

// Register handlers for Max messages
function formatMaxAtom(value) {
  if (Array.isArray(value)) {
    return `[ ${value.map(formatMaxAtom).join(' ')} ]`;
  }
  return String(value);
}

if (Max.MESSAGE_TYPES && Max.MESSAGE_TYPES.ALL) {
  Max.addHandler(Max.MESSAGE_TYPES.ALL, (...args) => {
    Max.post(`[Bach TCP Client] ALL handler args: ${JSON.stringify(args)}`);
  });
}

Max.addHandler("list", (...args) => {
  Max.post(`[Bach TCP Client] list handler args: ${JSON.stringify(args)}`);
});

Max.addHandler("bang", () => {
  Max.post("[Bach TCP Client] bang received");
});

Max.addHandler("sendMessage", function(...args) {
  let message = '';
  Max.post(`[Bach TCP Client] sendMessage raw args: ${JSON.stringify(args)}`);
  
  if (args.length === 0) {
    return false;
  } else if (args.length === 1) {
    message = formatMaxAtom(args[0]);
  } else {
    message = args.map(arg => formatMaxAtom(arg)).join(' ');
  }
  
  const result = global.maxTCPClient.send(message);
  Max.post(
    `[Bach TCP Client] sendMessage result=${result ? 'ok' : 'failed'} payload="${message}"`
  );
  Max.outlet(['sent', message]);
  return result;
});

Max.addHandler("disconnect", () => {
  global.maxTCPClient.disconnect();
});

Max.addHandler("getStatus", () => {
  const status = {
    connected: global.maxTCPClient.isConnected(),
    host: global.maxTCPClient.host,
    port: global.maxTCPClient.port
  };
  Max.outlet(['status', status.connected ? 'connected' : 'disconnected']);
});

Max.addHandler("reconnectTo", (host, port) => {
  const actualHost = host || '127.0.0.1';
  const actualPort = port || 3000;
  global.maxTCPClient.host = actualHost;
  global.maxTCPClient.port = actualPort;
  global.maxTCPClient.reconnectAttempts = 0;
  global.maxTCPClient.connect();
});
