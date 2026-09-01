# Master Build Prompt — Reward-Hackability Auditor (CLI + Claude Skill)

**How to use this document:** Paste everything below the divider into Claude Code (or Codex/Cursor/Gemini CLI) as the opening message of a fresh session. It contains full context, a validated spec, and explicit operating instructions so the agent doesn't need anything outside this file to start working.

---

## 0. Mission

Build and ship **a tool that audits an RL environment's verifier or reward function for reward-hacking exploitability before it's deployed for training or benchmarking** — then package it two ways: a general-purpose CLI/library, and a Claude Skill (SKILL.md) distributed through the Agent Skills ecosystem. Fail-closed by default: if a verifier scores above a gameability threshold, the tool blocks the ship (CI exit code, pre-commit hook, or explicit gate command).

One-line pitch: *"Fuzz your verifier before an RL agent does."*

## 1. Why this, why now — the evidence (verify freshness before relying on it; this is current as of Sept 2026)

**The problem is real and well-documented, not hypothetical:**
- A 2026 audit that catalogs reward-hackable terminal-agent benchmark environments (Terminal Wrench, Bercovich et al., arXiv 2604.17596) found over 15% of verifiers across popular benchmarks could be bypassed by an agent optimizing for the reward signal rather than the intended solution — 331 hackable environments cataloged, 3,632 exploit trajectories collected.
- A related audit put it at 323 of 1,968 tasks (16%) hackable by frontier models given only the task description.
- A dedicated hackability audit of SWE-bench Verified (arXiv 2606.16062) found 14 of 49 audited tasks — 28.5% — were Docker-verified hackable, concentrated in specific repositories (astropy, django).
- This is a live, active research area: SpecBench, RHB (Reward Hacking Benchmark), TRACE, EvilGenie, Countdown-Code, and the "hacker-fixer loop" paper are all 2025-2026 work independently converging on the same failure mode.
- Documented exploit classes (this is your test taxonomy — see §4.2): test/assertion tampering, monkey-patched graders, stack introspection, operator overloading, premature termination, dependency-chain/environment hijacking (reading git history or walkthroughs for the answer), in-container parser overwrites, config leakage, and — for LLM-judge/rubric-graded environments — judge bias exploitation (verbosity bias, sycophancy, formatting bias).

**The wave is real and still rising:**
- OpenEnv (the Gymnasium-style standard for RL post-training environments) is coordinated by a committee including Meta-PyTorch, Reflection, Unsloth, Modal, Prime Intellect, Nvidia, Mercor, Fleet AI, Microsoft, Hugging Face, and RadixArk.
- Prime Intellect's Environments Hub is past 2,500 community-contributed RL environments as of mid-2026, backed by a $49.9M Series B (Dec 2025, $70.4M total raised).
- Separately, Anthropic's Agent Skills ecosystem (launched Oct 2025, open standard at agentskills.io since Dec 18, 2025) now spans ~40 compatible platforms (Codex, Copilot, Cursor, Gemini CLI, VS Code, Claude), with community directories indexing on the order of 1.9 million public skills and 2,500+ registered Claude Code plugin marketplaces. This is the distribution channel for the Skill half of this build — don't manufacture an audience, plug into this one.

## 2. Who you're building this for (builder context)

Solo builder, first-year CS/CE student, fluent in Python, Go, and TypeScript, comfortable shipping under hackathon deadlines. Relevant existing assets to reuse as test fixtures and launch-narrative material — **do not rebuild these, extend/reference them**:
- An OpenEnv-compatible RL environment for industrial energy management (top ~1% finish in a major ML hackathon).
- An LLVM/MLIR compiler-optimization RL environment.
- Hands-on experience authoring tasks for an LLM agentic terminal benchmark (Parsewave Terminal-Bench) — this is direct, credible experience with exactly the kind of verifier design this tool audits. Use it in the README/launch narrative as the "why me" answer.

Time budget: **not yet specified — ask the human for this before committing to the full phase plan in §6**, and scope Phase 1 (§6) to be shippable inside a single hackathon-length window (48-72 hours) regardless of the answer, since that's this builder's default cadence.

## 3. Competitive landscape — DO NOT SKIP THIS STEP

Before writing a single line of code, **search live and investigate these directly**, because stale assumptions here will waste the whole build:

