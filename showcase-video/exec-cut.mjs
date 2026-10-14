// Leadership cut of the AgentForge showcase: business wording, captions only (no audio), consulting-style palette.
//   CUT=exec node showcase-video/record.mjs  ->  showcase-video/agentforge-executive.mp4
//
// Palette: navy #051C2C, electric blue #2251FF, cyan #00A9F4, cool grey #A2AAAD. Headlines in Georgia.
// Responsible AI: the "About this demo" card discloses the practice model and AI-assisted production, and the
// "Responsible AI" card maps EG's Best Practices for AI Agents (sections 25-26) to controls shown in the run.
// Every number on screen comes from the live run; nothing is invented.

import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const J = JSON.stringify;

const css = `
  #tour-dim { background:rgba(5,28,44,.74); }
  .tour-ring { border:3px solid #00A9F4; border-radius:6px; animation-name:exPulse;
    box-shadow:0 0 0 4px rgba(0,169,244,.22), 0 0 22px rgba(0,169,244,.5); }
  @keyframes exPulse { 50% { box-shadow:0 0 0 9px rgba(0,169,244,.08), 0 0 40px rgba(0,169,244,.8); } }
  #tour-cap { background:#FFFFFF; border-top:0; color:#051C2C; padding-top:18px; box-shadow:0 -10px 30px rgba(0,0,0,.35); }
  #tour-prog { background:#2251FF; top:0; }
  #tour-chip { text-transform:none; letter-spacing:.2px; font-weight:700; font-size:14px; color:#FFFFFF; background:#2251FF; border-radius:3px; padding:3px 10px; }
  #tour-title { font-family:Georgia,"Times New Roman",serif; font-weight:700; font-size:30px; color:#051C2C; }
  #tour-text { color:#33475B; }
  #tour-tip { background:#2251FF; color:#FFFFFF; border-radius:4px; font-weight:700; }
  .tour-ripple { border-color:#00A9F4; }
  #tour-lens { background:#051C2C; border:1px solid #00A9F4; border-radius:6px; }
  #tour-lens .lh { color:#00A9F4; letter-spacing:.2px; }

  #tour-card { background:#051C2C; color:#FFFFFF; }
  #tour-card .ex { width:1240px; text-align:left; font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; }
  #tour-card .kick { display:flex; align-items:center; gap:14px; color:#00A9F4; font-size:18px; font-weight:600; letter-spacing:.3px; margin-bottom:16px; }
  #tour-card .kick::before { content:''; width:44px; height:3px; background:#2251FF; }
  #tour-card .ex h1 { font-family:Georgia,serif; font-size:88px; font-weight:400; margin:0 0 18px; letter-spacing:0; }
  #tour-card .ex h2 { font-family:Georgia,serif; font-size:46px; font-weight:400; line-height:1.15; margin:0 0 32px; }
  #tour-card .ex .lead { font-size:26px; line-height:1.4; color:#A2AAAD; margin:0; max-width:980px; }
  #tour-card .ex .rule { width:120px; height:4px; background:#2251FF; margin:34px 0 22px; }
  #tour-card .ex .foot { font-size:17px; color:#A2AAAD; margin-top:28px; }
  #tour-card .grid3 { display:grid; grid-template-columns:repeat(3,1fr); gap:28px 36px; }
  #tour-card .grid2 { display:grid; grid-template-columns:repeat(2,1fr); gap:24px 44px; }
  #tour-card .chain { display:flex; align-items:flex-start; }
  #tour-card .chain .it { flex:1; }
  #tour-card .chain .to { color:#00A9F4; font-size:30px; padding:34px 16px 0; }
  #tour-card .it { border-top:1px solid rgba(255,255,255,.22); padding-top:14px; }
  #tour-card .it i { display:block; font-style:normal; font-family:Georgia,serif; font-size:30px; color:#00A9F4; margin-bottom:6px; }
  #tour-card .it b { display:block; font-size:23px; font-weight:600; margin-bottom:6px; }
  #tour-card .it span { display:block; font-size:17px; line-height:1.4; color:#A2AAAD; }
  #tour-card .note { font-size:20px; color:#A2AAAD; margin-top:30px; }
  #tour-card .note b { color:#00A9F4; font-weight:600; }
  #tour-card .map { display:grid; grid-template-columns:1fr 1fr; border-top:1px solid rgba(255,255,255,.22); }
  #tour-card .map > div { padding:13px 30px 13px 0; border-bottom:1px solid rgba(255,255,255,.14); font-size:20px; }
  #tour-card .map .h { color:#00A9F4; font-size:16px; font-weight:600; }
  #tour-card .map .l { color:#FFFFFF; font-weight:600; }
  #tour-card .map .r { color:#A2AAAD; }
  #tour-card .row { display:flex; gap:26px; align-items:baseline; border-top:1px solid rgba(255,255,255,.18); padding:15px 0; }
  #tour-card .row i { font-style:normal; font-family:Georgia,serif; font-size:28px; color:#00A9F4; width:48px; flex:none; }
  #tour-card .row b { font-size:24px; font-weight:500; }
`;

