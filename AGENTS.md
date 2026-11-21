# Core Directives

> Please use Korean when providing explanations, reporting on progress, and making reports.

## Objective

Build the pipeline one justified stage at a time, not as a long chain assembled up front. Every stage and every call must be able to answer two questions: why it is there, and what measured gain it produces over not having it. A stage that cannot show its own delta does not ship.

## Knowledge and Research

Never stop at known methods or default open-source wrappers — keep analyzing recent research and our own outputs, form third hypotheses beyond the obvious options, and customize or upgrade every adopted solution.

Before implementing, first survey recent papers, official documentation, and maintained open-source projects on GitHub, Hugging Face, PyPI, and arXiv.

Creating new code files from scratch without first searching for existing AI tools and verified open-source solutions is strictly prohibited. Do not build from scratch when a verified open-source solution already exists, and never use an open-source project as-is without customizing and upgrading it for our purpose.

**Strict Recency Rule (2026-10+):**
- Never judge or select "latest" from internal model memory; always verify live against the current date (`2026-10` or later).
- Never use any open-source repository, library, or model that was not released in 2026 or does not have active updates/commits continuing into 2026.

Never copy external numbers over as our own results. Only what we reproduce on our own environment and data counts as a measurement.

Do not answer from memory when a fact is uncertain, specialized, or may be outdated: check the repository files and research it live as of today's date, using only credible primary sources — research from big-tech labs and credible graduate institutes, peer-reviewed papers, official government/legal portals, official documentation, and actively maintained 2026 repositories; skip unvetted student-level work and generic search results. Cross-check consequential claims across independent sources, judge claimed gains by measured evidence, reproducibility, stability, and operating cost, and label each statement as a verified fact (with path or source), a source-backed conclusion, or an inference.

Judge the user's own claims on evidence like any other, and state plainly where the user is wrong or the claim is unverified.

[Pre-implementation Checkpoints]
Before writing code, state these three in the reply first:
1. Existing 2026-active open-source solutions, models, or libraries for the task (with source link and verified 2026 release/commit date)
2. Efficiency of adopting and customizing/upgrading them versus implementing manually
3. Final tool choice, concrete customization/upgrade plan, and why

## Evidence-Based Implementation & Zero Hardcoding

Hardcoding is strictly prohibited. Never hardcode prompts, model names, routing rules, endpoints, schedules, or user parameters in code; externalize all settings into configuration files.

Do not introduce arbitrary truncation such as `[:100]`, placeholder values, or unexplained constants.

Derive every limit from actual data/system characteristics, official documentation, or existing project conventions. Make it explicit, named, and configurable.

When inspecting data or records, never truncate any record. If full inspection is not required, draw a reproducible random sample across distinct indices, and display each selected record in full.

## Project Documents

Read these before any design or implementation work, and keep them current. Paths are relative to the repository root.

| Path | Role |
| :--- | :--- |
| `TODO.md` | Where work stopped; the first `- [ ]` is the next task |
| `docs/design.md` | Canonical design. If code and this file disagree, fix the document first, then the code |
| `docs/format.md` | Byte-level data and signature format that independent verifiers implement |
| `docs/configuration.md` | Every configurable value, its default, and its source |
| `docs/research.md` | Evidence behind design choices: sources, versions, dates, local measurements |
| `docs/decisions.md` | Confirmed decisions and the list of decisions waiting for the user. Do not implement anything blocked by a pending decision |

Cite these files by exact path and section number (e.g. `docs/design.md` §6.3) in replies, commits, and other documents. When a new document is added under `docs/`, add it to this table in the same change.

## Task Handoff

Read `TODO.md` before starting work and check off each item the moment it is done. Follow the rules at the top of that file.

## Code Change Discipline

Read the surrounding structure before changing it.

Once a code file for a feature is created, continuously reuse and update that existing file rather than creating new files. Generating redundant, temporary, or throwaway files is strictly prohibited.

Remove obsolete or unused code immediately, and add or modify only the minimal code strictly required. Never leave dead code, duplicate implementations, or speculative abstractions behind.

## Comments

When creating a new file, write exactly one line at the very top describing what the file is. That is the only comment permitted.

Writing comments is strictly prohibited when creating, modifying, or deleting code. Do not add them, and do not reintroduce them.

## Artifact Integrity

Every dataset, output, log, and metric is an immutable asset. Never overwrite, delete, relabel, or mix them.

Every run and every contract change carries an explicit version and preserves its provenance.

`--force` creates a new version and archives the previous artifact.

Exception: delete only when the user explicitly asks. Show the list of targets and get confirmation first.

## Local Environment & Commands

Give every local command as a native macOS `zsh` command.

Do not start or stop any server process or modify external system state without the user's permission. Kill commands target only the named PID.

## Reporting

Lead with the conclusion. Record everything measurable as numbers — counts, percentages, tables.

Keep explanation to the essentials. No conversational filler, and no restating procedure already evident from the result.
