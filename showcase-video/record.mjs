#!/usr/bin/env node
// Records a narrated, captioned walkthrough of the AgentForge dashboard to showcase-video/agentforge-demo.mp4.
//
// Zero installs: Node 22+ (built-in WebSocket), Google Chrome, ffmpeg and macOS `say`.
// It drives the real dashboard over the Chrome DevTools Protocol and only draws overlays on top of the page
// (captions, spotlight, pointer, title cards). The app itself is not modified.
//
//   python3 -m agentforge reset --yes
//   python3 -m agentforge serve          # in another terminal
//   node showcase-video/record.mjs              # mixed-audience cut, narrated -> agentforge-demo.mp4
//   CUT=exec node showcase-video/record.mjs     # leadership cut from exec-cut.mjs, captions only
//
// Env: AGENTFORGE_URL, CHROME, VOICE (default Samantha), RATE (words per minute, default 170), CUT.

import { spawn, execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(HERE, 'agentforge-demo.mp4');
const APP = process.env.AGENTFORGE_URL || 'http://127.0.0.1:8765';
const CHROME = process.env.CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const VOICE = process.env.VOICE || 'Samantha';
const RATE = process.env.RATE || '170';
const W = 1440, H = 810, DPR = 4 / 3;  // CSS viewport; frames come out at 1920x1080
const FPS = 25, SR = 44100;
const J = JSON.stringify;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// ---- Chrome DevTools Protocol ----------------------------------------------------------------------------
class CDP {
  constructor(url) { this.ws = new WebSocket(url); this.id = 0; this.pending = new Map(); this.handlers = {}; }
  open() {
    return new Promise((resolve, reject) => {
      this.ws.onopen = resolve; this.ws.onerror = reject;
      this.ws.onmessage = (e) => {
        const m = JSON.parse(e.data);
        if (m.id) {
          const p = this.pending.get(m.id); this.pending.delete(m.id);
          m.error ? p.reject(new Error(`${p.method}: ${m.error.message}`)) : p.resolve(m.result);
        } else (this.handlers[m.method] || []).forEach((f) => f(m.params));
      };
    });
  }
  send(method, params = {}, ms = 0) {  // ms > 0: reject if Chrome never replies (a reply can occasionally go missing)
    const id = ++this.id;
    this.ws.send(J({ id, method, params }));
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject, method });
      if (ms) setTimeout(() => this.pending.delete(id) && reject(new Error(`${method}: no reply within ${ms} ms`)), ms);
    });
  }
  on(method, f) { (this.handlers[method] ||= []).push(f); }
}

async function launchChrome(profile) {
  const proc = spawn(CHROME, ['--headless=new', '--remote-debugging-port=0', `--user-data-dir=${profile}`,
    '--no-first-run', '--no-default-browser-check', '--hide-scrollbars', '--mute-audio', `--window-size=${W},${H}`, 'about:blank'],
    { stdio: ['ignore', 'ignore', 'pipe'] });
  const wsUrl = await new Promise((resolve, reject) => {
    let buf = '';
    proc.stderr.on('data', (d) => { buf += d; const m = buf.match(/DevTools listening on (ws:\/\/\S+)/); if (m) resolve(m[1]); });
    proc.on('exit', (code) => reject(new Error(`Chrome exited (${code}) before DevTools was ready`)));
    setTimeout(() => reject(new Error('Chrome did not start within 20s')), 20000);
  });
  const targets = await (await fetch(`http://127.0.0.1:${new URL(wsUrl).port}/json/list`)).json();
  return { proc, pageWs: targets.find((t) => t.type === 'page').webSocketDebuggerUrl };
}

// ---- Narration -------------------------------------------------------------------------------------------
function narrate(text, file) {
  execFileSync('say', ['-v', VOICE, '-r', RATE, '-o', `${file}.aiff`, text]);
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', `${file}.aiff`, '-f', 's16le', '-ac', '1', '-ar', String(SR), `${file}.raw`]);
  const pcm = new Int16Array(new Uint8Array(fs.readFileSync(`${file}.raw`)).buffer);
  return { pcm, seconds: pcm.length / SR };
}

function writeWav(file, clips, seconds) {
  const total = Math.ceil(seconds * SR), mix = new Int16Array(total);
  for (const { at, pcm } of clips) {
    const start = Math.round(at * SR);
    if (start < total) mix.set(pcm.subarray(0, total - start), start);
  }
  const head = Buffer.alloc(44);
  head.write('RIFF', 0); head.writeUInt32LE(36 + total * 2, 4); head.write('WAVE', 8); head.write('fmt ', 12);
  head.writeUInt32LE(16, 16); head.writeUInt16LE(1, 20); head.writeUInt16LE(1, 22); head.writeUInt32LE(SR, 24);
  head.writeUInt32LE(SR * 2, 28); head.writeUInt16LE(2, 32); head.writeUInt16LE(16, 34); head.write('data', 36); head.writeUInt32LE(total * 2, 40);
  fs.writeFileSync(file, Buffer.concat([head, Buffer.from(mix.buffer)]));
}