export default function execCut({ T, all, group, pick, submit, decide, waitFor, act, pop }) {
  const n = (i) => String(i).padStart(2, '0');
  const kick = (i, t) => pop(i, t, 'div', '', 'kick');
  const it = (i, num, title, sub) => pop(i, `<i>${num}</i><b>${title}</b><span>${sub}</span>`, 'div', '', 'it');
  const grid = (cls, items, start) => `<div class="${cls}">${items.map(([t, s], k) => it(start + k, n(k + 1), t, s)).join('')}</div>`;
  const chain = (items, start) => `<div class="chain">${items.map(([t, s], k) =>
    (k ? pop(start + k * 2 - 1, '→', 'div', '', 'to') : '') + it(start + k * 2, n(k + 1), t, s)).join('')}</div>`;
  const map = (head, rows, start) => `<div class="map">${pop(start, head[0], 'div', '', 'h')}${pop(start, head[1], 'div', '', 'h')}${
    rows.map(([l, r], k) => pop(start + k + 1, l, 'div', '', 'l') + pop(start + k + 1, r, 'div', '', 'r')).join('')}</div>`;
  const rows = (items, start) => items.map((t, k) => pop(start + k, `<i>${n(k + 1)}</i><b>${t}</b>`, 'div', '', 'row')).join('');
  const ex = (html) => `<div class="ex">${html}</div>`;

  const CARDS = {
    cover: ex(`${kick(0, 'Agentic AI · enterprise starter')}${pop(1, 'AgentForge', 'h1')}
      ${pop(2, 'An AI engineering team that plans, builds, tests and documents software changes, with people in control.', 'p', '', 'lead')}
      ${pop(3, '', 'div', '', 'rule')}${pop(4, 'Demo recording · October 2026', 'div', '', 'foot')}`),
    challenge: ex(`${kick(0, 'The challenge')}${pop(1, 'Routine changes wait in line.<br>Unchecked AI adds risk.', 'h2')}${grid('grid3', [
      ['Backlogs grow', 'Small, routine changes queue behind bigger priorities'],
      ['Expert time is scarce', 'Senior engineers spend time on routine fixes and reviews'],
      ['AI without guardrails', 'Fast code generation, but no controls, audit trail or accountability']], 2)}`),
    answer: ex(`${kick(0, 'The answer')}${pop(1, 'A governed AI team, with a person in charge', 'h2')}${chain([
      ['Request', 'A ticket describes the change'],
      ['AI team builds', 'In a safe, separate workspace'],
      ['Automatic checks', 'Tests, review and security scan'],
      ['A person approves', 'Sees every changed line'],
      ['Delivered', 'Copied into the real project']], 2)}`),
    team: ex(`${kick(0, 'How it works')}${pop(1, 'Six specialist agents on one assembly line', 'h2')}${grid('grid3', [
      ['Planner', 'Plans the change using our standards and past work'],
      ['Tester', 'Sets the quality bar before any code exists'],
      ['Coder', 'Writes the change, within strict permissions'],
      ['Reviewer', 'Checks quality against our standards'],
      ['Security', 'Scans for secrets and risky code'],
      ['Docs', 'Writes the documentation']], 2)}
      ${pop(8, '<b>Self-correcting:</b> if a check fails, the work goes back to the coder automatically, up to three attempts.', 'p', '', 'note')}`),
    about: ex(`${kick(0, 'About this demo')}${pop(1, 'What you are about to see', 'h2')}${grid('grid2', [
      ['Live application', 'Recorded from the real dashboard, not a mock-up'],
      ['Practice AI model', 'A scripted model stands in for Claude: no cost, same result every time'],
      ['No company data', 'Five sample requests only'],
      ['AI-assisted production', 'This recording was produced with help from an AI assistant']], 2)}`),
    value: ex(`${kick(0, 'Business value')}${pop(1, 'What this means for the business', 'h2')}${grid('grid3', [
      ['Speed', 'Routine requests move from ticket to review-ready automatically'],
      ['Quality', 'Tests first, automatic retries and an independent review'],
      ['Security', 'Secrets and unsafe changes are blocked before they are saved'],
      ['Control', 'Nothing is delivered without an approval decision'],
      ['Cost limits', 'Hard caps on AI calls and usage for every job'],
      ['Flexibility', 'The AI model can be swapped with one setting']], 2)}`),
    rai: ex(`${kick(0, 'Responsible AI')}${pop(1, "Built for EG's Responsible AI expectations", 'h2')}${map(['EG expectation', 'How AgentForge meets it'], [
      ['Humans stay accountable', 'A person approves or rejects every change, on record'],
      ['AI code is reviewed like human code', 'Reviewer agent, then line-by-line human review'],
      ['Audit trail, logged and attributable', 'Every decision, tool call and block is logged'],
      ['No bypassing approval gates', 'Nothing is promoted without an approval decision'],
      ['No credentials in code', 'The secret scanner blocks keys before saving']], 2)}
      ${pop(8, 'Source: EG Best Practices for AI Agents, sections 25 and 26', 'div', '', 'foot')}`),
    golive: ex(`${kick(0, 'Today and next')}${pop(1, 'From starter kit to production', 'h2')}${map(['Today', 'To go live'], [
      ['Starter kit on one laptop', "Deployed on EG's platform, with production-readiness checks"],
      ['Scripted practice model', "Real Claude through EG's GenAI Proxy"],
      ['A separate process for each job', 'A sealed, isolated workspace for each job'],
      ['No sign-in', 'Company single sign-on and approver roles'],
      ['Learning demo', 'Responsible AI and privacy reviews completed']], 2)}`),
    summary: ex(`${kick(0, 'Summary')}${pop(1, 'What this recording showed', 'h2')}${rows([
      'A request became tested, reviewed and documented code, automatically',
      'Mistakes were caught and fixed without a person stepping in',
      'A hard-coded secret and an attempt to weaken the tests were blocked',
      'A person decided on every change, with a full audit trail',
      'A repeatable quality exam scored five out of five'], 2)}`),
  };

  const STEPS = [
    ['plan', 'Plan', 'The planner retrieves our coding standards and past work, then drafts the plan.'],
    ['tests', 'Tests', 'The quality bar comes first: tests are written before any code, and the coder cannot change them.'],
    ['code', 'Code', 'The coder writes the change. Its permissions allow writing in the source folder only.'],
    ['verify', 'Verify', 'The tests run automatically against the new code. All pass on the first attempt.'],
    ['review', 'Review', 'A reviewer agent checks the code against our standards and approves it.'],
    ['security', 'Security', 'A security scan looks for secrets and risky code. None found, so the risk is low.'],
    ['docs', 'Docs', 'Documentation is written automatically, so knowledge is never left behind.'],
    ['approval', 'Approval', 'The team now stops and waits for a person. Nothing has left the safe workspace.'],
  ];
  const STATS = [
    ['attempts', 'Attempts', 'One attempt needed. When checks fail, retries happen automatically.'],
    ['guardrail blocks', 'Safety blocks', 'Zero safety blocks: no rule was broken on this job.'],
    ['model calls', 'AI calls', 'Every job has a hard cap of 40 AI calls, so spend cannot run away.'],
    ['tokens (est.)', 'AI usage', 'Tokens measure AI usage, like a meter. Every job is capped at 80,000.'],
    ['security risk', 'Security risk', 'The security verdict for this change: low risk.'],
    ['last tests', 'Test result', 'The latest automated test run: pass.'],
  ];
  const J1 = 'Job 1 · Standard request';

  const scenes = [
    { chip: 'Opening', title: 'AgentForge', card: CARDS.cover, hold: 1,
      text: 'A team of AI agents that delivers software changes, with a person approving every one.' },
    { chip: 'Opening', title: 'The challenge', card: CARDS.challenge, hold: 3,
      text: 'Routine changes queue up behind big priorities. AI can write code fast, but without controls it adds risk.' },
    { chip: 'Opening', title: 'The answer', card: CARDS.answer, hold: 3,
      text: 'You submit a request, the AI team builds and checks it, and nothing is delivered until a person approves.' },
    { chip: 'Opening', title: 'How it works', card: CARDS.team, hold: 4,
      text: 'Six specialist agents, each with one job. Failed checks send the work back automatically.' },
    { chip: 'Opening', title: 'About this demo', card: CARDS.about, hold: 3,
      text: 'Recorded from the live app. A scripted practice model stands in for the real AI. No company data is used.' },

    { chip: 'Control room', title: 'Which AI is working', target: T.q('#provider'),
      text: 'Top left shows which AI model is running. Today: the scripted practice model.' },
    { chip: 'Control room', title: 'Quality score', target: T.q('#evalchip'),
      text: 'Top right shows the latest quality exam score. It has not been run yet.' },
    { chip: 'Control room', title: 'Request work', target: T.card('#submit'),
      text: 'Requests come in here. Five sample requests each demonstrate one capability.' },
    { chip: 'Control room', title: 'Every job on record', target: T.card('#runs'),
      text: 'Every job is kept on record with its outcome. The list starts empty.' },
    { chip: 'Control room', title: 'Live view', target: T.q('#detail'),
      text: 'This panel follows each job live, step by step.' },

    { chip: J1, title: 'A standard request', before: pick('palindrome'), target: T.card('#submit'),
      text: 'First, a routine request: a small text-checking feature. Everything should pass first time.' },
    { chip: J1, title: 'Run agents', before: submit('awaiting approval'), target: all(T.pill, T.q('#detail .stepper')),
      text: 'One click starts the team. With the practice model, it reaches the review step in about a second.' },
    { chip: J1, title: 'A nine-step pipeline', target: T.q('#detail .stepper'),
      text: 'Nine fixed steps, in the same order every time. Green is done, blue is the current step.' },
    ...STEPS.map(([stage, label, text], i) => ({ chip: `${J1} · Step ${i + 1} of 9`, title: label, target: T.step(label), align: 'top', lens: stage, text })),
    ...STATS.map(([label, title, text]) => ({ chip: `${J1} · Key numbers`, title, target: T.stat(label), text })),
    { chip: `${J1} · Key numbers`, title: 'Plain-language summaries', target: group(T.para('/^Plan:/'), T.para('/^Security:/')),
      text: 'One-line summaries of the plan and the security findings, for a quick sign-off.' },
    { chip: `${J1} · Human decision`, title: 'Human approval', target: T.q('.approval'), align: 'top',
      text: 'The key control: a person sees exactly what will change before anything is accepted.' },
    { chip: `${J1} · Human decision`, title: 'Every changed line', target: T.q('.approval details'),
      text: 'New lines are highlighted, so the reviewer sees precisely what the AI wrote.' },
    { chip: `${J1} · Human decision`, title: 'A reasoned sign-off', target: T.q('.approval input'),
      before: () => act(`__tour.type(${J(T.q('.approval input'))}, ${J('Approved: tests pass and the risk is low.')})`),
      text: 'The reviewer adds a note. It is stored in the audit trail with the decision.' },
    { chip: `${J1} · Human decision`, title: 'Approve', before: decide(true), target: all(T.pill, T.q('#detail .stepper'), T.para('/^Decision:/')),
      text: "Approved. The job completes, and the decision is recorded with the reviewer's note." },
    { chip: `${J1} · Step 9 of 9`, title: 'Promote', target: T.step('Promote'), align: 'top', lens: 'promote',
      text: 'Only after approval are the new files copied into the real project.' },
    { chip: J1, title: 'A full audit trail', target: group(`document.getElementById('tracebox').previousElementSibling`, T.q('#tracebox')),
      text: 'Every decision, tool call and safety check is logged, one line each, ready for audit.' },

    { chip: 'Job 2 · Self-correction', title: 'A mistake on the first attempt', before: pick('slugify'), target: T.card('#submit'),
      text: 'Next, the coder makes a mistake on its first attempt. Watch what happens.' },
    { chip: 'Job 2 · Self-correction', title: 'Two attempts', before: submit('awaiting approval'), target: T.stat('attempts'),
      text: 'Two attempts. The first version had a bug.' },
    { chip: 'Job 2 · Self-correction', title: 'Caught and fixed automatically',
      target: all(T.trace('/unittest: FAIL/'), T.trace('/attempt 2\\/3/'), T.trace('/unittest: PASS/')),
      text: 'The tests failed, the error went back to the coder, and the fix passed. No person was needed.' },
    { chip: 'Job 2 · Self-correction', title: 'Approve', before: decide(true), target: T.pill,
      text: 'The corrected work is approved.' },

    { chip: 'Job 3 · Security', title: 'A secret in the code', before: pick('billing'), target: T.card('#submit'),
      text: 'Next, the coder writes a secret key directly into the code.' },
    { chip: 'Job 3 · Security', title: 'A safety rule triggered', before: submit('awaiting approval'), target: T.stat('guardrail blocks'),
      text: 'One safety block: a rule stopped the agent.' },
    { chip: 'Job 3 · Security', title: 'Blocked before saving', target: T.trace('/BLOCKED/'),
      text: 'The secret scanner blocked the file before it was saved. The second attempt reads the key from a secure setting.' },
    { chip: 'Job 3 · Security', title: 'People have the final say', before: decide(false), target: all(T.pill, T.para('/^Decision:/')),
      text: 'The reviewer can still say no. Rejected, so nothing reaches the real project.' },

    { chip: 'Job 4 · Integrity', title: 'Trying to weaken the tests', before: pick('clamp'), target: T.card('#submit'),
      text: 'Next, the coder tries to make the tests easier to pass.' },
    { chip: 'Job 4 · Integrity', title: 'Blocked', before: submit('awaiting approval'), target: T.trace('/BLOCKED/'),
      text: 'Blocked. The coder cannot change the tests, so it has to fix its own code.' },
    { chip: 'Job 4 · Integrity', title: 'Approve', before: decide(true), target: T.pill,
      text: 'The honest fix passes and is approved.' },

    { chip: 'Job 5 · Limits', title: 'A request it cannot plan', before: pick('sso'), target: T.card('#submit'),
      text: 'Last, a request the practice model has no plan for: a single sign-on integration.' },
    { chip: 'Job 5 · Limits', title: 'Stops safely', before: submit('failed'), target: all(T.q('#detail .step.err'), T.q('#detail p.err')),
      text: 'The job stops safely at the plan step, instead of guessing and producing wrong code.' },

    { chip: 'Quality exam', title: 'Run the quality exam', target: T.card('#runevals'),
      before: () => act(`__tour.click(${J(T.q('#runevals'))})`),
      after: () => waitFor(`document.getElementById('runevals').textContent === 'Run eval suite' && document.querySelector('#evals table')`, 180000),
      text: 'The exam replays all five requests in a throwaway copy and checks every outcome.' },
    { chip: 'Quality exam', title: 'Five out of five', target: T.q('#evals'),
      text: 'Five of five passed. It is re-run on every change, so quality is measured, not assumed.' },
    { chip: 'Quality exam', title: 'Always visible', target: T.q('#evalchip'),
      text: 'The latest score stays visible at the top of the screen.' },

    { chip: 'Closing', title: 'Business value', card: CARDS.value, hold: 4,
      text: 'Speed, quality, security, control and cost limits, each one shown working in this recording.' },
    { chip: 'Closing', title: 'Responsible AI', card: CARDS.rai, hold: 5,
      text: "Each of EG's Responsible AI expectations maps to a control you saw in this demo." },
    { chip: 'Closing', title: 'From starter kit to production', card: CARDS.golive, hold: 5,
      text: 'Today it is a starter kit. These are the steps to run it in production.' },
    { chip: 'Summary', title: 'In summary', card: CARDS.summary, hold: 6,
      text: 'Fast, self-correcting, secure and fully auditable, with people in control. Thank you.' },
  ];

  return {
    out: path.join(HERE, 'agentforge-executive.mp4'),
    silent: true,
    theme: { css, lens: 'Audit trail: what happened in this step', click: 'Click: ', typing: 'Typing a note' },
    scenes,
  };
}
