# Connect your own Gemini key

1. Open [Google AI Studio](https://aistudio.google.com/api-keys), sign in, and create a key in a project you control. Follow Google's current prompts; you may need to create or import a Cloud project.
2. Review model access, billing and data terms for that project. The default Flash model has free-tier availability subject to Google's limits; paid-tier requests are billed separately. A paid ChatGPT or other coding-assistant plan does not pay for Gemini API calls.
3. In this folder, run `python3 reel.py setup-key`. Paste the key into the hidden terminal prompt. It saves a private `.env` file excluded from Git and from the shareable archive. Do not paste your key into chat, screenshots, captions or a web page.
4. Run the local demo first. Then prepare your own recording and call `analyze` when you accept sending its proxy to Google.

The alternative is a `GEMINI_API_KEY` process environment variable. The tool reads only that environment and this package's own `.env`; there are no hidden links to the author's machine. It uses `gemini-3.8-flash` by default. `gemini-3.1-pro-preview` is an explicit higher-cost option; there is no automatic model switching. Other models require a compatibility check and a current pricing entry in `reelkit/gemini.py`.

## Costs you can inspect

Flash's standard paid rate, checked on 2026-09-21: **$0.75 per million input tokens and $3.75 per million output tokens, including thinking**, through 2026-12-31. The tool stops after that rate expiry until its pricing entry is updated. Pro preview's <=200,000-input-token tier is **$2 input / $12 output per million tokens**. Example arithmetic for 20,000 input plus 4,000 output tokens: **$0.03 Flash or $0.088 Pro**. These are calculations, not fixed prices per reel; video tokenization and response length vary. The budget uses paid rates conservatively even when a project is eligible for free-tier usage.

Before generation, the tool counts input tokens and reserves the maximum output allowance. Default cumulative project budget: **$0.50**. It records actual usage when returned; an uncertain failed call retains its reservation. Only one provider request may own a project's budget at a time. There are no automatic retries. `api-usage.json` contains the accounting; it never contains your key.

Local preview, captions, clean rendering and the supplied demo have **$0 in provider API charges**. They still consume local time, electricity and disk space. Your coding assistant and any third-party assets have separate terms and costs.

## What leaves your machine

Only the proxy or final video selected by an explicit `analyze`, `decode` or `review` call, plus its prompt, is sent to Google's Gemini API. The adapter requests deletion of its temporary upload afterwards and reports a cleanup failure. Your provider's service terms and retention policies still apply; deletion is not a promise of zero provider retention.

References: [API key setup and protection](https://ai.google.dev/gemini-api/docs/api-key), [current pricing](https://ai.google.dev/gemini-api/docs/pricing), [video understanding](https://ai.google.dev/gemini-api/docs/video-understanding), [Gemini terms](https://ai.google.dev/gemini-api/terms). Check these again before a public release or model change.
