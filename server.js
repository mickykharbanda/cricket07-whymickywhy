#!/usr/bin/env node
/**
 * Cricket 07 Local & Public Multiplayer Host Server
 * - Serves the game with COOP/COEP headers and HTTP Range support
 * - Implements the full WebSocket NetplayRoom protocol (/netplay/<CODE> & /_netplay_ticket)
 * - Automatically launches a Cloudflare Quick Tunnel (https://*.trycloudflare.com)
 *   so your cousin/friends can open your server over HTTPS from anywhere!
 */

const http = require('http');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const os = require('os');
const { spawn } = require('child_process');

const PORT = Number(process.env.PORT || process.argv[2] || 8080);
const ROOT = __dirname;
const WASM_ETAG = '"d97d70fc5de1b71d0fd9c29f8f1392d7"';

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.wasm': 'application/wasm',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
  '.csv': 'text/csv; charset=utf-8',
  '.big': 'application/octet-stream',
  '.gob': 'application/octet-stream',
  '.viv': 'application/octet-stream',
  '.vp6': 'application/octet-stream',
  '.exe': 'application/octet-stream',
};

// ------------------------------------------------------------------ Network & Tunnel Info

function getLanIp() {
  const nets = os.networkInterfaces();
  for (const name of Object.keys(nets)) {
    for (const net of nets[name] || []) {
      if (net.family === 'IPv4' && !net.internal) return net.address;
    }
  }
  return '127.0.0.1';
}

let publicTunnelUrl = null;
let tunnelStatus = 'starting';
let tunnelProc = null;

function startCloudflareTunnel() {
  const candidates = [
    '/opt/homebrew/bin/cloudflared',
    '/usr/local/bin/cloudflared',
    path.join(ROOT, 'bin', 'cloudflared'),
    'cloudflared',
  ];
  let bin = candidates.find((p) => p === 'cloudflared' || fs.existsSync(p));
  if (!bin) {
    tunnelStatus = 'unavailable';
    return;
  }

  try {
    tunnelProc = spawn(bin, ['tunnel', '--url', `http://127.0.0.1:${PORT}`, '--no-autoupdate'], {
      stdio: ['ignore', 'pipe', 'pipe'],
    });
    const onData = (chunk) => {
      const text = chunk.toString();
      const m = text.match(/https:\/\/[a-z0-9-]+\.trycloudflare\.com/i);
      if (m && !publicTunnelUrl) {
        publicTunnelUrl = m[0];
        tunnelStatus = 'ready';
        console.log(`\n=============================================================`);
        console.log(`  PUBLIC SHARE URL (for your cousin): ${publicTunnelUrl}`);
        console.log(`=============================================================\n`);
      }
    };
    tunnelProc.stdout.on('data', onData);
    tunnelProc.stderr.on('data', onData);
    tunnelProc.on('error', () => { tunnelStatus = 'unavailable'; });
    tunnelProc.on('exit', () => {
      if (!publicTunnelUrl) tunnelStatus = 'unavailable';
    });
    const killTunnel = () => {
      try { tunnelProc?.kill('SIGTERM'); } catch {}
    };
    process.on('exit', killTunnel);
    process.on('SIGINT', () => { killTunnel(); process.exit(0); });
    process.on('SIGTERM', () => { killTunnel(); process.exit(0); });
  } catch {
    tunnelStatus = 'unavailable';
  }
}

// ------------------------------------------------------------------ ICE / TURN Ticket

let cachedIce = null;
let cachedIceAt = 0;

const FALLBACK_ICE = [
  { urls: ['stun:stun.cloudflare.com:3478', 'stun:stun.cloudflare.com:443', 'stun:stun.l.google.com:19302'] },
];

async function getIceServers() {
  if (cachedIce && Date.now() - cachedIceAt < 10 * 60 * 1000) return cachedIce;
  try {
    const res = await fetch('https://cricket07.dhaiwat.com/_netplay_ticket', {
      signal: AbortSignal.timeout(3500),
    });
    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data.iceServers)) {
        cachedIce = data.iceServers;
        cachedIceAt = Date.now();
        return cachedIce;
      }
    }
  } catch {
    // Offline or upstream unreachable; use standard STUN
  }
  return FALLBACK_ICE;
}

