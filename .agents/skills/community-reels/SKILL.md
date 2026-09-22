---
name: community-reels
description: Guide a beginner through the Community Reels Engine using a short conversation. Use for cleaning an existing recording or developing a faceless reel from an idea; do not use to publish or manage unrelated projects.
---

# Start with the person

Read `docs/ASSISTANT-PLAYBOOK.md` and the root README. Resolve these from the package root, three directories above this skill. Ask one useful question at a time. First establish whether they already have a recording or want a faceless reel from an idea. Infer what is already clear; never make them repeat answers. Handle technical work yourself, explaining only the action they need to take next.

For recordings, read `docs/workflow.md`, run `doctor`, then `prepare` with a new name. For a faceless idea, read `docs/faceless.md`, collect the brief, show the script and scenes, and agree the voice route before generating anything. The supplied `story` command imports narration or creates an intentionally silent review master; it does not generate a voice. Show what will be sent to Gemini and the budget; existing authorization for the same scope suffices. Never look for credentials in neighbouring folders.

Use `community-clean` for stage 1. It finishes at creator-approved clean playback and corrected captions. Use `community-elements` for stage 2. Use `community-eye` to audit actual footage and the rendered result. Use `community-decode` only when a reference is supplied or its style is needed.

Two roles organize these five skills: production and reference decoding. The PDF manual under `output/pdf/` explains the process to the person and includes your assistant instructions. Faceless output may use their voice, a separately authorized generated narrator, or intentional silence; never replace an on-camera speaker's voice silently.

Write the source of every claim. Real asset, authored explanation, sample and missing proof are different states. A promised download must actually exist before a reel is published. A script or diagram alone is not evidence of a working business result.

Open the local review page and report the concrete output, measured duration, API ledger and any unresolved issue. Never call `approve` without the creator's actual approval. Never publish implicitly.
