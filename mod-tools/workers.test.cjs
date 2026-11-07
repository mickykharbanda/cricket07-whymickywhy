const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const { webcrypto } = require('node:crypto');

function harness(script, initial, response, options = {}) {
  let bytes = Uint8Array.from(initial);
  const messages = [], requests = [];
  let closed = false;
  const handle = {
    getSize: () => bytes.length,
    read(target, { at }) { target.set(bytes.subarray(at, at + target.length)); return target.length; },
    write(source, { at }) {
      if (options.quota) throw Object.assign(new Error('storage full'), { name: 'QuotaExceededError' });
      if (bytes.length < at + source.length) { const grown = new Uint8Array(at + source.length); grown.set(bytes); bytes = grown; }
      bytes.set(source, at); return source.length;
    },
    truncate(size) { bytes = bytes.slice(0, size); }, flush() {}, close() { closed = true; },
  };
  const dir = { getDirectoryHandle: async () => dir, getFileHandle: async () => ({ createSyncAccessHandle: async () => handle }) };
  const context = {
    Uint8Array, DataView, URL, crypto: webcrypto,
    navigator: { storage: { getDirectory: async () => dir } },
    self: { postMessage: message => messages.push(message) },
    fetch: async (url, init) => { requests.push({ url, init }); return typeof response === 'function' ? response(url, init) : response; },
  };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '..', 'site', 'play', script), 'utf8'), context);
  return { send: data => context.self.onmessage({ data }), messages, requests, bytes: () => bytes, closed: () => closed };
}

function fixture() {
  const original = new Uint8Array(64);
  original.set(Buffer.from('BIGF'));
  const view = new DataView(original.buffer);
  view.setUint32(0x04, 64, true);
  view.setUint32(0x10, 32);
  view.setUint32(0x14, 12);
  return original;
}

async function rosterManifest(data) {
  return { originalSize: 64, originalEntry: [32, 12], indexPosition: 16, size: data.length,
    sha256: Buffer.from(await webcrypto.subtle.digest('SHA-256', data)).toString('hex'), file: 'roster.cdf' };
}

test('roster apply and original restore round-trip preserves every original byte', async () => {
  const data = Uint8Array.from([0, 12, 0, 0]);
  const manifest = await rosterManifest(data);
  const first = harness('roster-worker.js', fixture(), { ok: true, arrayBuffer: async () => data.buffer });
  await first.send({ directory: 'test', manifest, enabled: true, base: 'mods/' });
  assert.equal(first.messages.at(-1).done, true);
  assert.equal(first.bytes().length, 68);
  assert.equal(new DataView(first.bytes().buffer).getUint32(16), 64);
  const second = harness('roster-worker.js', first.bytes(), {});
  await second.send({ directory: 'test', manifest, enabled: false, base: 'mods/' });
  assert.equal(second.messages.at(-1).done, true);
  assert.deepEqual(second.bytes(), fixture());
  assert.ok(first.closed() && second.closed());
});

test('roster rejects corrupted downloads before modifying the archive', async () => {
  const data = Uint8Array.from([0, 12, 0, 0]);
  const manifest = await rosterManifest(data);
  const runner = harness('roster-worker.js', fixture(), { ok: true, arrayBuffer: async () => Uint8Array.from([99]).buffer });
  await runner.send({ directory: 'test', manifest, enabled: true, base: 'mods/' });
  assert.match(runner.messages.at(-1).error, /integrity/);
  assert.deepEqual(runner.bytes(), fixture());
});

test('roster refuses to overwrite an unknown existing modification', async () => {
  const data = Uint8Array.from([0, 12, 0, 0]);
  const manifest = await rosterManifest(data);
  const original = fixture(); original[16] = 99;
  const runner = harness('roster-worker.js', original, {});
  await runner.send({ directory: 'test', manifest, enabled: true, base: 'mods/' });
  assert.match(runner.messages.at(-1).error, /does not match/);
  assert.deepEqual(runner.bytes(), original);
});

async function expansionManifest(data) {
  return { ...(await rosterManifest(data)), resources: [
    { resource: 'roster', indexPosition: 16, originalEntry: [32, 12], offset: 0, size: 2 },
    { resource: 'kit', indexPosition: 24, originalEntry: [44, 8], offset: 2, size: data.length - 2 },
  ] };
}

