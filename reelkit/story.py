"""Prepare a faceless story for review from measured narration or intentional silence."""
import math
from pathlib import Path
import shutil
from .core import digest, duration, ffmpeg, load, probe, project, save, validate_captions


def prepare_story(plan_path, name, audio_path=None, silent=False):
    plan_path = Path(plan_path).expanduser().resolve()
    plan = load(plan_path)
    p = project(name)
    if p.exists():
        raise ValueError("Project exists. Choose a new name; story never overwrites a prior reel.")
    if bool(audio_path) == bool(silent):
        raise ValueError("Choose a narration file with --audio, or deliberate --silent playback.")
    if not str(plan.get("script_approved_by", "")).strip():
        raise ValueError("Show the script to the creator, then record their actual approval in script_approved_by.")
    if not str(plan.get("script", "")).strip() or not str(plan.get("audience", "")).strip():
        raise ValueError("The story needs its approved script and audience.")
    total = float(plan.get("duration", 0))
    if not math.isfinite(total) or not 1 <= total <= 180:
        raise ValueError("This starter supports a measured story duration between 1 and 180 seconds.")
    captions = plan.get("captions", [])
    if not captions:
        raise ValueError("Add measured captions for narration or readable text for a silent story.")
    validate_captions(captions, total)
    elements = plan.get("elements", [])
    if not elements:
        raise ValueError("Add a meaningful scene plan before preparing a faceless story.")
    # Early timing checks prevent generating an unusable master. Layout-specific checks stay in build().
    last = 0.0
    for e in elements:
        a, b = float(e["start"]), float(e["end"])
        if not all(math.isfinite(x) for x in (a, b)) or a < last or b <= a or b > total:
            raise ValueError("Scene times must be ordered, finite and inside the story duration.")
        last = b
    source_audio = None
    if audio_path:
        source_audio = Path(audio_path).expanduser().resolve()
        if plan.get("timing_verified") is not True or not plan.get("timing_verified_by"):
            raise ValueError("Listen to the narration and measure caption timing before setting timing_verified.")
        if not any(s["codec_type"] == "audio" for s in probe(source_audio)["streams"]):
            raise ValueError("The supplied narration has no audio stream.")
        measured = duration(source_audio)
        if abs(measured - total) > .12:
            raise ValueError("Story duration differs from the narration. Measure it; do not guess speech timing.")
    # Validate and gather real images before writing a project.
    assets = []
    for i, e in enumerate(elements):
        if e.get("kind") != "asset":
            continue
        src = (plan_path.parent / e["path"]).resolve()
        if not src.is_relative_to(plan_path.parent) or not src.is_file() or not e.get("source"):
            raise ValueError("Story images must be inside the story plan's folder, with a source note.")
        if src.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
            raise ValueError("A story image must be PNG, JPEG or WebP.")
        assets.append((src, "assets/story-" + str(i) + src.suffix.lower()))
        e["path"] = assets[-1][1]
    p.mkdir(parents=True)
    for src, dst in assets:
        (p / dst).parent.mkdir(exist_ok=True)
        shutil.copy2(src, p / dst)
    source_record = {"type": "intentional silence"}
    inputs = ["-f", "lavfi", "-i", f"color=c=0x172b35:s=1080x1920:r=30:d={total}"]
    if source_audio:
        local = p / ("narration-source" + source_audio.suffix.lower())
        shutil.copy2(source_audio, local)
        source_record = {"type": plan.get("voice_source", "creator-supplied audio"), "file": local.name,
                         "sha256": digest(local)}
        inputs += ["-i", local]
    else:
        inputs += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
    ffmpeg(inputs + ["-map", "0:v:0", "-map", "1:a:0", "-t", str(total),
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", p / "clean.mp4"])
    save(p / "story.json", plan)
    save(p / "plan.json", {"mode": "faceless story", "source_audio": source_record,
                            "script_approved_by": plan["script_approved_by"],
                            "keep": [{"start": 0, "end": total, "reason": "Approved story; playback still needs review"}]})
    save(p / "captions.json", captions)
    save(p / "elements.json", elements)
    save(p / "clean-build.json", {"plan_sha256": digest(p / "plan.json"), "clean_sha256": digest(p / "clean.mp4"),
                                  "duration": duration(p / "clean.mp4"), "status": "awaiting story playback review"})
    return p
