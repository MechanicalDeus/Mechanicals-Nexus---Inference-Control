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

5. **Nexus ≠ free model**  
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
