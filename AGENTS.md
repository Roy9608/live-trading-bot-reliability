# AGENTS.md — how an AI agent should work in this repository

If you are an AI agent asked to "look at this repo", "use it for my bot", or "add a pitfall to it", this file is the contract.
Everything stated here is drawn from the repository's own README and `docs/`; where the repository does not state something, this file says so instead of guessing.

## 0. What this repository is

A reliability field guide for AI-built / vibe-coded automated trading bots: no strategies, no performance data, engineering only. It contains **documentation and one runnable example script, and nothing else** — four Chinese-language documents under `docs/` (the list of real pitfalls, the seven-layer defence design, observability, the deployment checklist) plus `examples/false_green_light.py`, a self-contained reproduction of the "false green light" failure. The content comes from one real running automated trading system, desensitised. Its audience is people who do not program but drive AI to get work done; professional quant / SRE engineers can use the seven layers and the deployment checklist directly.

```
README.md                          entry point (English; README.zh-CN.md is the Chinese version)
examples/false_green_light.py      the only executable artefact; stdlib only, no network, no keys
docs/pitfalls.md                   real failures, ordered by pain
docs/defenses.md                   the seven layers and their trade-offs
docs/observability.md              three-state design, alert chain, heartbeat
docs/deployment-checklist.md       the three-step deployment check + acceptance template
LICENSE                            MIT, Copyright (c) 2026 Roy9608
```

## 1. Prove it runs (no network, no keys, no install)

```bash
python examples/false_green_light.py
```

Python 3, standard library only. Nothing is installed, nothing is configured, no credentials are needed.

Expected shape of the output (as documented in `README.md`): the script runs two scenarios. Scenario 1 prints a log line saying the task completed and an exit code of `0`, then shows two criteria reaching **opposite** verdicts, ending with the line:

```
  >>> 两个判据结论相反。真相是：任务根本没执行。
```

Scenario 2 is the correct implementation as a control, and then a numbered conclusion is printed. Confirm the run by finding that "two criteria disagree" line in the output — **do not** confirm it by the exit code, which is exactly the mistake this repository is about.

Side effects, and they are the point: the script creates an `examples/state/` folder next to itself and resets it on every run. It is demo evidence and can be deleted at any time (`rm -rf examples/state` on POSIX shells). Deleting it does not break anything.

If the user only asked to "look at the repo", stop after this step.

Not documented in the source repository (do not assert these): the exact byte size of the output, the exact exit code of the example script, and a minimum Python version beyond "Python 3".

## 2. Ask the user before going further

Do not guess any of these. Each one changes what you should recommend or write.

| # | Question | Why it matters |
|---|---|---|
| 1 | Is the bot already trading **real money**, or still running in paper / dry-run mode? | It sets the urgency and therefore the order in which you work through the seven layers. |
| 2 | What actually runs it — cron, Windows Task Scheduler, a platform automation, or a manual terminal? | Layers 2 and 6 are built on a scheduler re-invoking a script every minute; the mechanism differs per host. |
| 3 | Do you have a **second, independent** alert channel (a different service, or a different machine)? | Layer 6's outer blind spot can only be closed by something outside the monitored system. Without a second channel, that layer must stay marked as a known hole — do not paper over it. |
| 4 | What is the live data source, and what is its normal update interval? | Layer 3's heartbeat threshold must be larger than the longest normal run — `docs/observability.md` suggests 2–3× that time. You cannot pick a threshold without this number. |
| 5 | Under which user and working directory does the scheduled job run, and where do its log and output files live? | The deployment checklist's step 3 (checking traces) needs concrete paths and a "before" snapshot; "it works by hand" and "it works on a schedule" are two different environments. |
| 6 | Do you want to **use** the repository, or **change** it? | If the answer is "use it", do not edit anything — walk them through `docs/`. If it is "change it", see the rules in section 4. |

Never invent the user's threshold, channel, paths, or scheduler. Ask.

## 3. Failure modes → meaning

