# 🏗️ AgentForge: a visual walkthrough

Pictures first, plain words, with the technical term in (brackets). Every part points to the real code (`file:line`, paths under `agentforge/`). Watch it in action: `showcase-video/agentforge-demo.mp4`.

## 0️⃣ Who made what
| Part | Made by |
|---|---|
| 🧠 The app `agentforge/`, plus `lessons/`, `tests/`, `knowledge/` | Already in the folder before this session |
| 🎬 `showcase-video/record.mjs` + `exec-cut.mjs` + `agentforge-executive.mp4` | Made in this session |

---

## 1️⃣ The big map: who talks to whom
```
                         👤 YOU
              browser │              │ terminal
                      ▼              ▼
          ┌────────────────────┐   ┌───────────────────┐
          │ 🖥️ dashboard.html   │   │ ⌨️ cli.py          │
          │   the screen       │   │ run · serve · eval │
          └─────────┬──────────┘   │ trace · reset      │
                    │ asks for news └─────────┬─────────┘
                    │ every 1.2 seconds       │
          ┌─────────▼──────────┐              │
          │ 🌐 server.py        │ front desk   │
          │   (web API)        │              │
          └─────────┬──────────┘              │
                    ▼                         ▼
          ┌──────────────────────────────────────────────┐
          │ 🧭 orchestrator.py: THE MANAGER               │
          │   runs the 9 steps in a fixed order           │
          │   (plain Python code, NOT the AI)             │
          └──┬────────────┬─────────────┬────────────┬───┘
             ▼            ▼             ▼            ▼
      🤖 agents.py   🧰 tools.py    📚 memory.py   📜 tracing.py
      6 helpers      the hands      the library    the diary
             │            │            (RAG)        (trace)
             ▼            ▼
      🧠 llm.py      🛡️ guardrails.py
      the brain      safety rules
      switch
             │
      ┌──────┴──────────┐
      ▼                 ▼
 🎭 mock_library.py   ☁️ real Claude
 pretend brain        (one setting)

 🧪 evals.py = the exam        ✅ tests/ = 32 checks of the machine itself
```

---

## 2️⃣ The parts (each file, in one line)
| | Part | Everyday comparison | File (lines) | How it does it | Proof |
|---|---|---|---|---|---|
| 🧭 | Orchestrator | the **manager** | `orchestrator.py` (182) | Fixed list of 9 steps plus a retry loop of up to 3 tries | `orchestrator.py:93-170` |
| 🤖 | Agents | **6 helpers** | `agents.py` (155) | Each one = a role + instructions + one job. They only *answer*, never touch files | `agents.py:1-4`, `:36-64` |
| 🧰 | Toolbox | the **hands** | `tools.py` (165) | The only way to write files, run tests, scan or copy. Every write is checked | `tools.py:75-102` |
| 🛡️ | Guardrails | **safety rules** | `guardrails.py` (105) | 4 layers written in code (see section 4) | `guardrails.py:1-8` |
| 📚 | Memory | the **library** (RAG) | `memory.py` (52) | Finds the 3 most relevant paragraphs in `knowledge/*.md` (TF-IDF scoring) | `memory.py:41-52` |
| 🧠 | LLM switch | the **brain socket** | `llm.py` (107) | Same plug for the pretend brain or real Claude | `llm.py:83-92` |
| 🎭 | Mock library | the **pretend brain's script** | `mock_library.py` (328) | Scripted answers, with a deliberate mistake on try 1. The Reviewer is real logic | `mock_library.py:1-12` |
| 📜 | Tracer | the **diary** | `tracing.py` (58) | One line per event → `runs/<id>/trace.jsonl` | `tracing.py:29-44` |
| 🌐 | Server | the **front desk** | `server.py` (202) | Web API. Each job runs in the background and waits at the approval gate | `server.py:56-77` |
| 🖥️ | Dashboard | the **screen** | `dashboard.html` (220) | Asks the server for news every 1.2 s and redraws | `dashboard.html:215` |
| 🧪 | Evals | the **exam** | `evals.py` (85) | Replays the 5 samples in a throwaway copy and checks each expected result | `evals.py:25-60` |
| ⌨️ | CLI | **terminal buttons** | `cli.py` (141) | `run`, `serve`, `eval`, `trace`, `reset` | `cli.py:106-127` |
| 🎬 | Recorder | the **camera robot** | `showcase-video/record.mjs` (538) | Drives hidden Chrome, adds captions and voice, saves the mp4 | made this session |

---

