// Ray-lit sphere material: the Taiji pattern follows a rotating 3D surface.
let surface=null,gl=null,program=null,locations=null,unavailable=false;
function init(){
 if(surface||unavailable)return;
 surface=document.createElement('canvas');gl=surface.getContext('webgl',{alpha:true,premultipliedAlpha:false,antialias:true});
 if(!gl){unavailable=true;surface=null;return;}
 const shader=(type,source)=>{const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));return s;};
 const vertex=shader(gl.VERTEX_SHADER,'attribute vec2 a;varying vec2 v;void main(){v=a;gl_Position=vec4(a,0.,1.);}');
 const fragment=shader(gl.FRAGMENT_SHADER,`precision highp float;
 varying vec2 v;uniform float yaw;uniform float pitch;uniform float time;
 float edge(float distance,float radius){return 1.-smoothstep(radius-.008,radius+.008,distance);}
 void main(){vec2 q=v*1.08;float rr=dot(q,q);if(rr>1.02){gl_FragColor=vec4(0.);return;}
 float alpha=1.-smoothstep(.99,1.015,rr);vec3 n=vec3(q.x,q.y,sqrt(max(0.,1.-rr)));
 float z1=-n.y*sin(pitch)+n.z*cos(pitch);vec3 p=vec3(n.x*cos(yaw)+z1*sin(yaw),n.y*cos(pitch)+n.z*sin(pitch),-n.x*sin(yaw)+z1*cos(yaw));
 float yang=smoothstep(-.008,.008,p.x);yang=mix(yang,0.,edge(length(p.xy-vec2(0.,.5)),.5));yang=mix(yang,1.,edge(length(p.xy-vec2(0.,-.5)),.5));yang=mix(yang,1.,edge(length(p.xy-vec2(0.,.5)),.105));yang=mix(yang,0.,edge(length(p.xy-vec2(0.,-.5)),.105));
 vec3 blue=vec3(.13,.23,.42),pearl=vec3(.88,.90,.95);vec3 base=mix(blue,pearl,yang);
 float facing=max(n.z,0.);float rim=pow(1.-facing,2.3);float irid=.5+.5*sin(n.x*5.5+n.y*4.+n.z*8.+time*.00015);
 vec3 rainbow=mix(vec3(.92,.58,.78),vec3(.42,.86,.93),irid);rainbow=mix(rainbow,vec3(.98,.85,.56),(.5+.5*sin(n.y*9.-n.x*3.))*.23);
 base=mix(base,base*.68+rainbow*.48,.26+rim*.6);
 vec3 light=normalize(vec3(-.5,.65,1.));float diffuse=max(0.,dot(n,light));float spec=pow(max(dot(n,normalize(light+vec3(0.,0.,1.))),0.),85.);float spec2=pow(max(dot(n,normalize(vec3(.75,-.3,1.6))),0.),48.);
 vec3 color=base*(.42+.58*diffuse)+vec3(1.,.96,.88)*spec*.95+vec3(.57,.82,1.)*spec2*.32+rainbow*rim*.44;
 float glint=pow(max(0.,sin(p.x*97.+p.y*113.)*sin(p.y*83.-p.z*101.)),22.);color+=vec3(.8,.9,1.)*glint*(.1+.1*sin(time*.001+p.x*30.));
 gl_FragColor=vec4(color,alpha);}`);
 program=gl.createProgram();gl.attachShader(program,vertex);gl.attachShader(program,fragment);gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(program));gl.useProgram(program);
 const buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,-1,1,1,-1,1,1]),gl.STATIC_DRAW);const a=gl.getAttribLocation(program,'a');gl.enableVertexAttribArray(a);gl.vertexAttribPointer(a,2,gl.FLOAT,false,0,0);locations={yaw:gl.getUniformLocation(program,'yaw'),pitch:gl.getUniformLocation(program,'pitch'),time:gl.getUniformLocation(program,'time')};
}
export function drawPearlSphere(ctx,cx,cy,r,yaw,pitch,time){
 try{init();}catch{unavailable=true;surface=null;}
 const halo=ctx.createRadialGradient(cx,cy,r*.7,cx,cy,r*1.3);halo.addColorStop(0,'#c1ddff00');halo.addColorStop(.72,'#9dbff12e');halo.addColorStop(.84,'#eab6dd1b');halo.addColorStop(1,'#779fc500');ctx.fillStyle=halo;ctx.beginPath();ctx.arc(cx,cy,r*1.3,0,Math.PI*2);ctx.fill();
 if(gl&&surface&&!unavailable){const size=Math.min(1000,Math.max(350,Math.ceil(r*2*1.08*(devicePixelRatio||1))));if(surface.width!==size){surface.width=surface.height=size;gl.viewport(0,0,size,size);}gl.useProgram(program);gl.uniform1f(locations.yaw,yaw);gl.uniform1f(locations.pitch,pitch);gl.uniform1f(locations.time,time);gl.drawArrays(gl.TRIANGLES,0,6);ctx.drawImage(surface,cx-r*1.08,cy-r*1.08,r*2.16,r*2.16);return;}
 // Canvas fallback preserves a shaded sphere and Taiji instead of an empty map.
 ctx.save();ctx.beginPath();ctx.arc(cx,cy,r,0,Math.PI*2);ctx.clip();const pearl=ctx.createRadialGradient(cx-r*.35,cy-r*.4,r*.08,cx,cy,r);pearl.addColorStop(0,'#fff9f1');pearl.addColorStop(.5,'#d6d7ef');pearl.addColorStop(.8,'#7ca8c8');pearl.addColorStop(1,'#273654');ctx.fillStyle=pearl;ctx.fillRect(cx-r,cy-r,r*2,r*2);ctx.fillStyle='#4b6489aa';ctx.beginPath();ctx.arc(cx,cy,r,-Math.PI/2,Math.PI/2);ctx.arc(cx,cy+r/2,r/2,Math.PI/2,-Math.PI/2,true);ctx.arc(cx,cy-r/2,r/2,Math.PI/2,-Math.PI/2);ctx.fill();ctx.restore();
}