1. **`rewardfuzz`** — a GitHub project surfaced under the `rl-environment` topic, self-described as: *"Verifier-gated RL environment packager: audit a verifier for gameability with rewardfuzz before you ship it (verifiers/OpenEnv emit, fail-closed gate)."* This is uncomfortably close to this spec. Its exact repo, star count, last-commit date, and feature completeness were **not confirmed** as of this prompt's writing — search GitHub directly (`site:github.com rewardfuzz`, and browse `github.com/topics/rl-environment` and `github.com/topics/reward-hacking`). Read its README and code in full. If it's a stalled hackathon project, differentiate on breadth, format support, and active maintenance. If it's further along, pivot the scope narrower (e.g., focus entirely on the Skill packaging + dynamic LLM-fuzzing mode if the static side is already covered).
2. **`cc-audit`** (ryo-ebata) — Rust-based static scanner for Claude Code artifacts (Skills, Hooks, MCP configs); 100+ detection rules, CVE database, remote repo scanning. Targets *skill/tool security* (prompt injection, exfiltration, privilege escalation) — **not** RL verifier reward-hacking. Adjacent, not overlapping, but check for scope creep in either direction.
3. **Repello SkillCheck** — browser-based Claude Skill security scanner. Same category as `cc-audit`: general skill security, not RL verifier gaming.
4. **`adithya-s-k/RL_Envs_101`** — ships Claude/Codex/Cursor-compatible skills that *generate* OpenEnv/verifiers/ORS/NeMo-Gym environments from plain-English descriptions, including a reward-hacking *lesson*. It builds environments; it does not audit them for gameability before shipping. Confirm this gap still holds.
5. Search for anything published in the last 30 days before you start — this space moves fast enough that a 6-week-old finding can already be stale.

**The gap this spec is built to fill, as of this prompt:** nobody has packaged verifier/reward-function gameability auditing as an installable, cross-format (OpenEnv + verifiers spec), statically-**and**-dynamically-tested, discoverable Claude Skill. Confirm that gap still exists before committing engineering time to it.

## 4. Product specification

### 4.1 Core capability
Given a target RL environment's verifier or reward function (as OpenEnv-compliant code, a `verifiers`-spec environment, or a raw Gymnasium `step()`/reward implementation), run a battery of exploit-class probes against it in an isolated sandbox and produce a scored exploitability report with concrete, actionable fixes — not just a pass/fail.

### 4.2 Exploit taxonomy to detect (build both a static and a dynamic pass)
Pull the taxonomy from the cited research, not from first principles — these are documented, real exploit classes:
- **Test/assertion tampering:** overwriting or deleting test files, monkey-patching the grading function, editing test files directly.
- **Grader manipulation:** stack introspection, operator overloading, in-container parser overwrites, pytest-hook overrides that force all tests to pass.
- **Premature/trivial termination:** exiting early with a fabricated success signal; binary wrapper trojans.
- **Dependency-chain / environment hijacking:** reading git history, walkthroughs, or answer keys available in the sandbox; config leakage.
- **Reward-component skipping:** bypassing individual reward terms rather than solving the task (validation-never-checks-correctness patterns).
- **LLM-judge / rubric bias exploitation** (for rubric-graded or LLM-as-judge environments): verbosity bias, sycophancy, formatting-over-substance bias, chain-of-thought reasoning that frames the exploit as legitimate problem-solving.

### 4.3 Two detection modes
- **Static mode:** pattern-based scan of verifier/reward code for known-vulnerable constructs (shared mutable state, unsanitized eval of agent-controlled input, missing sandboxing, world-writable reward files, weak/narrow test coverage heuristics).
- **Dynamic mode:** spin up a sandboxed attacker LLM and run it against the verifier using a hint-guided methodology (seed it with the exploit taxonomy in §4.2, run both hinted and blind/unhinted attempts, multiple samples per task) — this mirrors the audit methodology used by the Terminal Wrench and hacker-fixer-loop research this spec cites, so the tool's findings are defensible against the same standard the research community already uses.

