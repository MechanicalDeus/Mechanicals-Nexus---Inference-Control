# Agent usage metrics (Cursor): with vs without Nexus

This page documents **screenshots of real agent sessions** (Cursor usage / token dashboard). **Canonical copies for GitHub / the website** live under **[`docs/assets/usage-metrics/`](assets/usage-metrics/)** (stable filenames, no spaces). Optional local exports may still sit in **[`usage metrics/`](../usage%20metrics/)** at the repo root under the original names.

| Asset (in `docs/assets/usage-metrics/`) | Meaning |
|------------------------------------------|---------|
| `without-nexus-1.png` … `without-nexus-5.png` | Five separate runs **without** Nexus-style tiering: orientation via **broad search and file reads** (no rule / no `nexus-grep` / `nexus -q` first). |
| `with-nexus-1.png`, `with-nexus-2.png` | Two runs **with** Nexus in the loop (structural queries first, bounded slices, then targeted reads). |

Original root filenames (same content as above): `works without nexus .png`, `works without nexus 2 .png`, …, `works WITH nexus.png`, `works WITH nexus 2.png`.

**What you are looking at:** product-reported **total tokens** for a session, usually split into components such as **Input**, **Output**, and **Cache Read** (exact labels depend on the IDE version). **Cache Read** is the dominant line item in these examples — consistent with **large context being re-injected** on many turns when the model repeatedly pulls wide file or grep-shaped material into the prompt.

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

So in **these** examples, totals are not “a bit lower” — they sit in a **different band**, often **roughly one order of magnitude** less than the high “without Nexus” runs.

---

## How to read this honestly

**Strong claim supported by the screenshots:** In this workflow and these tasks, **total session tokens dropped dramatically** when Nexus shaped retrieval; the **Cache Read** component suggests **less repeated wide context**, not merely shorter answers.

**What this is *not*:** A **universal** proof for every repository, model, agent policy, or task mix. Different prompts, tools, and follow-up counts will move the numbers.

**What would make it “paper-grade”:** Controlled benchmarks — **same** task description, **same** repo snapshot, **same** tool set except Nexus on/off, **fixed** turn budget or stop condition, **many** repetitions, reported with variance.

**Practical wording for README or posts:**

- *These runs are strong empirical evidence that Nexus can slash model context use in agent loops that otherwise lean on broad repo reading.*
- *The mechanism is plausible: orientation moves from **text absorption** to **CPU-side structural queries** (`nexus-grep`, `nexus -q`, `--perspective`, `nexus-policy`).*
- *Totals still include reasoning, edits, and intentional reads; Nexus targets **search-shaped** context.*

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
