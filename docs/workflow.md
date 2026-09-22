# One recording, two stages

Use `python3` below, or `python` if that is your Python 3 command. Run commands from this folder. Commands use paths as arguments, never shell-generated editing scripts.

## 1. Understand and clean

```sh
python3 reel.py prepare "/path/to/recording.mp4" --name my-first-reel
python3 reel.py analyze my-first-reel --allow-upload --budget-usd 0.50
```

`prepare` copies the original into `projects/my-first-reel/`, records its hash, and makes a small proxy plus a 10 ms audio waveform. Portrait phone orientation is handled by FFmpeg. HDR sources are tone-mapped into SDR for browser/render compatibility; inspect the result. Landscape material is fitted inside the vertical frame rather than cropped silently.

`analyze` produces a whole-video reading, proposed keeper spans, uncertain phrases, gestures and useful visual opportunities. Open `projects/my-first-reel/review.html` to watch the recording. The provider's times are proposals, not word-accurate measurements.

Your coding assistant should:

1. Compare the actual video with `analyze.json`. Re-hear uncertain words in short clips. Keep English product names in Latin letters inside Arabic captions.
2. Start `transcript.json` from `transcript.gemini-draft.json`, then correct it against the recording. Each entry uses `start`, `end`, verbatim `text`, and `direction` (`auto`, `rtl` or `ltr`). Times still refer to the original source.
3. Start `plan.json` from `plan.gemini-draft.json`. Inspect the waveform and replay the audio around every boundary, including quiet word tails. Decide which repeated attempt actually finishes the thought. Preserve meaningful gestures and breaths.
4. Record `boundaries_verified: true` and the actual reviewer's name in `verified_by` only after this check. This is an editor's timing check, not creator approval.

```json
{
  "boundaries_verified": true,
  "verified_by": "Editor who replayed the joins",
  "keep": [
    {"start": 0.3, "end": 5.8, "reason": "Complete opening"},
    {"start": 7.1, "end": 13.4, "reason": "Finished second attempt"}
  ]
}
```

These times are a format example, never a suggested cut for your video.

```sh
python3 reel.py clean my-first-reel
```

The clean builder expands boundaries to 30 fps frame edges, preserves the source, uses a CPU-compatible H.264 encoder and tiny click-suppression fades. Intermediate audio is uncompressed to avoid AAC padding at every join. It writes `clean.mp4`, remapped `captions.draft.json`, and any cut-through-phrase questions.

Watch the clean video. Resolve all `caption-questions.json` entries against its actual speech. Save the final, measured phrase captions as `captions.json`. Each caption is 1–110 characters, one readable phrase at a time, with no overlapping intervals. The remapping must never invent a clipped phrase.

After the creator approves the clean playback **and** caption wording:

```sh
python3 reel.py approve my-first-reel --by "Creator name"
```

This records hashes of the video, captions and plan. Changing any of these invalidates stage 2 until reviewed again. The command records an approval; it does not create consent on its own.

## 2. Explain visually

Read the transcript sentence by sentence. For each useful visual beat, state its purpose: compare, connect, demonstrate, count or invite. Add only supported facts and real assets. Write `elements.json` on the **clean** timeline:

```json
[
  {"start": 1.0, "end": 4.0, "kind": "flow", "label": "WORKFLOW",
   "title": "Start with the message", "items": ["Understand", "Clean", "Explain"]},
  {"start": 4.2, "end": 7.0, "kind": "asset", "label": "REAL EXAMPLE",
   "title": "The actual working screen", "path": "assets/screen.png",
   "source": "Creator's own capture; private data removed"}
]
```

Replace these sample times and wording with the approved recording's actual meaning. `statement` accepts a short `body`; `compare` accepts two short `items`. Starter layouts are deliberately bounded: 2–3 items, a short title, and one panel at a time. More complex explanations should be authored as a new composition, not crammed into a template.

```sh
python3 reel.py dress my-first-reel --style editorial
python3 reel.py render my-first-reel --style editorial
```

HyperFrames checks the composition, renders the picture, then FFmpeg copies in the approved clean audio. The tool verifies its decoded audio hash against the clean master. Open `review.html` again. Click play; browsers do not reliably autoplay sound.

For a full Gemini hearing/visual audit of the new result (another explicit upload, sharing the same project's budget):

```sh
python3 reel.py review my-first-reel --style editorial --allow-upload --budget-usd 0.50
```

Check each model finding against the frames and audio before editing. If it is wrong, record why; do not damage a good join to satisfy an unverified suggestion. Creator playback remains the final gate. Nothing publishes automatically.

## Faceless mode: keep the voice, replace the picture

If the person has an idea but no recording, start with the interview and story workflow in [faceless.md](faceless.md). The steps below are for reusing audio from an existing approved recording.

The same approved recording can become a faceless reel. Record your own voice with the phone camera pointed away from you, or use the audio from a recording you have already approved. Prepare and clean it normally. Then:

```sh
python3 reel.py dress my-first-reel --style diagram --faceless
python3 reel.py render my-first-reel --style diagram --faceless
```

This composition contains no source-video element. It shows the selected graphic elements and captions and restores only the approved audio. It does not synthesize or clone a voice, invent B-roll, or animate an empty element plan. Add enough meaningful visual beats to support the whole spoken explanation. The faceless result has its own output folder, preserving the talking-head version.

To see this mode with the synthetic sample: `python3 reel.py dress demo --style diagram --faceless`, then the matching `render` command.

## Decode a reference

Prepare a local reference video you have permission to use under a separate project name, then run `python3 reel.py decode reference --allow-upload --budget-usd 0.50`. The result distinguishes observed visual grammar from proposed implementation. It does not identify an editing application from appearance, fetch social-media accounts, or grant rights to copy a brand or voice.