### 4.4 Format compatibility
Must ingest and emit both **OpenEnv**-compliant environments and **`verifiers`**-spec environments (Prime Intellect's library), and degrade gracefully to raw Gymnasium `step()`/reward functions where neither spec is used. This is the difference between "another scattered research script" and the general-purpose tool the evidence says doesn't exist yet.

### 4.5 Distribution surfaces
1. **CLI / Python package** — pip-installable, scriptable, CI-friendly (`ratctl audit ./my_env --fail-on gameability>0.3`).
2. **GitHub Action** — for teams/individuals who want the fail-closed gate in CI before an environment is merged or published to Environments Hub.
3. **Claude Skill (SKILL.md)** — the packaged, discoverable version, installable via `npx skills add <you>/reward-hackability-auditor` and listed on the Claude Code plugin marketplace / agentskills.io showcase. This is the primary distribution bet — it rides existing infrastructure instead of requiring you to build an audience from zero.

### 4.6 Output format
A severity-scored report (0-100 gameability score, consistent with how existing skill-security tools like SkillCheck report), a breakdown by exploit class with which ones succeeded, and a suggested hardened patch for each finding — not just "this is broken," but "here's the fix."

## 5. Differentiation bar (must clear all of these)

- General-purpose, not benchmark-specific (works on any OpenEnv/verifiers/Gymnasium environment, not hardcoded to one benchmark's internals).
- Both static AND dynamic detection — most prior art (per §3) is one or the other.
- Installable and documented on day one, not a research script requiring the reader to reconstruct the method.
- Built on **published, public methodology only** — the cited papers, public task-writing guidelines — never on anything from a specific employer's non-public task set. Keep it clean and generalizable.
- Shipped as a discoverable Skill, not just a GitHub repo nobody finds.

## 6. Build plan

**Phase 0 (do this first, before any code):** Complete the competitive-landscape investigation in §3. Write a short `COMPETITIVE.md` documenting what you found and the specific differentiation decision you're making. Get human sign-off on this before Phase 1.

**Phase 1 — Static analyzer (fast, hackathon-scoped):** Python package that pattern-matches the exploit taxonomy in §4.2 against verifier source code. Ship a CLI that takes a path and returns a report. Validate against your own OpenEnv energy-management environment and LLVM/MLIR environment as first test fixtures (dogfooding + credibility for the launch narrative).

**Phase 2 — Dynamic fuzzing engine:** Sandboxed attacker-LLM harness that attempts the exploit taxonomy against a running verifier, hint-guided and blind, multiple samples per task, scored pass rate. Reuse the hint-catalog methodology from the cited hacker-fixer-loop research rather than inventing attack strategies from scratch.

**Phase 3 — Format adapters:** OpenEnv and `verifiers`-spec import/export compliance, so it works natively in both major ecosystems.

**Phase 4 — Packaging:** pip package, GitHub Action, and SKILL.md wrapper (write the skill so it's spec-compliant with agentskills.io and installs cleanly via `npx skills add`).

**Phase 5 — Validation dataset:** Run the tool against publicly documented hackable environments (Terminal Wrench's 331 cataloged environments are a natural benchmark; the SWE-bench Verified hackable subset from the cited 2026 audit is another) to produce a credible "we caught N known exploits out of M" claim for the README — this doubles as demo material.

**Phase 6 — Launch prep:** see §7.

## 7. Demo & launch checklist

- README as landing page: value prop above the fold, hero GIF in the first screen, then a "why this vs. rewardfuzz / cc-audit" section that's honest about what those tools do and don't do.
- 5-7 short functional GIFs of real usage against real (or reproduced) hackable environments — not slides.
- One coordinated launch across the 2-3 channels this audience actually lives in (OpenEnv/Prime Intellect community channels, r/reinforcementlearning or similar, agentskills.io showcase submission, Claude Code plugin marketplace listing) on the same day, rather than a slow trickle.
- Fast issue/PR response for the first month.

## 8. Success criteria

- **Demo-able in under 10 seconds:** run against a known-hackable environment, catch the exploit, show the hardened-patch suggestion — one GIF, no narration needed.
- **Evidence of pain:** already cleared (§1) — don't re-litigate this, build.
- **Differentiation:** cleared only if Phase 0 confirms the gap in §3 still holds.
- **Buildable in budget:** confirm with the human; scope Phase 1 to ship regardless of the answer.

## 9. Operating instructions for you, the agent

1. **Do Phase 0 before writing code.** Report back what you found on `rewardfuzz` and the other competitors with specifics (repo URL, stars, last commit, feature list) before proceeding — don't assume the prompt's competitive research is still accurate; it may be stale by the time you read this.
2. **Ask exactly one clarifying question if genuinely blocked** (most likely candidates: time budget, whether to prioritize static or dynamic mode first if forced to choose, hosting/API-cost approach for the dynamic-mode attacker LLM calls) — otherwise pick the reasonable default stated in this doc and proceed.
3. **Work in the phase order above, with a working checkpoint at the end of each phase** — don't build all six phases before showing anything runnable.
4. **Write tests as you go**, not as a final pass.
5. **Stay solo-maintainable** — no team-based workflows, no infrastructure this builder can't operate alone.
6. **Reuse the existing OpenEnv/LLVM-MLIR environments as test fixtures**, don't build synthetic ones from scratch when real ones already exist.
7. **Keep the methodology tied to published, public research** (§5) — flag immediately if any implementation detail risks pulling in non-public benchmark internals.
8. When in doubt between building a new feature and shipping what's already working, **ship what's working** — Phase 6 (launch) is not optional and should not slip indefinitely in favor of more Phase 1-3 polish.

## 10. Open questions to resolve with the human (ask these, don't guess)

- Time budget for the initial ship (hackathon weekend vs. multi-week)?
- Preferred name/branding (avoid collision with `rewardfuzz` once Phase 0 confirms its status)?
- License (MIT is the default across the comparable tools researched — confirm before publishing)?
- Budget/approach for dynamic-mode LLM API calls (self-funded, or defer dynamic mode to a later phase if cost is a blocker)?