// ---- In-page overlay (serialised with toString and evaluated in the dashboard) ---------------------------
// A cut's theme can append CSS overrides and replace the few labels that are drawn as text.
function installTour(theme = {}) {
  if (window.__tour) return;
  const th = { css: '', lens: '📜 FROM THE DIARY (TRACE): WHAT HAPPENED IN THIS STEP', click: '🖱️ Click: ', typing: '⌨️ Typing a note', ...theme };
  const CAP = 160, TOP = 14, PAD = 6;
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const css = document.createElement('style');
  css.textContent = `
    body { padding-bottom: 70vh; }
    #tour-dim { position:fixed; inset:0; background:rgba(3,7,12,.66); z-index:9000; pointer-events:none; opacity:0; transition:opacity .35s; }
    .tour-ring { position:fixed; z-index:9001; pointer-events:none; border:3px solid #ffd166; border-radius:10px; display:none;
      box-shadow:0 0 0 4px rgba(255,209,102,.25), 0 0 22px rgba(255,209,102,.55); animation:tourPulse 1.4s ease-in-out infinite; }
    @keyframes tourPulse { 50% { box-shadow:0 0 0 9px rgba(255,209,102,.10), 0 0 40px rgba(255,209,102,.85); } }
    #tour-cap { position:fixed; left:0; right:0; bottom:0; height:${CAP}px; z-index:9500; box-sizing:border-box; padding:16px 40px 0;
      background:linear-gradient(180deg,#0d141e,#070b11); border-top:2px solid #4f9cf9; color:#eef2f7;
      font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; }
    #tour-prog { position:absolute; left:0; top:-3px; height:4px; width:0; background:#ffd166; transition-property:width; transition-timing-function:linear; }
    #tour-body.in { animation:tourIn .35s ease both; }
    #tour-chip { display:inline-block; font-size:13px; font-weight:800; letter-spacing:1.2px; text-transform:uppercase; color:#08111c;
      background:#4f9cf9; border-radius:999px; padding:3px 12px; }
    #tour-title { font-size:29px; font-weight:800; margin:6px 0 3px; }
    #tour-text { font-size:20px; line-height:1.38; color:#c9d3e0; max-width:1340px; }
    #tour-card { position:fixed; left:0; right:0; top:0; bottom:${CAP}px; z-index:9400; display:none; align-items:center; justify-content:center;
      background:radial-gradient(1100px 620px at 30% 15%,#1c2c44,#0a0f17 72%); color:#eef2f7; font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; }
    #tour-card.show { display:flex; animation:tourIn .5s ease both; }
    #tour-card .tc { text-align:center; max-width:1280px; padding:0 40px; }
    #tour-card h1 { font-size:76px; margin:4px 0 10px; letter-spacing:.5px; }
    #tour-card h2 { font-size:42px; margin:0 0 28px; }
    #tour-card p { font-size:25px; color:#c9d3e0; margin:10px 0; }
    #tour-card .pop { opacity:0; animation:tourIn .5s ease forwards; }
    #tour-card .flow { display:flex; align-items:center; justify-content:center; gap:12px; margin:14px 0; }
    #tour-card .box { background:#162130; border:2px solid #2f4360; border-radius:16px; padding:14px 16px; min-width:150px; }
    #tour-card .box .ic { font-size:44px; line-height:1.1; }
    #tour-card .box b { display:block; font-size:21px; margin-top:6px; }
    #tour-card .box span { display:block; font-size:15px; color:#9fb0c5; margin-top:2px; }
    #tour-card .box.you { border-color:#ffd166; } #tour-card .box.keep { border-color:#3fb67a; }
    #tour-card .arrow { font-size:34px; color:#4f9cf9; }
    #tour-card .loop { font-size:20px; color:#ffd166; margin:4px 0 16px; }
    #tour-card .grid { display:grid; grid-template-columns:1fr 1fr; gap:18px; text-align:left; }
    #tour-card .grid .box { display:flex; gap:16px; align-items:center; padding:18px 20px; }
    #tour-card .grid .box b { margin:0; font-size:24px; } #tour-card .grid .box span { font-size:17px; }
    #tour-card code { font-family:ui-monospace,Menlo,monospace; background:#162130; border:2px solid #2f4360; padding:10px 20px;
      border-radius:10px; font-size:30px; color:#ffd166; display:inline-block; margin:8px 0; }
    #tour-lens { position:fixed; right:30px; bottom:${CAP + 18}px; width:780px; z-index:9300; display:none; background:#111925;
      border:2px solid #ffd166; border-radius:12px; padding:12px 14px; box-shadow:0 10px 40px rgba(0,0,0,.6); animation:tourIn .35s ease both; }
    #tour-lens .lh { font:700 14px system-ui,-apple-system,sans-serif; color:#ffd166; margin-bottom:6px; letter-spacing:.4px; }
    #tour-lens .ev { font:13px/1.5 ui-monospace,Menlo,monospace; }
    #tour-cursor { position:fixed; z-index:9800; left:${innerWidth * 0.78}px; top:${innerHeight * 0.55}px; pointer-events:none; opacity:0;
      transition:left .8s cubic-bezier(.4,0,.2,1), top .8s cubic-bezier(.4,0,.2,1), opacity .3s; filter:drop-shadow(0 2px 3px rgba(0,0,0,.6)); }
    #tour-tip { position:fixed; z-index:9810; pointer-events:none; opacity:0; white-space:nowrap; background:#ffd166; color:#08111c;
      font:800 15px system-ui,-apple-system,sans-serif; padding:5px 11px; border-radius:8px; box-shadow:0 4px 14px rgba(0,0,0,.5);
      transition:left .8s cubic-bezier(.4,0,.2,1), top .8s cubic-bezier(.4,0,.2,1), opacity .25s; }
    .tour-ripple { position:fixed; z-index:9790; width:18px; height:18px; margin:-9px 0 0 -9px; border-radius:50%; border:3px solid #ffd166;
      pointer-events:none; animation:tourRipple .6s ease-out forwards; }
    @keyframes tourRipple { to { transform:scale(4); opacity:0; } }
    @keyframes tourIn { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:none; } }
  ` + th.css;
  document.head.append(css);
  const el = (tag, id, html = '') => { const e = document.createElement(tag); if (id) e.id = id; e.innerHTML = html; document.body.append(e); return e; };
  const dim = el('div', 'tour-dim');
  const cardEl = el('div', 'tour-card');
  const lensEl = el('div', 'tour-lens');
  const cap = el('div', 'tour-cap', '<div id="tour-prog"></div><div id="tour-body"><span id="tour-chip"></span><div id="tour-title"></div><div id="tour-text"></div></div>');
  const cursor = el('div', 'tour-cursor', '<svg width="30" height="30" viewBox="0 0 28 28"><path d="M2 2 L2 22 L7.5 16.8 L11.6 25.4 L15.4 23.7 L11.4 15.3 L19 15.3 Z" fill="#fff" stroke="#111" stroke-width="1.6" stroke-linejoin="round"/></svg>');
  const tip = el('div', 'tour-tip');
  const rings = [];
  let targetFn = null;

  const union = (rs) => {
    const left = Math.min(...rs.map((r) => r.left)), top = Math.min(...rs.map((r) => r.top));
    const right = Math.max(...rs.map((r) => r.right)), bottom = Math.max(...rs.map((r) => r.bottom));
    return { left, top, right, bottom, width: right - left, height: bottom - top };
  };
  const evaluate = (src) => new Function(`return (${src});`)();
  const items = () => {
    if (!targetFn) return [];
    let v; try { v = targetFn(); } catch { return []; }
    return (Array.isArray(v) ? v : [v]).filter(Boolean);
  };
  const elsOf = (it) => (it.group ? it.group.filter(Boolean) : [it]);
  const rects = () => items().map((it) => {
    const rs = elsOf(it).map((e) => e.getBoundingClientRect()).filter((r) => r.width || r.height);
    if (!rs.length) return null;
    const u = union(rs);
    return { left: u.left - PAD, top: u.top - PAD, width: u.width + 2 * PAD, height: u.height + 2 * PAD, right: u.right + PAD, bottom: u.bottom + PAD };
  }).filter(Boolean);

  (function frame() {
    const rs = rects();
    while (rings.length < rs.length) { const r = document.createElement('div'); r.className = 'tour-ring'; document.body.append(r); rings.push(r); }
    rings.forEach((ring, i) => {
      const r = rs[i];
      if (!r) { ring.style.display = 'none'; return; }
      Object.assign(ring.style, { display: 'block', left: `${r.left}px`, top: `${r.top}px`, width: `${r.width}px`, height: `${r.height}px` });
    });
    if (rs.length) {
      const holes = rs.map((r) => `M${r.left} ${r.top}h${r.width}v${r.height}h${-r.width}Z`).join(' ');
      dim.style.clipPath = `path(evenodd, "M0 0H${innerWidth}V${innerHeight}H0Z ${holes}")`;
      dim.style.opacity = 1;
    } else dim.style.opacity = 0;
    requestAnimationFrame(frame);
  })();

  async function focus(src, align = 'center') {
    targetFn = src ? () => evaluate(src) : null;
    const its = items();
    if (!its.length) return;
    const tb = document.getElementById('tracebox');
    const inner = its.flatMap(elsOf).filter((e) => tb && e !== tb && tb.contains(e));
    if (inner.length) {  // centre trace lines inside the scrolling trace box first
      const u = union(inner.map((e) => e.getBoundingClientRect())), tr = tb.getBoundingClientRect();
      tb.scrollTo({ top: tb.scrollTop + (u.top - tr.top) - (tb.clientHeight - u.height) / 2, behavior: 'smooth' });
      await wait(550);
    }
    const u = union(rects()), avail = innerHeight - CAP - 2 * TOP;
    const delta = align === 'top' || u.height > avail ? u.top - TOP - 70 : u.top - (TOP + (avail - u.height) / 2);
    window.scrollBy({ top: delta, behavior: 'smooth' });
    await wait(750);
  }

  async function click(src, label) {
    const target = evaluate(src);
    if (!target) throw new Error(`click target not found: ${src}`);
    await focus(src);
    const r = target.getBoundingClientRect(), x = r.left + r.width / 2, y = r.top + r.height / 2;
    tip.textContent = label || `${th.click}${target.textContent.trim()}`;
    Object.assign(cursor.style, { opacity: 1, left: `${x}px`, top: `${y}px` });
    Object.assign(tip.style, { opacity: 1, left: `${Math.min(x + 24, innerWidth - tip.offsetWidth - 12)}px`, top: `${y + 26}px` });
    await wait(900);
    const rip = document.createElement('div');
    rip.className = 'tour-ripple'; rip.style.left = `${x}px`; rip.style.top = `${y}px`;
    document.body.append(rip); setTimeout(() => rip.remove(), 700);
    target.click();
    await wait(700);
    tip.style.opacity = 0;
  }

  async function type(src, text) {
    const input = evaluate(src);
    await click(src, th.typing);
    input.focus();
    for (const ch of text) { input.value += ch; await wait(38); }
  }

  function caption(chip, title, text, idx, total, seconds) {
    document.getElementById('tour-chip').textContent = chip;
    document.getElementById('tour-title').textContent = title;
    document.getElementById('tour-text').textContent = text;
    const body = document.getElementById('tour-body');
    body.classList.remove('in'); void body.offsetWidth; body.classList.add('in');
    const prog = document.getElementById('tour-prog');
    prog.style.transitionDuration = '0s'; prog.style.width = `${(idx / total) * 100}%`; void prog.offsetWidth;
    prog.style.transitionDuration = `${seconds}s`; prog.style.width = `${((idx + 1) / total) * 100}%`;
  }

  function card(html) {
    cardEl.classList.remove('show');
    cardEl.innerHTML = html || '';
    if (html) { void cardEl.offsetWidth; cardEl.classList.add('show'); cursor.style.opacity = 0; targetFn = null; }
  }

  function stageLines(stage) {
    const groups = [];
    for (const e of document.querySelectorAll('#tracebox .ev')) {
      const m = (e.querySelector('.msg')?.textContent || '').match(/^stage: (\w+)/);
      if (m) groups.push({ stage: m[1], lines: [e] }); else if (groups.length) groups[groups.length - 1].lines.push(e);
    }
    return groups.filter((g) => g.stage === stage).pop()?.lines || [];
  }

  function lens(stage) {
    if (!stage) { lensEl.style.display = 'none'; return; }
    const lines = stageLines(stage);
    const head = document.createElement('div');
    head.className = 'lh'; head.textContent = th.lens;
    lensEl.replaceChildren(head, ...lines.slice(0, 9).map((e) => e.cloneNode(true)));
    lensEl.style.display = 'none'; void lensEl.offsetWidth; lensEl.style.display = 'block';
  }

  window.__tour = { focus, click, type, caption, card, lens };
}

