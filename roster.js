(() => {
  const select = document.getElementById('roster-mode');
  const status = document.getElementById('roster-status');
  const base = 'mods/modern-2026/';
  const manifest = fetch(base + 'manifest.json', { cache: 'no-store' }).then(response => {
    if (!response.ok) throw new Error('The modern team pack is unavailable.');
    return response.json();
  });
  manifest.catch(error => { status.textContent = error.message; });
  // Never carry forward the retired prototype that replaced OG India.
  const remembered = localStorage.getItem('c07-roster');
  select.value = remembered === 'modern-2026' ? remembered : 'original';
  const update = () => {
    localStorage.setItem('c07-roster', select.value);
    document.getElementById('go-online').disabled = select.value !== 'original';
    status.textContent = select.value === 'original'
      ? 'All OG teams, squads and uniforms. Your existing saves.'
      : 'OG India and senior teams stay. India 2026 + ten IPL teams replace the A-sides and invitational XIs under Other. New kits, separate saves; solo play.';
  };
  select.onchange = update;
  update();
  window.C07Roster = {
    async prepare(session) {
      const enabled = select.value === 'modern-2026';
      if (session && enabled) throw new Error('Choose Original teams before starting multiplayer.');
      const data = await manifest;
      status.textContent = enabled ? 'Preparing the 2026 teams and kits…' : 'Restoring OG teams…';
      await new Promise((resolve, reject) => {
        const worker = new Worker('modern-worker.js');
        worker.onmessage = ({ data }) => { worker.terminate(); data.error ? reject(new Error(data.error)) : resolve(); };
        worker.onerror = event => { worker.terminate(); reject(new Error(event.message)); };
        worker.postMessage({ directory: 'c07game', manifest: data, enabled, base });
      });
      select.disabled = true;
      return enabled ? '/opfs/' + (localStorage.getItem('c07-modern-save-directory') || 'userdata-modern-2026-v1') : null;
    },
  };
})();
