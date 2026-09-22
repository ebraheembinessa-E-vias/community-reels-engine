# From an idea to a faceless reel

This is an assistant reference, not a form to give a beginner. Start with the interview in ASSISTANT-PLAYBOOK.md. The person can start with no recording and no script.

## 1. Find the story

Ask one question at a time. Establish audience, one specific topic, the useful takeaway, language/dialect, tone and final action. Recommend a narrow first idea. Draft a short hook, explanation and ending, with one purpose for each visual. Show the script and plain-language scene plan. Get actual script approval before creating narration or paid assets.

## 2. Choose and review sound

- **Their voice:** help them record the approved script; accept an audio file without requiring face footage. Clean it and check complete words before using it.
- **Artificial narrator:** only if they choose it. Use a voice capability actually available in their assistant, or guide them through [Google's speech-generation workflow](https://ai.google.dev/gemini-api/docs/speech-generation). Explain the destination, model and estimated charge before a call. The video-analysis command does not generate speech, and `story` only imports the finished audio. Do not silently install an unverified voice service or clone a real person's voice. If a provider is unavailable, report that and offer their recorded voice or intentional silence.
- **Text only:** the person explicitly chooses no narration. Use readable text, purposeful motion and a deliberate silent track. Do not present this as a failed voiceover or fabricate speech synchronization.

For narration, listen to the real generated/recorded file and measure the exact caption intervals. Save the full script and actual timing evidence. Do not estimate word onsets from reading speed. For text-only, assign enough reading time and review the result at normal speed.

## 3. Write the story plan for them

The assistant writes a JSON file such as `work/first-story/story.json`. Save its images beside it, with source notes. Example format only:

```json
{
  "audience": "First-time creators",
  "script": "Start with one useful idea. Make it clear before adding motion.",
  "script_approved_by": "Name of the creator who approved this script",
  "voice_source": "Creator's own recording",
  "duration": 8,
  "timing_verified": true,
  "timing_verified_by": "Editor who listened and measured",
  "captions": [
    {"start": 0.2, "end": 3.4, "text": "Start with one useful idea."},
    {"start": 3.7, "end": 7.7, "text": "Make it clear before adding motion."}
  ],
  "elements": [
    {"start": 0, "end": 4, "kind": "statement", "label": "START HERE", "title": "One useful idea", "body": "Who is it for?"},
    {"start": 4, "end": 8, "kind": "flow", "label": "YOUR PROCESS", "title": "Build a clear story", "items": ["Message", "Visual", "Review"]}
  ]
}
```

Do not copy these times or approval names into a real project. They show the shape only. The actual voice file sets the duration. Text-only stories do not require a hearing-verification claim. Use `direction: "rtl"` where needed in captions.

## 4. Build a review master

With measured narration:

```sh
python3 reel.py story work/first-story/story.json --name first-story --audio work/first-story/narration.wav
```

Or, only when deliberately text-only:

```sh
python3 reel.py story work/first-story/story.json --name first-story --silent
```

The command copies narration/images, creates `clean.mp4`, saves captions and scene instructions, and opens no provider connection. It refuses a reused project name, missing script approval, unmeasured narration or inconsistent durations. The review master has a plain background; this is an audio/text checkpoint before visual production. No creator approval is automatically recorded.

Show the audio/script checkpoint and the caption wording to the creator. After approval:

```sh
python3 reel.py approve first-story --by "Creator name"
python3 reel.py dress first-story --style diagram --faceless
python3 reel.py render first-story --style diagram --faceless
```

Review the rendered result at normal speed, with sound if chosen. Fix empty visual gaps, unreadable labels and mismatched narration before handing it over. The three styles are starting points. More complex scenes can be authored in HyperFrames after a small preview is approved.

## Continuation

Save the brief, sources, approved wording, voice choice, next step and actual review decisions inside the ignored project. If the idea or narration changes, create a new review version and renew approval. Do not treat script approval as permission to post.