function expansionFixture() {
  const bytes = fixture(), view = new DataView(bytes.buffer);
  view.setUint32(24, 44); view.setUint32(28, 8);
  return bytes;
}

test('modern roster and kit publish together and restore every original byte', async () => {
  const data = Uint8Array.from([1, 2, 3, 4, 5, 6]), manifest = await expansionManifest(data);
  const runner = harness('modern-worker.js', expansionFixture(), { ok: true, arrayBuffer: async () => data.buffer });
  await runner.send({ directory: 'test', manifest, enabled: true, base: 'mods/' });
  assert.equal(runner.messages.at(-1).done, true);
  const view = new DataView(runner.bytes().buffer);
  assert.deepEqual([view.getUint32(16), view.getUint32(24)], [64, 66]);
  const restore = harness('modern-worker.js', runner.bytes(), {});
  await restore.send({ directory: 'test', manifest, enabled: false, base: 'mods/' });
  assert.equal(restore.messages.at(-1).done, true);
  assert.deepEqual(restore.bytes(), expansionFixture());
});

test('modern pack upgrades an earlier verified resource layout', async () => {
  const data = Uint8Array.from([1, 2, 3, 4, 5, 6]), manifest = await expansionManifest(data);
  const prior = new Uint8Array(68); prior.set(expansionFixture());
  new DataView(prior.buffer).setUint32(16, 64);
  new DataView(prior.buffer).setUint32(20, 4);
  manifest.previousLayouts = [{ size: 4, resources: [{ resource: 'roster', offset: 0, size: 4 }] }];
  const runner = harness('modern-worker.js', prior, { ok: true, arrayBuffer: async () => data.buffer });
  await runner.send({ directory: 'test', manifest, enabled: true, base: 'mods/' });
  assert.equal(runner.messages.at(-1).done, true);
  assert.equal(runner.bytes().length, 70);
});

test('modern pack rejects corrupt downloads and unknown resource pointers', async () => {
  const data = Uint8Array.from([1, 2, 3, 4]), manifest = await expansionManifest(data);
  const corrupt = harness('modern-worker.js', expansionFixture(), { ok: true, arrayBuffer: async () => Uint8Array.from([99]).buffer });
  await corrupt.send({ directory: 'test', manifest, enabled: true, base: 'mods/' });
  assert.match(corrupt.messages.at(-1).error, /integrity/);
  assert.deepEqual(corrupt.bytes(), expansionFixture());
  const unknown = expansionFixture(); unknown[24] = 99;
  const runner = harness('modern-worker.js', unknown, {});
  await runner.send({ directory: 'test', manifest, enabled: true, base: 'mods/' });
  assert.match(runner.messages.at(-1).error, /does not match/);
  assert.deepEqual(runner.bytes(), unknown);
});

test('switching packs: the other pack refuses to restore, the installed one restores, then the new one applies', async () => {
  // Two packs over the same index entries, with different sizes: the launcher's switch order.
  const modernData = Uint8Array.from([1, 2, 3, 4, 5, 6]), modern = await expansionManifest(modernData);
  const worldData = Uint8Array.from([9, 9, 8, 8, 7, 7, 6, 6, 5, 5]), world = await expansionManifest(worldData);
  const apply = harness('modern-worker.js', expansionFixture(), { ok: true, arrayBuffer: async () => modernData.buffer });
  await apply.send({ directory: 'test', manifest: modern, enabled: true, base: 'mods/' });
  assert.equal(apply.messages.at(-1).done, true);
  const wrong = harness('modern-worker.js', apply.bytes(), {});
  await wrong.send({ directory: 'test', manifest: world, enabled: false, base: 'mods/' });
  assert.match(wrong.messages.at(-1).error, /unrecognised|does not match/);
  assert.deepEqual(wrong.bytes(), apply.bytes());
  const restore = harness('modern-worker.js', wrong.bytes(), {});
  await restore.send({ directory: 'test', manifest: modern, enabled: false, base: 'mods/' });
  assert.deepEqual(restore.bytes(), expansionFixture());
  const next = harness('modern-worker.js', restore.bytes(), { ok: true, arrayBuffer: async () => worldData.buffer });
  await next.send({ directory: 'test', manifest: world, enabled: true, base: 'mods/' });
  assert.equal(next.messages.at(-1).done, true);
  assert.equal(next.bytes().length, 64 + worldData.length);
  const back = harness('modern-worker.js', next.bytes(), {});
  await back.send({ directory: 'test', manifest: world, enabled: false, base: 'mods/' });
  assert.deepEqual(back.bytes(), expansionFixture());
});

