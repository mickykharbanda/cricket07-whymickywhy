// Install or restore a verified resource pack in the browser cache only.
self.onmessage = async ({ data: { directory, manifest, enabled, base } }) => {
  let handle, validated = false;
  const write = (bytes, at) => {
    let done = 0;
    while (done < bytes.length) {
      const count = handle.write(bytes.subarray(done), { at: at + done });
      if (!count) throw new Error('Browser storage is full.');
      done += count;
    }
  };
  const indexBytes = pair => { const bytes = new Uint8Array(8); const view = new DataView(bytes.buffer); view.setUint32(0, pair[0]); view.setUint32(4, pair[1]); return bytes; };
  const header = size => { const bytes = new Uint8Array(4); new DataView(bytes.buffer).setUint32(0, size, true); return bytes; };
  const restore = () => {
    for (const resource of manifest.resources) write(indexBytes(resource.originalEntry), resource.indexPosition);
    write(header(manifest.originalSize), 4);
    handle.truncate(manifest.originalSize);
    handle.flush();
  };
  const hash = async bytes => Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)), byte => byte.toString(16).padStart(2, '0')).join('');
  try {
    let dir = await navigator.storage.getDirectory();
    dir = await dir.getDirectoryHandle(directory);
    dir = await dir.getDirectoryHandle('Data');
    handle = await (await dir.getFileHandle('data.gob')).createSyncAccessHandle();
    const size = handle.getSize();
    if (![manifest.originalSize, manifest.originalSize + manifest.size, manifest.originalSize + 620140, ...(manifest.previousLayouts || []).map(layout => manifest.originalSize + layout.size)].includes(size))
      throw new Error('The game cache has an unrecognised modification.');
    for (const resource of manifest.resources) {
      const bytes = new Uint8Array(8); handle.read(bytes, { at: resource.indexPosition });
      const view = new DataView(bytes.buffer), offset = view.getUint32(0), length = view.getUint32(4);
      const original = offset === resource.originalEntry[0] && length === resource.originalEntry[1];
      const versions = [resource, ...(manifest.previousLayouts || []).flatMap(layout => layout.resources.filter(item => item.resource === resource.resource))];
      const modified = versions.some(item => offset === manifest.originalSize + item.offset && length === item.size);
      if (!original && !modified) throw new Error('This expansion does not match the installed game.');
    }
    validated = true;
    if (!enabled) restore();
    else {
      const response = await fetch(base + manifest.file, { cache: 'no-store' });
      if (!response.ok) throw new Error('Could not download the modern-team pack.');
      const bytes = new Uint8Array(await response.arrayBuffer());
      if (bytes.length !== manifest.size || await hash(bytes) !== manifest.sha256) throw new Error('Modern-team pack integrity check failed.');
      write(bytes, manifest.originalSize);
      handle.truncate(manifest.originalSize + bytes.length);
      handle.flush();
      const check = new Uint8Array(bytes.length); handle.read(check, { at: manifest.originalSize });
      if (await hash(check) !== manifest.sha256) throw new Error('Could not verify the installed team pack.');
      // Publish pointers only after the entire roster and all kits are safely written.
      for (const resource of manifest.resources) write(indexBytes([manifest.originalSize + resource.offset, resource.size]), resource.indexPosition);
      write(header(manifest.originalSize + bytes.length), 4);
      handle.flush();
    }
    handle.close(); handle = null;
    self.postMessage({ done: true });
  } catch (error) {
    if (validated && handle) { try { restore(); } catch { /* retain the original error */ } }
    self.postMessage({ error: error.name === 'InvalidStateError' || error.name === 'NoModificationAllowedError' ? 'Close other Cricket 07 game windows, then try again.' : error.message });
  } finally { handle?.close(); }
};
