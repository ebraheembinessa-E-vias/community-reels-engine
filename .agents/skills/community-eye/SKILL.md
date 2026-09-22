---
name: community-eye
description: Review whole-video speech and visuals with Gemini plus local playback evidence in the Community Reels Engine. Use for source comprehension, uncertain wording and final QA; do not treat model timestamps or screenshots alone as approval.
---

# See, hear, then verify

Use the package's `analyze` or `review` command for the specified source, with authorization and a stated budget. The tool has no implicit retries. A provider failure is an incomplete review, not a pass.

Read every finding as a hypothesis. Extract a frame for a visual issue and replay the relevant sound for a speech issue. Verify a claimed covered face, wrong logo or unreadable text at the actual reported time. The waveform supports timing; it cannot decide sentence meaning. Gemini can understand meaning but its timestamps are approximate.

Check the opening, every edit join, every element entrance/exit and the last word. Compare captions to the spoken words, not to the desired marketing script. Report what was observed, what was measured and what is still uncertain.

Check the output MP4's dimensions, codecs, duration and audio. The engine compares decoded final audio with the approved clean master. This proves preservation, not the artistic quality of the cut. The creator's playback test is the final acceptance gate.
