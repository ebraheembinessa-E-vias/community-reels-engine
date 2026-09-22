// Every visible state is seekable. No CSS animation, wall clock or random values.
const tl = gsap.timeline({paused:true});
/* VOX PAPER steps its graphics on a ~15 fps clock: the cards land with a small settle and a tilt, the sweep is stepped. */
if (REEL.style==='vox') { gsap.ticker.lagSmoothing(0); }
tl.to('#progress-fill',{scaleX:1,duration:REEL.duration,ease:'none'},0);
for (const event of REEL.events) {
  const sel='#'+event.id, len=event.end-event.start;
  tl.set(sel,{visibility:'visible',opacity:1},event.start);
  if(!REEL.faceless) tl.set('.masthead',{visibility:'visible'},Math.max(0,event.start-.34));   // the masthead belongs to the paper: shown only while the footage is squeezed
  tl.fromTo(sel,{y:55,scale:.98},{y:0,scale:1,duration:Math.min(.3,len/3),ease:'power3.out'},event.start);
  if(document.querySelector(sel+' .node')) tl.fromTo(sel+' .node',{opacity:0,y:18},{opacity:1,y:0,duration:Math.min(.22,len/4),stagger:Math.min(.11,len/10),ease:'power2.out'},event.start+.08);
  if (REEL.style==='pulse' && document.querySelector(sel+' .graph')) pulseGraph(sel, event);
  tl.set(sel,{visibility:'hidden'},event.end);
  if(!REEL.faceless && REEL.style==='vox'){ const k=REEL.events.indexOf(event); tl.to('#video-frame',{scale:.38,y:200,x:(k%2?140:-140),rotation:(k%2?2.4:-2.6),borderRadius:0,duration:.4,ease:'power3.inOut'},Math.max(0,event.start-.4)); }
  else if(!REEL.faceless) tl.to('#video-frame',{scale:.39,y:190,borderRadius:REEL.style==='editorial'?8:45,duration:.34,ease:'power3.inOut'},Math.max(0,event.start-.34));
  const next=REEL.events.find(e=>e.start>=event.end);
  if (!REEL.faceless && (!next || next.start-event.end>.7)) { tl.to('#video-frame',{scale:1,y:0,x:0,rotation:0,borderRadius:0,duration:.34,ease:'power3.inOut'},event.end); tl.set('.masthead',{visibility:'hidden'},event.end+.2); }
}
REEL.captions.forEach((cap,i)=>{
  const id='#cap-'+i;
  tl.set(id,{visibility:'visible',opacity:1},cap.start);
  tl.fromTo(id,{y:12},{y:0,duration:Math.min(.14,(cap.end-cap.start)/3),ease:'power2.out'},cap.start);
  if (REEL.style==='vox') tl.fromTo(id+' > span',{backgroundSize:'0% 46%'},{backgroundSize:'100% 46%',duration:Math.min(.9,(cap.end-cap.start)*.6),ease:'power2.out'},cap.start+.1);
  tl.set(id,{visibility:'hidden'},cap.end);
});
window.__timelines=window.__timelines||{};
window.__timelines.reel=tl;

/* PULSE: the signal rides the links between the steps. Positions are read from the static layout; no random values. */
function pulseGraph(sel, event){
  const graph=document.querySelector(sel+' .graph'), nodes=[...graph.querySelectorAll('.gnode')], tiles=nodes.map(n=>n.querySelector('.tile'));
  const links=[...graph.querySelectorAll('.glink')], dot=graph.querySelector('.gdot');
  const len=event.end-event.start, hold=Math.min(.35,len*.08), travel=Math.max(.25,(len-hold*(nodes.length+1))/Math.max(1,nodes.length-1));
  const cx=n=>n.offsetLeft+n.offsetWidth/2;
  let t=event.start+.05;
  tl.set(dot,{left:cx(nodes[0]),opacity:1},t);
  tl.to(tiles[0],{borderColor:'#ff9a3c',boxShadow:'0 0 34px #ff7b00aa,0 0 8px #ff7b00,0 14px 30px #0007',color:'#ffb15c',duration:.18},t);
  t+=hold;
  for (let i=1;i<nodes.length;i++){
    const link=links[i-1];
    if (link){ tl.set(link,{left:cx(nodes[i-1]),width:cx(nodes[i])-cx(nodes[i-1])},event.start); tl.fromTo(link.querySelector('i'),{width:0},{width:'100%',duration:travel,ease:'none'},t); }
    tl.to(dot,{left:cx(nodes[i]),duration:travel,ease:'power1.inOut'},t);
    t+=travel;
    const last=i===nodes.length-1;
    tl.to(tiles[i],last?{borderColor:'#00d2ff',boxShadow:'0 0 34px #00d2ffaa,0 0 8px #00d2ff,0 14px 30px #0007',color:'#8ff0ff',duration:.22}
                       :{borderColor:'#ff9a3c',boxShadow:'0 0 34px #ff7b00aa,0 0 8px #ff7b00,0 14px 30px #0007',color:'#ffb15c',duration:.18},t);
    if (last) tl.to(dot,{opacity:0,duration:.3},t+.1);
    t+=hold;
  }
}
