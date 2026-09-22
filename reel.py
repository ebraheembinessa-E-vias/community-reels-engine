#!/usr/bin/env python3
"""Community Reels Engine. Run --help; provider calls are always explicit."""
import argparse
from array import array
import getpass
import html
import json
import subprocess
import math
import os
from pathlib import Path
import shutil
import sys
import time
import wave

from reelkit.core import (latinize, normalize_times, ROOT, approval_valid, digest, duration, ffmpeg, hf, load,
                          map_captions, probe, project, run, save, validate_captions,
                          validate_plan, video_filter)
from reelkit import gemini
from reelkit.composition import STYLES, build


def setup_key(args):
    path = ROOT / ".env"
    if path.exists() and not args.replace:
        raise ValueError("A local .env already exists. Use --replace only to replace your existing local settings.")
    key = getpass.getpass("Paste your Gemini key (hidden): ").strip()
    if not key or any(c in key for c in "\n\r "):
        raise ValueError("Invalid empty or whitespace-containing key.")
    path.write_text("GEMINI_API_KEY=" + key + "\nGEMINI_MODEL=" + gemini.DEFAULT_MODEL + "\n")
    path.chmod(0o600)
    print("Saved locally to .env. It is ignored by Git. No API request was made.")


def doctor(_args):
    problems = []
    for tool in ("ffmpeg", "ffprobe", "node", "npm"):
        exists = bool(shutil.which(tool))
        print(("OK      " if exists else "MISSING ") + tool)
        if not exists:
            problems.append(tool)
    if shutil.which("node") and int(run(["node", "--version"], capture=True).strip().lstrip("v").split(".")[0]) < 22:
        problems.append("Node.js 22+")
    print("Python:", sys.version.split()[0])
    print("Provider key:", "configured" if any(os.environ.get(k) for k in ("GEMINI_API_KEY", "GOOGLE_API_KEY")) or (ROOT/".env").exists() else "not configured (demo still works)")
    if problems:
        raise ValueError("Install missing requirements: " + ", ".join(problems))
    print("Core render browser:", hf("browser", "path", capture=True).strip())
    print("Core dependencies found. Docker, synthetic voices and generated music are not required by this workflow.")


def waveform(p):
    audio = p / "analysis.wav"
    ffmpeg(["-i", p/"proxy.mp4", "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", audio])
    with wave.open(str(audio), "rb") as w:
        samples = array("h", w.readframes(w.getnframes()))
        if sys.byteorder != "little":
            samples.byteswap()
    step = 160  # 10 ms windows; this is evidence, not automatic word recognition.
    windows = []
    for i in range(0, len(samples), step):
        chunk = samples[i:i+step]
        rms = math.sqrt(sum(v*v for v in chunk)/max(1,len(chunk))) / 32768
        windows.append(round(20*math.log10(max(rms,1e-6)),2))
    save(p / "waveform.json", {"window_ms":10,"sample_rate":16000,"rms_dbfs":windows})
    # The review page plots this directly, avoiding an external plotting dependency.


def prepare(args):
    src = Path(args.input).expanduser().resolve()
    if not src.is_file():
        raise ValueError("Input video does not exist.")
    p = project(args.name)
    if p.exists():
        raise ValueError("Project already exists. Choose another name; existing edits are never overwritten by prepare.")
    info = probe(src)
    if not any(s["codec_type"] == "audio" for s in info["streams"]):
        raise ValueError("This talking-reel workflow needs a recording with audio.")
    p.mkdir(parents=True)
    dst = p / ("source" + src.suffix.lower())
    shutil.copy2(src, dst)
    d = float(info["format"]["duration"])
    save(p / "intake.json", {"source_file": dst.name, "source_sha256": digest(dst), "duration":d,
                              "probe":info, "source_treatment":"HDR sources are tone-mapped to SDR; fit, never crop."})
    ffmpeg(["-i",dst,"-vf",video_filter(info,360,640),"-r","15","-c:v","libx264","-preset","veryfast",
            "-crf","25","-c:a","aac","-b:a","96k","-movflags","+faststart",p/"proxy.mp4"])
    waveform(p)
    save(p / "plan.json", {"boundaries_verified":False,"verified_by":"","keep":[{"start":0,"end":d,"reason":"Unreviewed full recording"}]})
    save(p / "elements.json", [])
    make_review(p)
    print("Prepared",args.name,"— original copied, analysis proxy and waveform ready.")