When the user describes a symptom, this is what it most likely means. (These pairings come from the repository's own pitfalls and lessons.)

| Symptom | What it means | What to do |
|---|---|---|
| The log says the task succeeded, but the expected output file does not exist | **False green light.** A trailing cleanup command such as `rm -f` overwrote the exit code, so the wrapper always returns 0 | Stop reading exit codes. Read for traces: did the log grow, did the timestamp move. Then make the wrapper end on verification, not cleanup |
| A dashboard shows `0` or "no position" | Possibly **"could not fetch"**, not "zero". Two different states rendering identically | Apply the three-state rule: value / real zero / `unavailable`. Never let 0 stand in for "unknown" |
| An alert "fired" but the phone never rang | The chain broke between generating the alert and delivering it; the sender's exception was swallowed, or a token expired, or the platform rate-limited it | Verify end to end: actively send a test message and confirm receipt. "The code calls the send function" proves nothing |
| The guardian process exists and there is no alert, yet you cannot explain why | The guardian may itself be dead. Every guard layer can fail, and the outermost one has no observer | Read the guardian's heartbeat file. If the external check is also silent, you are at the documented blind spot — escalate to an independent channel rather than assuming health |
| Two processes of the same job are running | A **race in the guardian**: it relaunched while the previous start was still in progress | Add a lock file and check the process list before launching |
| The process is present but nothing is being produced | **Alive is not working.** A process can be deadlocked, looping, or waiting on a request that never returns — and a liveness check still reports "running" | Use a heartbeat, not a liveness check. The threshold must exceed the longest normal single run |
| The data looks normal but the numbers are not advancing | A **stale feed**: data arrives but the timestamp does not move. Distinct from "the market is genuinely quiet" | Compare timestamps, not just arrival. A probe should return three states (`OK` / `STALE` / `DEAD`) rather than one boolean |
| The system is quietly running on a backup data source | **Silent degradation.** The fallback happened, nobody was told, and the premise behind every downstream decision changed | A fallback must raise an alert. Silent downgrade is more dangerous than a crash |
| A log rotation happened and the incident window is gone | The rotation **truncated** instead of **archived** | Switch to archiving (keep dated files), then prune old archives on a schedule |
| The user says "everything has been normal for weeks" | Treat this as unverified, not as evidence. That is precisely the state the false green light produces | Ask for a trace: log line count, output file timestamp, a database row |

## 4. Iron rules for an agent working in this repository

1. **Never remove or soften the honesty statements.** The declared blind spot in the outermost layer, and the statement that full observability does not exist, are the product, not boilerplate. Do not rewrite them into "fully covered" or delete them for tidiness.
2. **Never invent facts, numbers, commands, metrics, or file paths.** If a figure is needed and the repository does not provide it, write "not provided in the source" rather than producing a plausible number.
3. **Do not add a section teaching the reader how to verify something.** Verification belongs in a runnable script or a concrete command; the prose keeps only the entry point. A capable agent re-derives method on its own — what it cannot invent is your script and your data.
4. **Do not renumber or rename the seven layers, or the five lessons.** The numbering is not cosmetic: each layer and each lesson maps to a specific failure that actually happened. Adding a new layer at the end is acceptable if it comes from a real incident; reordering is not.
5. **Every new pitfall must carry the same three parts as the existing ones:** the symptom, the root cause, and the criterion that tells you which state you are in. A pitfall without its criterion is a story, not a lesson.
6. **Never introduce secrets or identifying data into any file here.** No tokens, API keys, email addresses, server IPs or host paths, exchange names, account information, client names, or company names. This repository's desensitisation is a hard requirement — if the user pastes real values, replace them with placeholders before writing anything.
7. **Never introduce a strategy, a parameter, an instrument, or a performance number.** That is the one thing this repository explicitly does not contain.
8. **Keep both language versions complete.** `README.md` (English) and `README.zh-CN.md` (Chinese) must each be readable on their own; an English stub with the detail only in Chinese, or the reverse, is a defect, not a shortcut. `docs/` is currently Chinese-only in the source repository.
9. **Do not silently change tone or scope.** The register is deliberately blunt and honest ("Disk is cheap. Being unable to reconstruct the past is expensive."). Do not inflate it into marketing copy, and do not make promises about outcomes this repository cannot back.
10. **Do not present the example script's exit code as proof of anything** — in your own verification steps or in the docs you edit. It is the exact illusion the repository exists to expose.
