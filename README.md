# Live Trading Bot Reliability

**English** · [中文](README.zh-CN.md)

> Getting an automated trading system to run is easy. Keeping it out of trouble while you sleep is the hard part.
>
> *Reliability lessons for AI-coded / vibe-coded trading bots. No strategies, no performance data — engineering only.*

---

## 1. What this is

A short, honest field guide — plus one runnable reproduction — for people who built an automated trading bot with AI and now need to know it is still alive while they sleep.

It is written first for people who **do not program but get real work done with AI**: if you have a trading script that already runs, and maybe already trades real money, this repository is for you. Quant / SRE engineers can use the seven-layer design and the deployment checklist directly.

## 2. Why you need it — with the conclusion up front

**The answer, first:** a bot almost never fails by crashing. It fails by going quiet — the process is gone, the process is stuck, or the alert never arrived — while everything you look at says it is fine. The strategy part is done; the part that notices the silence is the part nobody wrote.

Most people assume: *"if the program dies, monitoring will tell me."* Here is what actually happens:

| You assume | What actually happens |
|---|---|
| If the program dies, an alert fires | **The monitoring script dies too — and nobody notices** |
| A successful task reports Success | **That Success can be a lie — the task never ran at all** |
| If the alert fired, there is a problem | **The alert fired, but the message was never delivered** |
| No position on the dashboard = no position | **It can also mean the data feed is down** |

Every row above is a real failure from a real running system — §4 shows what each looks like and how to defend against it.

## 3. How to use it

### Run it yourself — one command, no keys, no network

```bash
python examples/false_green_light.py
```

Python 3, standard library only — nothing to install, no keys, no network. It writes its evidence into an `examples/state/` folder next to itself and resets it on every run; delete the folder any time.

It makes one task produce **two opposite verdicts**:

```
[Scenario 1] The typical AI style (swallowed exception + rm -f at the end)
  Last log line : task completed successfully
  Exit code     : 0

  Criterion A: read the exit code -> rc = 0            -> verdict: success
  Criterion B: read the traces    -> the output file does not exist
                                     the task never actually ran
                                                       -> verdict: failure

  >>> The two criteria disagree. The truth is: the task never ran at all.
```

(The script prints in Chinese; the lines above translate what you see.) It is not a contrived bug — run it and read the source comments; about a minute.

### Contents

| File | What it is |
|---|---|
| [`examples/false_green_light.py`](examples/false_green_light.py) | Minimal runnable reproduction of the false green light |
| [`docs/pitfalls.md`](docs/pitfalls.md) | The list of real failures |
| [`docs/defenses.md`](docs/defenses.md) | The seven layers and the trade-offs behind each |
| [`docs/observability.md`](docs/observability.md) | Observability: three-state design, the alert chain, heartbeats |
| [`docs/deployment-checklist.md`](docs/deployment-checklist.md) | The three-step deployment check |

The documents under `docs/` are currently written in Chinese only.

### Path A — you just want to use it

Before the bot goes live with real money, read these four in this order:

`pitfalls` → `defenses` → `observability` → `deployment-checklist`

### Path B — you want to change it

Plain Markdown plus one Python script: no build step, no dependencies, no configuration. Edit and re-run.

If you are an **AI agent** asked to work in this repository, read [`AGENTS.md`](AGENTS.md) first — it is the contract for what you may and may not do here.

## 4. The five lessons that matter most

In this repository's own judgement these are the most valuable of the lot, and they are why AI-written reliability code fails in clusters rather than at random. The table is the index; **each lesson only adds what the table cannot say: the criterion, what to do, the real scenario, the cost.**

| What AI typically writes | Why it is dangerous | The one-line fix |
|---|---|---|
| `except Exception: pass` | The error vanishes completely — no crash, no report, not even a log line | An exception must either be logged or raise an alert. Pick one |
| Optimistic logging: "sent", "task complete" | It records *that the call was made*, not *that it happened* | Log only facts you have **verified** |
| A wrapper script that ends with `rm -f` | The cleanup command almost always succeeds → the exit code is always 0 → false green light | Never let a cleanup command overwrite the exit code of the critical command; end on a verification step instead |
| Adding a guardian process without declaring its blind spot | Every layer of guarding can itself die, and the AI will not volunteer that | Write down explicitly *which layer the defence stops at, and what that layer cannot see* |

> Individually, each of these is harmless — even "best practice". Combined, they turn your entire monitoring setup into decoration.

### Lesson 1 — The false green light: "Success" in the log can be a lie

**What happened.** A scheduled task logged that it had run successfully. But the traces it should have left behind were not there.

**The criterion.** Do not read a task's exit code. Read the traces it should have produced: did the log grow, did the file's timestamp move, is there a new row in the database?

**The cost.** You spend weeks inside the illusion that everything is normal. This is the most expensive failure in the list, because nothing about it looks wrong.

### Lesson 2 — "Unknown" is not "none": the three-state design

