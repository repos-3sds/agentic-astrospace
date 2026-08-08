# AGENTS.md — cross-agent operating protocol

Status: canonical, permanent protocol. This file changes rarely and only by
agreement between the agents active on this repo. It does not track who is
doing what today — that's [docs/agent_work_ledger.md](docs/agent_work_ledger.md),
which changes daily and should never be edited to make a "yes we followed
the rules" claim; only this file makes rules.

Agents currently active on this repo: **Claude Code (Sonnet 5)**, **GPT
Codex (5.5 Medium)**, **Gemini 3.1 Pro**, **Qwen Coder**. If a fifth agent
joins, add it to the roster in the ledger, not here — this file's rules
apply to whoever is present, by name is not load-bearing.

## Why this file exists

Four independent agentic tools can all read and write the same working
directory and push to the same `main`, with no shared session and no
built-in awareness of each other. Every real collision so far has been a
**shared-state** problem, not a **feature-ownership** problem:

- Two agents running local dev servers on the same ports, twice.
- One agent mid-editing a file with uncommitted changes while another was
  independently diagnosing a bug in that same file — by the time the second
  agent flagged the bug, the code had already changed shape underneath it.
- A task run in an isolated worktree produced a patch against a stale
  snapshot because the worktree couldn't see live uncommitted work in the
  main checkout.
- A PR that touched `.gitignore` deleted a deliberately-documented exclusion
  (a 528MB knowledge-base directory, kept out of git history on purpose)
  under the label "cleanup" — CI was green, and it would have merged clean
  if nobody had checked `git status` afterward.

None of these were caused by the wrong agent doing the wrong feature. They
were caused by the *absence* of rules for touching things more than one
agent can reach. Fix that first. Feature assignment (in the ledger) is the
second-order problem — get this file right and the ledger mostly manages
itself.

## Rule 1: Claim before you start, every time

Before starting non-trivial work, add or update your row in
[docs/agent_work_ledger.md](docs/agent_work_ledger.md): what you're doing,
which branch, which files/areas you expect to touch. Before touching a file
outside your own owned area (see Rule 4), check the ledger for whether
someone else's row already claims it. If it does, don't silently start
anyway — either wait, pick a different task, or say so out loud in whatever
channel reaches that agent (the ledger comment, or relayed through the
user).

## Rule 2: Commit before you stop, every time

No agent leaves uncommitted work sitting in the shared working directory
across a session boundary — i.e., before you stop responding, either commit
what you have (even as a small, honestly-scoped WIP commit) or explicitly
note in the ledger that specific files are mid-edit and not yet safe for
another agent to touch. "I'll commit it next time I'm back" is exactly the
failure mode that produced the stale-worktree-patch incident above — the
next agent (or the next *you*, in a fresh session with no memory of this
one) can't tell live-in-progress apart from abandoned.

Corollary: if you find uncommitted changes you didn't make, don't assume
they're stale garbage and don't build on top of them without understanding
what they are. Check `git log`/`git diff` for context, check the ledger for
who claimed that area, and ask before discarding or overwriting.

## Rule 3: Dev servers — check before you start one

Before starting any local server (backend, frontend, or otherwise), check
what's already running (`ps`, `lsof -i :<port>`) rather than assuming the
port is free. If it's already running and it's not yours, don't kill it
without checking the ledger for who owns it and, if unclear, asking first.

## Rule 3b: Branch switches in the shared working directory

Added 2026-08-08 after two live incidents in one session; confirmed by
agreement from Claude and Codex (the two agents directly affected), per
Rule 7.

**The problem, demonstrated twice on the same day:** this repo's working
directory is shared across agents in real time, not just its git history.
Running `git checkout` or `git checkout -b` doesn't just change your own
view — it switches the branch for *everyone* currently active in that
directory. Concurrent, uncommitted work from another agent lands on
whatever branch you just switched to, silently, with no error and no
warning.

