// Write directly to OPFS: no temporary duplicate of a large game file, and
// interrupted downloads retain their bytes for the next Range request.
self.onmessage = async ({ data: { base, directory, path, size } }) => {
  let handle;
  try {
    let dir = await navigator.storage.getDirectory();
    dir = await dir.getDirectoryHandle(directory, { create: true });
    const parts = path.split('/');
    for (const part of parts.slice(0, -1)) dir = await dir.getDirectoryHandle(part, { create: true });
    const file = await dir.getFileHandle(parts.at(-1), { create: true });
    handle = await file.createSyncAccessHandle();
    let offset = handle.getSize();
    if (offset > size) { handle.truncate(0); offset = 0; }
    if (offset === size) { self.postMessage({ done: true }); return; }
    const response = await fetch(base + parts.map(encodeURIComponent).join('/'), {
      headers: offset ? { Range: `bytes=${offset}-` } : {}, cache: 'no-store',
    });
    if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
    if (response.status === 206 && !response.headers.get('Content-Range')?.startsWith(`bytes ${offset}-`))
      throw new Error(`${path}: incorrect download range`);
    if (response.status !== 206) { handle.truncate(0); offset = 0; }
    self.postMessage({ bytes: offset });
    const reader = response.body.getReader();
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      let written = 0;
      while (written < value.length) {
        const count = handle.write(value.subarray(written), { at: offset });
        if (!count) throw new Error(`${path}: could not write game file`);
        written += count;
        offset += count;
      }
      self.postMessage({ bytes: offset });
    }
    handle.flush();
    if (handle.getSize() !== size) {
      const shortWrite = handle.getSize() < offset;
      throw Object.assign(new Error(`${path}: incomplete download`), { name: shortWrite ? 'QuotaExceededError' : 'Error' });
    }
    self.postMessage({ done: true });
  } catch (error) {
    self.postMessage({ error: error.message, name: error.name });
  } finally { handle?.close(); }
};