// ---- Targets (JS expressions evaluated in the page) ------------------------------------------------------
const T = {
  q: (sel) => `document.querySelector(${J(sel)})`,
  card: (sel) => `document.querySelector(${J(sel)}).closest('.card')`,
  sample: (id) => `[...document.querySelectorAll('#samples button')].find((b) => b.textContent === ${J(id)})`,
  step: (label) => `[...document.querySelectorAll('#detail .step')].find((s) => s.textContent === ${J(label)})`,
  stat: (label) => `[...document.querySelectorAll('#detail .stat')].find((s) => s.querySelector('span').textContent === ${J(label)})`,
  trace: (re) => `[...document.querySelectorAll('#tracebox .ev')].find((e) => ${re}.test(e.textContent))`,
  para: (re) => `[...document.querySelectorAll('#detail p')].find((p) => ${re}.test(p.textContent))`,
  pill: `document.querySelector('#detail .pill')`,
};
const all = (...xs) => `[${xs.join(', ')}]`;
const group = (...xs) => `{ group: [${xs.join(', ')}] }`;

// ---- Actions (run from Node) -----------------------------------------------------------------------------
let js;
const waitFor = async (src, ms = 60000) => {
  for (const end = Date.now() + ms; Date.now() < end; await sleep(200)) {
    if (await js(`!!(${src})`, 2000).catch(() => false)) return;  // the page may be mid-navigation
  }
  throw new Error(`timed out waiting for: ${src}`);
};
// Long tour actions (scrolling, clicking, typing) run in the page on their own and are polled until done,
// so a lost reply to one long request cannot stall the recording.
let acts = 0;
const act = async (expr) => {
  const id = ++acts, done = `window.__act?.id === ${id} && window.__act.result`;
  await js(`window.__act = { id: ${id}, result: null }; Promise.resolve().then(() => ${expr})
    .then(() => 'ok', (e) => 'error: ' + (e?.message || e)).then((r) => { window.__act.result = r; }); 0`, 3000)
    .catch(() => {});  // if this reply is lost, the poll below still sees whether the action started
  await waitFor(done);
  const result = await js(done, 2000).catch(() => js(done, 2000));
  if (result !== 'ok') throw new Error(result);
};
const pick = (id) => () => act(`__tour.click(${J(T.sample(id))})`);
const submit = (...statuses) => async () => {
  await act(`__tour.click(${J(T.q('#submit'))})`);
  await waitFor(`document.querySelector('#detail h3')?.textContent === document.getElementById('title').value
    && ${J(statuses)}.includes(document.querySelector('#detail .pill')?.textContent)`);
  await sleep(500);
};
const decide = (approve) => async () => {
  await act(`__tour.click(${J(T.q(approve ? '.approval button.ok' : '.approval button.bad'))})`);
  await waitFor(`${T.pill}?.textContent === ${J(approve ? 'completed' : 'rejected')}`);
  await sleep(500);
};