test('a pack published as parts is joined, each part checked, and a bad part rejected', async () => {
  const data = Uint8Array.from([1, 2, 3, 4, 5, 6]), manifest = await expansionManifest(data);
  const sha = async bytes => Buffer.from(await webcrypto.subtle.digest('SHA-256', bytes)).toString('hex');
  const a = data.slice(0, 4), b = data.slice(4);
  manifest.parts = [{ file: 'p0.bin', size: 4, sha256: await sha(a) }, { file: 'p1.bin', size: 2, sha256: await sha(b) }];
  const serve = (parts) => (url) => ({ ok: true, arrayBuffer: async () => parts[url.split('/').pop()].buffer });
  const runner = harness('modern-worker.js', expansionFixture(), serve({ 'p0.bin': a, 'p1.bin': b }));
  await runner.send({ directory: 'test', manifest, enabled: true, base: 'mods/' });
  assert.equal(runner.messages.at(-1).done, true);
  assert.deepEqual(runner.requests.map(r => r.url), ['mods/p0.bin', 'mods/p1.bin']);
  assert.equal(runner.bytes().length, 70);
  const bad = harness('modern-worker.js', expansionFixture(), serve({ 'p0.bin': a, 'p1.bin': Uint8Array.from([9, 9]) }));
  await bad.send({ directory: 'test', manifest, enabled: true, base: 'mods/' });
  assert.match(bad.messages.at(-1).error, /integrity/);
  assert.deepEqual(bad.bytes(), expansionFixture());
});

function streamed(bytes, status = 206, range = 'bytes 2-3/4') {
  let done = false;
  return { ok: true, status, headers: { get: () => range }, body: { getReader: () => ({ read: async () => {
    if (done) return { done: true }; done = true; return { done: false, value: Uint8Array.from(bytes) };
  } }) } };
}

test('folder import accepts the downloadable EXE filename and excludes unrelated files', () => {
  const source = fs.readFileSync(path.join(__dirname, '..', 'site', 'play', 'c07.js'), 'utf8');
  const context = { EXE: 'Cricket07.cracked.exe' };
  vm.runInNewContext(source.slice(source.indexOf('function wanted('), source.indexOf('async function importFromPicker(')), context);
  assert.equal(context.wanted('Cricket07.exe'), 'Cricket07.cracked.exe');
  assert.equal(context.wanted('Cricket07.cracked.exe'), 'Cricket07.cracked.exe');
  assert.equal(context.wanted('Data/data.gob'), 'Data/data.gob');
  assert.equal(context.wanted('private-notes.json'), null);
  assert.equal(context.wanted('unrelated.exe'), null);
});

test('installer resumes partial files using Range and verifies all bytes', async () => {
  const runner = harness('install-worker.js', [1, 2], streamed([3, 4]));
  await runner.send({ base: 'https://example.test/game/', directory: 'test', path: 'Data/test', size: 4 });
  assert.equal(runner.requests[0].init.headers.Range, 'bytes=2-');
  assert.deepEqual(Array.from(runner.bytes()), [1, 2, 3, 4]);
  assert.equal(runner.messages.at(-1).done, true);
  assert.ok(runner.closed());
});

test('installer restarts safely if the server ignores Range', async () => {
  const runner = harness('install-worker.js', [99, 98], streamed([1, 2, 3, 4], 200));
  await runner.send({ base: 'https://example.test/game/', directory: 'test', path: 'Data/test', size: 4 });
  assert.deepEqual(Array.from(runner.bytes()), [1, 2, 3, 4]);
  assert.equal(runner.messages.at(-1).done, true);
});

test('installer reports quota exhaustion and closes its file handle', async () => {
  const runner = harness('install-worker.js', [1, 2], streamed([3, 4]), { quota: true });
  await runner.send({ base: 'https://example.test/game/', directory: 'test', path: 'Data/test', size: 4 });
  assert.equal(runner.messages.at(-1).name, 'QuotaExceededError');
  assert.ok(runner.closed());
});

