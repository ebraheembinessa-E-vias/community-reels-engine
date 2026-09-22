"""Build a release ZIP from explicit public roots. Never ZIP the whole working directory."""
from pathlib import Path
import hashlib
import json
import re
import zipfile

ROOT=Path(__file__).resolve().parents[1]
TOP={'README.md','AGENTS.md','CLAUDE.md','START-HERE.html','THIRD-PARTY-NOTICES.md',
     'RELEASE.md','package.json','package-lock.json','reel.py','.gitignore','.env.example',
     'AUTHOR.md','LICENSE-CC0.txt','START-WITH-YOUR-ASSISTANT.txt',
     'output/pdf/community-reels-guide.pdf'}
DIRS={'.agents','reelkit','prompts','docs','templates','scripts','tests','examples'}
EXT={'.md','.py','.html','.css','.js','.json','.svg','.png','.jpg','.woff2'}
DEMO_VIDEOS={'editorial-demo.mp4','signal-demo.mp4','diagram-demo.mp4','faceless-demo.mp4','pulse-demo.mp4','vox-demo.mp4'}


def inventory():
    result=[]
    for p in sorted(ROOT.rglob('*')):
        rel=p.relative_to(ROOT)
        if rel.parts[0] not in DIRS and str(rel) not in TOP:continue
        if '__pycache__' in rel.parts or p.name=='.DS_Store':continue
        if p.is_symlink():raise ValueError('No symlinks in the public package: '+str(rel))
        if not p.is_file():continue
        if str(rel) not in TOP and p.suffix not in EXT and not (rel.parts[0]=='examples' and p.name in DEMO_VIDEOS):continue
        if p.suffix in {'.md','.py','.html','.css','.js','.json','.txt'} or p.name=='.env.example':
            data=p.read_text(encoding='utf-8')
            if re.search(r'AIza[0-9A-Za-z_-]{30,}',data):raise ValueError('Potential API key in '+str(rel))
            if re.search(r'/Users/[A-Za-z0-9_-]+/',data):raise ValueError('Private machine path in '+str(rel))
        result.append(p)
    return result


def main():
    files=inventory()
    out=ROOT/'dist';out.mkdir(exist_ok=True)
    archive=out/'community-reels-engine.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in files:z.write(p,'community-reels-engine/'+str(p.relative_to(ROOT)))
    manifest={'file_count':len(files),'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
              'files':[{'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(f'Packaged {len(files)} public files; {archive.stat().st_size/1e6:.2f} MB. No work folders or local keys included.')


if __name__=='__main__':main()
