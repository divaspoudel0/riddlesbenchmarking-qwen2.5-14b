# Correcting a riddle after a version has run

A contributor sometimes finds a mistake in one of their riddles after the
model runs and human evaluation for that version are already done. This is
the process we follow so a single fix does not force everyone to rerun.

The guiding rule (Julia's freeze principle): we do not reopen a version
that has already run. We fix the source, exclude the bad entry from the
frozen version's analysis, and let the corrected riddle get a fresh
evaluation in the next version.

## Branch naming

- One-off riddle fix: `fix/riddle-<community>-<id>`,
  e.g. `fix/riddle-spanish-cuba-016`.
- Changes to this process or tooling: `chore/riddle-correction-process`.

## Steps

### 1. Fix the source row
The contributor corrects the riddle in the source sheet / submission. This
is the single source of truth; every dataset build reads from it. Nothing
downstream is edited by hand.

### 2. Identify the riddle id
Riddle ids look like `spanish_cuba_history_016` (`<community>_<topic>_<n>`).
"Entry 16" from a contributor means the 16th riddle in their sheet, which
is usually the `_016` id within that community, but confirm with them.

### 3. Exclude it from the already-run version's analysis
The frozen version keeps its files as-is (the model answers are answers to
the OLD riddle, so scoring them would be noise). We just skip the id in the
analysis loader.

In `analysis/model_results_v0/load_results.py`, add the id to
`EXCLUDED_RIDDLES` with a one-line reason (mirrors the existing
`EXCLUDED_FOLDERS` pattern). Then rerun the runbook to regenerate the tidy
frame, the data quality report, and the figures. Denominators drop by one
per affected community; the data quality report documents why.

### 4. Let the corrected riddle run in the next version
Because the source row is already fixed (step 1), the corrected riddle
flows into the next version's dataset build automatically and gets a full,
fresh evaluation there. No manual "moving" of files. At build time, sanity
check that the corrected text came through.

### 5. Regenerate the HuggingFace export when convenient
The published dataset and the model-answer export must agree with each
other. Do NOT publish a corrected riddle next to answers for the old one.
Either drop the entry from the frozen version's release (riddle + its model
answers) or keep the old riddle as a documented snapshot. Note the change
in the dataset README. While the dataset is private, there is no rush.

## Cache notes

The run cache is shared (one cache dir), partitioned by a namespace string
that embeds the dataset name, and keyed on prompt content. A rerun only
avoids API calls when it reuses the same namespace and cache dir; a new
dataset name means a fresh namespace and everything runs again. This is why
"rerun only the one changed riddle" is only cheap against the SAME version
that already ran, which is exactly the reopening we avoid.

## Planned: one-command patch mode (not yet built)

Proposed for the v2 CLI: a patch mode that reruns only changed riddles
against the cache within a version, so a future fix is one command instead
of a coordination round. Until it lands, follow the steps above. Owner:
Tenney.
