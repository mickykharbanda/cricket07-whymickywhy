// Cricket 07's on-screen controls for phones and tablets: the browser twin of the Android app's ControlsView
// (game-room-public/android/.../ControlsView.java). Same layout, same keys, same behaviour, same settings:
//
//   - left: a thumbstick (or, switched in settings, four separate arrows) that holds the arrow keys; a diagonal
//     is two arrows held together, exactly what a keyboard reports. A generous dead zone, so a resting thumb
//     doesn't walk the batsman;
//   - right: the shot diamond S (big, nearest the thumb), D, W, A, with LOFT beside it. LOFT latches, but only
//     ARMS Shift: Shift goes down with a shot and lifts with it, so it is never held in a menu (where Shift
//     moves the team-selection screen to the next category);
//   - top right: ESC, SPC, OK (Enter), CTRL, ALT and the gear. The row can be hidden; the gear never is.
//   - every finger arrives at one listener, so sliding from one control to another behaves like a real pad;
//   - the gear opens settings: thumbstick or arrows, size, opacity, the top row, "Move controls" (drag them
//     anywhere; tap the gear to finish) and "Reset layout". Remembered per browser (localStorage).
//
// Taps that land on no control fall through to the game canvas, where c07.js turns them into menu clicks.
// It draws on its own <canvas> inside #touch and listens on #stage in the capture phase, so a control press
// never also reaches the game as a tap. press(code, down) is c07.js's: KeyboardEvent.code names, the same keys
// the keyboard uses, so it works online too.
'use strict';

