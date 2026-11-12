// Portable backups of native game saves. This does not snapshot a running match.
(() => {
  const message = document.getElementById('save-status');
  const saveKey = () => document.getElementById('roster-mode')?.value === 'modern-2026' ? 'c07-modern-save-directory' : 'c07-save-directory';
  const current = () => localStorage.getItem(saveKey()) || (saveKey() === 'c07-modern-save-directory' ? 'userdata-modern-2026-v1' : 'userdata');
  async function collect(dir, prefix = '') {
    const files = [];
    for await (const [name, handle] of dir.entries()) {
      const path = prefix + name;
      if (handle.kind === 'directory') files.push(...await collect(handle, path + '/'));
      else {
        const bytes = new Uint8Array(await (await handle.getFile()).arrayBuffer());
        let data = '';
        for (let i = 0; i < bytes.length; i += 8192) data += String.fromCharCode(...bytes.subarray(i, i + 8192));
        files.push({ path, data: btoa(data) });
      }
    }
    return files;
  }
  function idle() {
    if (window.c07Running) throw new Error('Close the game and reopen the launcher before managing saves.');
  }
  async function exclusive(action) {
    const buttons = ['save-export', 'save-import'].map(id => document.getElementById(id));
    if (buttons.some(button => button.disabled)) return;
    buttons.forEach(button => button.disabled = true);
    document.getElementById('roster-mode').disabled = true;
    document.getElementById('play').disabled = true;
    document.getElementById('go-online').disabled = true;
    try { idle(); await action(); }
    catch (error) { message.textContent = error.message; }
    finally {
      buttons.forEach(button => button.disabled = false);
      document.getElementById('roster-mode').disabled = false;
      document.getElementById('play').disabled = false;
      document.getElementById('go-online').disabled = document.getElementById('roster-mode')?.value === 'modern-2026';
    }
  }
  document.getElementById('save-export').onclick = () => exclusive(async () => {
    const root = await navigator.storage.getDirectory();
    let dir;
    try { dir = await root.getDirectoryHandle(current()); }
    catch (error) { if (error.name !== 'NotFoundError') throw error; }
    const files = dir ? await collect(dir) : [];
    if (!files.length) throw new Error('No saved games yet. Save from the game menu first.');
    const url = URL.createObjectURL(new Blob([JSON.stringify({ format: 'cricket07-saves', version: 1, files })], { type: 'application/json' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = `cricket07-saves-${new Date().toISOString().slice(0, 10)}.json`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 10000);
    message.textContent = `Backup downloaded (${files.length} files).`;
  });
  document.getElementById('save-import').onchange = event => exclusive(async () => {
    const file = event.target.files[0];
    if (!file) return;
    if (file.size > 64 * 1024 * 1024) throw new Error('Backup is too large (maximum 64 MB).');
    const backup = JSON.parse(await file.text());
    if (backup.format !== 'cricket07-saves' || backup.version !== 1 || !Array.isArray(backup.files) || !backup.files.length)
      throw new Error('Choose a Cricket 07 save backup.');
    const seen = new Set();
    const files = backup.files.map(entry => {
      if (typeof entry.path !== 'string' || entry.path.includes('\\') || entry.path.split('/').some(part => !part || part === '.' || part === '..') || typeof entry.data !== 'string' || seen.has(entry.path))
        throw new Error('Invalid save backup.');
      seen.add(entry.path);
      return { path: entry.path.split('/'), bytes: Uint8Array.from(atob(entry.data), char => char.charCodeAt(0)) };
    });
    const root = await navigator.storage.getDirectory();
    const name = 'c07-restored-' + crypto.randomUUID();
    const dir = await root.getDirectoryHandle(name, { create: true });
    try {
      for (const file of files) {
        let parent = dir;
        for (const part of file.path.slice(0, -1)) parent = await parent.getDirectoryHandle(part, { create: true });
        const handle = await parent.getFileHandle(file.path.at(-1), { create: true });
        const writer = await handle.createWritable();
        await writer.write(file.bytes);
        await writer.close();
      }
      // Switch only after every file is safely written; the previous directory stays intact.
      localStorage.setItem(saveKey(), name);
    } catch (error) {
      await root.removeEntry(name, { recursive: true }).catch(() => {});
      throw error;
    }
    message.textContent = `Restored ${files.length} save files. Press Play Solo, then load from the game menu.`;
    event.target.value = '';
  });
})();
