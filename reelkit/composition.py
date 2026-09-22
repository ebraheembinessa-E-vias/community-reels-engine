"""Generate a local HyperFrames composition from an approved recording and explicit elements."""
import html
import json
import re
import shutil
from .core import ROOT, approval_valid, duration, load, save, validate_captions

STYLES = ("editorial", "signal", "diagram", "pulse", "vox")


def caption_html(text):
    # Isolate Latin islands while letting the browser perform Arabic shaping.
    if not re.search(r"[\u0600-\u06ff]", text):
        return html.escape(text)
    pieces = re.split(r"([A-Za-z][A-Za-z0-9 .+/#-]*[A-Za-z0-9]|[A-Za-z])", text)
    # The islands are runs of ONE caption; the layout check measures each as a block, so they carry the allow-overlap mark.
    return "".join(f'<bdi dir="ltr" data-layout-allow-overlap="true">{html.escape(x)}</bdi>' if re.fullmatch(r"[A-Za-z][A-Za-z0-9 .+/#-]*", x or "")
                   else html.escape(x) for x in pieces)


def build(p, style="editorial", faceless=False):
    if style not in STYLES:
        raise ValueError("Unknown style.")
    approval_valid(p)
    total = duration(p / "clean.mp4")
    captions = load(p / "captions.json")
    validate_captions(captions, total)
    elements = load(p / "elements.json") if (p / "elements.json").exists() else []
    if faceless and not elements:
        raise ValueError("Faceless mode needs a meaningful visual plan in elements.json.")
    out = p / ("style-" + style + ("-faceless" if faceless else ""))
    out.mkdir(exist_ok=True)
    (out / "assets").mkdir(exist_ok=True)
    shutil.copy2(ROOT / "node_modules/gsap/dist/gsap.min.js", out / "assets/gsap.min.js")
    for source, target in [(ROOT / "node_modules/gsap/LICENSE.txt", "GSAP-LICENSE.txt"),
                           (ROOT / "node_modules/@fontsource/noto-sans-arabic/LICENSE", "FONT-LICENSE.txt")]:
        if source.exists():
            shutil.copy2(source, out / "assets" / target)
    if not faceless:
        shutil.copy2(p / "clean.mp4", out / "assets/clean.mp4")
    # Use a bundled open font, if installed by npm; no Mac-specific fonts or CDN at render time.
    fonts = ROOT / "node_modules/@fontsource/noto-sans-arabic/files"
    font_css = ""
    if fonts.exists():
        for subset in ("arabic", "latin"):
            f = fonts / f"noto-sans-arabic-{subset}-600-normal.woff2"
            shutil.copy2(f, out / "assets" / f.name)
            font_css += f'@font-face{{font-family:ReelArabic;src:url(assets/{f.name});font-weight:600;}}' if subset == "arabic" else f'@font-face{{font-family:ReelLatin;src:url(assets/{f.name});font-weight:600;}}'
    cap_nodes = []
    for i, cap in enumerate(captions):
        cap_nodes.append(f'<div id="cap-{i}" class="clip caption{" long" if len(cap["text"]) > 60 else ""}" dir="{cap.get("direction","auto")}" data-start="{cap["start"]}" data-duration="{cap["end"]-cap["start"]}" data-track-index="4"><span>{caption_html(cap["text"])}</span></div>')
    nodes, events = [], []
    last = 0
    for i, e in enumerate(elements):
        a, b = float(e["start"]), float(e["end"])
        if a < last or b <= a or b > total + .03:
            raise ValueError("Elements must be chronological, non-overlapping and inside the clean timeline.")
        last = b
        kind = e.get("kind", "statement")
        if kind not in ("statement", "flow", "asset", "compare"):
            raise ValueError("Element kind must be statement, flow, asset or compare.")
        title = html.escape(str(e.get("title", "")))
        if len(e.get("title", "")) > 65:
            raise ValueError("Element titles must be short enough to read on a phone (65 characters maximum).")
        label = html.escape(str(e.get("label", "EXPLANATION")))
        body = ""
        if kind in ("flow", "compare"):
            items = e.get("items", [])
            if not 2 <= len(items) <= 3 or any(len(str(x)) > 28 for x in items):
                raise ValueError("Flow/compare needs 2–3 short labels of at most 28 characters each.")
            if style == "pulse" and kind == "flow":
                # the PULSE graph: node tiles, the links between them, and the signal dot that rides them (motion.js)
                body = '<div class="graph">' + ''.join(f'<div class="glink"><i></i></div>' for _ in items[1:]) + ''.join(
                    f'<div class="gnode"><div class="tile">{j+1:02}</div><span dir="auto">{html.escape(str(x))}</span><small>STEP {j+1}</small></div>' for j, x in enumerate(items)) + '<b class="gdot" data-layout-allow-occlusion="true"></b></div>'
            else:
                body = '<div class="nodes">' + ''.join(f'<div class="node"><small>{j+1:02}</small><span dir="auto">{html.escape(str(x))}</span></div>' for j,x in enumerate(items)) + '</div>'
        elif kind == "asset":
            asset = (p / e["path"]).resolve()
            if not asset.is_relative_to(p.resolve()) or not asset.is_file():
                raise ValueError("Assets must be real files inside this project.")
            if asset.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp") or not e.get("source"):
                raise ValueError("A proof asset needs an image and a source/provenance note.")
            dst = out / "assets" / (f"proof-{i}" + asset.suffix.lower())
            shutil.copy2(asset, dst)
            body = f'<img class="proof" src="assets/{dst.name}" alt="{title}"><small class="source">{html.escape(e["source"])}</small>'
        else:
            body = f'<p dir="auto">{html.escape(str(e.get("body", "")))}</p>'
            if len(e.get("body", "")) > 95:
                raise ValueError("Keep an element body under 95 characters.")
        nodes.append(f'<section id="element-{i}" class="clip element {kind}" data-start="{a}" data-duration="{b-a}" data-track-index="2"><div class="eyebrow">{label}</div><h2 dir="auto">{title}</h2>{body}</section>')
        events.append({"id": f"element-{i}", "start": a, "end": b})
    css = (ROOT / "templates" / "stage.css").read_text()
    js = (ROOT / "templates" / "motion.js").read_text()
    config = json.dumps({"duration": total, "events": events, "captions": captions, "style": style, "faceless":faceless}).replace("</", "<\\/")
    footage = "" if faceless else f'<div id="video-frame"><video id="recording" class="clip" src="assets/clean.mp4" data-start="0" data-duration="{total}" data-track-index="0" muted playsinline></video></div>'
    doc = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{html.escape(p.name)} · {style}</title><script src="assets/gsap.min.js"></script><style>{font_css}\n{css}</style></head>
<body><main id="reel" class="{style}{' faceless' if faceless else ''}" data-composition-id="reel" data-start="0" data-width="1080" data-height="1920" data-duration="{total}" data-fps="30">
<div class="texture"></div><div class="masthead"><span>YOUR STORY / YOUR VOICE</span><span>{style.upper()}</span></div>
{footage}
{''.join(nodes)}{''.join(cap_nodes)}<div class="progress"><i id="progress-fill"></i></div></main>
<script>const REEL={config};\n{js}</script></body></html>'''
    (out / "index.html").write_text(doc, encoding="utf-8")
    save(out / "hyperframes.json", {"name": p.name + "-" + style})
    save(out / "build.json", {"style": style, "faceless":faceless, "duration": total, "clean_approval": load(p / "approval.json"), "assets": elements})
    return out
