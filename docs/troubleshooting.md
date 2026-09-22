# When something stops

| Symptom | What to do |
|---|---|
| `python3` not found | Install Python 3.9+ or use your system's `python` command if it is Python 3. |
| HDR phone recording looks flat or `prepare` mentions `zscale` | Newer phones record HDR (HLG/PQ). The tool tone-maps with `zscale` when your ffmpeg has it and otherwise uses a portable colour conversion. For the exact curve, install an ffmpeg build with libzimg. |
| `ffmpeg` or `ffprobe` missing | Install FFmpeg and put both commands on PATH. Restart the terminal, run `doctor`. |
| Missing Chrome | Install Google Chrome, or deliberately run `npx hyperframes browser ensure` to download its rendering browser. |
| macOS denies Desktop/Downloads access | Allow the coding app access in macOS privacy settings or select the project folder in the app. An assistant's approval cannot override macOS file privacy. |
| Gemini 401/403 | Check your own key, model access, Google project and current key restrictions. Never post the key to debug it. |
| Gemini 429/503 | Stop and inspect quota/provider status. Retry explicitly with `--again` only after accounting for the reserved budget. |
| Incomplete model JSON | The report is not usable. Keep the accounted charge; shorten the input or increase the output allowance deliberately. |
| Budget guard | Read `api-usage.json`. Failed uncertain calls retain their reserve. Raising a local budget does not change Google billing limits. |
| Existing project | Use a new project name. `prepare` never destroys earlier work. |
| Caption crosses a cut | Re-hear and split that transcript segment. Do not blindly crop its text by time fraction. |
| Approval mismatch | A reviewed file changed. Rebuild/review the clean output, then approve its new version. |
| Fonts differ | Run `npm ci`. Do not substitute system fonts silently. |
| Silence in player | Click play and unmute with the video controls. Check `verification.json` and the clean master; do not assume autoplay enabled audio. |
| Render too slow | Keep `--workers 1` for low memory. More workers may increase memory demand. Do not assume a GPU or VPS is required. |

The package targets macOS and Linux-compatible command-line dependencies. Only the machine listed in `verification.md` has actually been tested. Windows needs a separate fresh-machine test; no universal compatibility claim is made.