def analysis(args):
    p = project(args.name)
    kind = args.command
    if kind == "review":
        media = p / ("style-" + args.style + ("-faceless" if args.faceless else "")) / "final.mp4"
        if not media.exists():
            raise ValueError("Render the selected style before reviewing it.")
    else:
        media = p / "proxy.mp4"
    output = p / (kind + ".json")
    if output.exists() and not args.again:
        raise ValueError("This report already exists. Use --again only for a deliberate new provider request.")
    prompt_name = "analyze" if kind == "analyze" else kind
    prompt = (ROOT / "prompts" / (prompt_name + ".md")).read_text()
    prompt += f"\nMeasured video duration: {duration(media):.3f} seconds."
    result = gemini.analyze(media, prompt, p/"api-usage.json", args.budget_usd, args.allow_upload)
    result = normalize_times(result, duration(media))   # minutes written as hundreds -> seconds (first real run, 2026-09-22)
    save(output, result)
    if kind == "analyze":
        # Never overwrite an editor's working plan when requesting another opinion.
        save(p/"plan.gemini-draft.json", {"boundaries_verified":False,"verified_by":"","keep":result.get("keep",[])})
        segments = [dict(s, text=latinize(str(s.get("text", "")))) for s in result.get("segments", [])]
        save(p/"transcript.gemini-draft.json", segments)
    make_review(p)
    print("Saved",output.name,"— model suggestions require local verification.")


def clean(args):
    p = project(args.name)
    intake, plan = load(p/"intake.json"), load(p/"plan.json")
    if plan.get("boundaries_verified") is not True or not plan.get("verified_by"):
        raise ValueError("Measure and replay every cut boundary, then set boundaries_verified and verified_by in plan.json.")
    src = p/intake["source_file"]
    if digest(src) != intake["source_sha256"]:
        raise ValueError("The original recording changed. Prepare a new project.")
    keeps = validate_plan(plan,intake["duration"])
    parts = p/"parts"
    parts.mkdir(exist_ok=True)
    filters = video_filter(intake["probe"])
    names = []
    for i,k in enumerate(keeps):
        target = parts / f"part-{i:03}.mkv"
        names.append(target)
        d = k["end"]-k["start"]
        # Short fades suppress clicks; they do not overlap or remove time from speech.
        af = f"afade=t=in:d=0.008,afade=t=out:st={max(0,d-.008):.6f}:d=0.008,apad,atrim=duration={d:.6f}"
        ffmpeg(["-ss",f'{k["start"]:.6f}',"-i",src,"-t",f"{d:.6f}","-vf",filters,"-af",af,
                "-c:v","libx264","-preset","fast","-crf","18","-pix_fmt","yuv420p","-c:a","pcm_s16le",
                "-ar","48000","-ac","2","-map_metadata","-1","-color_primaries","bt709","-color_trc","bt709",
                "-colorspace","bt709",target])
    # Relative names are generated internally: no shell or concat path injection.
    (parts/"concat.txt").write_text("".join("file '"+x.name+"'\n" for x in names))
    ffmpeg(["-f","concat","-safe","1","-i",parts/"concat.txt","-c:v","copy","-c:a","aac","-b:a","192k","-movflags","+faststart",p/"clean.mp4"])
    if (p/"transcript.json").exists():
        caps, unresolved = map_captions(load(p/"transcript.json"),keeps)
        save(p/"captions.draft.json",caps)
        save(p/"caption-questions.json",unresolved)
    save(p/"clean-build.json",{"keeps":keeps,"plan_sha256":digest(p/"plan.json"),"clean_sha256":digest(p/"clean.mp4"),
                               "duration":duration(p/"clean.mp4"),"status":"awaiting playback review"})
    if (p/"approval.json").exists():
        (p/"approval.json").unlink()
    make_review(p)
    print("Clean cut ready. Review the joins and speech; correct captions.draft.json and save captions.json before approval.")


