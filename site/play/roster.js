(() => {
  const select = document.getElementById('roster-mode');
  const status = document.getElementById('roster-status');
  const base = 'mods/modern-2026/';
  const manifest = fetch(base + 'manifest.json', { cache: 'no-store' }).then(response => {
    if (!response.ok) throw new Error('The modern team pack is unavailable.');
    return response.json();
  });
  manifest.catch(error => { status.textContent = error.message; });
  // The 2026 teams are the game now, not a choice. The selector is left in the markup so nothing
  // else that reaches for it breaks, but it is pinned and hidden.
  //
  // Multiplayer used to require the original squads, because a peer on the pack and a peer without
  // it hold different game data and lockstep cannot survive that. With one roster for everyone the
  // mismatch cannot arise, so the restriction goes with it.
  select.value = 'modern-2026';
  localStorage.setItem('c07-roster', 'modern-2026');
  const field = select.closest('label') || select.parentElement;
  if (field) field.hidden = true;
  const online = document.getElementById('go-online');
  if (online) online.disabled = false;
  status.textContent = 'India 2026 and all ten IPL sides, with the OG national teams kept alongside them.';
  window.C07Roster = {
    async prepare(session) {
      const enabled = true;
      const data = await manifest;
      status.textContent = 'Preparing the 2026 teams and kits…';
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
