# Cursor usage metrics and Nexus — why the dashboard looks “broken”

In **Cursor’s usage view** you sometimes see rows with **very low or no reported token use** right next to older sessions in the **hundreds of thousands or millions** of tokens. When the same person uses **Nexus** for orientation, the dashboard can feel like a bug: *“The metric fell off a cliff.”*

This note explains **without hand-waving** how that happens — and what it **does** and **does not** mean.

**Related:** [Token efficiency & measurement](token-efficiency.md) (amortization, purpose vs. totals).

---

## 1. What you see on the dashboard

The screenshots below illustrate typical **before/after** or **side-by-side** patterns: large blocks from **exploratory** runs (heavy context, many reads) vs. **short** rows where almost nothing **billable-looking** is shown.

![Token cost / usage — overview](../console%20tutorial/Token%20cost%20analysis.png)

![Token cost / usage — detail or second view](../console%20tutorial/Token%20cost%20analysis2.png)

**Important:** A **“0”** or **“Included”** there is usually **not** proof that *no* model work happened. It usually means the **measured, attributed context** for that session sits **below a threshold** or lands in a **flat / included bucket** — together with a workflow that pushes **little raw text** into the model.

**Observed runs:** The **“0” token rows** in question came from **repo analysis** work: structure, core flow, impact, tests, and similar — **via Nexus** (terminal / console, small briefs, targeted queries instead of walls of raw code). **On the usage / billing display**, those sessions were **effectively free**: you would typically have **bought** the same **analytic outcome** with **far more** context visible in the meter.

### Important note — estimation, backfill, and magnitude

Usage dashboards increasingly lean on **estimates** first, then **correct or backfill** numbers when firmer data arrives. That means:

- A row can show **0** or a **placeholder** early, then **update later** when the estimate is reconciled.
- **Even after** reconciliation, the **displayed magnitude can still sit below** what you might consider the **full** economic or technical load for the session — e.g. **local** work (Nexus scan, terminal, console) **never** appears as model tokens, and attribution rules may not map 1:1 to “everything the model effectively consumed” in a broad sense.

**Notice 2 — minimal values get backfilled too:** The same **estimate → reconcile** pipeline applies at the **low** end, not only for big rows. A session can first appear as **0** or **near-zero**, then later show a **small positive** count once usage is fully attributed. So **minimal** numbers are also **not necessarily final** — they can be **topped up** after the fact. For **Nexus-heavy repo analysis**, any such correction still tends to stay **orders of magnitude below** old exploratory baselines; the point is that **both** “0” and “small” rows may **move** when estimates settle.

The crop below is a **real example**: **11:03 AM** shows **0** tokens (Nexus-backed **repo analysis**); **10:53 AM** shows a **non-zero** row on the order of **~154k** tokens — still **tiny** next to multi-hundred-k or million-token exploration runs, and consistent with the idea that **what lands in the table is an attributed slice**, not a complete ground-truth log of all work in the session.

![Cursor usage table — zero-token row next to a later-estimated non-zero row](../console%20tutorial/cursor-usage-estimation-example.png)

**Do not over-read the screenshot:** red marks are **editorial highlights** on the crop, not part of the product UI.

### Retrieved data — the numbers after they land

The view labeled **retrieved data** (or equivalent **settled** usage export) shows **actual measured values** for the same kind of sessions — after estimates have been reconciled. Below is a real extract from **Apr 3**: every row is **Included** / **auto**, with token counts now **filled in** across the board.

![Usage table — retrieved data with concrete token counts](../console%20tutorial/retrieved%20data.png)

**Number format:** The table uses a **period (`.`)** as the **thousands separator**, **not** a comma. So **24.753** means on the order of **24.7k** tokens, **423.516** on the order of **424k** — the dot groups thousands; it is **not** a decimal point in these counts.

**How this pairs with the earlier crop:** The **11:03 AM** session that showed **0** in the live table appears here with a **small but non-zero** total — a concrete illustration of **Notice 2** (minimal values **backfilled** after retrieval). The block still spans **tens to low hundreds of thousands** of tokens per row, i.e. **far below** million-token **exploratory** runs, while proving that **“0” in the dashboard was provisional**, not a permanent absence of attributed usage.