def approve(args):
    p = project(args.name)
    built = load(p/"clean-build.json")
    if built["clean_sha256"] != digest(p/"clean.mp4") or built["plan_sha256"] != digest(p/"plan.json"):
        raise ValueError("Clean build and current edit plan do not match. Rebuild before approval.")
    validate_captions(load(p/"captions.json"),duration(p/"clean.mp4"))
    if not args.by.strip():
        raise ValueError("Name the person who reviewed playback and captions.")
    save(p/"approval.json",{"by":args.by,"at":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
                            "sha256":{name:digest(p/name) for name in ("clean.mp4","captions.json","plan.json")}})
    make_review(p)
    print("Recorded clean-cut and caption approval; stage 2 is ready.")


def dress(args):
    p = project(args.name)
    out = build(p,args.style,args.faceless)
    make_review(p)
    print("Composition ready:",out.name)


def story(args):
    from reelkit.story import prepare_story
    p=prepare_story(args.plan,args.name,args.audio,args.silent)
    make_review(p)
    print("Story review master ready. The plain background is intentional. Review the narration and captions before approval and faceless animation.")


def verify_video(path, expected):
    info=probe(path)
    v=next(s for s in info["streams"] if s["codec_type"]=="video")
    aud=[s for s in info["streams"] if s["codec_type"]=="audio"]
    if (v["width"],v["height"],v["codec_name"],v.get("pix_fmt")) != (1080,1920,"h264","yuv420p"):
        raise ValueError("Output is not 1080×1920 H.264 yuv420p.")
    if not aud or aud[0]["codec_name"] != "aac":
        raise ValueError("The output is missing the original clean audio.")
    actual=float(info["format"]["duration"])
    if abs(actual-expected)>.12:
        raise ValueError("Unexpected output duration mismatch.")
    return {"dimensions":[1080,1920],"video_codec":"h264","pixel_format":"yuv420p","audio_codec":"aac","duration":actual}


def render(args):
    p=project(args.name)
    approval_valid(p)
    out=p/("style-"+args.style+("-faceless" if args.faceless else ""))
    if load(out/"build.json")["clean_approval"] != load(p/"approval.json"):
        raise ValueError("Composition was built from a different approval. Run dress again.")
    started=time.monotonic()
    # The layout check exits non-zero on any note, even an informational one. Stop only on errors; keep every note in the report.
    executable = ROOT / "node_modules" / ".bin" / ("hyperframes.cmd" if os.name == "nt" else "hyperframes")
    proc = subprocess.run([str(executable), "check", str(out), "--json"], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                          env=dict(os.environ, HYPERFRAMES_NO_TELEMETRY="1"))
    check = proc.stdout or ""
    (out/"check.json").write_text(check)
    try:
        report = json.loads(check[check.index("{"):])
    except (ValueError, json.JSONDecodeError):
        raise RuntimeError("The composition check returned no readable report:\n" + (proc.stderr or "")[-1500:])
    errors = sum(int(v.get("errorCount", 0)) for v in report.values() if isinstance(v, dict))
    notes = sum(int(v.get("warningCount", 0)) + int(v.get("infoCount", 0)) for v in report.values() if isinstance(v, dict))
    if errors:
        raise RuntimeError(f"The composition check found {errors} error(s). Read {out/'check.json'} and fix the composition before rendering.")
    if notes:
        print(f"Composition check: {notes} note(s) kept in check.json (no errors).", flush=True)
    hf("render",out,"--output",out/"picture.mp4","--fps","30","--quality","high","--workers",str(args.workers),"--no-best-effort")
    ffmpeg(["-i",out/"picture.mp4","-i",p/"clean.mp4","-map","0:v:0","-map","1:a:0",
            "-c:v","copy","-c:a","copy","-t",str(duration(p/"clean.mp4")),"-movflags","+faststart",out/"final.mp4"])
    result=verify_video(out/"final.mp4",duration(p/"clean.mp4"))
    # Compare decoded audio exactly; an audible track is not proof it is the right track.
    audio_hashes=[]
    for source in (p/"clean.mp4",out/"final.mp4"):
        audio_hashes.append(run(["ffmpeg","-v","error","-i",source,"-map","0:a:0","-f","hash","-hash","sha256","-"],capture=True).strip())
    if len(set(audio_hashes)) != 1:
        raise ValueError("Final audio differs from the approved clean audio.")
    result.update({"audio_matches_clean":True,"render_seconds":round(time.monotonic()-started,2),"owner_final_approval":False})
    save(out/"verification.json",result)
    make_review(p)
    print("Rendered and checked",args.name,args.style,"— owner playback remains the final check.")