**What happened.** A dashboard showed "no position" when its data source was disconnected. **"Having no position" and "not knowing whether you have a position" look identical on screen — and you may act on that screen.**

**The fix.** Every monitored metric needs **three** states, not two:

| State | What to display |
|---|---|
| There is a value | Show the value |
| The value really is zero | Show `0` |
| The value cannot be fetched | Show `unavailable` / `N/A` — **never substitute 0** |

**The cost.** Using `0` for "could not fetch" lets a failure disguise itself as a normal state — the most dangerous class of bug: nothing throws, no test catches it, and it only shows itself after something has gone wrong.

### Lesson 3 — The alert chain must be verified end to end

**What happened.** The local log says "alert sent". The phone never rang.

**Why.** If any link breaks, you get nothing: trigger → build the alert → call the sender → delivered → you see it — and the code still looks fine, because the middle step returned. Real failure modes: the push credential expired while the log still said "sent"; a network timeout whose exception was swallowed; the platform rate-limited the message and dropped it silently.

**The criterion.** Actively send a test message and confirm you receive it — not "check that the code calls the send function", but confirm that **your phone actually rang**.

### Lesson 4 — The guardian process dies too

**What happened.** A guardian process was built to watch the main process. But who watches the guardian?

**The fix.** This is an infinite recursion, and the only honest answer is to stop somewhere — on purpose:

| Layer | Mechanism |
|---|---|
| Main process | Watched by the guardian |
| Guardian | **Writes a heartbeat file** |
| External check | Reads the heartbeat file; alerts if it is overdue |

**But the outermost layer still has a hole**: if the external check itself stops, nobody knows either.

> The honest conclusion: this problem can be deepened forever. You must stop at some layer — and state clearly **where you stopped, and what that layer cannot see**. Do not pretend you have full coverage.

### Lesson 5 — Archive logs, do not truncate them

**What happened.** The log file reached its size limit, and when you went looking for the incident, the segment you needed was gone.

| Approach | Consequence |
|---|---|
| Truncate (keep the last N lines) | **History is lost** — and the part that gets deleted is precisely the part you need |
| Archive (keep the old files) | Uses disk space, but stays traceable |

> Disk is cheap. Being unable to reconstruct the past is expensive.

## 5. The defence map

```
Layer 1  Process liveness     trading process died      -> push an alert
Layer 2  Guardian process     monitoring died           -> relaunch automatically
Layer 3  Heartbeat            process running but stuck -> timeout, restart
Layer 4  Dashboard service    dashboard died            -> relaunch automatically
Layer 5  Log management       reached the size limit    -> archive, keep history
Layer 6  Guardian self-check  guardian stopped          -> read heartbeat, alert
Layer 7  Data-source health   live feed unusable        -> fallback + probe verify
```

**Every layer corresponds to a failure that actually happened.** The full design, its trade-offs, and two traps worth knowing before you copy it (a race in Layer 2, Layer 3's threshold) are in [`docs/defenses.md`](docs/defenses.md).

**One principle behind all seven layers:** "I added this check" is not the same as "this check works" — each layer must prove itself against a deliberately caused failure.

Two things stay in `docs/`: the data-source layer (how to tell a dead feed from a quiet market, why a fallback must raise an alert, which states the probe returns) in [`docs/observability.md`](docs/observability.md), and the three deployment checks (configuration, referenced files, traces of a real run) in [`docs/deployment-checklist.md`](docs/deployment-checklist.md).

## 6. Boundaries and non-applicability

What this repository deliberately does **not** contain:

- Any strategy logic, trading parameters, or instrument information
- Any performance data or live-trading results
- Any exchange names or account information

All strategy details of the source system have been desensitised. **The value here is not "which strategy makes money" — it is "how to keep a system you wrote from dying silently while you sleep".**

Honest limits, stated up front:

- **Full observability does not exist.** The outermost layer always keeps its blind spot (Lesson 4). If the monitoring system itself dies with no outside observer, you cannot know.
- **These lessons come from one real running automated trading system**, desensitised — a field report plus a checklist, not an industry standard.
- **This is not a monitoring product you install.** It ships documentation and one runnable example, not a library to drop into your bot. Everything has to be adapted to your own process names, paths, scheduler, and alert channel.
- **It does not apply if you want strategies or returns.** There is nothing about alpha here. If your automation always runs with a human watching, several layers (guardian, heartbeat, self-monitoring) solve a problem you do not have yet.

**A useful criterion for whether this repository applies to you:** can you answer, right now, whether your bot is alive *and* whether its alerts can reach you? If you are not sure about the second one, start at Lesson 3.

## License

MIT — use it however you like, no attribution required. If it saves you from one blown-up night, that is enough.

## More from this author

- [backtest-honesty](https://github.com/Roy9608/backtest-honesty)
- [blackbox-indicator-reverse](https://github.com/Roy9608/blackbox-indicator-reverse)
- [macro-radar](https://github.com/Roy9608/macro-radar)

More at [@Roy9608](https://github.com/Roy9608).