(function () {
  const PREFS = 'cricket-controls-v1';
  const K = { LEFT: 'ArrowLeft', RIGHT: 'ArrowRight', UP: 'ArrowUp', DOWN: 'ArrowDown', S: 'KeyS', D: 'KeyD', W: 'KeyW',
    A: 'KeyA', ESC: 'Escape', SHIFT: 'ShiftLeft', ENTER: 'Enter', SPACE: 'Space', CTRL: 'ControlLeft', ALT: 'AltLeft' };
  const ARROWS = [K.LEFT, K.RIGHT, K.UP, K.DOWN];
  const SHOTS = [K.W, K.A, K.S, K.D];
  const TOP = [K.ESC, K.ENTER, K.SPACE, K.CTRL, K.ALT];

  function load() {
    try { return JSON.parse(localStorage.getItem(PREFS)) || {}; } catch { return {}; }
  }
  function store(p) {
    try { localStorage.setItem(PREFS, JSON.stringify(p)); } catch { /* storage blocked: this visit only */ }
  }

  function setup(press) {
    const stage = document.getElementById('stage');
    const root = document.getElementById('touch');
    const cv = document.createElement('canvas');
    root.appendChild(cv);
    const ctx = cv.getContext('2d');
    const toast = document.createElement('div');
    toast.id = 'touch-toast';
    toast.className = 'hidden';
    root.appendChild(toast);

    const prefs = load();
    let stickMode = prefs.stick ?? true;
    let topBar = prefs.topbar ?? true;
    let scale = prefs.scale ?? 1;
    let opacity = prefs.alpha ?? 0.82;
    const offs = prefs.offs || {};   // control -> [dx, dy] from where the layout puts it

    const mk = (code, label, toggle, pill) => ({ code, label, toggle, pill, cx: 0, cy: 0, rx: 0, ry: 0, down: false, on: new Set() });
    const pads = [
      mk(K.LEFT, '◀', false, false), mk(K.RIGHT, '▶', false, false), mk(K.UP, '▲', false, false), mk(K.DOWN, '▼', false, false),
      mk(K.S, 'S', false, false), mk(K.D, 'D', false, false), mk(K.W, 'W', false, false), mk(K.A, 'A', false, false),
      mk(K.SHIFT, 'LOFT', true, true),
      mk(K.ENTER, 'OK', false, true), mk(K.SPACE, 'SPC', false, true), mk(K.ESC, 'ESC', false, true),
      mk(K.CTRL, 'CTRL', false, true), mk(K.ALT, 'ALT', false, true),
    ];
    const pad = (code) => pads.find((p) => p.code === code);
    const hit = (p, x, y) => {
      if (p.pill) return x >= p.cx - p.rx && x <= p.cx + p.rx && y >= p.cy - p.ry && y <= p.cy + p.ry;
      const dx = (x - p.cx) / p.rx, dy = (y - p.cy) / p.ry;
      return dx * dx + dy * dy <= 1;
    };
    const visible = (p) => {
      if (ARROWS.includes(p.code) && stickMode) return false;
      return !TOP.includes(p.code) || topBar;
    };
    const within = (x, y, cx, cy, r) => (x - cx) ** 2 + (y - cy) ** 2 <= r * r;

    // the stick
    let stickCx = 0, stickCy = 0, stickR = 0, knobR = 0, knobX = 0, knobY = 0, stickPointer = null;
    const stickKeys = [false, false, false, false];   // LEFT RIGHT UP DOWN
    const gear = { cx: 0, cy: 0, rx: 0, ry: 0 };

    let W = 0, H = 0, editing = false, dragging = null, dragX = 0, dragY = 0;
    const owner = new Map();   // pointerId -> pad it went down on
    let loftHeld = false;

    // Places everything from the stage size, as ControlsView.layoutPads (dp = CSS px). Phones keep gestures
    // along the edges (home bar, back swipe), so nothing sits within `edge` of them, plus the notch insets.
    // the notch / home-bar insets, read off a probe that pads itself with them (env() can't be read directly)
    const probe = document.createElement('div');
    probe.style.cssText = 'position:fixed;visibility:hidden;pointer-events:none;padding:env(safe-area-inset-top) ' +
      'env(safe-area-inset-right) env(safe-area-inset-bottom) env(safe-area-inset-left)';
    document.body.appendChild(probe);
    const inset = (side) => parseFloat(getComputedStyle(probe)['padding' + side[0].toUpperCase() + side.slice(1)]) || 0;
    function layout() {
      const r = stage.getBoundingClientRect();
      W = r.width; H = r.height;
      if (!W || !H) return;
      const dpr = Math.min(window.devicePixelRatio || 1, 3);
      cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      // small landscape phones are ~390px tall: shrink a little so the stick and diamond don't meet
      const s = scale * Math.min(1, H / 400);
      const L = 34 + inset('left'), R = 34 + inset('right'), B = 26 + inset('bottom'), T = inset('top');

      stickR = 74 * s; knobR = 30 * s;
      stickCx = L + stickR; stickCy = H - B - stickR;
      const ar = 34 * s, off = 44 * s;   // the arrow cross shares the stick's centre
      place(pad(K.LEFT), stickCx - off, stickCy, ar, ar);
      place(pad(K.RIGHT), stickCx + off, stickCy, ar, ar);
      place(pad(K.UP), stickCx, stickCy - off, ar, ar);
      place(pad(K.DOWN), stickCx, stickCy + off, ar, ar);

      const dr = 40 * s, dOff = 54 * s;   // shot diamond, bottom right; S nearest the thumb's rest
      const cx = W - R - (dr + dOff), cy = H - B - (dr + dOff);
      place(pad(K.S), cx, cy + dOff, dr * 1.18, dr * 1.18);
      place(pad(K.D), cx + dOff, cy, dr, dr);
      place(pad(K.W), cx, cy - dOff, dr, dr);
      place(pad(K.A), cx - dOff, cy, dr, dr);

      const pw = 46 * s, ph = 24 * s, lw = 60 * s, lh = 34 * s;
      place(pad(K.SHIFT), cx - dOff - lw - 14, cy + dOff, lw, lh);   // LOFT: thumb reach, left of the diamond

      const top = Math.max(T, 34 * 0.6) + ph;   // menu keys along the top right, clear of both thumbs
      let x = W - R - pw;
      for (const code of [K.ESC, K.SPACE, K.ENTER, K.CTRL, K.ALT]) { place(pad(code), x, top, pw, ph); x -= pw * 2 + 12; }
      Object.assign(gear, { cx: x, cy: top, rx: pw * 0.75, ry: ph });

      // dragged controls keep their offset, and are kept on screen so none can be pushed out of reach
      for (const p of pads) {
        const o = offs[p.code] || [0, 0];
        p.cx = Math.max(p.rx, Math.min(W - p.rx, p.cx + o[0]));
        p.cy = Math.max(p.ry, Math.min(H - p.ry, p.cy + o[1]));
      }
      const so = offs.stick || [0, 0];
      stickCx = Math.max(stickR, Math.min(W - stickR, stickCx + so[0]));
      stickCy = Math.max(stickR, Math.min(H - stickR, stickCy + so[1]));
      knobX = stickCx; knobY = stickCy;
      draw();
    }
    function place(p, cx, cy, rx, ry) { Object.assign(p, { cx, cy, rx, ry }); }

    // ---------------------------------------------------------------- painting
    // Dark translucent fill with a light outline, so a control reads against a white menu and the pitch alike.
    const rgba = (r, g, b, a) => `rgba(${r},${g},${b},${Math.max(0, Math.min(1, a))})`;
    function pill(cx, cy, rx, ry, label, pressed, rounded) {
      const a = opacity;
      ctx.fillStyle = pressed ? rgba(236, 240, 245, a + 0.15) : rgba(16, 20, 26, a);
      ctx.strokeStyle = pressed ? rgba(16, 20, 26, a + 0.12) : rgba(255, 255, 255, a + 0.12);
      ctx.lineWidth = 2;
      ctx.beginPath();
      if (rounded) ctx.roundRect(cx - rx, cy - ry, rx * 2, ry * 2, ry);
      else ctx.arc(cx, cy, rx, 0, Math.PI * 2);
      ctx.fill(); ctx.stroke();
      ctx.fillStyle = pressed ? rgba(16, 20, 26, a + 0.24) : rgba(255, 255, 255, a + 0.24);
      ctx.font = `700 ${Math.round(Math.min(ry * 0.9, rx * 0.72))}px ui-sans-serif, system-ui, -apple-system, sans-serif`;
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.fillText(label, cx, cy + 1);
    }
    function draw() {
      ctx.clearRect(0, 0, W, H);
      for (const p of pads) if (visible(p)) pill(p.cx, p.cy, p.rx, p.ry, p.label, p.down, p.pill);
      if (stickMode) {
        ctx.fillStyle = rgba(16, 20, 26, opacity * 0.55);
        ctx.strokeStyle = rgba(255, 255, 255, opacity);
        ctx.lineWidth = 2;
        ctx.beginPath(); ctx.arc(stickCx, stickCy, stickR, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
        ctx.fillStyle = rgba(238, 242, 247, opacity + 0.12);
        ctx.strokeStyle = rgba(16, 20, 26, opacity);
        ctx.beginPath(); ctx.arc(knobX, knobY, knobR, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
      }
      pill(gear.cx, gear.cy, gear.rx, gear.ry, '⚙', editing, true);
      if (editing) {   // a dashed outline round everything that can be dragged
        ctx.setLineDash([6, 5]); ctx.strokeStyle = 'rgba(69,207,121,.9)'; ctx.lineWidth = 2;
        for (const p of pads) if (visible(p)) { ctx.beginPath(); ctx.roundRect(p.cx - p.rx - 4, p.cy - p.ry - 4, p.rx * 2 + 8, p.ry * 2 + 8, 8); ctx.stroke(); }
        if (stickMode) { ctx.beginPath(); ctx.arc(stickCx, stickCy, stickR + 4, 0, Math.PI * 2); ctx.stroke(); }
        ctx.setLineDash([]);
      }
    }
    let raf = 0;
    const redraw = () => { if (!raf) raf = requestAnimationFrame(() => { raf = 0; draw(); }); };

    // ---------------------------------------------------------------- keys
    const send = (code, down) => press(code, down);
    const shotDown = () => pads.some((p) => p.down && SHOTS.includes(p.code));
    // LOFT stays lit across shot after shot, but only arms Shift: Shift lands just before a shot and lifts
    // just after it (the order a keyboard reports), and nothing is held in between.
    function syncLoft() {
      const want = pad(K.SHIFT).down && shotDown();
      if (want === loftHeld) return;
      loftHeld = want;
      send(K.SHIFT, want);
    }
    function set(p, down) {
      if (p.down === down) return;
      p.down = down;
      if (p.code === K.SHIFT) { syncLoft(); return; }   // the LOFT pad is the latch, not the key
      if (down) { syncLoft(); send(p.code, true); } else { send(p.code, false); syncLoft(); }
      if (down) navigator.vibrate?.(8);
    }
    function pressPad(p, id) { p.on.add(id); if (!p.toggle) set(p, true); }
    function liftPad(p, id) {
      p.on.delete(id);
      if (p.on.size) return;   // another finger is still on it
      if (p.toggle) set(p, !p.down); else set(p, false);
    }
    function moveStick(x, y) {
      let dx = x - stickCx, dy = y - stickCy, len = Math.hypot(dx, dy);
      const max = stickR - knobR;
      if (len > max && len > 0) { dx = dx / len * max; dy = dy / len * max; len = max; }
      knobX = stickCx + dx; knobY = stickCy + dy;
      const want = [false, false, false, false];
      if (len > max * 0.34) {   // dead zone
        const a = Math.atan2(dy, dx);
        want[0] = Math.cos(a) < -0.383; want[1] = Math.cos(a) > 0.383;
        want[2] = Math.sin(a) < -0.383; want[3] = Math.sin(a) > 0.383;
      }
      for (let i = 0; i < 4; i++) if (want[i] !== stickKeys[i]) { stickKeys[i] = want[i]; send(ARROWS[i], want[i]); }
    }
    function centreStick() {
      knobX = stickCx; knobY = stickCy;
      for (let i = 0; i < 4; i++) if (stickKeys[i]) { stickKeys[i] = false; send(ARROWS[i], false); }
    }
    function releaseAll() {
      for (const p of pads) { p.on.clear(); set(p, false); }
      owner.clear(); stickPointer = null; centreStick(); redraw();
    }

    // ---------------------------------------------------------------- pointers
    const local = (e) => { const r = stage.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; };
    const active = () => document.documentElement.classList.contains('playing') && root.offsetParent !== null &&
      !document.getElementById('touch-settings');
    const find = (x, y) => pads.find((p) => visible(p) && hit(p, x, y));
    const onGear = (x, y) => Math.abs(x - gear.cx) <= gear.rx + 6 && Math.abs(y - gear.cy) <= gear.ry + 6;
    const ours = (e) => { e.preventDefault(); e.stopPropagation(); };

    stage.addEventListener('pointerdown', (e) => {
      if (!active() || e.pointerType === 'mouse' && !params().has('touch')) return;
      const [x, y] = local(e);
      if (editing) {
        ours(e);
        if (onGear(x, y)) { setEditing(false); return; }
        dragging = find(x, y)?.code || (stickMode && within(x, y, stickCx, stickCy, stickR * 1.25) ? 'stick' : null);
        dragX = x; dragY = y;
        return;
      }
      if (onGear(x, y)) { ours(e); openSettings(); return; }
      const p = find(x, y);
      if (p) { ours(e); owner.set(e.pointerId, p); pressPad(p, e.pointerId); }
      else if (stickMode && stickPointer === null && within(x, y, stickCx, stickCy, stickR * 1.25)) {
        ours(e); stickPointer = e.pointerId; moveStick(x, y);
      } else return;   // not ours: it reaches the game canvas as a menu tap
      try { stage.setPointerCapture(e.pointerId); } catch { /* gone already */ }
      redraw();
    }, true);
    stage.addEventListener('pointermove', (e) => {
      if (editing) {
        if (!dragging) return;
        ours(e);
        const [x, y] = local(e);
        const o = offs[dragging] || (offs[dragging] = [0, 0]);
        o[0] += x - dragX; o[1] += y - dragY; dragX = x; dragY = y;
        layout();
        return;
      }
      if (e.pointerId === stickPointer) { ours(e); moveStick(...local(e)); redraw(); return; }
      const held = owner.get(e.pointerId);
      if (!held) return;
      ours(e);
      if (held.toggle) return;   // a latch flips on release; drifting must not flip it
      const [x, y] = local(e);
      // sliding off releases and sliding back on presses again, as on a real pad
      if (hit(held, x, y)) pressPad(held, e.pointerId); else liftPad(held, e.pointerId);
      redraw();
    }, true);
    const up = (e) => {
      if (editing) { if (dragging) { ours(e); save(); } dragging = null; return; }
      let mine = false;
      if (e.pointerId === stickPointer) { stickPointer = null; centreStick(); mine = true; }
      const held = owner.get(e.pointerId);
      if (held) { owner.delete(e.pointerId); liftPad(held, e.pointerId); mine = true; }
      if (mine) { ours(e); redraw(); }
    };
    stage.addEventListener('pointerup', up, true);
    stage.addEventListener('pointercancel', up, true);
    document.addEventListener('c07-release', releaseAll);   // the gate covered the controls
    window.addEventListener('blur', releaseAll);
    document.addEventListener('visibilitychange', () => { if (document.hidden) releaseAll(); });

    const params = () => new URLSearchParams(location.search);

    // ---------------------------------------------------------------- settings
    function save() {
      store({ stick: stickMode, topbar: topBar, scale, alpha: opacity, offs });
    }
    function showToast(t) {
      toast.textContent = t; toast.classList.remove('hidden'); toast.style.opacity = '1';
      clearTimeout(showToast.t1); clearTimeout(showToast.t2);
      showToast.t1 = setTimeout(() => { toast.style.opacity = '0'; }, 3500);
      showToast.t2 = setTimeout(() => toast.classList.add('hidden'), 3900);
    }
    function setEditing(on) {
      if (editing === on) return;
      releaseAll();
      editing = on; dragging = null;
      if (on) showToast('Drag the controls where you want them, then tap the gear.');
      redraw();
    }
    function openSettings() {
      releaseAll();
      let stick = stickMode;
      const box = document.createElement('div');
      box.id = 'touch-settings';
      box.innerHTML = `<div class="sheet" role="dialog" aria-modal="true" aria-label="Controls">
          <h2>Controls</h2>
          <div class="seg"><button type="button" data-m="stick">Thumbstick</button><button type="button" data-m="pad">Four arrows</button></div>
          <label>Size <input type="range" min="70" max="150" data-k="size"></label>
          <label>Opacity <input type="range" min="25" max="100" data-k="alpha"></label>
          <label><input type="checkbox" data-k="top"> Show Esc / Enter / Spc / Ctrl / Alt</label>
          <div class="row3"><button type="button" data-a="reset">Reset layout</button>
            <button type="button" data-a="move">Move controls</button><button type="button" class="primary" data-a="done">Done</button></div>
        </div>`;
      const q = (sel) => box.querySelector(sel);
      const seg = () => box.querySelectorAll('.seg button').forEach((b) => b.setAttribute('aria-pressed', String((b.dataset.m === 'stick') === stick)));
      box.querySelectorAll('.seg button').forEach((b) => { b.onclick = () => { stick = b.dataset.m === 'stick'; seg(); }; });
      seg();
      q('[data-k=size]').value = Math.round(scale * 100);
      q('[data-k=alpha]').value = Math.round(opacity * 100);
      q('[data-k=top]').checked = topBar;
      const apply = () => {
        stickMode = stick;
        topBar = q('[data-k=top]').checked;
        scale = Math.max(0.7, Math.min(1.5, q('[data-k=size]').value / 100));
        opacity = Math.max(0.25, Math.min(1, q('[data-k=alpha]').value / 100));
        save(); box.remove(); layout();
      };
      q('[data-a=done]').onclick = apply;
      q('[data-a=move]').onclick = () => { apply(); setEditing(true); };
      q('[data-a=reset]').onclick = () => { for (const k of Object.keys(offs)) delete offs[k]; apply(); };
      box.addEventListener('pointerdown', (e) => { if (e.target === box) apply(); });   // tap outside: keep and close
      stage.appendChild(box);
    }

    new ResizeObserver(layout).observe(stage);
    window.addEventListener('orientationchange', () => setTimeout(layout, 300));
    layout();
  }

  window.C07Touch = { setup };
})();