def make_review(p):
    files=[("Original analysis copy","proxy.mp4"),("Clean cut","clean.mp4")]
    for style in STYLES:
        files.append((style.title()+" · finished",f"style-{style}/final.mp4"))
        files.append((style.title()+" · faceless",f"style-{style}-faceless/final.mp4"))
    cards=[]
    for title,file in files:
        if (p/file).exists():
            cards.append(f'<article><h2>{html.escape(title)}</h2><video controls playsinline preload="metadata" src="{file}"></video><p><a href="{file}" download>Download video</a></p></article>')
    status="Awaiting clean-cut review"
    if (p/"approval.json").exists():
        try:
            record=approval_valid(p)
            status=("Synthetic fixture - no creator approval" if record.get("by", "").startswith("synthetic fixture")
                    else "Clean approval recorded and current")
        except (ValueError, FileNotFoundError):
            status="Clean files changed - review and approval required again"
    links=' '.join(f'<a href="{f}">{label}</a>' for f,label in [("analyze.json","Gemini analysis"),("plan.json","Edit plan"),("captions.json","Captions"),("elements.json","Visual plan"),("decode.json","Reference decode")] if (p/f).exists())
    waveform_data=load(p/"waveform.json")["rms_dbfs"] if (p/"waveform.json").exists() else []
    doc='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Reel review</title><style>