// ---- Title cards -----------------------------------------------------------------------------------------
// pop() fades an element in after the previous ones, so each card builds up piece by piece.
const pop = (i, html, tag = 'div', style = '', cls = '') =>
  `<${tag} class="pop ${cls}" style="animation-delay:${(i * 0.18).toFixed(2)}s;${style}">${html}</${tag}>`;
const box = (ic, title, sub, cls = '') => `<div class="box ${cls}"><div class="ic">${ic}</div><div><b>${title}</b><span>${sub}</span></div></div>`;
const flow = (boxes, start = 0) =>
  `<div class="flow">${boxes.map((b, i) => (i ? pop(start + i * 2 - 1, '➜', 'div', '', 'arrow') : '') + pop(start + i * 2, b)).join('')}</div>`;

const CARDS = {
  title: `<div class="tc">${pop(0, '🤖 🛠️ 🙋', 'div', 'font-size:84px')}${pop(1, 'AgentForge', 'h1')}
    ${pop(2, 'A team of AI helpers that writes code, with a human in charge', 'p')}
    ${pop(3, 'A recording of the real dashboard · offline demo mode', 'p', 'font-size:19px;color:#8c97a8')}</div>`,
  idea: `<div class="tc">${pop(0, 'The idea in one picture', 'h2')}${flow([
    box('🙋', 'You ask', 'for a small job (a ticket)'),
    box('🤖', 'AI team works', 'in a safe scratch area (sandbox)'),
    box('🙋', 'You decide', 'approve or reject', 'you'),
    box('📦', 'Kept', 'in the real folder (workspace)', 'keep')], 1)}</div>`,
  pipeline: `<div class="tc">${pop(0, 'One job per helper', 'h2')}${flow([
    box('📐', 'Planner', 'makes the plan'), box('📋', 'Tester', 'writes the checklist first'),
    box('🔨', 'Coder', 'writes the code'), box('✔️', 'Check', 'runs the checklist'), box('👀', 'Reviewer', 'checks quality')], 1)}
    ${pop(10, '↺ checklist fails → the Coder tries again (up to 3 times)', 'div', '', 'loop')}
    ${flow([box('🛡️', 'Security', 'looks for danger'), box('📝', 'Docs', 'writes instructions'),
      box('🙋', 'You', 'approve or reject', 'you'), box('📦', 'Promote', 'copy to real folder', 'keep')], 11)}</div>`,
  mock: `<div class="tc">${pop(0, '🎭', 'div', 'font-size:84px')}${pop(1, 'A pretend AI, for a safe demo', 'h2')}
    ${pop(2, '✅ Free &nbsp;&nbsp; ✅ Works offline &nbsp;&nbsp; ✅ Same result every time', 'p')}
    ${pop(3, 'One setting switches it to real Claude:', 'p', 'margin-top:30px')}${pop(4, '<code>AGENTFORGE_PROVIDER=anthropic</code>')}</div>`,
  safety: `<div class="tc">${pop(0, 'Four safety layers, written in code', 'h2')}<div class="grid">
    ${pop(1, box('🔒', 'Permissions', 'each helper may only write its own folder'))}${pop(2, box('🔑', 'Secret scanner', 'no passwords or keys in code'))}
    ${pop(3, box('⏱️', 'Budgets', 'max 40 AI calls and 80,000 tokens per job'))}${pop(4, box('🙋', 'Human approval', 'nothing is kept without a yes', 'you'))}</div></div>`,
  limits: `<div class="tc">${pop(0, 'Honest limits', 'h2')}<div class="grid">
    ${pop(1, box('🎭', 'Scripted AI', 'the demo AI follows a script'))}${pop(2, box('📦', 'Scratch area', 'a separate process, not a sealed container'))}
    ${pop(3, box('🔓', 'No login', 'the page only runs on your own computer'))}${pop(4, box('🧸', 'Learning demo', 'not production software'))}</div></div>`,
  try: `<div class="tc">${pop(0, 'Try it yourself', 'h2')}${pop(1, '<code>python3 -m agentforge serve</code>')}
    ${pop(2, 'then open <b>http://127.0.0.1:8765</b>', 'p')}${pop(3, 'Thank you! 🙏', 'h1', 'margin-top:36px')}</div>`,
};

