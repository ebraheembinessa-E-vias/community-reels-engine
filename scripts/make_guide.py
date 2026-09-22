"""Render the canonical beginner manual. Optional rebuild dependency: reportlab."""
from pathlib import Path
import html,re
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/pdf/community-reels-guide.pdf'
OUT.parent.mkdir(parents=True,exist_ok=True)
W,H=595.28,841.89
INK=HexColor('#18313b');GREEN=HexColor('#275743');PAPER=HexColor('#f4f3ec');LINE=HexColor('#d0dbce')
CREDIT='Designed by E.B.E - powered by E-VIAS'
source=(ROOT/'docs/MANUAL.md').read_text()
pages=source.split('<!-- page -->')
c=canvas.Canvas(str(OUT),pagesize=(W,H))
c.setTitle('Community Reels Manual - E.B.E powered by E-VIAS')
c.setAuthor('E.B.E - powered by E-VIAS')
c.setSubject('Beginner guide and assistant instructions for recorded and faceless reels')
styles={
 'body':ParagraphStyle('body',fontName='Helvetica',fontSize=11.4,leading=17,textColor=INK),
 'title':ParagraphStyle('title',fontName='Helvetica-Bold',fontSize=29,leading=34,textColor=INK),
 'sub':ParagraphStyle('sub',fontName='Helvetica',fontSize=12,leading=18,textColor=HexColor('#52655f')),
 'h2':ParagraphStyle('h2',fontName='Helvetica-Bold',fontSize=12.5,leading=18,textColor=GREEN),
 'code':ParagraphStyle('code',fontName='Courier',fontSize=7.7,leading=12,textColor=INK),
}

def markup(text):
 text=html.escape(text)
 text=re.sub(r'\*\*(.*?)\*\*',r'<b>\1</b>',text)
 text=re.sub(r'\[([^\]]+)\]\((https://[^)]+)\)',r'<link href="\2" color="#275743">\1</link>',text)
 return text

for page_no,raw in enumerate(pages,1):
 lines=raw.strip().splitlines();title=lines.pop(0).removeprefix('# ');subtitle=lines.pop(0)
 c.setFillColor(PAPER);c.rect(0,0,W,H,fill=1,stroke=0)
 c.setFillColor(GREEN);c.setFont('Helvetica-Bold',10);c.drawString(48,H-38,'E.B.E')
 c.setFont('Helvetica',8.5);c.drawString(85,H-38,'powered by E-VIAS');c.drawRightString(W-48,H-38,'COMMUNITY REELS MANUAL')
 c.setStrokeColor(LINE);c.line(48,H-51,W-48,H-51)
 c.setFont('Helvetica-Bold',8.5);c.drawString(48,H-78,'FOR YOUR ASSISTANT' if page_no>8 else 'FOR YOU / NO EDITING EXPERIENCE NEEDED')
 y=H-95
 def draw(text,kind='body',card=False,gap=11):
  global y
  x=64 if card else 48;width=W-128 if card else W-96
  p=Paragraph(text,styles[kind]);_,height=p.wrap(width,H)
  total=height+(30 if card else 0)
  if y-total<64:raise RuntimeError(f'Page {page_no} overflow: {text[:60]}')
  if card:
   c.setFillColor(HexColor('#e5ecd9'));c.roundRect(48,y-total,W-96,total,9,fill=1,stroke=0)
  p.drawOn(c,x,y-height-(15 if card else 0));y-=total+gap
 draw(markup(title),'title',gap=10);draw(markup(subtitle),'sub',gap=22)
 for block in re.split(r'\n\s*\n','\n'.join(lines).strip()):
  if not block.strip():continue
  if block.startswith('```'):
   draw('<br/>'.join(html.escape(x) for x in block.splitlines()[1:-1]),'code',card=True)
  elif block.startswith('> '):draw(markup(block.removeprefix('> ')),card=True,gap=15)
  elif block.startswith('## '):
   parts=block.split('\n',1);draw(markup(parts[0][3:]),'h2',gap=4)
   if len(parts)>1:
    quoted=parts[1].startswith('> ')
    draw(markup(parts[1].removeprefix('> ')),card=quoted)
  else:draw(markup(block))
 c.setStrokeColor(LINE);c.line(48,49,W-48,49)
 c.setFillColor(HexColor('#52655f'));c.setFont('Helvetica',8);c.drawString(48,32,CREDIT);c.drawRightString(W-48,32,f'{page_no:02} / {len(pages):02}')
 c.showPage()
c.save()
first=re.search(r'> (Read this manual.*?)\n',source).group(1)
(ROOT/'START-WITH-YOUR-ASSISTANT.txt').write_text(CREDIT+'\n\nOpen the companion folder with your coding assistant and give it this PDF.\n\nCopy this message:\n\n'+first+'\n\nIf the assistant cannot read the PDF, ask it to read docs/MANUAL.md and docs/ASSISTANT-PLAYBOOK.md.\n\nDo not have the folder? Download it from https://github.com/ebraheembinessa-E-vias/community-reels-engine (Code -> Download ZIP), or ask your assistant to download it for you.\n')
print(f'Created {len(pages)}-page beginner manual and first-message card.')