---

## 2. Where work happens (and what Cursor measures)

Cursor mostly measures what goes through the **model API / billable path**: **prompt**, **completion**, and bundled tool/context charges — **not** CPU time spent in **local** helpers on your machine.

![Workflow: worker / agent runs Nexus locally, then only a small structured slice for the model](../console%20tutorial/worker%20using%20nexus.png)

**With Nexus**, work typically shifts like this:

| Phase | Where it runs | Shows up as “LLM tokens”? |
|--------|----------------|---------------------------|
| Scan repo, build graph, `-q` / `nexus-grep` | **Local (CPU)**, terminal or `nexus-console` | **No** |
| Agent gets a **short** brief (symbols, `NEXT_OPEN`, cards) | **Small** model input | **Yes, but little** |
| Instead of five huge `read_file` walls: one tight slice | Less **search/navigation** context in the prompt | **Much less** |

**Outcome:** **Expensive in-context search** (grep-like dumps, half a file) **shrinks or disappears**; **the heavy work moves “left”** into the local Nexus pipeline. The dashboard then shows **only the narrow right-hand slice** — and that can be **so small** it is **rounded**, **not broken out**, or shown as **“Included”**.

---

## 3. Why the metric “breaks” — concrete mechanisms

Common reasons the display **no longer scales** with repo size the way it used to:

1. **Decoupling repo size from prompt size**  
   Bigger repo ⇒ more **local** scan — **not** automatically more tokens per question if you use **capped** Nexus output.

2. **Small structured inputs**  
   Name lists, briefs with `--max-symbols`, `nexus-grep` slices: often **only a few hundred tokens** instead of multiple files of text.

3. **Fewer exploratory tool loops**  
   Less “open everything until it clicks” ⇒ less **cumulative** context per usage row.

4. **Product display thresholds**  
   Very small sessions may show as **0** or **Included** even if a **tiny** amount was still counted — depends on product version and plan.

5. **Estimates and late corrections**  
   As in the notices above: numbers may **change after the fact** — including **minimal** rows that start at **0** and later pick up a **small reconciled** value (**Notice 2**). **Reported totals** are still **not guaranteed** to match every notion of “actual” usage (**Notice 1**).

6. **Nexus ≠ free model**  
   You still **pay** for real model use; you **move** the **search/structure** work off the expensive meter **onto local inference**.

---

## 4. What this does **not** mean

- **Not:** “The model used zero tokens.”  
- **Not:** “The pricing model is broken.”  
- **Not:** “Nexus replaces every code read.”  

**Rather:** The **correlation between “complex repo” and “high token count in the usage row”** is **weakened by better retrieval discipline** — and **that** is why the metric **looks** “broken”: people used to read it **implicitly** as a proxy for **navigation effort**.

---

## 5. Takeaway

**Cursor measures the LLM context path first.** Nexus does the **large, repeatable** part of **structure and navigation locally**. When the agent only needs **short, targeted** prompts afterward, the **usage row** drops **orders of magnitude** compared to **grep-heavy** sessions — down to **zeros** that are mostly **measurement/display artifacts**, not “nothing happened.” **Repo analyses** done this way are **often effectively invisible token-wise** in the stats — **effectively free** next to the old expensive exploration runs.

For **reproducible** before/after comparisons (characters, tokens, purpose labels), see **[token-efficiency.md](token-efficiency.md)** — especially **§1.1** (totals vs. purpose).

---

## Screenshots in this repo

Assets live under [`console tutorial/`](../console%20tutorial/) (see also [`TUTORIAL.md`](../TUTORIAL.md)).

| File | Role in this article |
|------|----------------------|
| `worker using nexus.png` | Pipeline: local Nexus → narrow LLM slice |
| `Token cost analysis.png` | Usage / cost overview |
| `Token cost analysis2.png` | Second usage view |
| `cursor-usage-estimation-example.png` | Zero vs. non-zero row; estimation / backfill caveat |
| `retrieved data.png` | Settled “retrieved data” — full token counts (Notice 2 in practice) |