// ---- The script ------------------------------------------------------------------------------------------
const STEPS = [
  ['plan', 'Plan', 'The planner (architect) looks up our coding standards and past jobs (retrieval, or RAG), then asks the AI for a plan.'],
  ['tests', 'Tests', 'The tester writes the checklist (unit tests) before any code exists. The coder is not allowed to change it.'],
  ['code', 'Code', 'The coder (builder) writes the code. A safety rule (guardrail) only lets the coder save files in the source folder.'],
  ['verify', 'Verify', 'The checklist runs against the new code. Every test passes on the first try.'],
  ['review', 'Review', 'The reviewer (foreman) checks the code against our standards and approves it.'],
  ['security', 'Security', 'The security checker scans for dangerous patterns, such as passwords in code. It finds none, so the risk is low.'],
  ['docs', 'Docs', 'The docs writer creates a short instruction page for the new code.'],
  ['approval', 'Approval', 'Now the team stops and waits for a human. Nothing has left the scratch area yet.'],
];
const STATS = [
  ['attempts', 'Attempts', 'How many tries the coder needed. Here: one.'],
  ['guardrail blocks', 'Guardrail blocks', 'How many times a safety rule (guardrail) stopped a helper. Here: zero.'],
  ['model calls', 'Model calls', 'How many times the helpers asked the AI (model calls). Every job has a hard limit.'],
  ['tokens (est.)', 'Tokens', 'How much text the AI read and wrote (tokens). Think of it as a taxi meter for cost. With the pretend AI, it is free.'],
  ['security risk', 'Security risk', "The security checker's verdict: low."],
  ['last tests', 'Last tests', 'The result of the last checklist run: pass.'],
];
const J1 = 'Job 1 · palindrome';

