# Licensing — Nexus (`nexus-inference`)

This document explains **how licenses apply** to this repository and its **optional** GUI dependency. It is **not legal advice**; consult counsel for distribution or compliance decisions.

---

## Project license (core)

The **Nexus source code in this repository** — library, CLI entry points (`nexus`, `nexus-grep`, `nexus-policy`, `nexus-cursor-rules`), tests, and documentation — is released under the **MIT License**. See the root [`LICENSE`](../LICENSE) file.

Installing the package **without** the `[ui]` extra pulls in **PyYAML** (MIT-licensed) as the only non-stdlib runtime dependency declared for the default install.

---

## Optional GUI: PyQt6 (`[ui]` extra)

The **Inference Console** (`nexus-console` / `python -m nexus.ui`) is **optional**. It is **not** installed by default.

If you install with the **`[ui]`** extra, **PyQt6** is added as a dependency. **PyQt** is **dual-licensed**:

- **GNU General Public License v3** (**GPLv3**), or  
- a **commercial license** from the vendor ([Riverbank Computing](https://www.riverbankcomputing.com/software/pyqt/)).

PyQt is **not** offered under LGPL in the same way some Qt components are; **shipping or combining** the console in a way that triggers copyleft obligations is **your** responsibility. Typical cases to think about:

- **Internal use** on your own machine: often straightforward; still read the PyQt and Qt terms that apply to your situation.  
- **Redistributing** a product that bundles PyQt6: you likely need to **comply with GPLv3** (source offer, license texts, etc.) **or** purchase a **commercial PyQt license**.  
- **CI / dev only**: `pytest-qt` and PyQt6 for tests — treat like any other dev dependency in your compliance process.

**Practical split for Nexus:**

| Component | Default install | With `pip install …[ui]` |
|-----------|-----------------|---------------------------|
| `nexus`, `nexus-grep`, `nexus-policy`, `nexus-cursor-rules` | MIT (this repo) + PyYAML | Same + **PyQt6** (GPLv3 *or* commercial) |
| `nexus-console` | Entry point exists; PyQt may be missing → install hint | Runs with PyQt6 |

The **MIT license of this repository** applies to **our** code. It does **not** “override” PyQt6’s license when you choose to install and use the GUI stack.

---

## Third-party references (verify upstream)

- **PyQt6 / PyQt licensing:** [Riverbank Computing — PyQt](https://www.riverbankcomputing.com/software/pyqt/)  
- **PyYAML:** [PyYAML](https://github.com/yaml/pyyaml) (MIT)

---

## Summary

- **Core Nexus (no `[ui]`):** MIT + PyYAML — suitable for many proprietary and open stacks under normal MIT terms.  
- **With Inference Console (`[ui]`):** add **PyQt6**; **GPLv3 or commercial PyQt** applies to that stack — **evaluate before you redistribute** or embed the GUI.

For questions about **inference exports and sensitivity** (not copyright), see [`SECURITY.md`](../SECURITY.md).
