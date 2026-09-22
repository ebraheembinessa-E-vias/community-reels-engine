import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
FPS = 30


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run(args, capture=False, cwd=None):
    env = dict(os.environ, HYPERFRAMES_NO_TELEMETRY="1")
    # stderr is always captured so a failure names itself (2026-09-22: a blank "STOP:" hid a missing ffmpeg filter).
    result = subprocess.run([str(x) for x in args], cwd=cwd, env=env,
                            stdout=subprocess.PIPE if capture else None, stderr=subprocess.PIPE, text=True)
    if result.returncode:
        detail = ((result.stderr or "") + "\n" + (result.stdout or "")).strip()
        raise RuntimeError((Path(str(args[0])).name + " failed (exit " + str(result.returncode) + "):\n" + detail)[-3000:])
    if result.stderr and capture is False:
        print(result.stderr.strip()[-2000:], file=sys.stderr)
    return result.stdout if capture else None


def probe(path):
    return json.loads(run(["ffprobe", "-v", "error", "-show_format", "-show_streams",
                           "-of", "json", path], capture=True))


def duration(path):
    return float(probe(path)["format"]["duration"])


_FILTERS = None


def has_filter(name):
    """Does this machine's ffmpeg carry the filter? Homebrew and distro builds differ (zscale needs libzimg)."""
    global _FILTERS
    if _FILTERS is None:
        try:
            out = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True).stdout
        except OSError:
            out = ""
        _FILTERS = set(re.findall(r"^\s*\S+\s+(\S+)\s", out, re.M))
    return name in _FILTERS


def video_filter(info, width=1080, height=1920, zscale=None):
    video = next(s for s in info["streams"] if s["codec_type"] == "video")
    filters = []
    if video.get("color_transfer") in ("arib-std-b67", "smpte2084"):
        if has_filter("zscale") if zscale is None else zscale:
            filters += ["zscale=t=linear:npl=100", "format=gbrpf32le", "zscale=p=bt709",
                        "tonemap=tonemap=mobius:desat=0", "zscale=t=bt709:m=bt709:r=tv"]
        else:
            # Portable HDR -> SDR without libzimg: convert the BT.2020 primaries and treat the transfer as BT.2020
            # gamma. Slightly more contrast than a true tone-map; the picture stays natural (checked on a phone HLG
            # recording, 2026-09-22). Install an ffmpeg with zscale for the exact curve.
            filters += ["colorspace=all=bt709:iall=bt2020:itrc=bt2020-10:iprimaries=bt2020:fast=0"]
    # Fit the complete picture; never silently crop a speaker or screen recording.
    filters += [f"scale={width}:{height}:force_original_aspect_ratio=decrease:force_divisible_by=2",
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=0x11141b",
                "setsar=1", "fps=30", "format=yuv420p"]
    return ",".join(filters)


def ffmpeg(args):
    return run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y"] + args)


def validate_plan(plan, source_duration):
    keeps = plan.get("keep", [])
    if not keeps:
        raise ValueError("The keep list is empty.")
    last = -1.0
    result = []
    for i, item in enumerate(keeps):
        start, end = float(item["start"]), float(item["end"])
        if not all(math.isfinite(x) for x in (start, end)):
            raise ValueError("Cut times must be finite numbers.")
        if start < 0 or end > source_duration + .001 or end <= start or start < last:
            raise ValueError(f"Invalid or overlapping keep span {i + 1}.")
        if end - start < .1:
            raise ValueError("A keep span shorter than 100 ms cannot be a safe speech edit.")
        # Expand to frame boundaries; a measured word tail must not be rounded away.
        a, b = math.floor(start * FPS + 1e-6) / FPS, math.ceil(end * FPS - 1e-6) / FPS
        if result and a < result[-1]["end"] - .0001:
            raise ValueError("Keep spans overlap after frame alignment. Merge or revise them.")
        result.append({"start": a, "end": b, "reason": item.get("reason", "")})
        last = end
    return result


def map_captions(segments, keeps):
    captions, unresolved = [], []
    offset = 0.0
    for k in keeps:
        for s in segments:
            a, b = float(s["start"]), float(s["end"])
            if min(b, k["end"]) <= max(a, k["start"]):
                continue
            if a < k["start"] - .001 or b > k["end"] + .001:
                unresolved.append({"segment": s, "reason": "Cut crosses this transcript segment; re-hear and split it."})
                continue
            captions.append({"start": round(offset + a - k["start"], 4),
                             "end": round(offset + b - k["start"], 4), "text": s["text"],
                             "direction": s.get("direction", "auto")})
        offset += k["end"] - k["start"]
    return captions, unresolved


def validate_captions(captions, total):
    last = 0.0
    for c in captions:
        a, b = float(c["start"]), float(c["end"])
        if not all(math.isfinite(x) for x in (a, b)) or a < last - .001 or b <= a or b > total + .04:
            raise ValueError("Captions must be ordered, non-overlapping and within the clean video's duration.")
        if not isinstance(c.get("text"), str) or not c["text"].strip() or len(c["text"]) > 110:
            raise ValueError("Each caption needs 1–110 characters. Split long speech at measured phrase boundaries.")
        if c.get("direction", "auto") not in ("auto", "rtl", "ltr"):
            raise ValueError("Caption direction must be auto, rtl or ltr.")
        last = b


def project(name):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", name):
        raise ValueError("Use a short project name with lowercase letters, numbers and hyphens.")
    return ROOT / "projects" / name