const SCENES = [
  { chip: 'Intro', title: 'AgentForge', card: CARDS.title,
    text: 'Meet AgentForge: a team of AI helpers (agents) that writes and checks code, while a human stays in charge.' },
  { chip: 'Intro', title: 'The idea in one picture', card: CARDS.idea,
    text: 'You ask for a small piece of software. The AI team works in a safe scratch area (sandbox). Nothing is kept until a person says yes.' },
  { chip: 'Intro', title: 'One job per helper', card: CARDS.pipeline,
    text: 'Planner, tester, coder, reviewer, security checker and docs writer. The tester writes the checklist first. If it fails, the coder tries again, up to 3 times.' },
  { chip: 'Intro', title: 'A pretend AI, for a safe demo', card: CARDS.mock,
    text: 'This recording uses a scripted pretend AI (mock model): free, offline, and the same result every time. One setting switches it to real Claude.' },

  { chip: 'Screen tour', title: 'Which AI is working', target: T.q('#provider'),
    text: 'Top left: which AI is working. Here it is the pretend one (mock).' },
  { chip: 'Screen tour', title: 'The exam score', target: T.q('#evalchip'),
    text: 'Top right: the exam score (evals), meaning how many practice jobs the whole team passed. We have not run the exam yet.' },
  { chip: 'Screen tour', title: 'Ask for work', target: T.card('#submit'),
    text: 'On the left you ask for work (a ticket). The five buttons fill in ready-made example jobs. Each one shows a different lesson.' },
  { chip: 'Screen tour', title: 'History', target: T.card('#runs'),
    text: 'Below it: the history of every job (runs) and how it ended. It is empty because we started fresh.' },
  { chip: 'Screen tour', title: 'Watch the team work', target: T.q('#detail'),
    text: 'The big area on the right shows the job you pick, step by step.' },

  { chip: J1, title: 'The happy path', before: pick('palindrome'), target: T.card('#submit'),
    text: 'Job one: a palindrome checker, for words that read the same both ways, like "level". Everything should go right the first time.' },
  { chip: J1, title: 'Run agents', before: submit('awaiting approval'), target: all(T.pill, T.q('#detail .stepper')),
    text: 'We press Run agents. In under a second the team finishes and stops at the approval step, waiting for us.' },
  { chip: J1, title: 'The progress bar', target: T.q('#detail .stepper'),
    text: 'These are the nine steps. Green means done. Blue means where the job is now. Let us go through each one.' },
  ...STEPS.map(([stage, label, text], i) => ({ chip: `${J1} · Step ${i + 1} of 9`, title: label, target: T.step(label), align: 'top', lens: stage, text })),
  ...STATS.map(([label, title, text]) => ({ chip: `${J1} · The numbers`, title, target: T.stat(label), text })),
  { chip: `${J1} · The numbers`, title: 'Two summaries', target: group(T.para('/^Plan:/'), T.para('/^Security:/')),
    text: 'Two one-line summaries: what the planner decided, and what the security checker found.' },
  { chip: `${J1} · Your decision`, title: 'Human approval', target: T.q('.approval'), align: 'top',
    text: 'The most important part: human approval. It shows exactly what will change, file by file.' },
  { chip: `${J1} · Your decision`, title: 'What changed', target: T.q('.approval details'),
    text: 'Green lines are new. Here is the code the coder wrote, line by line.' },
  { chip: `${J1} · Your decision`, title: 'Leave a note', target: T.q('.approval input'),
    before: () => act(`__tour.type(${J(T.q('.approval input'))}, ${J('Looks good: tests pass and the risk is low.')})`),
    text: 'We can add a note. It is saved in the audit trail (a record of who decided what, and why).' },
  { chip: `${J1} · Your decision`, title: 'Approve', before: decide(true), target: all(T.pill, T.q('#detail .stepper'), T.para('/^Decision:/')),
    text: 'We press Approve and promote. The job is now completed, and our decision is recorded.' },
  { chip: `${J1} · Step 9 of 9`, title: 'Promote', target: T.step('Promote'), align: 'top', lens: 'promote',
    text: 'Only after our yes, the new files are copied into the real project folder (workspace).' },
  { chip: J1, title: 'The diary', target: group(`document.getElementById('tracebox').previousElementSibling`, T.q('#tracebox')),
    text: 'Everything you just saw is written here, one line per decision (the trace). This is the audit record.' },

  { chip: 'Job 2 · slugify', title: 'A mistake gets caught', before: pick('slugify'), target: T.card('#submit'),
    say: 'Job two: turn a title into a web address, also called slug-ify. This time the coder makes a mistake on the first try.',
    text: 'Job two: turn a title into a web address (slugify). This time the coder makes a mistake on the first try.' },
  { chip: 'Job 2 · slugify', title: 'Two tries', before: submit('awaiting approval'), target: T.stat('attempts'),
    text: 'Attempts: two. The first try had a bug.' },
  { chip: 'Job 2 · slugify', title: 'Caught by the checklist', target: all(T.trace('/unittest: FAIL/'), T.trace('/attempt 2\\/3/'), T.trace('/unittest: PASS/')),
    text: 'In the diary: the checklist failed, the coder got the error as feedback, fixed it, and passed. No human had to step in.' },
  { chip: 'Job 2 · slugify', title: 'Approve', before: decide(true), target: T.pill,
    text: 'It looks right, so we approve it.' },

  { chip: 'Job 3 · billing', title: 'A password in the code', before: pick('billing'), target: T.card('#submit'),
    text: 'Job three: connect to a billing service. On the first try, the coder types a secret key straight into the code.' },
  { chip: 'Job 3 · billing', title: 'A safety rule fired', before: submit('awaiting approval'), target: T.stat('guardrail blocks'),
    text: 'Guardrail blocks: one. A safety rule stopped something.' },
  { chip: 'Job 3 · billing', title: 'Blocked before saving', target: T.trace('/BLOCKED/'),
    text: 'Here, in red: the secret scanner found the key and blocked the file before it was saved. On the second try, the coder reads the key from a safe setting instead.' },
  { chip: 'Job 3 · billing', title: 'Saying no', before: decide(false), target: all(T.pill, T.para('/^Decision:/')),
    text: 'A human can always say no. We press Reject. Nothing is copied to the real folder.' },

  { chip: 'Job 4 · clamp', title: 'Trying to cheat', before: pick('clamp'), target: T.card('#submit'),
    text: 'Job four: keep a number inside a range (clamp). On the first try, the coder tries to make the checklist easier to pass.' },
  { chip: 'Job 4 · clamp', title: 'Blocked', before: submit('awaiting approval'), target: T.trace('/BLOCKED/'),
    text: 'Blocked. The coder may only write in the source folder, never in the tests. So it has to fix its own code instead.' },
  { chip: 'Job 4 · clamp', title: 'Approve', before: decide(true), target: T.pill,
    text: 'The final code is honest and passes, so we approve it.' },

  { chip: 'Job 5 · sso', title: 'Too hard for the script', before: pick('sso'), target: T.card('#submit'),
    say: 'Job five: add company single sign-on, S S O. The pretend AI has no script for this one.',
    text: 'Job five: add company single sign-on (SSO). The pretend AI has no script for this one.' },
  { chip: 'Job 5 · sso', title: 'Stops safely', before: submit('failed'), target: all(T.q('#detail .step.err'), T.q('#detail p.err')),
    text: 'The plan step turns red and the job stops. It fails safely, instead of guessing and writing something wrong.' },

  { chip: 'Exam · evals', title: 'Run the exam', target: T.card('#runevals'),
    before: () => act(`__tour.click(${J(T.q('#runevals'))})`),
    after: () => waitFor(`document.getElementById('runevals').textContent === 'Run eval suite' && document.querySelector('#evals table')`, 180000),
    text: 'Last, the exam. Run eval suite replays all five example jobs in a throwaway copy, and checks that each one behaves as expected.' },
  { chip: 'Exam · evals', title: 'Scorecard', target: T.q('#evals'),
    text: 'Five out of five passed. We re-run this exam on every change, so we measure the team instead of just trusting it.' },
  { chip: 'Exam · evals', title: 'Always visible', target: T.q('#evalchip'),
    text: 'The score also shows at the top of the screen.' },

  { chip: 'Wrap-up', title: 'Four safety layers', card: CARDS.safety,
    text: 'Four safety layers, written in code rather than in instructions to the AI: permissions, the secret scanner, budgets, and human approval.' },
  { chip: 'Wrap-up', title: 'Honest limits', card: CARDS.limits,
    text: 'To be honest: the AI here is scripted, the scratch area is a separate process rather than a sealed container, and the page has no login. It is a learning demo.' },
  { chip: 'Wrap-up', title: 'Try it yourself', card: CARDS.try,
    text: 'One command starts it, then open the page in your browser. Thanks for watching!' },
];

