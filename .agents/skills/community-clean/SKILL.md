---
name: community-clean
description: Clean a spoken recording with the Community Reels Engine while preserving the creator's voice, meaning and complete words. Use before adding visual elements or whenever a speech edit changes; do not use for animation-only revisions.
---

# Stage 1: make the speech work

Read `docs/workflow.md` from the package root, three directories above this skill. Gemini must understand the whole source first. Run `analyze` only for authorized footage and budget. If hearing is unavailable, say so; a contact sheet or waveform cannot prove the transcript.

Read the analysis, then check it against actual frames and replay. Build a corrected verbatim `transcript.json`; keep technical/product words in Latin spelling within Arabic. Mark uncertain speech instead of making it fluent by invention. Pick the repeated attempt that finishes the thought, not automatically the first or last attempt.

Build `plan.json` with chronological keeper spans and reasons. Use `waveform.json` as timing evidence. Replay short clips around every boundary. Quiet word tails can sit below a silence threshold; never remove them just because the graph looks small. A meaningful gesture is performance, not dead air. Protect complete speech when body continuity conflicts with it.

After actual boundary review, set `boundaries_verified` and the reviewer's name. Run `clean`, inspect the produced joins, resolve cut-through-phrase questions and save measured `captions.json`. Compare the ending with the original; preserve the last consonant.

Show the clean MP4 and captions. Record approval only when the creator approves both. If they request a timing change, make it here and repeat review. Stage 2 must use the approved output.
