// Reversible edit to the cached archive only. The source archive stays unchanged.
self.onmessage = async ({ data: { directory, manifest, enabled, base } }) => {
  let handle;
  let knownArchive = false;
  const writeAll = (bytes, at) => {
    let offset = 0;
    while (offset < bytes.length) {
      const count = handle.write(bytes.subarray(offset), { at: at + offset });
      if (!count) throw new Error('Not enough browser storage for the roster.');
      offset += count;
    }
  };
  try {
    let dir = await navigator.storage.getDirectory();
    dir = await dir.getDirectoryHandle(directory);
    dir = await dir.getDirectoryHandle('Data');
    handle = await (await dir.getFileHandle('data.gob')).createSyncAccessHandle();
    const index = new Uint8Array(8);
    handle.read(index, { at: manifest.indexPosition });
    const view = new DataView(index.buffer);
    const original = view.getUint32(0) === manifest.originalEntry[0] && view.getUint32(4) === manifest.originalEntry[1];
    const modified = view.getUint32(0) === manifest.originalSize && view.getUint32(4) === manifest.size;
    if (!original && !modified) throw new Error('This roster does not match the installed game database.');
    knownArchive = true;
    if (handle.getSize() < manifest.originalSize) throw new Error('Game installation is incomplete. Reload to repair it.');
    if (handle.getSize() > manifest.originalSize + manifest.size) throw new Error('The cached archive has another modification.');
    if (enabled) {
      const response = await fetch(base + manifest.file, { cache: 'no-store' });
      if (!response.ok) throw new Error('Could not download the India roster.');
      const data = new Uint8Array(await response.arrayBuffer());
      const digest = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', data)), n => n.toString(16).padStart(2, '0')).join('');
      if (data.length !== manifest.size || digest !== manifest.sha256) throw new Error('India roster integrity check failed.');
      writeAll(data, manifest.originalSize);
      handle.flush();
      if (handle.getSize() !== manifest.originalSize + data.length) throw new Error('Not enough browser storage for the India roster.');
      const written = new Uint8Array(data.length);
      handle.read(written, { at: manifest.originalSize });
      if (!written.every((byte, i) => byte === data[i])) throw new Error('Could not verify the written roster.');
      view.setUint32(0, manifest.originalSize);
      view.setUint32(4, data.length);
    } else {
      view.setUint32(0, manifest.originalEntry[0]);
      view.setUint32(4, manifest.originalEntry[1]);
    }
    writeAll(index, manifest.indexPosition);
    const sizeBytes = new Uint8Array(4);
    new DataView(sizeBytes.buffer).setUint32(0, manifest.originalSize + (enabled ? manifest.size : 0), true);
    writeAll(sizeBytes, 4);
    if (!enabled) handle.truncate(manifest.originalSize);
    handle.flush();
    const check = new Uint8Array(8);
    handle.read(check, { at: manifest.indexPosition });
    if (!check.every((byte, i) => byte === index[i])) throw new Error('Could not verify roster installation.');
    handle.close();
    handle = null;
    self.postMessage({ done: true });
  } catch (error) {
    // If a known archive edit fails, point back to the untouched original data.
    if (knownArchive && handle && handle.getSize() >= manifest.originalSize) {
      try {
        const index = new Uint8Array(8);
        const view = new DataView(index.buffer);
        view.setUint32(0, manifest.originalEntry[0]);
        view.setUint32(4, manifest.originalEntry[1]);
        writeAll(index, manifest.indexPosition);
        const header = new Uint8Array(4);
        new DataView(header.buffer).setUint32(0, manifest.originalSize, true);
        writeAll(header, 4);
        handle.truncate(manifest.originalSize);
        handle.flush();
      } catch { /* Preserve the original error if storage also prevents rollback. */ }
    }
    self.postMessage({ error: error.message });
  }
  finally { handle?.close(); }
};
