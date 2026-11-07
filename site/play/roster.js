(() => {
  // Three rosters, one installed game. Each pack is appended to the cached data.gob and its index
  // entries repointed (modern-worker.js); "original" is the archive with no pack at all. Only one
  // pack can be applied at a time, so switching first restores whichever pack is in the file.
  const PACKS = {
    'world-2026': { base: 'mods/world-2026/', saves: 'userdata-world-2026-v1', saveKey: 'c07-world-save-directory',
      status: 'Every 2026 national squad, the ten IPL sides, World XI 2026 and the all-time OG, Test, ODI and T20 XIs.' },
    'modern-2026': { base: 'mods/modern-2026/', saves: 'userdata-modern-2026-v1', saveKey: 'c07-modern-save-directory',
      status: 'The OG national teams, with India 2026 and all ten IPL sides alongside them.' },
  };
  const DEFAULT = 'world-2026';
  const select = document.getElementById('roster-mode');
  const status = document.getElementById('roster-status');
  const cards = [...document.querySelectorAll('[data-roster]')];
  const manifests = {};
  for (const [id, pack] of Object.entries(PACKS)) {
    manifests[id] = fetch(pack.base + 'manifest.json', { cache: 'no-store' }).then(response => {
      if (!response.ok) throw new Error('This team pack is unavailable right now.');
      return response.json();
    });
    manifests[id].catch(() => {});
  }

  const stored = (() => { try { return localStorage.getItem('c07-roster'); } catch { return null; } })();
  // Anyone who had the pinned modern-2026 roster before this option existed gets the new one once.
  const seen = (() => { try { return localStorage.getItem('c07-roster-world-seen'); } catch { return null; } })();
  select.value = (stored && (stored in PACKS || stored === 'original') && seen) ? stored : DEFAULT;
  try { localStorage.setItem('c07-roster-world-seen', '1'); } catch {}

  function describe() {
    const id = select.value;
    status.textContent = id === 'original' ? 'The 2006 squads exactly as the game shipped them.' : PACKS[id].status;
    for (const card of cards) card.setAttribute('aria-checked', String(card.dataset.roster === id));
    try { localStorage.setItem('c07-roster', id); } catch {}
  }
  for (const card of cards) {
    card.onclick = () => {
      if (select.disabled) return;
      select.value = card.dataset.roster;
      select.dispatchEvent(new Event('change'));
    };
  }
  select.onchange = describe;
  describe();

  // Peers in one lockstep match must hold identical data, so the room is told which pack we use;
  // the room refuses to start a game whose players report different versions.
  window.C07RosterId = () => select.value;

  function runWorker(manifest, enabled, base) {
    return new Promise((resolve, reject) => {
      const worker = new Worker('modern-worker.js');
      worker.onmessage = ({ data }) => { worker.terminate(); data.error ? reject(new Error(data.error)) : resolve(); };
      worker.onerror = event => { worker.terminate(); reject(new Error(event.message)); };
      worker.postMessage({ directory: 'c07game', manifest, enabled, base });
    });
  }

  window.C07Roster = {
    async prepare() {
      const id = select.value;
      select.disabled = true;
      cards.forEach(card => card.setAttribute('aria-disabled', 'true'));
      status.textContent = id === 'original' ? 'Restoring the original teams…' : 'Preparing the teams and kits…';
      // Take out any other pack first. A pack's restore refuses a file it does not recognise, which
      // is exactly the case where that pack is not the one installed, so that refusal is expected.
      for (const other of Object.keys(PACKS)) {
        if (other === id) continue;
        try { await runWorker(await manifests[other], false, PACKS[other].base); }
        catch (error) { if (!/unrecognised|does not match/i.test(error.message)) throw error; }
      }
      if (id === 'original') return null;
      await runWorker(await manifests[id], true, PACKS[id].base);
      let saves = null;
      try { saves = localStorage.getItem(PACKS[id].saveKey); } catch {}
      return '/opfs/' + (saves || PACKS[id].saves);
    },
  };
})();
