# Agent usage metrics (Cursor): with vs without Nexus

This page documents **screenshots of real agent sessions** (Cursor usage / token dashboard). **Canonical copies for GitHub / the website** live under **[`docs/assets/usage-metrics/`](assets/usage-metrics/)** (stable filenames, no spaces). Optional local exports may still sit in **[`usage metrics/`](../usage%20metrics/)** at the repo root under the original names.

| Asset (in `docs/assets/usage-metrics/`) | Meaning |
|------------------------------------------|---------|
| `without-nexus-1.png` … `without-nexus-5.png` | Five separate runs **without** Nexus-style tiering: orientation via **broad search and file reads** (no rule / no `nexus-grep` / `nexus -q` first). |
| `with-nexus-1.png`, `with-nexus-2.png` | Two runs **with** Nexus in the loop (structural queries first, bounded slices, then targeted reads). |
| `nexus-self-scan.png` | **This repository** analyzed **with Nexus in the agent loop** (session type labeled like a *Nexus scan* in Cursor). Shows that even a structured workflow still accrues **attributed** model tokens — often with **Cache Read** dominating. |
| `ttrpg-studio-with-nexus.png`, `ttrpg-studio-without-nexus.png` | **Controlled A/B** on a **large** local Python checkout (**TTRPG Studio**): **same** task prompt, sessions run **with** vs **without** Nexus-style retrieval first. Canonical copies here; originals: `rpg studio scan with nexus.png`, `rpg studio scan without nexus.png` in [`usage metrics/`](../usage%20metrics/). |

Original root filenames (same content as above, where applicable): `works without nexus .png`, …, `works WITH nexus 2.png`; self-scan source: **`analyzed nexus.png`**; TTRPG pair: **`rpg studio scan with nexus.png`**, **`rpg studio scan without nexus.png`** — all under [`usage metrics/`](../usage%20metrics/).

**What you are looking at:** product-reported **total tokens** for a session, usually split into components such as **Input**, **Output**, and **Cache Read** (exact labels depend on the IDE version). **Cache Read** is the dominant line item in these examples — consistent with **large context being re-injected** on many turns when the model repeatedly pulls wide file or grep-shaped material into the prompt.

---

## Measurement map (what is being compared)

These captures **do not** all answer the same question. Treat them as **layers** on a timeline, not one mega-chart.

| Layer | Checkout / scale | What the rows represent | Takeaway |
|-------|------------------|-------------------------|----------|
| **Small tree** | **This repo** (Nexus checkout, on the order of **~7 MB** on disk) | Usage rows from **build-leaning** agent work (**with** vs **without** Nexus in the loop). Example: **~169k** vs **~95k** total; **fresh Input** only **~8.7k** vs **~7.7k** — almost flat. | **Expected:** the **inference graph is tiny**, so Nexus barely reduces **search-shaped** load; the session is **not** a fair stress test for orientation. Good for honesty: *this is where it does not need to shine.* |
| **Large tree (controlled)** | **TTRPG Studio** (local checkout on the order of **~7 GB**) | **Same analysis-style task wording**, **Nexus on** vs **off** for retrieval first (**N=1**). See **§ Controlled benchmark** for numbers. | **Scaling:** totals and **Cache Read** move — **~43%** lower total and **~25%** lower **Input** in the captured pair — without relying on **10×** outlier sessions. |
| **Gallery (exploratory)** | Various / mixed | Open-ended agent sessions **without** Nexus tiering vs **with** Nexus; often **long** exploration. | **Wide spread** (~**7×–15×** style ratios vs the highest “without” totals) — **real**, but **not** a controlled A/B on one repo + one prompt. |

**Still open (optional next capture):** a **pure analysis** pair on the large checkout — **no** build/edit steps — with the **same** stop condition, to isolate orientation tokens further.

---

## Summary numbers (from the captured runs)

These are **rounded** totals read off the dashboards (not a statistical study).

**Without Nexus** (five separate runs shown in the screenshots):