// ------------------------------------------------------------------ Minimal RFC 6455 WebSocket Implementation

function acceptWebSocket(req, socket) {
  const key = req.headers['sec-websocket-key'];
  if (!key) { socket.destroy(); return null; }
  const accept = crypto
    .createHash('sha1')
    .update(key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11')
    .digest('base64');

  socket.write(
    'HTTP/1.1 101 Switching Protocols\r\n' +
    'Upgrade: websocket\r\n' +
    'Connection: Upgrade\r\n' +
    `Sec-WebSocket-Accept: ${accept}\r\n\r\n`
  );
  socket.setNoDelay(true);

  const ws = {
    readyState: 1,
    onmessage: null,
    onclose: null,
    send(data) {
      if (ws.readyState !== 1) return;
      const payload = Buffer.from(typeof data === 'string' ? data : JSON.stringify(data), 'utf8');
      const len = payload.length;
      let header;
      if (len < 126) {
        header = Buffer.alloc(2);
        header[0] = 0x81; // FIN + text frame
        header[1] = len;
      } else if (len < 65536) {
        header = Buffer.alloc(4);
        header[0] = 0x81;
        header[1] = 126;
        header.writeUInt16BE(len, 2);
      } else {
        header = Buffer.alloc(10);
        header[0] = 0x81;
        header[1] = 127;
        header.writeBigUInt64BE(BigInt(len), 2);
      }
      try { socket.write(Buffer.concat([header, payload])); } catch { /* ignore */ }
    },
    close() {
      if (ws.readyState !== 1) return;
      ws.readyState = 3;
      try {
        socket.write(Buffer.from([0x88, 0x00]));
        socket.end();
      } catch { /* ignore */ }
    },
  };

  let buf = Buffer.alloc(0);
  socket.on('data', (chunk) => {
    buf = Buffer.concat([buf, chunk]);
    while (buf.length >= 2) {
      const b0 = buf[0];
      const b1 = buf[1];
      const opcode = b0 & 0x0f;
      const masked = (b1 & 0x80) !== 0;
      let len = b1 & 0x7f;
      let offset = 2;

      if (len === 126) {
        if (buf.length < 4) return;
        len = buf.readUInt16BE(2);
        offset = 4;
      } else if (len === 127) {
        if (buf.length < 10) return;
        len = Number(buf.readBigUInt64BE(2));
        offset = 10;
      }

      const maskLen = masked ? 4 : 0;
      if (buf.length < offset + maskLen + len) return;

      const payload = Buffer.from(buf.subarray(offset + maskLen, offset + maskLen + len));
      if (masked) {
        const mask = buf.subarray(offset, offset + 4);
        for (let i = 0; i < payload.length; i++) payload[i] ^= mask[i & 3];
      }
      buf = buf.subarray(offset + maskLen + len);

      if (opcode === 0x08) { // Close
        ws.readyState = 3;
        socket.end();
        ws.onclose?.();
        return;
      } else if (opcode === 0x09) { // Ping -> Pong
        try { socket.write(Buffer.concat([Buffer.from([0x8a, payload.length]), payload])); } catch {}
      } else if (opcode === 0x01 || opcode === 0x02) {
        ws.onmessage?.(payload.toString('utf8'));
      }
    }
  });

  const handleClose = () => {
    if (ws.readyState === 3) return;
    ws.readyState = 3;
    ws.onclose?.();
  };
  socket.on('close', handleClose);
  socket.on('error', handleClose);

  return ws;
}

// ------------------------------------------------------------------ Netplay Rooms

const rooms = new Map(); // code -> { code, started, version, players: Map<slot, player> }

function getOrCreateRoom(code) {
  let room = rooms.get(code);
  if (!room) {
    room = {
      code,
      started: null,
      version: null,
      players: new Map(), // slot -> { slot, name, version, rtt, p2p, ws, leftTimer }
    };
    rooms.set(code, room);
  }
  return room;
}

function broadcastLobby(room) {
  const playersList = [...room.players.values()]
    .sort((a, b) => a.slot - b.slot)
    .map((p) => ({
      slot: p.slot,
      name: p.name,
      version: p.version,
      rtt: p.rtt || 0,
      p2p: p.p2p || {},
      via: 'MAC',
    }));

  for (const p of room.players.values()) {
    p.ws?.send({
      t: 'lobby',
      you: p.slot,
      host: p.slot === 0,
      players: playersList,
      started: room.started,
      colo: 'Your Mac Host',
    });
  }
}

function handleRoomConnection(code, ws) {
  const room = getOrCreateRoom(code);
  let myPlayer = null;

  ws.onmessage = (raw) => {
    let m;
    try { m = JSON.parse(raw); } catch { return; }

    if (m.t === 'ping') {
      ws.send({ t: 'pong', ts: m.ts });
      return;
    }

    if (m.t === 'hello') {
      if (room.started) {
        ws.send({ t: 'error', msg: 'That game has already started.' });
        ws.close();
        return;
      }
      if (room.players.size >= 2) {
        ws.send({ t: 'error', msg: 'This room already has 2 players.' });
        ws.close();
        return;
      }
      const slot = room.players.has(0) ? 1 : 0;
      myPlayer = {
        slot,
        name: String(m.name || 'Player').slice(0, 24),
        version: m.version || 'local',
        rtt: 0,
        p2p: {},
        ws,
      };
      room.players.set(slot, myPlayer);
      console.log(`[Netplay] Room ${code}: Player "${myPlayer.name}" joined as slot ${slot}`);
      broadcastLobby(room);
      return;
    }

    if (m.t === 'rejoin') {
      const p = room.players.get(m.slot);
      if (!p) {
        ws.send({ t: 'error', msg: 'Session expired.' });
        ws.close();
        return;
      }
      if (p.leftTimer) { clearTimeout(p.leftTimer); p.leftTimer = null; }
      p.ws = ws;
      myPlayer = p;
      ws.send({ t: 'rejoined' });
      console.log(`[Netplay] Room ${code}: Slot ${m.slot} rejoined`);
      return;
    }

    if (!myPlayer) return;

    if (m.t === 'rtt') {
      myPlayer.rtt = Math.round(Number(m.ms) || 0);
      if (!room.started) broadcastLobby(room);
    } else if (m.t === 'p2p') {
      myPlayer.p2p = m.rtt || {};
      if (!room.started) broadcastLobby(room);
    } else if (m.t === 'sig') {
      const target = room.players.get(Number(m.to));
      target?.ws?.send({ t: 'sig', from: myPlayer.slot, data: m.data });
    } else if (m.t === 'start') {
      if (myPlayer.slot !== 0 || room.players.size < 2 || room.started) return;
      room.started = true;
      const delay = Math.max(2, Math.min(30, Number(m.delay) || 4));
      console.log(`[Netplay] Room ${code}: Match starting (2 players, delay=${delay} frames)`);
      for (const p of room.players.values()) {
        p.ws?.send({
          t: 'start',
          players: room.players.size,
          delay,
          you: p.slot,
        });
      }
    } else if (m.t === 'in') {
      for (const p of room.players.values()) {
        if (p.slot !== myPlayer.slot) {
          p.ws?.send({ t: 'in', d: m.d, h: m.h });
        }
      }
    }
  };

  ws.onclose = () => {
    if (!myPlayer || myPlayer.ws !== ws) return;
    myPlayer.ws = null;
    if (!room.started) {
      room.players.delete(myPlayer.slot);
      // If slot 0 left while slot 1 is still in lobby, promote slot 1 to host (slot 0)
      if (myPlayer.slot === 0 && room.players.has(1)) {
        const remaining = room.players.get(1);
        room.players.delete(1);
        remaining.slot = 0;
        room.players.set(0, remaining);
      }
      if (room.players.size === 0) rooms.delete(code);
      else broadcastLobby(room);
    } else {
      // Give 15s for reconnect before marking player left
      myPlayer.leftTimer = setTimeout(() => {
        room.players.delete(myPlayer.slot);
        for (const p of room.players.values()) {
          p.ws?.send({ t: 'left', slot: myPlayer.slot });
        }
        if (room.players.size === 0) rooms.delete(code);
      }, 15000);
    }
  };
}

// ------------------------------------------------------------------ HTTP Server

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
  const pathname = decodeURIComponent(url.pathname);

  // Required COOP/COEP headers for SharedArrayBuffer & Wasm pthreads
  res.setHeader('Cross-Origin-Opener-Policy', 'same-origin');
  res.setHeader('Cross-Origin-Embedder-Policy', 'require-corp');
  res.setHeader('Cross-Origin-Resource-Policy', 'same-origin');

  if (pathname === '/_netplay_ticket') {
    const iceServers = await getIceServers();
    const ticket = `${Math.floor(Date.now() / 1000) + 3600}.${crypto.randomBytes(16).toString('hex')}`;
    res.writeHead(200, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
    res.end(JSON.stringify({ ticket, iceServers }));
    return;
  }

  if (pathname === '/_host_info') {
    const lanIp = getLanIp();
    res.writeHead(200, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
    res.end(
      JSON.stringify({
        localUrl: `http://localhost:${PORT}`,
        lanUrl: `http://${lanIp}:${PORT}`,
        publicUrl: publicTunnelUrl,
        tunnelStatus,
        activeRooms: [...rooms.values()].map((r) => ({
          code: r.code,
          players: r.players.size,
          started: !!r.started,
        })),
      })
    );
    return;
  }

  // Static files
  let relPath = pathname === '/' ? '/index.html' : pathname;
  const safePath = path.normalize(path.join(ROOT, relPath));
  if (!safePath.startsWith(ROOT)) {
    res.writeHead(403);
    res.end('Forbidden');
    return;
  }

  fs.stat(safePath, (err, stat) => {
    if (err || !stat.isFile()) {
      res.writeHead(404);
      res.end('Not found');
      return;
    }

    const ext = path.extname(safePath).toLowerCase();
    const contentType = MIME[ext] || 'application/octet-stream';
    const etag = relPath === '/build/cricket07.wasm' ? WASM_ETAG : `"${stat.size.toString(16)}-${Math.floor(stat.mtimeMs).toString(16)}"`;

    res.setHeader('Accept-Ranges', 'bytes');
    res.setHeader('Content-Type', contentType);
    res.setHeader('ETag', etag);
    res.setHeader('Cache-Control', 'no-cache');

    if (req.method === 'HEAD') {
      res.setHeader('Content-Length', stat.size);
      res.writeHead(200);
      res.end();
      return;
    }

    const range = req.headers.range;
    if (range) {
      const m = range.match(/bytes=(\d+)-(\d*)/);
      if (m) {
        const start = parseInt(m[1], 10);
        const end = m[2] ? parseInt(m[2], 10) : stat.size - 1;
        if (start >= 0 && start < stat.size && end >= start && end < stat.size) {
          res.setHeader('Content-Range', `bytes ${start}-${end}/${stat.size}`);
          res.setHeader('Content-Length', end - start + 1);
          res.writeHead(206);
          fs.createReadStream(safePath, { start, end }).pipe(res);
          return;
        }
      }
    }

    res.setHeader('Content-Length', stat.size);
    res.writeHead(200);
    fs.createReadStream(safePath).pipe(res);
  });
});

server.on('upgrade', (req, socket) => {
  const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
  const m = url.pathname.match(/^\/netplay\/([A-Za-z0-9_-]{3,16})$/);
  if (!m) {
    socket.destroy();
    return;
  }
  const code = m[1].toUpperCase();
  const ws = acceptWebSocket(req, socket);
  if (ws) handleRoomConnection(code, ws);
});

server.listen(PORT, '0.0.0.0', () => {
  const lanIp = getLanIp();
  console.log(`Cricket 07 Server listening on:`);
  console.log(`  Local Mac:  http://localhost:${PORT}`);
  console.log(`  LAN IP:     http://${lanIp}:${PORT}`);
  startCloudflareTunnel();
});