// CUT=<name> loads <name>-cut.mjs, which builds its own scenes from these helpers.
const CUT = process.env.CUT
  ? (await import(`./${process.env.CUT}-cut.mjs`)).default({ T, all, group, pick, submit, decide, waitFor, act, pop })
  : { out: OUT, theme: {}, scenes: SCENES };

// ---- Main ------------------------------------------------------------------------------------------------
async function main() {
  const info = await fetch(`${APP}/api/info`).then((r) => r.json()).catch(() => null);
  if (!info) throw new Error(`AgentForge is not running at ${APP}. Start it with: python3 -m agentforge serve`);
  const runs = (await fetch(`${APP}/api/runs`).then((r) => r.json())).runs;
  if (runs.length) console.warn(`! ${runs.length} run(s) already exist; for a clean video run: python3 -m agentforge reset --yes (then restart serve)`);

  const { out, theme, scenes, silent } = CUT;
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'agentforge-rec-'));
  if (silent) {  // captions only: hold each scene for reading time (~180 wpm) plus a moment to look at the screen
    scenes.forEach((s) => { s.seconds = Math.max(4, 2 + s.text.split(/\s+/).length / 3) + (s.hold || 0); });
    console.log(`Timing ${scenes.length} silent scenes: ${scenes.reduce((a, s) => a + s.seconds, 0).toFixed(0)}s of captions`);
  } else {
    console.log(`Narrating ${scenes.length} scenes with voice ${VOICE}...`);
    const say = (t) => t.replace(/AgentForge/g, 'Agent Forge').replace(/[()]/g, ',');
    scenes.forEach((s, i) => Object.assign(s, narrate(s.say || say(s.text), path.join(tmp, `clip${i}`))));
    console.log(`  ${scenes.reduce((a, s) => a + s.seconds, 0).toFixed(0)}s of narration`);
  }

  const { proc: chrome, pageWs } = await launchChrome(path.join(tmp, 'profile'));
  const cdp = new CDP(pageWs);
  await cdp.open();
  js = async (expression, ms = 10000) => {
    const r = await cdp.send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true }, ms);
    if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
    return r.result.value;
  };
  const sync = (expression) => js(expression, 3000).catch(() => js(expression, 3000));  // instant, repeatable overlay calls

  let ff;
  try {
    await cdp.send('Page.enable');
    await cdp.send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: DPR, mobile: false });
    await cdp.send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-color-scheme', value: 'dark' }] });
    await cdp.send('Page.navigate', { url: APP });
    await waitFor(`document.querySelectorAll('#samples button').length === 5 && document.getElementById('provider').textContent !== 'loading...'`);
    await js(`(${installTour.toString()})(${J(theme)})`);

    // Constant 25 fps: the latest screencast frame is written to ffmpeg on every tick.
    const video = path.join(tmp, 'video.mp4');
    ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
      '-vf', 'scale=1920:1080:flags=lanczos,format=yuv420p', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', video],
      { stdio: ['pipe', 'inherit', 'inherit'] });
    const ffDone = new Promise((resolve) => ff.on('exit', resolve));
    let latest = null, written = 0, t0 = 0;
    cdp.on('Page.screencastFrame', (p) => {
      latest = Buffer.from(p.data, 'base64');
      cdp.send('Page.screencastFrameAck', { sessionId: p.sessionId }).catch(() => {});
    });
    await cdp.send('Page.startScreencast', { format: 'jpeg', quality: 90, maxWidth: 1920, maxHeight: 1080 });
    while (!latest) await sleep(50);
    t0 = performance.now();
    const now = () => (performance.now() - t0) / 1000;
    const pump = setInterval(() => { for (const due = Math.floor(now() * FPS); written < due; written++) ff.stdin.write(latest); }, 20);

    const clips = [];
    for (const [i, s] of scenes.entries()) {
      console.log(`  [${String(i + 1).padStart(2)}/${scenes.length}] ${s.chip} · ${s.title}${silent ? `: ${s.text}` : ''}`);
      await sync(`__tour.card(${J(s.card || '')})`);
      await sync('__tour.lens(null)');
      if (s.before) await s.before();  // the click happens under the previous caption, so the new one matches the result
      await sync(`__tour.caption(${J(s.chip)}, ${J(s.title)}, ${J(s.text)}, ${i}, ${scenes.length}, ${s.seconds + 1.5})`);
      await act(`__tour.focus(${J(s.target || '')}, ${J(s.align || 'center')})`);
      if (s.lens) await sync(`__tour.lens(${J(s.lens)})`);
      if (s.pcm) clips.push({ at: now() + 0.15, pcm: s.pcm });
      await sleep(s.seconds * 1000 + 900);
      if (s.after) await s.after();
    }
    await sleep(1500);
    clearInterval(pump);
    ff.stdin.end();
    await ffDone;

    if (silent) {
      execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', video, '-c:v', 'copy', '-an', '-movflags', '+faststart', out]);
    } else {
      const wav = path.join(tmp, 'narration.wav');
      writeWav(wav, clips, written / FPS);
      execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', video, '-i', wav, '-map', '0:v', '-map', '1:a',
        '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', out]);
    }
    console.log(`\nSaved ${out} (${(written / FPS / 60).toFixed(1)} min)`);
    fs.rmSync(tmp, { recursive: true, force: true });
  } catch (e) {
    ff?.kill();
    console.error(`\nRecording failed; temp files kept in ${tmp}`);
    throw e;
  } finally {
    cdp.ws.close();
    chrome.kill();
  }
}

main().catch((e) => { console.error(e.message || e); process.exit(1); });