| Approx. total tokens |
|---------------------|
| ~954k |
| ~852k |
| ~1.375M |
| ~1.387M |
| ~1.663M |

**With Nexus** (two runs shown):

| Approx. total tokens |
|---------------------|
| ~110k |
| ~147k |

**Rough ratios** (same order as above, pairing the “with” runs illustratively against the spread of “without”):

- ~110k vs ~954k → on the order of **~12%** of the larger total (~**8×** fewer tokens).
- ~110k vs ~852k → ~**13%** (~**7–8×**).
- ~147k vs ~1.38M → ~**10–11%** (~**9×**).
- ~147k vs ~1.66M → **under ~9%** (~**11×+**).

So in **these** examples, totals are not “a bit lower” — they sit in a **different band**, often **roughly one order of magnitude** less than the high “without Nexus” runs. **Do not** merge that band with the **TTRPG** row in the table above: different **tasks**, **repos**, and **session shapes**. The Studio pair is the **conservative, same-prompt** anchor; the gallery is the **“exploration hell”** regime.

---

## Controlled benchmark: TTRPG Studio (same task, with vs without Nexus)

This pair is **not** the open-ended gallery above: **one** deliberate **A/B** on the same **large** checkout, **same** agent task wording, **Nexus on** vs **Nexus off** for orientation. Still **N=1** (no variance across repetitions) — but it answers the “small repo vs huge repo” question: here the map is large enough that retrieval discipline can show up in the dashboard.

**Rows read off the screenshots** (Cursor usage table, **Included** / **auto**; tooltip breakdowns):

| Variant | Approx. total | Cache Read | Input | Output |
|---------|----------------|------------|-------|--------|
| **With Nexus** (e.g. Apr 3, ~02:14 PM) | **~180k** | **~160k** | **~16.4k** | **~2.9k** |
| **Without Nexus** (e.g. Apr 3, ~02:11 PM) | **~314k** | **~290k** | **~21.9k** | **~2.5k** |

**Rough read:** total session tokens **~43% lower** in the “with Nexus” capture (**~1.75×** fewer total tokens: **~314k → ~180k**); **fresh Input** **~25% lower**. The largest **absolute** gap is **Cache Read** (**~130k** fewer in the “with” row in this capture) — consistent with **less wide context recycled** across turns while the agent orients. **Output** differs only slightly; the story is **context volume**, not answer length.

**How this sits next to the gallery:** the **five “without”** gallery runs sit around **~0.85M–1.7M** totals — a different **task mix** and often **longer** open exploration. The Studio pair is **deliberately narrower**: one **large** tree, **one** prompt design, **N=1**. It reads as **more conservative and more defensible** for skeptical readers than quoting only **10×** outliers.

![TTRPG Studio — with Nexus (controlled run)](assets/usage-metrics/ttrpg-studio-with-nexus.png)

![TTRPG Studio — without Nexus (controlled run)](assets/usage-metrics/ttrpg-studio-without-nexus.png)

---

## Self-scan: Nexus repository analyzed with Nexus (Cursor)

This is a **different slice** than the open-ended “with vs without” comparison above: one **deliberate** workflow where the **Nexus checkout** was inspected **using Nexus** (`nexus-grep` / `nexus -q`, repo map on the CPU) inside Cursor. The usage table still shows **model-attributed** tokens for that chat — **not** the local AST cost (see **[`cursor-metrics-nexus.md`](cursor-metrics-nexus.md)**).

**Observed rows** (same day, two consecutive entries; **Included** / **auto**):

| Time (example) | Approx. total tokens |
|----------------|---------------------|
| Earlier row | **~54.7k** |
| Later row | **~169k** |

**Tooltip-style breakdown** for the **~169k** row (product UI):

| Component | Approx. tokens |
|-----------|-----------------|
| **Cache Read** | **~158k** |
| Input | ~8.7k |
| Output | ~2.2k |
| Cache Write | 0 |

