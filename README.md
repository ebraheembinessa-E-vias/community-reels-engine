# Make a reel with your own AI assistant

**Designed by E.B.E - powered by E-VIAS**

**Public home:** [github.com/ebraheembinessa-E-vias/community-reels-engine](https://github.com/ebraheembinessa-E-vias/community-reels-engine) — press **Code → Download ZIP**, `git clone` it, or take [the release ZIP](https://github.com/ebraheembinessa-E-vias/community-reels-engine/releases/latest/download/community-reels-engine.zip).

Start with the **[Community Reels Manual](output/pdf/community-reels-guide.pdf)**. Give it to your own Codex or Claude Code together with this folder. You do not need to know how to code or edit.

**Arabic edition:** [الدليل بالعربي (PDF)](output/pdf/community-reels-guide-ar.pdf) — the same manual in Gulf Arabic; its source is docs/MANUAL-AR.html.

Your assistant should ask one useful question at a time and handle the technical work. You choose the message and review the result.

## Two ways to start

- **You have a recording:** keep your voice, clean repetitions and gaps, review the clean version, then add captions and meaningful animation.
- **You want a faceless reel:** start with an idea. Your assistant helps choose the audience and message, writes a script for your review, agrees the voice or text-only route, then creates the scenes.

## Give your assistant this message

> Read this manual and the companion asset folder. I am a beginner. Guide me one step at a time in my preferred language. Ask whether I have a recording or want a faceless reel from an idea. Ask one useful question at a time and handle the technical work for me. Show me the script or clean cut before adding visuals. Explain any upload or cost before using a provider.

If it cannot read the PDF, ask it to read [the same manual as text](docs/MANUAL.md) and [the assistant playbook](docs/ASSISTANT-PLAYBOOK.md). A copyable first message is also in START-WITH-YOUR-ASSISTANT.txt.

## What you receive

| Included | Purpose |
|---|---|
| 12-page manual, in English and in Arabic | Eight pages for you; four pages addressed to your assistant |
| Two production routes | Improve an existing recording, or develop a faceless reel from an idea |
| Five agent skills | Guided workflow, cleaning, visual/hearing review, reference decoding and elements |
| Five editable styles | VOX (the designer's own), Editorial, Signal, Diagram and Pulse (the faceless series) |
| Six sample videos | Original synthetic examples of layout and motion |
| Google key guide | Private setup, explicit media transfer and estimated costs |
| Review checkpoints | Script or clean-cut review, then visual review before handoff |

## Use it, change it, share it or sell it

Original material is dedicated under **CC0 1.0 Universal**. Credit is appreciated, not required. There is no mandatory watermark or restriction to personal work. See [AUTHOR.md](AUTHOR.md) and [LICENSE-CC0.txt](LICENSE-CC0.txt). Third-party components retain [their own terms](THIRD-PARTY-NOTICES.md).

## For the assistant

Read [ASSISTANT-PLAYBOOK.md](docs/ASSISTANT-PLAYBOOK.md), AGENTS.md and the relevant skill before setup. Do not lead a beginner with the commands below.

Requirements: Node.js 22+, Python 3.9+, FFmpeg/FFprobe and a supported Chrome render browser. Handle required setup with the user's permissions. No Docker or HeyGen account is needed for the supplied workflow.

```sh
npm ci
python3 reel.py doctor
python3 reel.py demo
python3 reel.py render demo --style editorial
```

The local synthetic sample costs **$0 in provider API charges** and is not a speech-recognition test. [Recorded-video workflow](docs/workflow.md), [faceless story workflow](docs/faceless.md), [Google setup and costs](docs/gemini-setup.md), [styles/assets](docs/styles.md), [troubleshooting](docs/troubleshooting.md).

Faceless narration can be the person's audio or a separately authorized generated voice. The `story` command imports audio or makes an intentionally silent story; it does not generate narration. Use an available voice tool or Google's current speech workflow only after the creator chooses that route.

Technical status is in [verification](docs/verification.md): the whole road — Gemini analysis, a corrected clean cut, captions, a style, the render and the review — finished on a real 2:18 phone recording on 2026-09-22 (VOX and Editorial), and the fixes that run found are in the engine. Acceptance of a member's reel is always the member's own. These tools never push, deploy or post anything.

Package with `python3 scripts/package.py`. It excludes keys, private media and working projects. The optional PDF rebuild uses ReportLab: `python3 scripts/make_guide.py`; the canonical content is docs/MANUAL.md. ReportLab is not needed to make reels.