test('quota recovery discards only cached movies, completes required files and keeps saves', async () => {
  const installed = new Map([['Data/game.bin', 4], ['Data/intro.vp6', 2]]);
  const removed = [];
  let marker;
  const directory = {
    getDirectoryHandle: async () => directory,
    removeEntry: async name => { removed.push(name); installed.delete('Data/' + name); },
    getFileHandle: async name => ({ getFile: async () => ({ size: installed.get(name) ?? installed.get('Data/' + name) ?? -1 }) }),
  };
  const ids = Object.fromEntries(['progress', 'status'].map(id => [id, { classList: { add() {}, remove() {} } }]));
  const context = {
    navigator: { storage: { persist: async () => false } },
    gameDir: async () => directory,
    existingSize: async (_, name) => installed.get(name) ?? -1,
    writeMarker: async (version, compact) => { marker = { version, compact }; },
    $: id => ids[id], mb: n => String(n), status() {}, OPFS_DIR: 'game', GAME_BASE: 'game/',
    Worker: class {
      postMessage({ path, size }) {
        queueMicrotask(() => {
          if (path.endsWith('.vp6')) this.onmessage({ data: { error: 'storage full', name: 'QuotaExceededError' } });
          else { installed.set(path, size); this.onmessage({ data: { done: true } }); }
        });
      }
      terminate() {}
    },
    setTimeout,
  };
  const source = fs.readFileSync(path.join(__dirname, '..', 'site', 'play', 'c07.js'), 'utf8');
  vm.runInNewContext(source.slice(source.indexOf('function downloadFile('), source.indexOf('async function fetchManifest(')), context);
  await context.syncFromServer({ version: 'v1', files: [{ path: 'Data/game.bin', size: 4 }, { path: 'Data/intro.vp6', size: 12 }] });
  assert.deepEqual(removed, ['intro.vp6']);
  assert.deepEqual(marker, { version: 'v1', compact: true });
  assert.equal(installed.get('Data/game.bin'), 4);
});

async function hostedChunks() {
  return Promise.all([[1, 2], [3, 4]].map(async (data, index) => ({
    path: `chunks/${index}.bin`, offset: index * 2, size: 2,
    sha256: Buffer.from(await webcrypto.subtle.digest('SHA-256', Uint8Array.from(data))).toString('hex'),
  })));
}

test('hosted chunks resume within a chunk and retain completed chunks', async () => {
  const chunks = await hostedChunks();
  const runner = harness('install-worker.js', [1, 2, 3], streamed([4], 206, 'bytes 1-1/2'));
  await runner.send({ base: 'https://example.test/game/', directory: 'test', path: 'Data/test', size: 4, chunks });
  assert.equal(runner.requests.length, 1);
  assert.equal(runner.requests[0].url, 'https://example.test/game/chunks/1.bin');
  assert.equal(runner.requests[0].init.headers.Range, 'bytes=1-');
  assert.deepEqual(Array.from(runner.bytes()), [1, 2, 3, 4]);
  assert.equal(runner.messages.at(-1).done, true);
});

test('hosted chunks only restart the interrupted chunk when Range is ignored', async () => {
  const chunks = await hostedChunks();
  const runner = harness('install-worker.js', [1, 2, 99], streamed([3, 4], 200));
  await runner.send({ base: 'https://example.test/game/', directory: 'test', path: 'Data/test', size: 4, chunks });
  assert.deepEqual(Array.from(runner.bytes()), [1, 2, 3, 4]);
  assert.equal(runner.messages.at(-1).done, true);
});

test('hosted chunks reject corruption without discarding earlier chunks', async () => {
  const chunks = await hostedChunks();
  const runner = harness('install-worker.js', [1, 2], streamed([99, 4], 200));
  await runner.send({ base: 'https://example.test/game/', directory: 'test', path: 'Data/test', size: 4, chunks });
  assert.match(runner.messages.at(-1).error, /integrity/);
  assert.deepEqual(Array.from(runner.bytes()), [1, 2]);
});

test('hosted chunks reject gaps before downloading', async () => {
  const chunks = await hostedChunks(); chunks[1].offset = 3;
  const runner = harness('install-worker.js', [], {});
  await runner.send({ base: 'https://example.test/game/', directory: 'test', path: 'Data/test', size: 4, chunks });
  assert.match(runner.messages.at(-1).error, /invalid hosted file manifest/);
  assert.equal(runner.requests.length, 0);
});