**How to read it:** **Cache Read** is again the bulk — consistent with the model **reusing or reloading a large conversational / tool context window**, even when **orientation** is guided by Nexus instead of raw repo grepping. Totals here are **far below** the **~0.85M–1.7M** “without Nexus” exploration runs in the gallery, but **not zero**: agents still pay for reasoning, summaries, and whatever context the host attaches to the thread.

![Cursor usage — Nexus self-repo scan session](assets/usage-metrics/nexus-self-scan.png)

---

## How to read this honestly

**Strong claim supported by the screenshots:** In this workflow and these tasks, **total session tokens dropped dramatically** when Nexus shaped retrieval; the **Cache Read** component suggests **less repeated wide context**, not merely shorter answers.

**What this is *not*:** A **universal** proof for every repository, model, agent policy, or task mix. Different prompts, tools, and follow-up counts will move the numbers.

**What would make it “paper-grade”:** The same controlled design as the **TTRPG Studio** pair **above**, but **many** repetitions and reported **variance** (the current Studio capture is **N=1**).

**Practical wording for README or posts:**

- *These runs are strong empirical evidence that Nexus can slash model context use in agent loops that otherwise lean on broad repo reading.*
- *The mechanism is plausible: orientation moves from **text absorption** to **CPU-side structural queries** (`nexus-grep`, `nexus -q`, `--perspective`, `nexus-policy`).*
- *Totals still include reasoning, edits, and intentional reads; Nexus targets **search-shaped** context.*
- *When communicating: keep the **gallery** (often **~7×–15×** vs the worst “without” rows) **and** add the **Studio** pair as a **conservative, same-prompt** datapoint — not a replacement, a **second axis** (outliers vs controlled large tree).*

---

## Screenshot gallery

### Without Nexus (five runs)

![Usage metrics — without Nexus (run 1)](assets/usage-metrics/without-nexus-1.png)

![Usage metrics — without Nexus (run 2)](assets/usage-metrics/without-nexus-2.png)

![Usage metrics — without Nexus (run 3)](assets/usage-metrics/without-nexus-3.png)

![Usage metrics — without Nexus (run 4)](assets/usage-metrics/without-nexus-4.png)

![Usage metrics — without Nexus (run 5)](assets/usage-metrics/without-nexus-5.png)

### With Nexus (two runs)

![Usage metrics — with Nexus (run 1)](assets/usage-metrics/with-nexus-1.png)

![Usage metrics — with Nexus (run 2)](assets/usage-metrics/with-nexus-2.png)

### Nexus on Nexus (self-scan, one session capture)

See **§ Self-scan** (heading above) for numbers and the full-size image `nexus-self-scan.png`.

### TTRPG Studio (controlled A/B, one pair)

See **§ Controlled benchmark: TTRPG Studio** for numbers. Images: `ttrpg-studio-with-nexus.png`, `ttrpg-studio-without-nexus.png` (also inlined in that section).

---

## Relation to the CLI

The **same** structural views the Console exposes are available on the command line via **`nexus --perspective …`** (stable names shared with the library). Typical agent-facing flow:

1. **`nexus-grep`** or **`nexus-policy`** — thin slice, few symbols.  
2. **`read_file`** (or editor) only at **`NEXT_OPEN`** / named paths.  
3. Deeper questions: **`nexus -q`** or **`--perspective llm_brief`** with a small **`--max-symbols`**.  
4. Centered views: **`trust_detail`**, **`focus_graph`**; mutation: **`mutation_trace`** — see **[`cli-perspective.md`](cli-perspective.md)**.

That loop is what the “WITH nexus” sessions are meant to reflect: **query the map first**, then read narrowly.

---

## See also

- **[`token-efficiency.md`](token-efficiency.md)** — caps, amortization, and why **totals alone** do not tell the whole story (§1.1).  
- **[`cursor-metrics-nexus.md`](cursor-metrics-nexus.md)** — why some dashboard lines may look surprising when work moves off the model.  
- **[`nexus-agent-cursor.md`](nexus-agent-cursor.md)** — agent loop, rules, recommended tiering.
