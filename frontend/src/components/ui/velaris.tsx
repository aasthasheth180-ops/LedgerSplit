import { useEffect, useRef, type ReactNode } from 'react';
import { cn } from '../../lib/utils';
const vertex = `attribute vec2 position; varying vec2 vUv; void main(){vUv=position*.5+.5;gl_Position=vec4(position,0.,1.);}`;
const fragment = `precision highp float; varying vec2 vUv; uniform vec2 u_resolution; uniform float u_time; uniform float u_grain; uniform vec3 u_colors[4]; uniform vec3 u_bg;
vec3 permute(vec3 x){return mod(((x*34.)+1.)*x,289.);}
float snoise(vec2 v){const vec4 C=vec4(.211324865405187,.366025403784439,-.577350269189626,.024390243902439);vec2 i=floor(v+dot(v,C.yy));vec2 x0=v-i+dot(i,C.xx);vec2 i1=x0.x>x0.y?vec2(1.,0.):vec2(0.,1.);vec4 x12=x0.xyxy+C.xxzz;x12.xy-=i1;i=mod(i,289.);vec3 p=permute(permute(i.y+vec3(0.,i1.y,1.))+i.x+vec3(0.,i1.x,1.));vec3 m = max(
  0.5 - vec3(
    dot(x0, x0),
    dot(x12.xy, x12.xy),
    dot(x12.zw, x12.zw)
  ),
  0.0
);m=m*m;m=m*m;vec3 x=2.*fract(p*C.www)-1.;vec3 h=abs(x)-.5;vec3 ox=floor(x+.5);vec3 a0=x-ox;m*=1.79284291400159-.85373472095314*(a0*a0+h*h);vec3 g;g.x=a0.x*x0.x+h.x*x0.y;g.yz=a0.yz*x12.xz+h.yz*x12.yw;return 130.*dot(m,g);}
void main(){vec2 uv=vUv;vec2 p=uv-.5;p.x*=u_resolution.x/max(u_resolution.y,1.);float t=u_time*0.6;float n1=snoise(p*.4+vec2(t*.2,-t*.3));float n2=snoise(p*.55+vec2(-t*.15,t*.25)+n1*.25);float n3=snoise(p*.75+vec2(t*.1,-t*.2)+n2*.2);vec3 col=u_bg;col=mix(col,u_colors[0],smoothstep(-.2,.5,n1)*.45);col=mix(col,u_colors[1],smoothstep(-.1,.6,n2)*.35);col=mix(col,u_colors[2],smoothstep(-.3,.4,n3)*.3);col=mix(col,u_colors[3],smoothstep(0.,.7,n1*n2)*.25);float dist=length(p)*1.5;col+=u_colors[1]*(1.-smoothstep(0.,.8,dist))*.08;col*=mix(.85,1.,1.-smoothstep(.3,1.2,dist));float grain=fract(sin(dot(uv,vec2(12.9898,78.233)))*43758.5453+u_time);col+=(grain-.5)*u_grain*.1;gl_FragColor=vec4(clamp(col,0.,1.),1.);}`;
export interface VelarisProps { bg?:string; colors?:readonly [string,string,string,string]; speed?:number; grain?:number; height?:string; className?:string; children?:ReactNode; }
const defaultColors = ['#4a7856','#75a483','#a1c9a5','#284d37'] as const;
function rgb(hex:string):[number,number,number]{const h=hex.replace('#','');return [0,2,4].map(i=>parseInt(h.slice(i,i+2),16)/255) as [number,number,number];}
export default function Velaris({bg='#365940',colors=defaultColors,speed=.35,grain=.05,height='auto',className,children}:VelarisProps){
 const canvasRef=useRef<HTMLCanvasElement>(null);const containerRef=useRef<HTMLDivElement>(null);
 useEffect(()=>{const canvas=canvasRef.current,container=containerRef.current;if(!canvas||!container)return;const gl=canvas.getContext('webgl',{alpha:false,antialias:false});if(!gl)return;
 const shader=(type:number,source:string)=>{const s=gl.createShader(type);if(!s)return null;gl.shaderSource(s,source);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS)){console.error('Velaris shader:',gl.getShaderInfoLog(s));gl.deleteShader(s);return null;}return s;};
 console.log(fragment.split('\n').map((line, i) => `${i + 1}: ${line}`).join('\n'));
 const vs=shader(gl.VERTEX_SHADER,vertex),fs=shader(gl.FRAGMENT_SHADER,fragment);if(!vs||!fs){if(vs)gl.deleteShader(vs);if(fs)gl.deleteShader(fs);return;}
 const program=gl.createProgram();if(!program){gl.deleteShader(vs);gl.deleteShader(fs);return;}gl.attachShader(program,vs);gl.attachShader(program,fs);gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS)){console.error('Velaris link:',gl.getProgramInfoLog(program));gl.deleteProgram(program);gl.deleteShader(vs);gl.deleteShader(fs);return;}gl.useProgram(program);
 const buffer=gl.createBuffer();if(!buffer){gl.deleteProgram(program);gl.deleteShader(vs);gl.deleteShader(fs);return;}gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,1,1]),gl.STATIC_DRAW);const pos=gl.getAttribLocation(program,'position');if(pos>=0){gl.enableVertexAttribArray(pos);gl.vertexAttribPointer(pos,2,gl.FLOAT,false,0,0);}
 const loc={res:gl.getUniformLocation(program,'u_resolution'),time:gl.getUniformLocation(program,'u_time'),grain:gl.getUniformLocation(program,'u_grain'),colors:gl.getUniformLocation(program,'u_colors[0]'),bg:gl.getUniformLocation(program,'u_bg')};const flat=new Float32Array(colors.flatMap(rgb));const background=rgb(bg);
 const resize=()=>{const dpr=Math.min(window.devicePixelRatio||1,2);canvas.width=Math.max(1,Math.round(container.clientWidth*dpr));canvas.height=Math.max(1,Math.round(container.clientHeight*dpr));gl.viewport(0,0,canvas.width,canvas.height);};const ro=new ResizeObserver(resize);ro.observe(container);resize();
 const media=window.matchMedia('(prefers-reduced-motion: reduce)');let raf=0,elapsed=0,last=0;const render=(time:number)=>{if(last)elapsed+=Math.min((time-last)/1000,.05);last=time;gl.uniform2f(loc.res,canvas.width,canvas.height);gl.uniform1f(loc.time,elapsed*speed);gl.uniform1f(loc.grain,grain);gl.uniform3f(loc.bg,...background);gl.uniform3fv(loc.colors,flat);gl.drawArrays(gl.TRIANGLE_STRIP,0,4);if(!media.matches&&!document.hidden)raf=requestAnimationFrame(render);};const restart=()=>{cancelAnimationFrame(raf);last=0;if(!document.hidden)raf=requestAnimationFrame(render);};restart();document.addEventListener('visibilitychange',restart);media.addEventListener('change',restart);
 return()=>{cancelAnimationFrame(raf);ro.disconnect();document.removeEventListener('visibilitychange',restart);media.removeEventListener('change',restart);gl.deleteBuffer(buffer);gl.deleteProgram(program);gl.deleteShader(vs);gl.deleteShader(fs);};
 },[bg,colors,speed,grain]);
 return <div ref={containerRef} style={{height,backgroundColor:bg}} className={cn('relative w-full overflow-hidden',className)}><canvas ref={canvasRef} aria-hidden="true" className="pointer-events-none absolute inset-0 h-full w-full"/><div className="relative z-10 w-full">{children}</div></div>;
}