**The rule:** don't run `git checkout <branch>` or `git checkout -b
<branch>` directly in the shared working directory. Use `git worktree add
<path> <branch>` instead — it creates an isolated directory checked out to
that branch, without touching what anyone else currently has checked out.
Do your work there, commit, push, then `git worktree remove <path>` when
done. This costs one extra command and removes the entire failure mode.

**Related, separate point this session also demonstrated:** if a
shared-branch collision happens anyway, fixing it (reset/force-push/branch
surgery) needs agreement from whoever's commits are affected before acting
— not just from whoever noticed the problem first. "I could see how to fix
it and had the access to do it" is not the same as "the affected party
agreed to this fix." A force-push always needs that agreement, even when
the goal is undoing an accidental collision rather than overwriting
intentional work.

## Rule 4: File and area ownership

Ownership means "primary maintainer, first reviewer, and default person to
ask" — not "no one else may ever touch it." Anyone can read anything.
Editing outside your own area is fine for small, obviously-correct fixes
(a typo, a clearly broken test); anything more than that should go through
the owner, per Rule 5.

| Area | Owner | Notes |
|---|---|---|
| `astrospace/agents/*`, `astrospace/api/ask_stream_routes.py`, Ask backend orchestration/sequencing | **Claude** | Also owns keeping [docs/ask_context_engine_multi_agent_architecture_2026-08-07.md](docs/ask_context_engine_multi_agent_architecture_2026-08-07.md) truthful — update it, don't fork a new dated doc |
| `ui/src/app/features/mobile/*`, native build/deploy (`ui/android/`, `ui/ios/`), mobile Ask UI renderer, cross-agent backlog/acceptance-criteria docs | **Codex** | Fullstack + mobile/UI lead; also build/install/deploy verification |
| New domain specs (taxonomy entries, domain addenda, golden-chart validation data) | **Gemini** | Start with data/spec artifacts, not direct orchestrator code — see the ledger for the first assigned domain |
| Test coverage audits, additive tests | **Qwen** | No unsupervised infra/config changes — see Rule 5 |
| `astrospace/admin/*` | **Codex** (by mutual agreement, 2026-08-08 — this file had a live-edit collision earlier and Codex took reconciliation ownership) | |
| `astrospace/agents/registry.py` | Shared | **Not append-only-safe** — see the correction below |

If an area isn't listed, default to: whoever's been working in it most
recently is the de facto owner until the ledger says otherwise.

**Correction (PR #2 review, Codex, 2026-08-08): `registry.py` is not
append-only-safe.** The first draft of this file called a new
`AGENT_REGISTRY` entry low-risk because it's structurally a small addition.
That was wrong — adding a domain there is what flips that domain from
`domain_not_ready` to the model generating real answers for real users.
That's the trust/safety boundary this whole architecture exists to protect
(see the architecture doc's Executive Position and "Registry holds only
configured/runnable agents" — the registry *is* the gate, not incidental to
it). **Adding a new domain `AgentConfig` enables production answers and
requires owner review plus tests** — domain addendum content, CE bundle
validation, verifier tests, and route tests, same bar as career/marriage
got. Pure formatting or comment-only edits to this file can still be
direct.

## Rule 5: What needs a PR + review vs. what can go straight to `main`

**Always PR + review from the relevant owner, never direct-push, never
auto-merge-on-green-CI alone:**

- `.gitignore`, anything under `.github/workflows/`, dependency manifests
  (`requirements*.txt`, `pyproject.toml`, `package.json`), CI/build config.
  Green CI means "doesn't obviously break," not "the person changing this
  understood why the previous version was the way it was" — the gitignore
  incident is exactly this gap.
- Anything outside your own owned area (Rule 4).
- A new entry in `AGENT_REGISTRY` (see the correction above).
- Database schema/migration-shaped changes.
- This file and the ledger's *structure* (not its daily content).
- Non-trivial feature work, even inside your own owned area — "owned" means
  "you're the default reviewer," not "risk doesn't apply here." A large Ask
  backend change or a large mobile UI change can still break shared
  behavior regardless of whose area it's in.

**Direct commit to `main` is fine:**

- Small fixes, docs, and tests inside your own owned area.
- Low-risk changes inside your own owned area — genuinely small in scope
  and blast radius, not just "I'm allowed to be here."
- Small, obviously-correct fixes anywhere (typo, one-line bug with a
  passing test proving it).
- Non-trivial work *only* when the user has explicitly asked for immediate
  direct push (as has happened this session) — that's the user overriding
  the default, not the default itself.

When in doubt, PR it. A review costs one round-trip; a silent regression in
shared config costs someone else finding it by accident.

## Rule 6: Handoffs

If you're stopping mid-task in a way another agent might need to pick up,
say so in the ledger: what's done, what's left, what's risky, what you'd
check first. Don't rely on the next agent re-deriving your context from the
diff alone — that's expensive and error-prone across four different agents
with four different ways of reading code.

## Rule 7: This file itself

Changes to the rules above need agreement from at least the two agents most
affected by the change (today: usually Claude and Codex, since they're the
two with direct `main`-push habits; loop in Gemini/Qwen once they're
actively working here). Don't unilaterally rewrite this file the way the
`.gitignore` "cleanup" rewrote existing conventions without checking why
they existed.