## 3️⃣ One job, start to finish
```
 🙋 you click "Run agents"
    │  POST /api/tickets ........................... server.py:165
    ▼
 🧵 a background worker starts ..................... server.py:56-77
    ▼
 📁 copy workspace/ ➜ runs/<id>/sandbox/ ........... orchestrator.py:64
    (the scratch area: nothing real is touched)
    ▼
 1 📐 PLAN      Planner reads the library, makes a plan ... orchestrator.py:95-102
 2 📋 TESTS     Tester writes the checklist FIRST ........ orchestrator.py:105-109
 ┌───────────── up to 3 tries ─────────────────────────┐ orchestrator.py:113-136
 │ 3 🔨 CODE    Coder writes src/  ──► 🛡️ checked       │
 │ 4 ✔️ VERIFY  run the checklist (unit tests)          │
 │ 5 👀 REVIEW  Reviewer says yes / no                  │
 │    ✗ anything fails ➜ the reason becomes feedback ↺  │
 └──────────────────────────────────────────────────────┘
 6 🛡️ SECURITY  scan for danger. HIGH risk = stop .......... orchestrator.py:141-144
 7 📝 DOCS      write the instruction page ................ orchestrator.py:147-151
 8 🙋 APPROVAL  show the changes, WAIT for a human ........ orchestrator.py:154-162
 9 📦 PROMOTE   copy sandbox ➜ real workspace/ ........... orchestrator.py:165-170
```
Mistakes become feedback for the next try: `orchestrator.py:121` (blocked), `:127` (tests failed), `:133` (review said no).

---

## 4️⃣ How safety works: 4 layers in code, not in prompts
| | Layer | Plain words | Code | In the video |
|---|---|---|---|---|
| 🔒 | Permissions | Tester ➜ `tests/` only · Coder ➜ `src/` only · Docs ➜ `docs/` only | `guardrails.py:41-45` | clamp 🛑 |
| 🔑 | Secret scanner | Spots keys and passwords before a file is saved | `guardrails.py:20-27` | billing 🛑 |
| ⏱️ | Budgets | Max 40 AI calls and 80,000 tokens per job | `config.py:23-25`, `guardrails.py:73-87` | — |
| 🙋 | Approval gate | The job pauses until you click | `guardrails.py:90-105` | approve / reject |
| ➕ | All or nothing | One bad file ➜ **nothing** gets written | `tools.py:75-90` | |
| ➕ | No key leaks | The test run gets no API keys | `tools.py:105-107` | |
| ➕ | No escape | A path like `../` that tries to leave the scratch area is refused | `guardrails.py:48-57`, `tools.py:94-96` | |

---

## 5️⃣ Seven design ideas behind it
```
 🧭 The manager is code, not AI     ➜ same order every time        orchestrator.py:5-6
 🤖 Helpers talk, tools act         ➜ AI can't touch files itself   agents.py:3-4
 🔁 Mistakes become feedback        ➜ fixes itself, up to 3 tries   orchestrator.py:113-136
 🔌 One plug for any brain          ➜ mock ⇄ real Claude            llm.py:83-92
 📜 Everything goes in the diary    ➜ full audit record             tracing.py:29-44
 🧪 Measure, don't trust            ➜ exam on every change          evals.py:38-60
 📦 Zero installs                   ➜ only Python's built-in parts  README.md
```

---

## 6️⃣ The folders
```
agentforge/
├── 🧠 agentforge/       the app (all code above)
├── 📚 knowledge/        4 rule books the helpers read: coding, security, testing, past tickets
├── 🎫 tickets/          samples.json: the 5 example jobs + what SHOULD happen
├── 📦 workspace/        the REAL folder approved work lands in
├── 🗂️ runs/             one folder per job: run.json + trace.jsonl + sandbox/
├── ✅ tests/            32 checks (guardrails 15 · orchestrator 11 · memory 3 · Claude 3)
├── 🎓 lessons/          9 lessons, 00 ➜ 08
├── 🎬 showcase-video/   recorder + video (this session)
└── 📄 README · SHOWCASE · api.http · .vscode · .devcontainer
```

---

## 7️⃣ How the video was made (this session)
```
 CUT=exec node showcase-video/record.mjs      (scenes + look come from exec-cut.mjs)
   ├─► 🌐 hidden Chrome ........... opens the real dashboard (DevTools Protocol)
   ├─► 🔦 overlays ................ captions · spotlight · pointer · title cards
   ├─► 🖱️ clicks real buttons ..... real jobs really run
   └─► 🎞️ ffmpeg .................. 25 fps frames, no sound ➜ agentforge-executive.mp4
```
Without `CUT=exec`, the same recorder makes a narrated version (macOS `say` voice) called `agentforge-demo.mp4`. That file is kept out of git.

---

_The line references were checked against the code on 2026-10-14. The everyday comparisons are explanations, not documented terms._