def hf(*args, capture=False):
    executable = ROOT / "node_modules" / ".bin" / ("hyperframes.cmd" if os.name == "nt" else "hyperframes")
    if not executable.exists():
        raise RuntimeError("HyperFrames is missing. Run npm ci in this folder first.")
    return run([executable] + list(args), capture=capture, cwd=ROOT)


def approval_valid(p):
    record = load(p / "approval.json")
    for name in ("clean.mp4", "captions.json", "plan.json"):
        if record.get("sha256", {}).get(name) != digest(p / name):
            raise ValueError("The approved clean video, captions or edit plan changed. Review and approve the new version.")
    return record


# --- two lessons from the first real run (2026-09-22) ---------------------------------------------------------------
TIME_KEYS = ("start", "end", "at", "kept_alternative_start")


def _times(obj, out):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in TIME_KEYS:
                try:
                    out.append(float(v))
                except (TypeError, ValueError):
                    pass
            else:
                _times(v, out)
    elif isinstance(obj, list):
        for x in obj:
            _times(x, out)
    return out


def normalize_times(obj, total):
    """Gemini sometimes writes minutes as hundreds (1:03.0 as 103.0) although the prompt asks for seconds. The whole report
    is read in that mode when it holds such values and none between 60 and 100; every value from 100 up is then converted.
    A report already in seconds is left alone."""
    vals = _times(obj, [])
    mmss = any(v >= 100 and (v % 100) < 60 for v in vals) and not any(60 <= v < 100 for v in vals) and (max(vals) > total + 1 or True)
    if not mmss:
        return obj
    def fix(v):
        try:
            f = float(v)
        except (TypeError, ValueError):
            return v
        if f >= 100 and (f % 100) < 60:
            return round(int(f // 100) * 60 + f % 100, 3)
        return v
    def walk(o):
        if isinstance(o, dict):
            return {k: (fix(v) if k in TIME_KEYS else walk(v)) for k, v in o.items()}
        if isinstance(o, list):
            return [walk(x) for x in o]
        return o
    return walk(obj)


# Arabic-letter spellings of product and tech words that must stay Latin in captions (the assistant still reviews).
LATIN_WORDS = {
    "\u0627\u064a\u062c\u0646\u062a": "agent", "\u0625\u064a\u062c\u0646\u062a": "agent", "\u0623\u064a\u062c\u0646\u062a": "agent",
    "\u0627\u0644\u0627\u064a\u062c\u0646\u062a": "\u0627\u0644\u0640 agent", "\u0627\u064a\u062c\u0646\u062a\u064a\u0646": "agents",
    "\u0627\u0644\u0627\u064a\u062c\u0646\u062a\u064a\u0646": "\u0627\u0644\u0640 agents", "\u0627\u0644\u0627\u064a\u062c\u0646\u062a\u0627\u062a": "\u0627\u0644\u0640 agents",
    "\u062c\u0648\u062c\u0644": "Google", "\u0644\u062c\u0648\u062c\u0644": "\u0644\u0640 Google", "\u0633\u062a\u0648\u062f\u064a\u0648": "Studio",
    "\u0627\u064a \u0628\u064a \u0627\u0627\u064a": "API", "\u0643\u064a\u0632": "keys", "\u0643\u064a": "key",
    "\u0627\u0644\u0628\u064a \u062f\u064a \u0627\u0641": "\u0627\u0644\u0640 PDF", "\u0628\u064a \u062f\u064a \u0627\u0641": "PDF", "\u0627\u0644\u0628\u064a": "\u0627\u0644\u0640 PDF",
    "\u0643\u0644\u0648\u062f": "Claude", "\u0644\u0643\u0644\u0648\u062f": "\u0644\u0640 Claude", "\u0643\u0648\u062f\u0643\u0633": "Codex",
    "\u062a\u0645\u0628\u0644\u062a": "templates", "\u062a\u0645\u0628\u0644\u064a\u062a": "templates", "\u062a\u0645\u0628\u0644\u0627\u062a": "templates",
    "\u0641\u064a\u0633\u0644\u0633": "faceless", "\u0631\u064a\u0644\u0632": "reels", "\u0627\u0644\u0633\u0643\u0631\u0628\u062a": "\u0627\u0644\u0640 script",
    "\u0633\u0643\u0631\u0628\u062a": "script", "\u0627\u0644\u0645\u0648\u062f\u064a\u0644": "\u0627\u0644\u0640 model",
    "\u0627\u0644\u064a\u062c\u0646\u062a": "\u0627\u0644\u0640 agent", "\u0627\u0644\u064a\u062c\u0646\u062a\u064a\u0646": "\u0627\u0644\u0640 agents",
    "\u0627\u064a\u062c\u0646\u062a\u064a\u0646": "agents", "\u0627\u0644\u0627\u064a\u062c\u0646\u062a\u064a\u0646": "\u0627\u0644\u0640 agents",
    "\u0627\u064a \u0628\u064a \u0622\u064a": "API", "\u0622\u062e\u0631": "\u0627\u062e\u0631",
    "\u0627\u0644\u0628\u064a \u062f\u064a \u0625\u0641": "\u0627\u0644\u0640 PDF", "\u0628\u064a \u062f\u064a \u0625\u0641": "PDF", "\u062f\u064a \u0625\u0641": "", "\u062f\u064a \u0627\u0641": "",
}


def latinize(text):
    """Replace known Arabic-letter spellings of Latin product words, longest first, whole words only."""
    for ar, lat in sorted(LATIN_WORDS.items(), key=lambda kv: -len(kv[0])):
        text = re.sub(r"(?<![\w\u0600-\u06ff])" + re.escape(ar) + r"(?![\w\u0600-\u06ff])", lat, text)
    return text
