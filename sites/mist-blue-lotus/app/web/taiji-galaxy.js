import {domePoints,projectDomePoint} from './celestial-dome-model.mjs';
// A deep celestial canopy. Only the larger, colored paper stars are interactive.
const TAU=Math.PI*2;
const seed=(i)=>{const n=Math.sin(i*127.1+311.7)*43758.5453;return n-Math.floor(n);};
const stars=Array.from({length:280},(_,i)=>({x:seed(i+9000),y:seed(i+10000),r:.3+seed(i+11000)*1.2,phase:seed(i+12000)*TAU}));
const backgrounds=new WeakMap();
const skyTexture=new Image();skyTexture.src=new URL('./assets/paper-nebula-reference.png',import.meta.url).href;
function background(ctx,width,height){
 const dpr=Math.max(1,Math.min(2,ctx.getTransform().a||1)),textured=skyTexture.complete&&skyTexture.naturalWidth>0;
 let cached=backgrounds.get(ctx);if(cached?.width===width&&cached?.height===height&&cached.dpr===dpr&&cached.textured===textured)return cached.canvas;
 const canvas=document.createElement('canvas');canvas.width=Math.ceil(width*dpr);canvas.height=Math.ceil(height*dpr);const c=canvas.getContext('2d');c.scale(dpr,dpr);
 const sky=c.createLinearGradient(0,0,width,height);sky.addColorStop(0,'#030b20');sky.addColorStop(.5,'#07162e');sky.addColorStop(1,'#02091b');c.fillStyle=sky;c.fillRect(0,0,width,height);
 // Preserve the supplied nebula artwork; a separate overlay dims it by exactly 50%.
 if(textured){const scale=Math.max(width/skyTexture.naturalWidth,height/skyTexture.naturalHeight),sw=width/scale,sh=height/scale;c.imageSmoothingQuality='high';c.drawImage(skyTexture,(skyTexture.naturalWidth-sw)/2,(skyTexture.naturalHeight-sh)/2,sw,sh,0,0,width,height);}
 backgrounds.set(ctx,{width,height,dpr,textured,canvas});return canvas;
}
function yinPath(c,r){c.beginPath();c.arc(0,0,r,-Math.PI/2,Math.PI/2);c.arc(0,r/2,r/2,Math.PI/2,-Math.PI/2,true);c.arc(0,-r/2,r/2,Math.PI/2,-Math.PI/2);c.closePath();}
function glyph(c,x,y,r,color,active,angle){
 c.save();c.translate(x,y);c.rotate(angle);c.shadowColor=color;c.shadowBlur=active?23:7;
 if(active){const glow=c.createRadialGradient(0,0,0,0,0,r*3.7);glow.addColorStop(0,'#e3f6ff80');glow.addColorStop(.35,color+'85');glow.addColorStop(1,color+'00');c.fillStyle=glow;c.beginPath();c.arc(0,0,r*3.7,0,TAU);c.fill();}
 c.shadowBlur=active?12:3;c.fillStyle=color;c.beginPath();c.arc(0,0,r,0,TAU);c.fill();c.fillStyle='#e9f5ff';yinPath(c,r);c.fill();
 c.fillStyle='#e9f5ff';c.beginPath();c.arc(0,-r/2,r*.2,0,TAU);c.fill();c.fillStyle=color;c.beginPath();c.arc(0,r/2,r*.2,0,TAU);c.fill();c.strokeStyle=active?'#f5fbff':'#d4e8ffad';c.lineWidth=active?1.2:.65;c.beginPath();c.arc(0,0,r,0,TAU);c.stroke();
 if(active){c.shadowBlur=0;c.strokeStyle='#d6f1ff6b';c.lineWidth=.8;c.beginPath();c.arc(0,0,r+5,0,TAU);c.stroke();}
 c.restore();
}
export function renderTaijiGalaxy(ctx,{width,height,yaw,pitch,points,selected,time=0}){
 ctx.globalAlpha=1;ctx.clearRect(0,0,width,height);ctx.drawImage(background(ctx,width,height),0,0,width,height);
 // Distant stars move less than nearby paper stars, creating rotation parallax.
 for(const s of stars){const x=((s.x*width+yaw*10)%width+width)%width,y=((s.y*height+(pitch-.88)*12)%height+height)%height;ctx.globalAlpha=.2+(Math.sin(time*.00035+s.phase)+1)*.2;ctx.fillStyle='#b4d7f4';ctx.beginPath();ctx.arc(x,y,s.r*.65,0,TAU);ctx.fill();}ctx.globalAlpha=1;
 // Dim only the background and distant stars by 50%; paper glyphs render afterward.
 ctx.fillStyle='rgba(0,0,0,.5)';ctx.fillRect(0,0,width,height);
 const camera={width,height,yaw,pitch},project=p=>projectDomePoint(p,camera);
 // Very faint latitude arcs suggest an open vault; there is no solid surface or outer sphere.
 ctx.lineWidth=.65;ctx.strokeStyle='#739fc51a';
 for(const latitude of [-.55,0,.55]){ctx.beginPath();for(let i=0;i<=80;i++){const a=i/80*TAU,q=project({x:420*Math.cos(latitude)*Math.cos(a),y:420*Math.sin(latitude),z:420*Math.cos(latitude)*Math.sin(a)});if(i)ctx.lineTo(q.sx,q.sy);else ctx.moveTo(q.sx,q.sy);}ctx.stroke();}
 // A diffuse, curved star cloud carries the old spiral's movement without drawing a Taiji icon.
 for(let i=0;i<520;i++){const a=seed(i+200)*TAU,r=80+seed(i+800)*270,q=project({x:Math.cos(a)*r,y:(seed(i+1300)-.5)*95+Math.sin(a*2)*65,z:Math.sin(a)*r});ctx.globalAlpha=.05+seed(i+1700)*.16;ctx.fillStyle=i%3?'#80bfe6':'#c4a4dc';ctx.beginPath();ctx.arc(q.sx,q.sy,.35+seed(i+2100)*.8,0,TAU);ctx.fill();}ctx.globalAlpha=1;
 const hits=domePoints(points).map(project).sort((a,b)=>b.depth-a.depth);
 for(const p of hits){const active=p.paper.id===selected,r=active?7:Math.max(1.6,2.5*p.perspective);p.hitRadius=Math.max(14,r+5);ctx.save();
  const halo=ctx.createRadialGradient(p.sx,p.sy,0,p.sx,p.sy,active?28:r*4);halo.addColorStop(0,p.color+(active?'d0':'a0'));halo.addColorStop(1,p.color+'00');ctx.fillStyle=halo;ctx.globalAlpha=active?1:.65;ctx.beginPath();ctx.arc(p.sx,p.sy,active?28:r*4,0,TAU);ctx.fill();
  if(active){ctx.globalAlpha=1;glyph(ctx,p.sx,p.sy,r,p.color,true,time*.00008);ctx.strokeStyle='#d9edffab';ctx.lineWidth=.7;ctx.beginPath();ctx.moveTo(p.sx-17,p.sy);ctx.lineTo(p.sx-11,p.sy);ctx.moveTo(p.sx+11,p.sy);ctx.lineTo(p.sx+17,p.sy);ctx.moveTo(p.sx,p.sy-17);ctx.lineTo(p.sx,p.sy-11);ctx.stroke();}
  else{ctx.globalAlpha=Math.min(.95,.45+p.perspective*.26);ctx.shadowColor=p.color;ctx.shadowBlur=7;ctx.fillStyle=p.color;ctx.beginPath();ctx.arc(p.sx,p.sy,r,0,TAU);ctx.fill();ctx.shadowBlur=0;ctx.fillStyle='#f3faff';ctx.globalAlpha=.88;ctx.beginPath();ctx.arc(p.sx,p.sy,Math.max(.6,r*.35),0,TAU);ctx.fill();}
  ctx.restore();
 }
 return hits;
}