body{margin:0;background:#f4f1ea;color:#1a293e;font:16px system-ui;padding:40px;max-width:1400px;margin:auto}h1{font-size:46px;letter-spacing:-2px;margin-bottom:12px}.label{font-size:13px;letter-spacing:3px;text-transform:uppercase;color:#35654c}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:25px}article{background:#fff;padding:20px;border:1px solid #d3d8d2;border-radius:14px}h2{font-size:20px}video{display:block;width:100%;max-height:640px;background:#10151d;border-radius:8px}a{color:#1746a5;margin-right:18px}canvas{width:100%;height:130px;background:#fff;border:1px solid #d3d8d2}header{margin-bottom:28px}p{line-height:1.6}.note{background:#e6ecd9;padding:15px 20px;border-radius:9px}</style></head><body>'''
    doc+=f'<header><div class="label">Community Reels Engine / local review</div><h1>{html.escape(p.name.replace("-"," ").title())}</h1><p>{status}. Click play and use the player volume control to hear the recording.</p><p>{links}</p></header><div class="grid">'+''.join(cards)+'</div>'
    doc+='<h2>Timing evidence</h2><p>10 ms RMS windows. Quiet audio is not automatically removable: word tails and breaths need replay.</p><canvas id="wave" width="1200" height="130"></canvas><p class="note">Check the opening, each join and the last word. Confirm captions against speech. A technical check is not permission to publish.</p>'
    doc+=f'<script>const data={json.dumps(waveform_data)};const ctx=document.querySelector("canvas").getContext("2d");ctx.strokeStyle="#1746a5";ctx.beginPath();data.forEach((db,i)=>{{const x=i/data.length*1200,y=125-Math.max(0,(db+65)/65)*115;i?ctx.lineTo(x,y):ctx.moveTo(x,y)}});ctx.stroke();</script></body></html>'
    (p/"review.html").write_text(doc,encoding="utf-8")


def demo(args):
    p=project(args.name)
    if p.exists():
        raise ValueError("Demo project exists. Choose --name with a new name.")
    p.mkdir(parents=True)
    # A synthetic motion + sound fixture, not a customer's footage or fake case study.
    ffmpeg(["-f","lavfi","-i","color=c=0x23364a:s=1080x1920:r=30:d=8",
            "-f","lavfi","-i","sine=frequency=330:sample_rate=48000:duration=8",
            "-vf","drawgrid=w=120:h=120:t=1:c=0x507d8b@0.4,drawbox=x=280:y=500:w=520:h=700:color=0x81bbb6:t=fill,drawbox=x=320:y=540:w=440:h=620:color=0x23364a:t=fill",
            "-af","volume=0.045,afade=t=in:d=0.2,afade=t=out:st=7.8:d=0.2","-c:v","libx264","-preset","veryfast","-crf","22","-pix_fmt","yuv420p","-c:a","aac","-b:a","128k","-movflags","+faststart",p/"clean.mp4"])
    save(p/"plan.json",{"fixture":True,"keep":[{"start":0,"end":8}]})
    captions=[{"start":.2,"end":2.3,"text":"Keep your voice. Clean the story.","direction":"ltr"},
              {"start":2.5,"end":5.1,"text":"Then make the idea visible.","direction":"ltr"},
              {"start":5.4,"end":7.8,"text":"Review it before you share it.","direction":"ltr"}]
    save(p/"captions.json",captions)
    save(p/"elements.json",[{"start":.5,"end":7.9,"kind":"flow","label":"SYNTHETIC DEMO / NO SPEECH","title":"One story. Two stages.","items":["Clean","Animate","Review"]}])
    save(p/"approval.json",{"by":"synthetic fixture generator, not an owner review","sha256":{n:digest(p/n) for n in ("clean.mp4","captions.json","plan.json")}})
    for style in STYLES:
        build(p,style)
    build(p,"diagram",True)
    build(p,"pulse",True)
    build(p,"vox")
    make_review(p)
    print("Created 5 local styles with synthetic media. No footage uploaded. No API charge. Render with: python3 reel.py render",args.name,"--style editorial")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest="command",required=True)
    s=commands.add_parser("setup-key",help="Save your key locally using a hidden prompt")
    s.add_argument("--replace",action="store_true");s.set_defaults(func=setup_key)
    commands.add_parser("doctor",help="Check local dependencies without API requests").set_defaults(func=doctor)
    s=commands.add_parser("prepare",help="Copy a recording and make local analysis evidence")
    s.add_argument("input");s.add_argument("--name",required=True);s.set_defaults(func=prepare)
    s=commands.add_parser("story",help="Prepare an approved faceless story from narration or intentional silence")
    s.add_argument("plan");s.add_argument("--name",required=True)
    voice=s.add_mutually_exclusive_group(required=True)
    voice.add_argument("--audio");voice.add_argument("--silent",action="store_true")
    s.set_defaults(func=story)
    for name in ("analyze","decode","review"):
        s=commands.add_parser(name,help={"analyze":"Gemini understands a raw recording","decode":"Gemini explains a reference's style","review":"Gemini reviews the finished video"}[name])
        s.add_argument("name");s.add_argument("--allow-upload",action="store_true");s.add_argument("--budget-usd",type=float,default=.5)
        s.add_argument("--again",action="store_true");s.add_argument("--style",choices=STYLES,default="editorial");s.set_defaults(func=analysis)
        s.add_argument("--faceless",action="store_true")
    s=commands.add_parser("clean",help="Build the reviewed keep-list into a clean cut")
    s.add_argument("name");s.set_defaults(func=clean)
    s=commands.add_parser("approve",help="Record a real person's clean-cut and caption approval")
    s.add_argument("name");s.add_argument("--by",required=True);s.set_defaults(func=approve)
    for name,func in (("dress",dress),("render",render)):
        s=commands.add_parser(name,help="Build visuals" if name=="dress" else "Check, render and restore the approved audio")
        s.add_argument("name");s.add_argument("--style",choices=STYLES,default="editorial")
        s.add_argument("--workers",type=int,choices=range(1,5),default=1);s.set_defaults(func=func)
        s.add_argument("--faceless",action="store_true")
    s=commands.add_parser("demo",help="Make five styles with original synthetic media, no API")
    s.add_argument("--name",default="demo");s.set_defaults(func=demo)
    args=parser.parse_args()
    try:
        args.func(args)
    except (ValueError,RuntimeError,FileNotFoundError,KeyError) as exc:
        print("STOP:",str(exc),file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
