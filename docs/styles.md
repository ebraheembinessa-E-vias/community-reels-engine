# Five starting points, two of them the designer's own

| Style | Use it when | Visual vocabulary |
|---|---|---|
| Editorial | A creator is explaining a point | Warm paper, blue labels, firm typography, framed footage |
| Signal | A short idea needs a strong beat | Dark background, lime accents, bold contrast, crisp entries |
| Diagram | Steps and relationships matter | Pale green, teal connections, numbered nodes, open spacing |
| Pulse | A faceless series: a process shown as a signal moving through its steps | Dark grid canvas, node tiles, an orange signal riding the links, the final step lit blue |
| VOX | A documentary explanation, the designer's own house style | Warm paper desk, the footage as a taped tilted polaroid that changes side, taped paper cards with red arrows, the highlighter sweeping the words |

All five use the same approved speech and measured captions. VOX is the style the designer's own reels are cut in, carried into this engine's language; Pulse is built for faceless reels. Pulse is built for faceless reels: a `flow` element becomes a node graph and the signal travels through it over the element's measured time; use one flow per idea and give each step a real name. Styles change how an idea is presented; they do not rewrite it. `templates/stage.css` holds the three visual systems; `templates/motion.js` is deterministic GSAP motion. `reelkit/composition.py` generates HyperFrames HTML you can inspect and extend.

## Design rules

- Lead with an understandable first sentence. The hook must be paid off by the recording or a real example.
- Keep the face visible. The starter animation places the full recording in a smaller frame while an explanation is present, then releases it.
- Keep captions above the bottom app controls and away from the right-hand action rail. The defaults reserve these areas but still require device review.
- Use whole words and phrases for Arabic motion. The browser shapes Arabic, and Latin tool names are isolated with `bdi`.
- Prefer a real, readable screen crop to a decorative fake dashboard. Add a provenance note for every proof asset. Redact names, keys and customer data before including a capture.
- A flow diagram can explain a proposed process. Label it as an explanation; it is not evidence the workflow is deployed.
- End with one natural request. If you promise a download, that download must exist and be usable before posting.

The supplied package has no personal mascot, private brand assets, copied logos, customer work or third-party video. Noto Sans Arabic is loaded locally from its pinned open-font package. GSAP and HyperFrames are installed dependencies with their own licenses.
