// ================================================================ STELLAR VISUAL VOCABULARY V1
// Reusable construction vocabulary for every Stellar room (docs/STELLAR_VISUAL_VOCABULARY_V1.md). Original Stellar drawing
// code that follows the reference station's construction rules (studied from its source; no art file, sprite or character
// is used). Room-agnostic: a builder takes a frame {cx,cy,a,f,L,D} or a footprint and options, never a room id. Rooms
// compose these families; H-CMD (calibration room) is the first composition. Inlined into the prototype page by render.py.
//
//   GRAMMAR    frame · corner block/post · bevel (chamfer) · recessed panel · raised panel · grille · bolt · hinge · handle /
//              slot lamp · control strip · lamp · indicator · cable · conduit · bracket · bezel · glass · shadow cavity ·
//              drawer · access hatch · support leg · plinth/base · edge wear
//   MATERIAL   SV.M: dark gunmetal base, three metal layers (lo/base/hi), olive and blue-steel storage steels, brass hardware,
//              amber technical light, cyan glass, darker cavities, brighter exposed edges, warm wear; prismX adds the
//              floor-line occlusion, warm key / cool rim split and a two-layer contact shadow
//   LAYERS     LOW (floor modules, plinths, cabinets) · MEDIUM (desks, consoles, bays, storage) · HIGH (racks, wall-hung SV.wall.upper
//              modules, screens, ribs, lamps): rooms compose all three, never one flat band
//   FAMILIES   SV.screen (module + inactive surfaces: info, tactical, instrument, status, multi) · SV.ws (standard, compact,
//              heavy; side and rear are views of the same construction) · SV.con (bank modules of 1-3 bays: single, double,
//              wide; bay kits screen, stack, instrument, switch, readout) · SV.eq (rack, relay, bay, service, storage locker,
//              storage drawers) · SV.door (standard A, hub B, restricted C, closed: one opening = one assembly) · SV.chair (standard, operator, command) · SV.small (instrument pod, service box, control box,
//              junction box, cable junction, lamp, indicator, bracket, conduit) · SV.wall (panel, rib, grille, service,
//              console, equipment, storage, junction; bay rhythms) · SV.floor (panel, grille, hatch, conduit, junction,
//              hazard, beam)
const SV={};
SV.M={deck:"#2a2b2e",plate:"#2f3033",seam:"#121315",gun:"#3d4046",gunHi:"#575a61",gunLo:"#2a2c31",rib:"#1d1f22",panel:"#33363c",
  edge:"#6c7078",cavity:"#141517",olive:"#4a4f3c",oliveHi:"#646b51",oliveLo:"#34382b",steel:"#3b4856",steelHi:"#55677a",steelLo:"#28323d",
  brass:"#b8904e",brassHi:"#e1bb72",amber:"#f08a2c",amberHi:"#ffd08a",ti:"#c3cbd4",glass:"#081016",glassLit:"#0f4655",glassHi:"#3fb7cc",
  wood:"#6b4a2f",woodHi:"#8c6239",woodLo:"#4a3220",felt:"#1f6f5c",feltHi:"#2a8a72",fabric:"#5b4c4a",fabricHi:"#776361",cream:"#d8cdb8",creamLo:"#b9ad96",leaf:"#3c8048",leafHi:"#5aa765",leafLo:"#2f6a3c",
  red:"#c43a4b",hazard:"#c9922e",leather:"#23262d",leatherHi:"#3a3e48",out:"#08090b",crown:"#7d7a70",yellow:"#c99a2e",rust:"#7e2f25",copper:"#b0663a"};
const CAL=SV.M; // the calibration rooms' palette is the vocabulary palette
// ---------------------------------------------------------------- GRAMMAR: geometry primitives
function frameRect(fr,s0,s1,d0,d1){const {cx,cy,a,f}=fr;const P2=(s,d)=>[cx+a[0]*s+f[0]*d,cy+a[1]*s+f[1]*d];return[P2(s0,d0),P2(s1,d0),P2(s1,d1),P2(s0,d1)]}
function frameCham(fr,s0,s1,d0,d1,c){const {cx,cy,a,f}=fr;const P2=(s,d)=>[cx+a[0]*s+f[0]*d,cy+a[1]*s+f[1]*d];return[P2(s0+c,d0),P2(s1-c,d0),P2(s1,d0+c),P2(s1,d1-c),P2(s1-c,d1),P2(s0+c,d1),P2(s0,d1-c),P2(s0,d0+c)]}
// a cast block: two-layer contact shadow, directional faces, floor-line occlusion, warm key / cool rim, dark outline, lit top edge
function prismX(pts,h0,h1,top,side,o={}){
  if(h0<0.05&&o.shadow!==false){ctx.fillStyle="rgba(0,0,0,.16)";ctx.fill(poly2(pts.map(p=>[p[0]+1.9,p[1]+1.9]),0.01));ctx.fillStyle="rgba(0,0,0,.26)";ctx.fill(poly2(pts.map(p=>[p[0]+0.9,p[1]+0.9]),0.01))}
  prism(pts,h0,h1,top,side,o);let cx=0,cy=0;for(const q of pts){cx+=q[0];cy+=q[1]}cx/=pts.length;cy/=pts.length;
  ctx.strokeStyle=CAL.out;ctx.lineWidth=o.lw||0.45;ctx.lineJoin="round";
  for(let i=0;i<pts.length;i++){const a=pts[i],b=pts[(i+1)%pts.length];let nx=b[1]-a[1],ny=a[0]-b[0];if(nx*((a[0]+b[0])/2-cx)+ny*((a[1]+b[1])/2-cy)<0){nx=-nx;ny=-ny}
    if(nx*V.cam[0]+ny*V.cam[1]<=0.001)continue;const p=[V.P(a[0],a[1],h0),V.P(b[0],b[1],h0),V.P(b[0],b[1],h1),V.P(a[0],a[1],h1)];
    if(o.mat!==false&&h1-h0>2.2){const L=Math.hypot(nx,ny)||1;const lit=(nx*LIGHT[0]+ny*LIGHT[1])/L;
      const g=ctx.createLinearGradient(0,p[3][1],0,p[0][1]);g.addColorStop(0,lit>0?"rgba(255,224,176,.07)":"rgba(127,180,216,.06)");g.addColorStop(0.55,"rgba(0,0,0,0)");g.addColorStop(1,h0<0.5?"rgba(0,0,0,.24)":"rgba(0,0,0,.1)");
      ctx.fillStyle=g;ctx.beginPath();ctx.moveTo(p[0][0],p[0][1]);for(let k=1;k<4;k++)ctx.lineTo(p[k][0],p[k][1]);ctx.closePath();ctx.fill()}
    ctx.beginPath();ctx.moveTo(p[0][0],p[0][1]);ctx.lineTo(p[1][0],p[1][1]);ctx.lineTo(p[2][0],p[2][1]);ctx.lineTo(p[3][0],p[3][1]);ctx.closePath();ctx.stroke();
    if(o.hi!==false){ctx.strokeStyle="rgba(255,240,215,.22)";ctx.lineWidth=0.3;ctx.beginPath();ctx.moveTo(p[3][0],p[3][1]+0.25);ctx.lineTo(p[2][0],p[2][1]+0.25);ctx.stroke();ctx.strokeStyle=CAL.out;ctx.lineWidth=o.lw||0.45}}
  if(top)ctx.stroke(poly2(pts,h1))}
function onFace(a,b,n,h0,h1,fn){if(n[0]*V.cam[0]+n[1]*V.cam[1]<=0.02)return false;const L=Math.hypot(b[0]-a[0],b[1]-a[1]);let A=a,B=b;
  if(V.P(B[0],B[1],h1)[0]<V.P(A[0],A[1],h1)[0]){A=b;B=a}const o=V.P(A[0],A[1],h1),e=V.P(B[0],B[1],h1),d=V.P(A[0],A[1],h0);
  ctx.save();ctx.transform((e[0]-o[0])/L,(e[1]-o[1])/L,(d[0]-o[0])/(h1-h0),(d[1]-o[1])/(h1-h0),o[0],o[1]);fn(L,h1-h0);ctx.restore();return true}
function onTop(fr,s0,s1,d0,d1,h,fn){const o=(s,d)=>[fr.cx+fr.a[0]*s+fr.f[0]*d,fr.cy+fr.a[1]*s+fr.f[1]*d];const O=V.P(...o(s0,d0),h),U=V.P(...o(s0+1,d0),h),W=V.P(...o(s0,d0+1),h);
  ctx.save();ctx.transform(U[0]-O[0],U[1]-O[1],W[0]-O[0],W[1]-O[1],O[0],O[1]);fn(s1-s0,d1-d0);ctx.restore()}
function calBounds(poly){const xs=poly.map(p=>p[0]),ys=poly.map(p=>p[1]);return[Math.min(...xs),Math.min(...ys),Math.max(...xs),Math.max(...ys)]}
// faces of a frame rectangle: [a,b,normal]; near-to-far ordering helper for parts that can overlap on screen
function faces(fr,s0,s1,d0,d1){const r=frameRect(fr,s0,s1,d0,d1);const F=fr.f,A=fr.a;return{front:[r[3],r[2],F],back:[r[1],r[0],[-F[0],-F[1]]],e1:[r[0],r[3],[-A[0],-A[1]]],e2:[r[2],r[1],A]}}
function camAlong(v){return v[0]*V.cam[0]+v[1]*V.cam[1]}
// ---------------------------------------------------------------- GRAMMAR: face painters (local face units, origin top-left)
function chamRect(x,y,w,h,c){ctx.beginPath();ctx.moveTo(x+c,y);ctx.lineTo(x+w-c,y);ctx.lineTo(x+w,y+c);ctx.lineTo(x+w,y+h-c);ctx.lineTo(x+w-c,y+h);ctx.lineTo(x+c,y+h);ctx.lineTo(x,y+h-c);ctx.lineTo(x,y+c);ctx.closePath()}
function dRecess(x,y,w,h,c){ctx.fillStyle=c||"#1f2125";ctx.fillRect(x,y,w,h);ctx.strokeStyle=CAL.out;ctx.lineWidth=0.25;ctx.strokeRect(x,y,w,h);ctx.fillStyle="rgba(0,0,0,.35)";ctx.fillRect(x,y,w,Math.min(0.45,h*0.2));ctx.fillStyle="rgba(255,240,215,.09)";ctx.fillRect(x,y+h-0.25,w,0.25)}
function dRaised(x,y,w,h,c){ctx.fillStyle=c||CAL.gunHi;ctx.fillRect(x,y,w,h);ctx.fillStyle="rgba(255,240,215,.16)";ctx.fillRect(x,y,w,0.3);ctx.fillStyle="rgba(0,0,0,.35)";ctx.fillRect(x,y+h-0.3,w,0.3);ctx.strokeStyle=CAL.out;ctx.lineWidth=0.22;ctx.strokeRect(x,y,w,h)}
function dVents(x,y,w,h,n){dRecess(x,y,w,h,"#17181b");ctx.fillStyle="#3c3f45";for(let k=0;k<n;k++)ctx.fillRect(x+0.4,y+0.35+k*(h-0.6)/n,w-0.8,(h-0.6)/n*0.45)}
function dGrille(x,y,w,h){ctx.fillStyle="#24262a";ctx.fillRect(x-0.45,y-0.45,w+0.9,h+0.9);ctx.fillStyle="#0e0f11";ctx.fillRect(x,y,w,h);ctx.fillStyle="#383b41";for(let k=y+0.45;k<y+h-0.3;k+=0.72)ctx.fillRect(x+0.3,k,w-0.6,0.3);
  ctx.fillStyle="rgba(255,240,215,.12)";ctx.fillRect(x-0.45,y-0.45,w+0.9,0.22)}
function dLouvrePair(x,y,w,h){const g=w*0.08;dGrille(x,y,(w-g)/2,h);dGrille(x+(w+g)/2,y,(w-g)/2,h)}
function dAmber(x,y,w,h=0.7){ctx.fillStyle="#2c1806";ctx.fillRect(x-0.2,y-0.2,w+0.4,h+0.4);ctx.fillStyle=CAL.amber;ctx.fillRect(x,y,w,h);ctx.fillStyle=CAL.amberHi;ctx.fillRect(x+w*0.15,y+h*0.25,w*0.7,h*0.35)}
// the signature lower-cabinet pull: a recessed dark frame carrying a lit amber bar with a hot core
function dSlotLamp(x,y,w){ctx.fillStyle="#0f1011";chamRect(x-0.5,y-0.35,w+1,1.25,0.25);ctx.fill();ctx.fillStyle="rgba(240,138,44,.22)";ctx.fillRect(x-0.6,y-0.45,w+1.2,1.45);
  ctx.fillStyle=CAL.amber;ctx.fillRect(x,y,w,0.55);ctx.fillStyle=CAL.amberHi;ctx.fillRect(x+w*0.12,y+0.12,w*0.76,0.22)}
const dHandle=dSlotLamp;
function dRivets(x,y,w,h,c){ctx.fillStyle=c||CAL.brass;for(const [u,v] of [[x+0.5,y+0.5],[x+w-0.5,y+0.5],[x+0.5,y+h-0.5],[x+w-0.5,y+h-0.5]]){ctx.beginPath();ctx.arc(u,v,0.22,0,TAU);ctx.fill()}}
function dHinges(x,y,h){ctx.fillStyle="#6a6d73";for(const v of [y+1,y+h-2.4]){ctx.fillRect(x,v,0.55,1.4);ctx.fillStyle="rgba(255,240,215,.2)";ctx.fillRect(x,v,0.55,0.25);ctx.fillStyle="#6a6d73"}}
function dKnob(x,y,r){ctx.fillStyle="#141518";ctx.beginPath();ctx.arc(x,y,r*1.3,0,TAU);ctx.fill();const g=ctx.createRadialGradient(x-r*0.35,y-r*0.35,r*0.1,x,y,r);g.addColorStop(0,CAL.brassHi);g.addColorStop(1,"#6b4e22");ctx.fillStyle=g;ctx.beginPath();ctx.arc(x,y,r,0,TAU);ctx.fill()}
function dButtons(x,y,cols,rows,s,seed){const C=["#f08a2c","#3a3d43","#c8402f","#3a3d43","#58c8de","#3a3d43","#e7c06a","#d8d2c2"];ctx.fillStyle="#141518";ctx.fillRect(x-0.25,y-0.25,cols*s+0.5,rows*s+0.5);
  for(let r=0;r<rows;r++)for(let c=0;c<cols;c++){ctx.fillStyle=C[(seed+r*7+c*3)%C.length];ctx.fillRect(x+c*s+0.12,y+r*s+0.12,s-0.3,s-0.3);ctx.fillStyle="rgba(255,255,255,.18)";ctx.fillRect(x+c*s+0.12,y+r*s+0.12,s-0.3,0.15)}}
function dKeys(x,y,w,h){ctx.fillStyle="#141518";ctx.fillRect(x,y,w,h);ctx.fillStyle="#a7aeb6";const cols=Math.max(5,Math.floor(w/0.85)),rows=3;
  for(let r=0;r<rows;r++)for(let c=0;c<cols;c++)ctx.fillRect(x+0.25+c*(w-0.5)/cols,y+0.25+r*(h-0.5)/rows,(w-0.5)/cols*0.72,(h-0.5)/rows*0.62);ctx.fillStyle="#c9cfd6";ctx.fillRect(x+w*0.3,y+h-0.55,w*0.4,0.28);ctx.fillStyle=CAL.amber;ctx.fillRect(x+0.3,y+0.3,0.5,0.35)}
function dPlate(x,y,w,h,txt){ctx.fillStyle="#121315";ctx.fillRect(x,y,w,h);ctx.strokeStyle=CAL.brass;ctx.lineWidth=0.22;ctx.strokeRect(x,y,w,h);
  if(txt&&cam.z>=1.8){ctx.fillStyle="#efe2c4";ctx.font=`700 ${h*0.62}px system-ui`;ctx.textAlign="center";ctx.textBaseline="middle";ctx.fillText(txt,x+w/2,y+h/2+0.05)}}
function dWear(W,H,seed){let s=((seed||1)*7919+13)%2147483647;const r=()=>{s=(s*16807)%2147483647;return s/2147483647};ctx.fillStyle="rgba(196,142,62,.5)";
  for(let k=0;k<8;k++){const e=k%4,t=r(),len=0.5+r()*1.6;if(e===0)ctx.fillRect(t*Math.max(0,W-len),0.12,len,0.26);else if(e===1)ctx.fillRect(t*Math.max(0,W-len),H-0.38,len,0.26);else if(e===2)ctx.fillRect(0.12,t*Math.max(0,H-len),0.26,len);else ctx.fillRect(W-0.38,t*Math.max(0,H-len),0.26,len)}
  ctx.fillStyle="rgba(0,0,0,.08)";for(let k=0;k<3;k++)ctx.fillRect(r()*W*0.8,r()*H*0.8,1+r()*2.5,0.6+r()*1.4)} // grime patches: small surface variation
function dLampCol(x,y,n,step){for(let k=0;k<n;k++)dAmber(x,y+k*(step||1.25),0.8,0.5)}
function dLampPips(x,y,n,step){for(let k=0;k<n;k++){ctx.fillStyle="#2c1806";ctx.fillRect(x-0.15,y+k*(step||1.3)-0.15,0.9,0.9);ctx.fillStyle=k%3===2?"#ffb25a":CAL.amber;ctx.fillRect(x,y+k*(step||1.3),0.6,0.6)}}
function dToggles(x,y,n){for(let k=0;k<n;k++){const u=x+k*1.3;ctx.fillStyle="#141518";ctx.fillRect(u,y,1,1.9);ctx.fillStyle="#a7aeb6";ctx.fillRect(u+0.32,y+0.2,0.36,0.95);ctx.fillStyle=k%3===1?CAL.amber:"#3a3d43";ctx.fillRect(u+0.15,y+1.3,0.7,0.42)}}
function dTrackball(x,y,r){ctx.fillStyle="#141518";chamRect(x-r-0.7,y-r-0.7,2*r+1.4,2*r+1.4,0.4);ctx.fill();const g=ctx.createRadialGradient(x-r*0.4,y-r*0.45,r*0.1,x,y,r);g.addColorStop(0,"#b4bcc6");g.addColorStop(1,"#2a2d33");
  ctx.fillStyle=g;ctx.beginPath();ctx.arc(x,y,r,0,TAU);ctx.fill();ctx.strokeStyle=CAL.brass;ctx.lineWidth=0.2;ctx.stroke()}
function dHatch(x,y,w,h){dRecess(x,y,w,h,"#2b2d32");ctx.strokeStyle="rgba(0,0,0,.5)";ctx.lineWidth=0.2;ctx.strokeRect(x+0.6,y+0.6,w-1.2,h-1.2);dRivets(x,y,w,h,"#8a7448")}
// analogue gauge with the needle at its rest stop: hardware detail, never a reading
function dGauge(x,y,r){ctx.fillStyle="#141518";ctx.beginPath();ctx.arc(x,y,r+0.35,0,TAU);ctx.fill();ctx.fillStyle="#cfc8b6";ctx.beginPath();ctx.arc(x,y,r,0,TAU);ctx.fill();
  ctx.strokeStyle="#1a1a1a";ctx.lineWidth=0.18;ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(x-r*0.62,y+r*0.5);ctx.stroke();ctx.strokeStyle=CAL.brass;ctx.lineWidth=0.22;ctx.beginPath();ctx.arc(x,y,r+0.2,0,TAU);ctx.stroke()}
function dSwitchMatrix(x,y,cols,rows,s,seed){ctx.fillStyle="#141518";ctx.fillRect(x-0.3,y-0.3,cols*s+0.6,rows*s+0.6);for(let r=0;r<rows;r++)for(let c=0;c<cols;c++){const on=((seed*31+r*7+c*13)%5)===0;
  ctx.fillStyle=on?CAL.amber:"#2e3036";ctx.fillRect(x+c*s+0.15,y+r*s+0.15,s-0.35,s-0.35);if(on){ctx.fillStyle=CAL.amberHi;ctx.fillRect(x+c*s+0.3,y+r*s+0.3,s-0.65,0.2)}}}
function dLoom(x0,x1,y,sag){const cols=["#16171a","#a8402e","#16171a","#3c6f9a"];cols.forEach((c,k)=>{ctx.strokeStyle=c;ctx.lineWidth=0.38;ctx.beginPath();ctx.moveTo(x0,y+k*0.42);ctx.quadraticCurveTo((x0+x1)/2,y+k*0.42+sag*2,x1,y+k*0.42);ctx.stroke()});
  ctx.fillStyle="#6a6d73";for(let u=x0+3;u<x1-2;u+=5){const t=(u-x0)/(x1-x0);ctx.fillRect(u,y-0.35+sag*4*t*(1-t),0.7,2.3)}}
function dConduit(x,y0,y1,w){ctx.fillStyle="#3a3d43";ctx.fillRect(x,y0,w||0.8,y1-y0);ctx.fillStyle="rgba(255,240,215,.14)";ctx.fillRect(x,y0,0.25,y1-y0);ctx.fillStyle="#6a6d73";for(let v=y0+2;v<y1-1;v+=5)ctx.fillRect(x-0.25,v,(w||0.8)+0.5,0.55)}
function dBracket(x,y,w){ctx.fillStyle="#5a5d63";ctx.fillRect(x,y,w,0.6);ctx.fillRect(x,y,0.6,1.6);ctx.fillRect(x+w-0.6,y,0.6,1.6);ctx.fillStyle="rgba(255,240,215,.16)";ctx.fillRect(x,y,w,0.18)}
function dIndicator(x,y,on){ctx.fillStyle="#0f1011";ctx.fillRect(x-0.2,y-0.2,0.95,0.75);ctx.fillStyle=on?"#5fe0a0":"#2b3a33";ctx.fillRect(x,y,0.55,0.35)}
// ---------------------------------------------------------------- GRAMMAR: world-space small parts
function cable3(a,b,sag,col,lw){ctx.strokeStyle=col;ctx.lineWidth=lw;ctx.beginPath();for(let k=0;k<=12;k++){const t=k/12;const q=V.P(a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,a[2]+(b[2]-a[2])*t-sag*4*t*(1-t));k?ctx.lineTo(q[0],q[1]):ctx.moveTo(q[0],q[1])}ctx.stroke()}
function socket3(x,y){prismX(rectPoly(x-0.9,y-0.9,x+0.9,y+0.9),0,0.8,"#3a3d43","#26282c",{lw:0.3,hi:false,mat:false});const p=V.P(x,y,0.82);ctx.fillStyle=CAL.amber;ctx.fillRect(p[0]-0.25,p[1]-0.2,0.5,0.4)}
function plinth(fr,s0,s1,d0,d1,h){prismX(frameRect(fr,s0+0.4,s1-0.4,d0+0.4,d1-0.4),0,h||1,CAL.rib,CAL.rib,{hi:false,mat:false})}
// cap top: a separate casting seen from above: lit front lip, bolted inset panel, one vent slot, wear
function capTop(fr,s0,s1,d0,d1,h,seed){onTop(fr,s0,s1,d0,d1,h+0.02,(W,Dd)=>{ctx.fillStyle="rgba(0,0,0,.18)";ctx.fillRect(0.7,0.7,W-1.4,Dd-1.4);ctx.strokeStyle="rgba(0,0,0,.4)";ctx.lineWidth=0.22;ctx.strokeRect(0.7,0.7,W-1.4,Dd-1.4);
  ctx.fillStyle="rgba(255,240,215,.12)";ctx.fillRect(0.2,Dd-0.45,W-0.4,0.3);if(W>3.5&&Dd>3){ctx.fillStyle="#17181b";ctx.fillRect(W*0.25,Dd*0.4,W*0.5,0.6)}dRivets(0.3,0.3,W-0.6,Dd-0.6,"#8a7448");dWear(W,Dd,seed||1)})}
function feet(fr,s0,s1,d0,d1,h){for(const s of [s0+0.6,s1-1.6])for(const d of [d0+0.5,d1-1.5])prismX(frameRect(fr,s,s+1,d,d+1),0,h||0.9,"#2a2c31","#1d1f23",{lw:0.3,hi:false,mat:false})}
// ================================================================ SCREEN family
// housing -> bezel -> glass -> UI surface -> frame -> mounting -> indicators. Approved content renders through draw();
// with no data the glass shows an inactive UI surface: etched structure only (panes, rules, reticle frame), never values
SV.screen={};
SV.screen.surface=(kind,x,y,w,h)=>{ctx.save();ctx.strokeStyle="rgba(110,175,185,.1)";ctx.lineWidth=0.15;
  if(kind==="tactical"&&w>4&&h>3){const r=Math.min(w,h)*0.32;ctx.beginPath();ctx.arc(x+w/2,y+h/2,r,0,TAU);ctx.stroke();ctx.beginPath();ctx.arc(x+w/2,y+h/2,r*0.5,0,TAU);ctx.stroke();ctx.beginPath();ctx.moveTo(x+w/2-r*1.2,y+h/2);ctx.lineTo(x+w/2+r*1.2,y+h/2);ctx.moveTo(x+w/2,y+h/2-r*1.2);ctx.lineTo(x+w/2,y+h/2+r*1.2);ctx.stroke()}
  else if(kind==="info"&&w>5){ctx.strokeRect(x+0.6,y+0.6,w-1.2,h-1.2);ctx.beginPath();ctx.moveTo(x+0.6,y+Math.min(2,h*0.28));ctx.lineTo(x+w-0.6,y+Math.min(2,h*0.28));ctx.moveTo(x+w*0.68,y+Math.min(2,h*0.28));ctx.lineTo(x+w*0.68,y+h-0.6);ctx.stroke()}
  else if(kind==="status"&&w>3){ctx.strokeRect(x+0.5,y+0.5,w-1,h-1);ctx.beginPath();ctx.moveTo(x+0.5,y+h*0.35);ctx.lineTo(x+w-0.5,y+h*0.35);ctx.stroke()}
  else if(kind==="instrument"&&w>2){ctx.beginPath();ctx.arc(x+w/2,y+h/2,Math.min(w,h)*0.32,0,TAU);ctx.stroke()}
  else if(w>3&&h>2)ctx.strokeRect(x+0.7,y+0.7,w-1.4,h-1.4);ctx.restore()};
function dScreenModule(x,y,w,h,lit,draw,kind){const c=Math.max(0.3,Math.min(1.1,Math.min(w,h)*0.14));
  ctx.fillStyle="#17181b";ctx.fillRect(x-1.85,y+h*0.3,0.6,h*0.4);ctx.fillRect(x+w+1.25,y+h*0.3,0.6,h*0.4); // mounting tabs
  ctx.fillStyle="#1d1f23";chamRect(x-1.35,y-1.35,w+2.7,h+2.7,c+0.35);ctx.fill();ctx.strokeStyle=CAL.out;ctx.lineWidth=0.22;ctx.stroke(); // housing
  ctx.fillStyle="#2e3137";chamRect(x-1.05,y-1.05,w+2.1,h+2.1,c);ctx.fill(); // bezel
  ctx.fillStyle="rgba(255,240,215,.17)";ctx.fillRect(x-1.05+c,y-1.05,w+2.1-2*c,0.3);ctx.fillStyle="rgba(0,0,0,.3)";ctx.fillRect(x-1.05+c,y+h+0.75,w+2.1-2*c,0.3);
  ctx.fillStyle="#08090b";ctx.fillRect(x-0.45,y-0.45,w+0.9,h+0.9);ctx.fillStyle=lit?CAL.glassLit:CAL.glass;ctx.fillRect(x,y,w,h); // frame + glass
  if(kind==="multi"&&!draw){const n=w>h*2.2?3:2;ctx.fillStyle="#1d1f23";for(let i=1;i<n;i++)ctx.fillRect(x+w*i/n-0.3,y,0.6,h)} // mullions
  if(draw){ctx.save();ctx.beginPath();ctx.rect(x,y,w,h);ctx.clip();ctx.translate(x,y);const k=Math.max(1,13/h);ctx.scale(1/k,1/k);draw(w*k,h*k);ctx.restore()}
  else if(lit){ctx.strokeStyle="rgba(120,230,250,.55)";ctx.lineWidth=0.18;const cc=Math.min(w,h)*0.18;
    for(const [u,v,dx,dy] of [[x+0.4,y+0.4,1,1],[x+w-0.4,y+0.4,-1,1],[x+0.4,y+h-0.4,1,-1],[x+w-0.4,y+h-0.4,-1,-1]]){ctx.beginPath();ctx.moveTo(u+dx*cc,v);ctx.lineTo(u,v);ctx.lineTo(u,v+dy*cc);ctx.stroke()}
    ctx.fillStyle="rgba(120,230,250,.22)";ctx.fillRect(x+0.6,y+0.6,w-1.2,0.35);ctx.fillStyle="rgba(120,230,250,.08)";for(let k=y+1.2;k<y+h;k+=0.8)ctx.fillRect(x,k,w,0.25)}
  else SV.screen.surface(kind||"plain",x,y,w,h);
  ctx.fillStyle="rgba(0,0,0,.42)";ctx.fillRect(x,y,w,Math.min(0.55,h*0.12));ctx.fillRect(x,y,Math.min(0.45,w*0.1),h); // shadow cavity under the bezel
  ctx.save();ctx.beginPath();ctx.rect(x,y,w,h);ctx.clip();ctx.fillStyle=`rgba(255,255,255,${lit?0.045:0.065})`;ctx.beginPath();ctx.moveTo(x+w*0.08,y);ctx.lineTo(x+w*0.4,y);ctx.lineTo(x+w*0.1,y+h);ctx.lineTo(x-w*0.22,y+h);ctx.closePath();ctx.fill();ctx.restore();
  ctx.fillStyle=CAL.brass;const bi=c*0.6;for(const [u,v] of [[x-1.05+bi,y-1.05+bi],[x+w+1.05-bi,y-1.05+bi],[x-1.05+bi,y+h+1.05-bi],[x+w+1.05-bi,y+h+1.05-bi]]){ctx.beginPath();ctx.arc(u,v,0.18,0,TAU);ctx.fill()}
  if(w>4&&h>1.5){const iy=y+h+0.42;dIndicator(x+w-1.5,iy,lit);ctx.fillStyle="#7a4515";ctx.fillRect(x+w-2.4,iy,0.55,0.3);ctx.fillStyle="#3a3d43";ctx.fillRect(x+w-3.3,iy,0.55,0.3)}}
SV.screen.module=dScreenModule;
// screen + its own amber lamp pips either side (the console screen bay unit)
function dScreenBay(x,y,w,h,lit,draw,kind){dScreenModule(x+1.6,y,w-3.2,h,lit,draw,kind);dLampPips(x+0.2,y+0.6,Math.max(1,Math.floor(h/1.4)),1.35);dLampPips(x+w-0.8,y+0.6,Math.max(1,Math.floor(h/1.4)),1.35)}
// ================================================================ WORKSTATION family
// fr: {cx,cy,a (unit along), f (unit toward the operator), L, D}. Variants: "standard" (two pedestals, raised control wings around a
// recessed keyboard tray, wide-screen housing with lamp columns and top clamps, side module + equipment box + cable + floor socket),
// "compact" (one pedestal + leg frame, stacked-screen housing), "heavy" (pods at both ends, double housing: main screen + instrument
// bay). Side and rear are views of the same construction: the rear face carries grilles, hatch and loom, or a repeater screen.
SV.ws={};
SV.ws.build=(fr0,o)=>{const v=o.variant||"standard";const sd=o.seed||0;const lit=!!o.lit;const F=fr0.f,B=[-F[0],-F[1]];
  const pod=v==="compact"?0:Math.min(5.2,fr0.L*0.15);const podSides=v==="heavy"?[-1,1]:v==="standard"?[1]:[];
  const shrink=pod*podSides.length;const off=v==="standard"?-pod/2:0;
  const fr={cx:fr0.cx+fr0.a[0]*off,cy:fr0.cy+fr0.a[1]*off,a:fr0.a,f:F,L:fr0.L-shrink,D:fr0.D};const hL=fr.L/2,hD=fr.D/2;const frontVis=camAlong(F)>0;
  const mh=o.housingH||(v==="compact"?14.5:v==="heavy"?19.5:18.5);
  const podAt=sg=>{const s0=sg<0?-fr0.L/2:fr0.L/2-pod,s1=s0+pod;const pf={cx:fr0.cx,cy:fr0.cy,a:fr0.a,f:F,L:fr0.L,D:fr0.D};
    return sg>0||v==="heavy"?(sg>0?SV.small.instrumentPod:SV.small.serviceBox)(pf,s0+0.3,s1-0.3,-hD+0.6,hD-0.6,{seed:sd+sg,lit}):null};
  const ends=podSides.slice().sort((p,q)=>(p-q)*camAlong(fr0.a));
  for(const sg of ends)if(camAlong(fr0.a)*sg<0)podAt(sg);
  plinth(fr,-hL,hL,-hD,hD-0.6,1.1);
  if(v==="compact"){const pw=Math.min(6,fr.L*0.26);SV.ws._pedestal(fr,hL-pw,hL,hD,sd,1);
    for(const s of [-hL+0.6,-hL+2.2])prismX(frameRect(fr,s,s+0.9,hD-1.9,hD-1),1.1,7.7,CAL.gunHi,"#4a4d54",{lw:0.3,mat:false}); // leg frame
    prismX(frameRect(fr,-hL+0.6,-hL+3.1,-hD+0.6,-hD+1.5),1.1,7.7,CAL.gunHi,"#4a4d54",{lw:0.3,mat:false});prismX(frameRect(fr,-hL+0.6,hL-pw,-hD+0.4,-hD+1.6),5.6,6.4,CAL.gun,CAL.gunLo,{lw:0.3,mat:false})}
  else{const pw=Math.min(6.5,fr.L*0.24);SV.ws._modesty(fr,-hL+pw,hL-pw,hD,sd);for(const sg of [-1,1].sort((p,q)=>(p-q)*camAlong(fr.a)))SV.ws._pedestal(fr,sg<0?-hL:hL-pw,sg<0?-hL+pw:hL,hD,sd,sg)}
  prismX(frameCham(fr,-hL+0.2,hL-0.2,-hD+0.4,hD+0.3,1.1),7.7,8.6,CAL.gunHi,CAL.gunLo); // slab
  {const [a,b]=faces(fr,-hL+1.3,hL-1.3,-hD+0.4,hD+0.3).front;onFace(a,b,F,7.7,8.6,(W,H)=>{ctx.fillStyle=CAL.brass;ctx.fillRect(0,H*0.3,W,H*0.35);ctx.fillStyle="#2c1806";ctx.fillRect(W/2-3,H*0.18,6,H*0.62);ctx.fillStyle=CAL.amber;ctx.fillRect(W/2-2.6,H*0.28,5.2,H*0.4)})}
  const ww=Math.min(8,fr.L*0.27);
  const deck=()=>{for(const sg of [-1,1]){const s0=sg<0?-hL+0.4:hL-0.4-ww,s1=s0+ww;prismX(frameCham(fr,s0,s1,-hD+2.9,hD+0.1,0.9),8.6,9.6,CAL.gunHi,CAL.gun,{lw:0.35,mat:false}); // raised control wings
      prismX(frameCham(fr,sg<0?s0:s1-1.6,sg<0?s0+1.6:s1,-hD+2.9,hD+0.1,0.5),9.6,10.6,"#4a4d54",CAL.gunLo,{lw:0.3,mat:false}); // shoulder block
      onTop(fr,sg<0?s0+1.6:s0,sg<0?s1:s1-1.6,-hD+2.9,hD+0.1,9.62,(W,Dd)=>{dRecess(0.4,0.5,W-0.8,Dd-1,"#1f2125");
        if(sg<0){dToggles(0.8,0.9,Math.max(2,Math.floor((W-1.6)/1.3)));dButtons(0.8,Dd-2.4,3,1,0.95,sd);dAmber(W-2,Dd-2.1,1.1,0.6)}
        else{dTrackball(W*0.6,Dd*0.55,Math.min(1.2,Dd*0.22));dKnob(1.5,1.5,0.55);dKnob(1.5,Dd-1.7,0.55);dButtons(W-2.1,0.8,1,3,0.95,sd+3)}})}
    onTop(fr,-hL+0.4+ww,hL-0.4-ww,-hD+2.9,hD+0.1,8.62,(W,Dd)=>{dRecess(0.4,0.5,W-0.8,Dd-1,"#17181b");const kw=Math.min(W-2,11);dKeys(W/2-kw/2,Dd*0.38,kw,Math.min(2.4,Dd*0.4));ctx.fillStyle="#0f3640";ctx.fillRect(W/2-1.5,0.9,3,0.8)});
    for(const sg of [-1,1]){const s=sg*Math.min(6,hL*0.4);prismX(frameRect(fr,s-1.1,s+1.1,-hD+2.8,-hD+3.6),8.6,10.6,CAL.gunHi,CAL.gunLo,{lw:0.3,mat:false})}}; // hinge brackets
  const housing=()=>{prismX(frameCham(fr,-hL+0.6,hL-0.6,-hD+0.4,-hD+2.8,0.8),8.6,mh,CAL.gun,CAL.gunLo);
    prismX(frameRect(fr,-hL+1.4,hL-1.4,-hD+0.6,-hD+2.6),mh,mh+0.9,CAL.gunHi,CAL.gunLo,{hi:false,mat:false}); // crown
    for(const sg of [-1,1]){const s=sg*(hL-3.4);prismX(frameCham(fr,s-2,s+2,-hD+0.2,-hD+3.1,0.6),mh+0.9,mh+2.2,CAL.gunHi,CAL.gun,{lw:0.35,mat:false})} // top clamps
    const fc=faces(fr,-hL+1.4,hL-1.4,-hD+0.4,-hD+2.8);
    const shown=onFace(fc.front[0],fc.front[1],F,8.6,mh,(W,H)=>{
      if(v==="heavy"){const sw=W*0.62;for(const x0 of [0.5,sw+0.3]){dRecess(x0,1.1,1.6,H-3.4,"#1d1f23");dLampCol(x0+0.4,1.7,Math.max(1,Math.floor((H-4.2)/1.25)))}
        dScreenModule(3.4,1.6,sw-4.4,H-4,lit,o.content,"info");const gx=sw+2.6,gw=W-gx-0.8;dRecess(gx,1,gw,H-3.2,"#1d1f23");dScreenModule(gx+1.6,2.2,gw-3.2,(H-4)*0.36,lit,null,"status");
        const r=Math.min(1.1,gw/6);dGauge(gx+gw*0.3,H*0.58,r);dGauge(gx+gw*0.7,H*0.58,r);dButtons(gx+1,H-4.6,Math.max(2,Math.floor((gw-2)/0.95)),1,0.9,sd)}
      else if(v==="compact"){const sideW=W>16?3.2:0;dScreenModule(1.4+sideW,1.6,W-2.8-sideW*2,H-4,lit,o.content,"info");
        if(sideW)for(const x0 of [0.9,W-sideW-0.5]){dScreenModule(x0+0.5,1.6,sideW-1.4,(H-4.8)/2,lit,null,"instrument");dScreenModule(x0+0.5,1.6+(H-4.8)/2+1.2,sideW-1.4,(H-4.8)/2,lit,null,"status")}}
      else{const lc=2.2;for(const x0 of [0.5,W-lc+0.1]){dRecess(x0,1.1,lc-0.6,H-3.4,"#1d1f23");dLampCol(x0+0.25,1.7,Math.max(1,Math.floor((H-4.2)/1.25)))}dScreenModule(lc+1.6,1.6,W-2*lc-3.2,H-4,lit,o.content,"info")}
      ctx.fillStyle="#24262b";ctx.fillRect(0,H-1.6,W,1.6);dAmber(0.5,H-1.15,0.9,0.5);dAmber(W-1.4,H-1.15,0.9,0.5);if(o.plate)dPlate(W/2-6.5,H-1.5,13,1.3,o.plate);dWear(W,H,sd+7)});
    onFace(fc.back[0],fc.back[1],B,8.6,mh,(W,H)=>{
      if(!shown&&o.content){dGrille(0.8,1.2,2.4,H-3.6);dGrille(W-3.2,1.2,2.4,H-3.6);dScreenModule(5,1.6,W-10,H-4,lit,o.content,"info");ctx.fillStyle="#24262b";ctx.fillRect(0,H-1.6,W,1.6);dAmber(W/2-0.5,H-1.15,1,0.5)} // rear repeater
      else{const gw=Math.min(9,W*0.3);dGrille(1.4,1.2,gw,H*0.5);dGrille(W-1.4-gw,1.2,gw,H*0.5);dHatch(W/2-3,0.9,6,H*0.58);dAmber(W/2-1,1.7,2,0.5);dLoom(1,W-1,H*0.7,0.6);if(o.plate)dPlate(W/2-6.5,H-1.8,13,1.3,o.plate)}
      dRivets(0.2,0.2,W-0.4,H-0.4);dWear(W,H,sd+9)});
    for(const k of ["e1","e2"]){const [c,d,n]=fc[k];onFace(c,d,n,8.6,mh,(W,H)=>{dAmber(W/2-0.5,1.5,1,0.5);dAmber(W/2-0.5,3,1,0.5);dHatch(0.4,H*0.42,W-0.8,H*0.45);dVents(0.9,H*0.5,W-1.8,H*0.28,3)})}
    return shown};
  let shown;if(frontVis){shown=housing();deck()}else{deck();shown=housing()}
  for(const sg of ends)if(camAlong(fr0.a)*sg>=0)podAt(sg);
  return shown};
SV.ws._pedestal=(fr,s0,s1,hD,sd,sg)=>{const F=fr.f;prismX(frameRect(fr,s0,s1,-hD+0.4,hD-0.8),1.1,7.7,CAL.gun,CAL.gun);const fc=faces(fr,s0,s1,-hD+0.4,hD-0.8);
  onFace(fc.front[0],fc.front[1],F,1.1,7.7,(W,H)=>{dRecess(1.1,0.5,W-2.2,H*0.28,"#2b2d32");dSlotLamp(W/2-1.2,H*0.13,2.4);dRecess(1.1,H*0.36,W-2.2,H*0.56,"#2b2d32");dVents(1.7,H*0.42,W-3.4,H*0.22,3);dSlotLamp(W/2-1.4,H*0.78,2.8);dRivets(0,0,W,H);dWear(W,H,sd+sg+2)});
  const e=sg<0?fc.e1:fc.e2;onFace(e[0],e[1],e[2],1.1,7.7,(W,H)=>{dRecess(0.6,0.6,W-1.2,H-1.4,"#30333a");dVents(1.2,1.1,W-2.4,H*0.4,4);dAmber(W*0.3,H*0.68,W*0.4,0.5);dWear(W,H,sd+5)});
  for(const cs of [s0,s1-0.9])prismX(frameRect(fr,cs,cs+0.9,hD-1.7,hD-0.8),1.1,7.9,CAL.gunHi,"#4a4d54",{lw:0.35,mat:false})}; // corner posts
SV.ws._modesty=(fr,s0,s1,hD,sd)=>{prismX(frameRect(fr,s0,s1,-hD+0.4,-hD+2.6),1.1,7.7,CAL.gunLo,"#202226");const [a,b]=faces(fr,s0,s1,-hD+0.4,-hD+2.6).front;
  onFace(a,b,fr.f,1.1,7.7,(W,H)=>{dRecess(0.8,0.6,W-1.6,H-1.4,"#1c1d21");dHatch(W/2-3,H*0.1,6,H*0.4);dSlotLamp(W/2-2.5,H*0.58,5);dLoom(0.6,W-0.6,H*0.72,0.5)})};
// ================================================================ CONSOLE family
// A bank module of 1-3 bays (single / double / wide). Full-height dividers split the bays and every bay carries UNLIKE kit
// (screen, stack, instrument, switch, readout), so a long bank never reads as one repeated motif. Each bay: its own cabinet
// door with a slot lamp, its own control strip on the slab, its own chamfered upper housing; one continuous crown on top.
SV.con={};
SV.con.KITS=["screen","instrument","stack","switch","readout"];
SV.con.bank=(fr,o)=>{const {L,D}=fr;const hL=L/2,hD=D/2;const n=Math.max(1,o.bays||1);const sd=o.seed||0;const lit=!!o.lit;const F=fr.f;const mh=o.housingH||15.5;const bw=L/n;
  const kits=o.kits||Array.from({length:n},(_,i)=>SV.con.KITS[(sd+i*2)%SV.con.KITS.length]);
  plinth(fr,-hL+0.2,hL-0.2,-hD+0.2,hD-0.6,1.1);
  prismX(frameRect(fr,-hL+0.4,hL-0.4,-hD+0.4,hD-0.9),1.1,7.7,CAL.gun,CAL.gun);
  {const [a,b]=faces(fr,-hL+0.4,hL-0.4,-hD+0.4,hD-0.9).front;onFace(a,b,F,1.1,7.7,(W,H)=>{const pw=W/n;
    for(let i=0;i<n;i++){const x=i*pw;if(kits[i]==="readout"||kits[i]==="switch"){dLouvrePair(x+0.9,0.9,pw-1.8,H*0.4)}else{dRecess(x+0.7,0.7,pw-1.4,H*0.48,"#2b2d32");dSlotLamp(x+pw/2-1.4,H*0.3,2.8)}
      dRecess(x+0.7,H*0.6,pw-1.4,H*0.27);dSlotLamp(x+pw/2-1.2,H*0.7,2.4);ctx.fillStyle="#141517";ctx.fillRect(x,0,0.4,H)}ctx.fillStyle="#1a1b1e";ctx.fillRect(0,H-1.1,W,1.1);dRivets(0,0,W,H);dWear(W,H,sd+11)})}
  prismX(frameCham(fr,-hL+0.2,hL-0.2,-hD+0.4,hD+0.3,1.1),7.7,8.6,CAL.gunHi,CAL.gunLo);
  {const [a,b]=faces(fr,-hL+1.3,hL-1.3,-hD+0.4,hD+0.3).front;onFace(a,b,F,7.7,8.6,(W,H)=>{ctx.fillStyle=CAL.brass;ctx.fillRect(0,H*0.3,W,H*0.35)})}
  const strip=()=>onTop(fr,-hL+0.6,hL-0.6,hD-3.6,hD,8.62,(W,Dd)=>{const pw=W/n;for(let i=0;i<n;i++){const x=i*pw;dRecess(x+0.4,0.4,pw-0.8,Dd-0.8,"#1d1f23");const k=kits[i];
      if(k==="switch")dSwitchMatrix(x+1,0.8,Math.max(3,Math.floor((pw-2)/0.95)),2,0.95,sd+i);
      else if(k==="instrument"){dKnob(x+1.8,Dd/2,0.6);dKnob(x+3.6,Dd/2,0.6);dButtons(x+pw-4.4,0.8,3,2,0.9,sd+i)}
      else{const kw=Math.min(6,pw*0.45);dKeys(x+pw/2-kw/2,0.8,kw,Math.min(2,Dd-1.4));dButtons(x+0.9,0.8,2,2,0.8,sd+i);dButtons(x+pw-2.6,0.8,2,2,0.8,sd+i+4)}}});
  const upper=()=>{for(let i=0;i<n;i++){const s0=-hL+0.6+i*bw,s1=s0+bw-(i<n-1?0:1.2);const hh=mh-(kits[i]==="switch"?2:kits[i]==="readout"?1:0);
      prismX(frameCham(fr,s0+0.4,s1-0.4,-hD+0.4,-hD+2.8,0.7),8.6,hh,CAL.gun,CAL.gunLo);const fc=faces(fr,s0+0.8,s1-0.8,-hD+0.4,-hD+2.8);
      onFace(fc.front[0],fc.front[1],F,8.6,hh,(W,H)=>{const k=kits[i];
        if(k==="screen")dScreenBay(0.4,1.6,W-0.8,H-4,lit,null,"tactical");
        else if(k==="stack"){const sw=W*0.62;dScreenBay(0.4,1.6,sw,H-4,lit,null,"info");const x0=sw+1.4;dScreenModule(x0,1.6,W-x0-1.2,(H-5)/2,lit,null,"instrument");dScreenModule(x0,1.6+(H-5)/2+1.4,W-x0-1.2,(H-5)/2,lit,null,"status")}
        else if(k==="instrument"){const r=Math.min(1.5,(H-5)/3.4);const m=Math.max(1,Math.floor((W-2)/(2*r+1.6)));for(let j=0;j<m;j++)dGauge(1.4+r+j*(2*r+1.6),1.6+r,r);dScreenModule(1.4,H*0.55,W-2.8,H*0.22,lit,null,"status")}
        else if(k==="switch"){dSwitchMatrix(1.2,1.2,Math.max(3,Math.floor((W-2.4)/1.2)),Math.max(2,Math.floor((H-4)/1.2)),1.2,sd+i)}
        else{dScreenModule(1.4,1.6,W-2.8,(H-4)*0.5,lit,null,"multi");dLampPips(1.4,H*0.62,1);for(let j=0;j<Math.floor((W-4)/1.3);j++)dIndicator(3+j*1.3,H*0.64,(j+sd)%4===0)}
        ctx.fillStyle="#24262b";ctx.fillRect(0,H-1.6,W,1.6);dAmber(0.5,H-1.15,0.9,0.5);dWear(W,H,sd+i)});
      const bk=faces(fr,s0+0.8,s1-0.8,-hD+0.4,-hD+2.8).back;onFace(bk[0],bk[1],bk[2],8.6,hh,(W,H)=>{dGrille(1,1,W-2,H*0.45);dLoom(0.6,W-0.6,H*0.68,0.5);dRivets(0,0,W,H)});
      for(const kk of ["e1","e2"]){const e=fc[kk];onFace(e[0],e[1],e[2],8.6,hh,(W,H)=>{dVents(0.5,H*0.4,W-1,H*0.3,3);dAmber(W/2-0.4,1.5,0.8,0.45)})}
      if(i<n-1){const s=s1-0.4;prismX(frameCham(fr,s-0.9,s+0.9,-hD+0.2,-hD+3.2,0.3),1.1,mh+0.6,"#4a4d54",CAL.gunLo,{lw:0.35}); // full-height bay divider
        const dv=faces(fr,s-0.9,s+0.9,-hD+0.2,-hD+3.2).front;onFace(dv[0],dv[1],F,1.1,mh+0.6,(W,H)=>{dLampPips(W/2-0.3,H*0.25,4,1.2);ctx.fillStyle=CAL.brass;ctx.beginPath();ctx.arc(W/2,H*0.85,0.3,0,TAU);ctx.fill()})}}
    prismX(frameRect(fr,-hL+1,hL-1,-hD+0.6,-hD+2.6),mh,mh+0.9,CAL.gunHi,CAL.gunLo,{hi:false,mat:false}); // continuous crown
    for(let s=-hL+4;s<hL-3;s+=7.5)prismX(frameRect(fr,s-0.7,s+0.7,-hD+0.8,-hD+2.2),mh+0.9,mh+1.6,"#4a4d54",CAL.gunLo,{lw:0.3,hi:false,mat:false})}; // crown brackets
  if(camAlong(F)>0){upper();strip()}else{strip();upper()}};
// ================================================================ EQUIPMENT family
SV.eq={};
// EQ-rack: countable blade units in a frame (reveal between blades, each blade lit-to-dark, stack falls off down its height),
// two columns, a chamfered cap wider than the body, a vented plinth with feet. LEDs are the smallest thing on it
SV.eq.rack=(fr,o={})=>{const hL=fr.L/2,hD=fr.D/2,H=o.h||20.5,sd=o.seed||0;feet(fr,-hL,hL,-hD,hD,1);prismX(frameCham(fr,-hL+0.3,hL-0.3,-hD+0.3,hD-0.3,0.5),1,2.2,"#2a2c31","#1d1f23",{lw:0.35,mat:false});
  prismX(frameCham(fr,-hL+0.5,hL-0.5,-hD+0.5,hD-0.5,0.6),2.2,H,CAL.gunHi,CAL.gun);prismX(frameCham(fr,-hL,hL,-hD,hD,0.8),H,H+1.4,CAL.gunHi,CAL.gunLo); // cap proud of the body
  onTop(fr,-hL+0.6,hL-0.6,-hD+0.6,hD-0.6,H+1.42,(W,Dd)=>{for(let k=0.8;k<Dd-0.5;k+=0.9){ctx.fillStyle="#1b1d20";ctx.fillRect(0.6,k,W-1.2,0.45)}});
  const fc=faces(fr,-hL+0.5,hL-0.5,-hD+0.5,hD-0.5);
  for(const k of ["front","back","e1","e2"]){const [a,b,n]=fc[k];onFace(a,b,n,2.2,H,(W,HH)=>{const front=k==="front"||k==="back";ctx.fillStyle="#141517";ctx.fillRect(0.5,0.5,W-1,HH-1);
    const nb=Math.max(4,Math.floor((HH-2)/2.9));const cw=front?[W*0.6,W*0.4]:[W];let x=0.8;
    for(const w of cw){for(let j=0;j<nb;j++){const y=1+j*(HH-2)/nb,bh=(HH-2)/nb-0.5;const dark=j/nb*0.25;ctx.fillStyle=`rgb(${48-dark*60|0},${51-dark*60|0},${57-dark*60|0})`;ctx.fillRect(x,y,w-1.6,bh);
        ctx.fillStyle="rgba(255,240,215,.14)";ctx.fillRect(x,y,w-1.6,0.22);ctx.fillStyle="#0e0f11";ctx.fillRect(x+0.6,y+bh*0.3,(w-1.6)*0.45,bh*0.4);
        if(front){dIndicator(x+w-3,y+bh*0.35,(j+sd)%3!==1);ctx.fillStyle=(j+sd)%5===0?CAL.amber:"#3a6f7a";ctx.fillRect(x+w-4.2,y+bh*0.35,0.55,0.35)}}x+=w}
    ctx.fillStyle="#4a4d54";ctx.fillRect(0,0,0.6,HH);ctx.fillRect(W-0.6,0,0.6,HH);dWear(W,HH,sd+k.length)})}};
// EQ-relay: an OPEN patch frame of contact combs you can see through, uprights on brass feet, one patch lead hanging off it
SV.eq.relay=(fr,o={})=>{const hL=fr.L/2,hD=fr.D/2,H=o.h||20,sd=o.seed||0;for(const s of [-hL+0.4,hL-1.6])for(const d of [-hD+0.4,hD-1.6])prismX(frameRect(fr,s,s+1.2,d,d+1.2),0,1.2,CAL.brass,CAL.brass,{hi:false,mat:false});
  prismX(frameRect(fr,-hL+0.6,hL-0.6,-0.6,0.6),1.2,H,"#26282c","#1a1b1e",{lw:0.3,mat:false}); // back spine
  const comb=(j)=>{const h0=2.4+j*(H-4)/5;prismX(frameRect(fr,-hL+1.2,hL-1.2,-hD+1.2,hD-1.2),h0,h0+1.6,"#3a3d43","#2c2e33",{lw:0.3,mat:false,shadow:false});
    for(const k of ["front","back"]){const [a,b,n]=faces(fr,-hL+1.2,hL-1.2,-hD+1.2,hD-1.2)[k];onFace(a,b,n,h0,h0+1.6,(W,HH)=>{ctx.fillStyle="#0e0f11";ctx.fillRect(0.4,0.3,W-0.8,HH-0.6);ctx.fillStyle=CAL.brassHi;for(let x=0.9;x<W-0.6;x+=0.75)ctx.fillRect(x,0.45,0.32,HH-0.9);dIndicator(W-1.4,0.5,(j+sd)%2===0)})}};
  const ups=[[-hL+0.4,-hD+0.4],[hL-1.6,-hD+0.4],[-hL+0.4,hD-1.6],[hL-1.6,hD-1.6]].sort((p,q)=>V.depth(...[fr.cx+fr.a[0]*p[0]+fr.f[0]*p[1],fr.cy+fr.a[1]*p[0]+fr.f[1]*p[1]])-V.depth(...[fr.cx+fr.a[0]*q[0]+fr.f[0]*q[1],fr.cy+fr.a[1]*q[0]+fr.f[1]*q[1]]));
  for(const [s,d] of ups.slice(0,2))prismX(frameRect(fr,s,s+1.2,d,d+1.2),1.2,H,CAL.gunHi,"#4a4d54",{lw:0.35,mat:false});
  for(let j=0;j<5;j++)comb(j);
  for(const [s,d] of ups.slice(2))prismX(frameRect(fr,s,s+1.2,d,d+1.2),1.2,H,CAL.gunHi,"#4a4d54",{lw:0.35,mat:false});
  prismX(frameCham(fr,-hL,hL,-hD,hD,0.7),H,H+1.3,"#45484f",CAL.gunLo,{mat:false});capTop(fr,-hL,hL,-hD,hD,H+1.3,sd);
  const p=[fr.cx+fr.a[0]*(hL-1)+fr.f[0]*(hD-0.4),fr.cy+fr.a[1]*(hL-1)+fr.f[1]*(hD-0.4)];cable3([p[0],p[1],H*0.72],[p[0]-fr.a[0]*3,p[1]-fr.a[1]*3,H*0.38],3.2,"#a8402e",0.45)}; // the one patch lead
// EQ-bay: lid of three plates, three bays (louvre pair | control panel with slot lamps, dial and lamp row | louvre pair),
// corner posts, kick slot lamps, plinth
SV.eq.bay=(fr,o={})=>{const hL=fr.L/2,hD=fr.D/2,TOP=o.h||10,sd=o.seed||0;plinth(fr,-hL,hL,-hD,hD,1);
  prismX(frameCham(fr,-hL,hL,-hD,hD,0.6),1,TOP-1,CAL.gun,CAL.gun);
  for(const k of ["front","back"]){const [a,b,n]=faces(fr,-hL,hL,-hD,hD)[k];onFace(a,b,n,1,TOP-1,(W,H)=>{const bw=W/3;
    for(let i=0;i<3;i++){const x=i*bw;ctx.fillStyle="#141517";ctx.fillRect(x,0,0.45,H);
      if(i===1){dRecess(x+0.8,0.8,bw-1.6,H*0.5,"#23252a");dSlotLamp(x+1.4,1.6,bw*0.35);dKnob(x+bw-2.2,2.2,0.75);dLampPips(x+1.4,H*0.36,1);for(let j=0;j<3;j++)dAmber(x+2.6+j*1.4,H*0.38,0.8,0.45)}
      else dLouvrePair(x+1,1,bw-2,H*0.48);
      dRecess(x+0.8,H*0.62,bw-1.6,H*0.26,"#26282c");dSlotLamp(x+bw/2-1.3,H*0.71,2.6)}dRivets(0,0,W,H);dWear(W,H,sd+k.length)})}
  for(const k of ["e1","e2"]){const [a,b,n]=faces(fr,-hL,hL,-hD,hD)[k];onFace(a,b,n,1,TOP-1,(W,H)=>{dLouvrePair(0.8,0.9,W-1.6,H*0.4);dRecess(0.8,H*0.6,W-1.6,H*0.28);dWear(W,H,sd+3)})}
  for(const s of [-hL,hL-1])for(const d of [-hD,hD-1])prismX(frameRect(fr,s,s+1,d,d+1),1,TOP-0.6,CAL.gunHi,"#4a4d54",{lw:0.3,mat:false,shadow:false}); // corner posts
  const lw=fr.L/3;for(let i=0;i<3;i++){const s0=-hL+i*lw+0.15,s1=-hL+(i+1)*lw-0.15;prismX(frameCham(fr,s0,s1,-hD-0.2,hD+0.2,0.5),TOP-1,TOP,"#45484f",CAL.gunLo,{lw:0.35,mat:false});
    onTop(fr,s0,s1,-hD-0.2,hD+0.2,TOP+0.02,(W,Dd)=>{ctx.fillStyle="rgba(255,240,215,.08)";ctx.fillRect(0.3,0.3,W-0.6,0.3);dRivets(0.2,0.2,W-0.4,Dd-0.4,"#8a7448");dWear(W,Dd,sd+i)})}}; // three-plate lid
// EQ-service: a tall narrow cabinet; tone "red" (hazard service) or "olive"/"steel" (utility); plinth, hood, hinged door, side detail
SV.eq.service=(fr,o={})=>{const hL=fr.L/2,hD=fr.D/2,H=o.h||13.6,sd=o.seed||0;const tone=o.tone||"red";const body=tone==="olive"?[CAL.oliveHi,CAL.olive]:tone==="steel"?[CAL.steelHi,CAL.steel]:["#4a4c52",CAL.gun];
  plinth(fr,-hL,hL,-hD,hD,0.8);prismX(frameCham(fr,-hL,hL,-hD,hD,0.7),0.8,H,body[0],body[1]);prismX(frameCham(fr,-hL-0.3,hL+0.3,-hD-0.3,hD+0.1,0.8),H,H+1,"#45484f",CAL.gunLo,{mat:false});capTop(fr,-hL-0.3,hL+0.3,-hD-0.3,hD+0.1,H+1,sd);
  const fc=faces(fr,-hL,hL,-hD,hD);onFace(fc.front[0],fc.front[1],fr.f,0.8,H,(W,HH)=>{
    if(tone==="red"){ctx.fillStyle=CAL.rust;ctx.fillRect(0.9,1,W-1.8,HH-2.2);ctx.strokeStyle=CAL.out;ctx.lineWidth=0.3;ctx.strokeRect(0.9,1,W-1.8,HH-2.2);ctx.fillStyle="rgba(0,0,0,.25)";ctx.fillRect(1.4,HH*0.55,W-2.8,0.25);
      ctx.fillStyle=CAL.yellow;ctx.beginPath();ctx.moveTo(W/2,HH*0.18);ctx.lineTo(W/2+1.6,HH*0.18+2.6);ctx.lineTo(W/2-1.6,HH*0.18+2.6);ctx.closePath();ctx.fill();ctx.fillStyle="#1a1a1a";ctx.fillRect(W/2-0.15,HH*0.18+0.9,0.3,1);dVents(1.6,HH-4.6,W-3.2,2.4,3)}
    else{dRecess(0.9,1,W-1.8,HH-2.2,tone==="olive"?CAL.oliveLo:CAL.steelLo);dScreenModule(1.9,2,W-3.8,HH*0.18,false,null,"status");dKnob(2.4,HH*0.42,0.55);dButtons(3.6,HH*0.4,2,1,0.9,sd);for(let j=0;j<3;j++)ctx.fillStyle="#2e3036",ctx.fillRect(2,HH*0.62+j*0.9,W-4,0.45)}
    ctx.fillStyle="#a6acb3";ctx.fillRect(W-2.2,HH*0.45,0.6,2.2);dHinges(0.5,1,HH-2);dRivets(0,0,W,HH);dWear(W,HH,sd)});
  for(const k of ["e1","e2","back"]){const [a,b,n]=fc[k];onFace(a,b,n,0.8,H,(W,HH)=>{dRecess(0.6,0.8,W-1.2,HH-1.6,tone==="red"?"#3a3c41":body[1]);dVents(1.1,1.4,W-2.2,HH*0.3,4);dPlate(W/2-1.6,HH*0.5,3.2,0.8,null);dConduit(W-1.6,HH*0.6,HH-0.4,0.9);dWear(W,HH,sd+2)})}};
// EQ-storage: a double-door locker (olive steel, verticals: louvre head + full-height handle per door) or a drawer bank on feet
SV.eq.locker=(fr,o={})=>{const hL=fr.L/2,hD=fr.D/2,H=o.h||18.4,sd=o.seed||0;plinth(fr,-hL,hL,-hD,hD,0.9);prismX(frameCham(fr,-hL,hL,-hD,hD,0.8),0.9,H,CAL.oliveHi,CAL.olive);
  prismX(frameCham(fr,-hL-0.3,hL+0.3,-hD-0.2,hD+0.3,0.9),H,H+1,"#45484f",CAL.gunLo,{mat:false});capTop(fr,-hL-0.3,hL+0.3,-hD-0.2,hD+0.3,H+1,sd);
  const fc=faces(fr,-hL,hL,-hD,hD);onFace(fc.front[0],fc.front[1],fr.f,0.9,H,(W,HH)=>{ctx.fillStyle=CAL.oliveLo;ctx.fillRect(0.4,0.4,W-0.8,HH-0.8);
    for(const [x,r] of [[0.9,false],[W/2+0.2,true]]){const dw=W/2-1.1;dRaised(x,1.2,dw,HH-2.6,CAL.olive);for(let j=0;j<3;j++){ctx.fillStyle="#2a2d22";ctx.fillRect(x+dw*0.2,2+j*0.9,dw*0.6,0.45)}
      ctx.fillStyle="#2a2d22";ctx.fillRect(r?x+0.8:x+dw-1.6,HH*0.3,0.8,HH*0.4);ctx.fillStyle="#a6acb3";ctx.fillRect(r?x+0.95:x+dw-1.45,HH*0.33,0.5,HH*0.12);dHinges(r?x+dw-0.6:x,1.2,HH-2.6)}
    dRivets(0,0,W,HH,"#8a7448");dWear(W,HH,sd)});
  for(const k of ["e1","e2"]){const [a,b,n]=fc[k];onFace(a,b,n,0.9,H,(W,HH)=>{dRecess(0.6,0.8,W-1.2,HH-1.6,CAL.oliveLo);dVents(1.1,1.4,W-2.2,3,3);dWear(W,HH,sd+1)})}};
SV.eq.drawers=(fr,o={})=>{const hL=fr.L/2,hD=fr.D/2,H=o.h||8.6,sd=o.seed||0;feet(fr,-hL,hL,-hD,hD,1);prismX(frameCham(fr,-hL,hL,-hD,hD,0.6),1,H,CAL.gunHi,CAL.gun);
  prismX(frameCham(fr,-hL-0.2,hL+0.2,-hD-0.2,hD+0.2,0.7),H,H+0.8,"#45484f",CAL.gunLo,{mat:false});capTop(fr,-hL-0.2,hL+0.2,-hD-0.2,hD+0.2,H+0.8,sd);
  for(const k of ["front","back"]){const [a,b,n]=faces(fr,-hL,hL,-hD,hD)[k];onFace(a,b,n,1,H,(W,HH)=>{const cols=Math.max(2,Math.round(W/6));const cw=(W-1)/cols;
    for(let r=0;r<2;r++)for(let c=0;c<cols;c++){const x=0.5+c*cw,y=0.5+r*(HH-1)/2;dRaised(x+0.2,y+0.2,cw-0.4,(HH-1)/2-0.4,"#33363c");dSlotLamp(x+cw/2-1.1,y+(HH-1)/4-0.3,2.2)}dWear(W,HH,sd+k.length)})}};
// ================================================================ CHAIR family
// standard: 5-star brass base on casters, gas column with lift lever, seat pan + cushion, armrests on posts with brass caps,
// two-cushion back on a chamfered shell, headrest on brass posts (left off when occupied so the head reads).
// operator: standard + armrest control pads. command: wide, high, quilted, armrest consoles, command-red seam.
SV.chair={};
SV.chair.build=(x,y,h0,u,o={})=>{const fr={cx:x,cy:y,a:[-u[1],u[0]],f:u};const v=o.variant||"standard";const W2=v==="command"?3.7:2.8;
  const back=frameCham(fr,-W2,W2,-3.9-(v==="command"?0.9:0),-3.4,0.5);
  const base=()=>{ell(x,y,3.4,h0+0.02,"rgba(0,0,0,.34)");
    for(let k=0;k<5;k++){const a=k*TAU/5+0.3;const ex=x+2.9*Math.cos(a),ey=y+2.9*Math.sin(a);line3([x,y,h0+0.9],[ex,ey,h0+0.55],"#121316",0.95);line3([x,y,h0+1.0],[ex,ey,h0+0.65],CAL.brass,0.4);
      ell(ex,ey,0.45,h0+0.3,"#141518");const p=V.P(ex,ey,h0+0.55);ctx.fillStyle=CAL.brassHi;ctx.fillRect(p[0]-0.2,p[1]-0.2,0.4,0.4)}
    cyl(x,y,0.75,h0+0.9,h0+1.6,"#2a2c31","#1d1f23",{n:8});cyl(x,y,0.5,h0+1.6,h0+3.0,null,CAL.brass,{n:8});
    prismX(frameRect(fr,-1.2,1.2,-1,1),h0+3.0,h0+3.4,"#2a2c31",CAL.gunLo,{lw:0.3,hi:false,mat:false});line3([x+fr.a[0]*1.2,y+fr.a[1]*1.2,h0+3.2],[x+fr.a[0]*2.3+u[0]*0.8,y+fr.a[1]*2.3+u[1]*0.8,h0+3.0],"#9aa1a9",0.3)};
  const seat=()=>{const lc=v==="command"?["#4a3a40","#36272d"]:[CAL.leatherHi,CAL.leather];
    prismX(frameCham(fr,-W2,W2,-2.7,2.5,0.7),h0+3.4,h0+3.8,CAL.gunLo,"#1d1f23",{lw:0.3,mat:false});prismX(frameCham(fr,-W2+0.2,W2-0.2,-2.5,2.3,0.8),h0+3.8,h0+4.9,lc[0],lc[1],{mat:false});
    onTop(fr,-W2+0.2,W2-0.2,-2.5,2.3,h0+4.92,(W,Dd)=>{ctx.strokeStyle="rgba(0,0,0,.35)";ctx.lineWidth=0.2;ctx.strokeRect(0.6,0.6,W-1.2,Dd-1.2)});
    for(const sgn of [-1,1]){const ax=sgn*(W2+0.15);if(v==="command"){prismX(frameRect(fr,ax-0.8,ax+0.8,-2.6,2.6),h0+3.6,h0+7.4,CAL.gunHi,CAL.gun,{lw:0.35,mat:false});onTop(fr,ax-0.8,ax+0.8,-2.6,2.6,h0+7.42,(W,Dd)=>{dButtons(0.2,Dd*0.45,1,2,0.9,sgn>0?2:5);dAmber(0.4,0.6,0.8,0.45)});continue}
      for(const d of [-0.6,0.9])prismX(frameRect(fr,ax-0.3,ax+0.3,d-0.3,d+0.3),h0+3.6,h0+6.3,CAL.brass,"#8a6a36",{lw:0.25,hi:false,mat:false});
      prismX(frameCham(fr,ax-0.55,ax+0.55,-2.2,1.6,0.3),h0+6.3,h0+7.0,lc[0],lc[1],{lw:0.3,mat:false});prismX(frameRect(fr,ax-0.6,ax+0.6,1.3,1.8),h0+6.2,h0+7.1,CAL.brassHi,CAL.brass,{lw:0.25,hi:false,mat:false});
      if(v==="operator")onTop(fr,ax-0.55,ax+0.55,-1.2,1.2,h0+7.02,(W,Dd)=>{dButtons(0.1,0.3,1,2,0.9,sgn>0?1:4)})}};
  const backPart=()=>{const hb=v==="command"?h0+16:h0+10.4;const lc=v==="command"?["#4a3a40","#36272d"]:[CAL.leatherHi,CAL.leather];
    prismX(back,h0+4.6,hb,"#2a2c31","#202227",{lw:0.3,mat:false});
    if(v==="command")prismX(frameCham(fr,-W2+0.3,W2-0.3,-4.4,-3.3,0.5),h0+5,hb,lc[0],lc[1],{mat:false});
    else{prismX(frameCham(fr,-2.5,2.5,-3.5,-2.6,0.5),h0+4.9,h0+7.6,lc[0],lc[1],{mat:false});prismX(frameCham(fr,-2.5,2.5,-3.5,-2.7,0.5),h0+7.8,hb,lc[0],lc[1],{mat:false})}
    {const r=frameRect(fr,-W2,W2,-3.9-(v==="command"?0.9:0),-3.4);onFace(r[1],r[0],[-u[0],-u[1]],h0+4.6,hb,(W,H)=>{ctx.fillStyle="#30343c";chamRect(0.6,0.5,W-1.2,H-1.1,0.8);ctx.fill();ctx.strokeStyle=CAL.brass;ctx.lineWidth=0.28;chamRect(0.35,0.3,W-0.7,H-0.6,0.9);ctx.stroke();
      ctx.strokeStyle="rgba(0,0,0,.5)";ctx.lineWidth=0.2;for(const vv of [H*0.3,H*0.72]){ctx.beginPath();ctx.moveTo(W*0.3,vv);ctx.lineTo(W*0.7,vv);ctx.stroke()}if(v==="command"){ctx.fillStyle=CAL.red;ctx.fillRect(0.6,0.4,W-1.2,0.45)}})}
    onFace(back[6],back[3],u,h0+4.9,hb,(W,H)=>{ctx.strokeStyle="rgba(0,0,0,.4)";ctx.lineWidth=0.25;for(let k=1;k<(v==="command"?5:2);k++){ctx.beginPath();ctx.moveTo(0.5,H*k/(v==="command"?5:2));ctx.lineTo(W-0.5,H*k/(v==="command"?5:2));ctx.stroke()}ctx.fillStyle=v==="command"?CAL.red:CAL.brass;ctx.fillRect(0,v==="command"?0:H-0.5,W,0.4)});
    if(!o.occupied&&v!=="command"){for(const sgn of [-1,1])line3([x+fr.a[0]*sgn-u[0]*3.3,y+fr.a[1]*sgn-u[1]*3.3,hb],[x+fr.a[0]*sgn-u[0]*3.3,y+fr.a[1]*sgn-u[1]*3.3,hb+0.8],CAL.brass,0.35);
      prismX(frameCham(fr,-1.8,1.8,-3.7,-2.9,0.4),hb+0.8,hb+2.1,lc[0],lc[1],{lw:0.3,mat:false})}
    if(v==="command")prismX(frameCham(fr,-2.4,2.4,-4.8,-3.1,0.4),hb,hb+2.2,lc[0],lc[1],{mat:false})};
  return{fr,back,base,seat,backPart,top:v==="command"?h0+18:h0+12.6}};
// ================================================================ SMALL TECHNICAL PROPS
SV.small={};
// instrument pod: a small floor-standing module (status screen, buttons, lamp) with a cable into a deck socket
SV.small.instrumentPod=(fr,s0,s1,d0,d1,o={})=>{const H=o.h||11;prismX(frameCham(fr,s0,s1,d0,d1,0.5),0,H,CAL.gunHi,CAL.gun);prismX(frameCham(fr,s0-0.2,s1+0.2,d0-0.2,d1+0.2,0.6),H,H+0.8,"#45484f",CAL.gunLo,{mat:false});capTop(fr,s0-0.2,s1+0.2,d0-0.2,d1+0.2,H+0.8,o.seed);
  const fc=faces(fr,s0,s1,d0,d1);onFace(fc.front[0],fc.front[1],fr.f,0,H,(W,HH)=>{dScreenModule(1.2,1.4,W-2.4,HH*0.24,!!o.lit,null,"status");dButtons(0.9,HH*0.47,Math.max(2,Math.floor((W-1.8)/0.9)),2,0.9,o.seed||0);dSlotLamp(W/2-1,HH*0.78,2);dWear(W,HH,o.seed||1)});
  for(const k of ["e1","e2","back"]){const [a,b,n]=fc[k];onFace(a,b,n,0,H,(W,HH)=>{dVents(0.6,1,W-1.2,HH*0.3,3);dRecess(0.6,HH*0.5,W-1.2,HH*0.35);dLampPips(W/2-0.3,HH*0.58,2)})}
  const p=[fr.cx+fr.a[0]*(s0+s1)/2+fr.f[0]*d1,fr.cy+fr.a[1]*(s0+s1)/2+fr.f[1]*d1];cable3([p[0],p[1],2.4],[p[0]+fr.f[0]*1.3,p[1]+fr.f[1]*1.3,0.7],0.6,"#16171a",0.5);socket3(p[0]+fr.f[0]*1.4,p[1]+fr.f[1]*1.4)};
// service box: a low equipment box (grille, hatch, slot lamp) at the end of a workstation
SV.small.serviceBox=(fr,s0,s1,d0,d1,o={})=>{const H=o.h||7.6;prismX(frameCham(fr,s0,s1,d0,d1,0.5),0,H,CAL.gunHi,CAL.gun);prismX(frameCham(fr,s0-0.2,s1+0.2,d0-0.2,d1+0.2,0.6),H,H+0.7,"#45484f",CAL.gunLo,{mat:false});capTop(fr,s0-0.2,s1+0.2,d0-0.2,d1+0.2,H+0.7,o.seed);
  const fc=faces(fr,s0,s1,d0,d1);for(const k of ["front","e1","e2","back"]){const [a,b,n]=fc[k];onFace(a,b,n,0,H,(W,HH)=>{dGrille(0.9,0.9,W-1.8,HH*0.36);dHatch(0.7,HH*0.5,W-1.4,HH*0.4);dSlotLamp(W/2-0.9,HH*0.66,1.8);dWear(W,HH,(o.seed||0)+k.length)})}};
// wall-mounted small props (face units): control box, junction box with cable drops, lamp fixture
SV.small.controlBox=(x,y,o={})=>{dRaised(x,y,6.4,4.6,"#3a3d43");dScreenModule(x+0.9,y+0.9,2.4,1.6,false,null,"status");dButtons(x+3.9,y+0.8,2,2,0.9,o.seed||0);dKnob(x+1.6,y+3.5,0.45);dAmber(x+3.4,y+3.4,2.2,0.45);dRivets(x,y,6.4,4.6)};
SV.small.junctionBox=(x,y,dropTo)=>{dHatch(x,y,6,4.4);dAmber(x+2.4,y+1.2,1.2,0.5);const cols=["#16171a","#a8402e","#3c6f9a"];cols.forEach((cl,k)=>{ctx.strokeStyle=cl;ctx.lineWidth=0.4;ctx.beginPath();ctx.moveTo(x+1.6+k*1.2,y+4.4);ctx.quadraticCurveTo(x+1+k*1.4,(y+4.4+dropTo)/2+1,x+0.2+k*2.4,dropTo);ctx.stroke()})};
SV.small.lamp=(x,y,w)=>{ctx.fillStyle="#2a2c31";ctx.fillRect(x-0.8,y-0.4,w+1.6,1.6);ctx.fillStyle="#f6ead2";ctx.fillRect(x,y,w,0.8);ctx.fillStyle="rgba(255,215,150,.28)";ctx.fillRect(x-1.4,y-0.2,w+2.8,2.2);ctx.fillStyle="#6a6d73";ctx.fillRect(x-0.5,y+0.1,0.4,0.9);ctx.fillRect(x+w+0.1,y+0.1,0.4,0.9)};
// ================================================================ WALL family (face units on a bulkhead face W x H)
// kinds: panel, rib, grille, service (door), console, equipment, storage (niche), junction; every element has a technical reason.
// SV.wall.BAYS: the rhythm between ribs, read as groups (flanking panels around one feature), not one motif per segment
SV.wall={};
SV.wall.BAYS=[["panel","equipment","panel"],["grille","console","grille"],["panel","service","panel"],["storage","junction","panel"],["panel","grille","equipment"]];
SV.wall.band=(W,H)=>{ctx.fillStyle="#1a1b1e";ctx.fillRect(0,H-2.8,W,2.8);ctx.fillStyle="rgba(255,240,215,.08)";ctx.fillRect(0,H-2.8,W,0.3);
  ctx.fillStyle="#2a2c31";ctx.fillRect(0,0.5,W,1.3);ctx.fillStyle="rgba(255,240,215,.1)";ctx.fillRect(0,0.5,W,0.22);ctx.fillStyle="#8a7448";for(let u=1.2;u<W;u+=2.6)ctx.fillRect(u,1.0,0.32,0.32)}; // kick band + bolted cornice
SV.wall.face=(kind,W,H,seed)=>{SV.wall.band(W,H);
  if(kind==="rib"){ctx.fillStyle="#34373c";ctx.fillRect(W/2-1.6,1.8,3.2,H-4.6);ctx.fillStyle=CAL.brass;for(const v of [2.6,H*0.35,H*0.65,H-4]){ctx.beginPath();ctx.arc(W/2,v,0.38,0,TAU);ctx.fill()}ctx.fillStyle="#141517";ctx.fillRect(W/2-0.3,3,0.6,H-7);
    dConduit(W/2-3,1.8,H-2.8);dConduit(W/2+2.2,1.8,H-2.8);return}
  ctx.strokeStyle="#1b1c1f";ctx.lineWidth=0.5;ctx.strokeRect(0.7,2.2,W-1.4,H-5.6);dRecess(1.6,H*0.14,1.4,H*0.64,"#26282c");dRecess(W-3,H*0.14,1.4,H*0.64,"#26282c");
  if(kind==="equipment"){dRecess(W/2-4.2,H*0.24,8.4,H*0.46,"#1b1d20");dGauge(W/2-2,H*0.24+2.2,1.2);dGauge(W/2+2,H*0.24+2.2,1.2);dGrille(W/2-3.2,H*0.24+4.6,6.4,H*0.46-5.4);dLampCol(W/2+3.1,H*0.26+4.6,2,1.2)}
  else if(kind==="service"){dRecess(W/2-3.4,H*0.18,6.8,H*0.82-3.2,"#2b2d32");ctx.strokeStyle="rgba(0,0,0,.55)";ctx.lineWidth=0.25;ctx.strokeRect(W/2-2.8,H*0.18+0.6,5.6,H*0.82-4.4);ctx.fillStyle="#0e2a32";ctx.fillRect(W/2-1.4,H*0.26,2.8,1.4);
    dHinges(W/2-3.2,H*0.25,H*0.5);dSlotLamp(W/2+0.8,H*0.52,1.4);for(let k=0;k<4;k++){ctx.fillStyle=k%2?"#1a1a1a":CAL.hazard;ctx.fillRect(W/2-2.8+k*1.4,H-4.6,1.4,0.9)}}
  else if(kind==="console"){dRecess(W/2-4,H*0.28,8,6,"#1b1d20");dScreenModule(W/2-1.4,H*0.28+1.2,4.2,2.8,false,null,"status");dButtons(W/2-3.4,H*0.28+1,1,3,1,seed);ctx.strokeStyle="#c99a2e";ctx.lineWidth=0.35;ctx.beginPath();ctx.moveTo(W/2-3,H*0.28+6);ctx.quadraticCurveTo(W/2-2,H*0.28+8,W/2-4.5,H-3);ctx.stroke();ctx.strokeStyle="#a8402e";ctx.beginPath();ctx.moveTo(W/2-2.2,H*0.28+6);ctx.quadraticCurveTo(W/2,H*0.28+9,W/2-3,H-3);ctx.stroke()}
  else if(kind==="junction")SV.small.junctionBox(W/2-3,H*0.3,H-3);
  else if(kind==="grille"){dGrille(W/2-3.6,H*0.3,7.2,5.6);ctx.fillStyle="#6a6d73";ctx.fillRect(W/2-3.9,H*0.3-0.5,7.8,0.5)}
  else if(kind==="storage"){dRecess(W/2-3.4,H*0.26,6.8,H*0.5,"#1d1f23");ctx.fillStyle="#26282c";ctx.fillRect(W/2-3.4,H*0.26+H*0.25,6.8,0.5);for(const [bx,by,bw,bh] of [[-2.8,1,2.6,2.2],[0.2,1.6,2.6,1.6],[-2.6,H*0.25+0.9,3.6,2],[1.4,H*0.25+1.2,1.6,1.7]]){ctx.fillStyle="#3a3d43";ctx.fillRect(W/2+bx,H*0.26+by,bw,bh);ctx.fillStyle="rgba(255,240,215,.12)";ctx.fillRect(W/2+bx,H*0.26+by,bw,0.25)}}
  else{dRecess(W/2-3,H*0.2,6,H*0.5,"#2c2e33");dVents(W/2-2.2,H*0.24,4.4,2.4,3);dAmber(W/2-1.2,H*0.58,2.4,0.55)}
  dWear(W,H-3,seed)};
SV.wall.tray=(W,H)=>{const ty=H*0.12;ctx.fillStyle="#1b1c1f";ctx.fillRect(0,ty-0.3,W,2.4);ctx.fillStyle="#a8402e";ctx.fillRect(0,ty,W,0.5);ctx.fillStyle="#c99a2e";ctx.fillRect(0,ty+0.65,W,0.5);ctx.fillStyle="#3c6f9a";ctx.fillRect(0,ty+1.3,W,0.5);dBracket(1,ty-0.6,0.8);dBracket(W-1.8,ty-0.6,0.8)};
// WALL-upper: the HIGH layer. A wall-hung module above the consoles, on two brackets: "cabinet" (louvres, hatch, lamp pips),
// "monitor" (a dark status screen in a housing, no data) or "cable" (a cable box with a loom dropping into the wall tray).
// fr: {cx,cy,a,f (out of the wall),L,D}; h0..h1 = mounting height
SV.wall.upper=(fr,kind,h0,h1,seed)=>{const hL=fr.L/2,hD=fr.D/2;
  for(const sg of [-0.6,0.6]){const s=sg*hL;prismX(frameRect(fr,s-0.35,s+0.35,-hD,hD-0.4),h0-2.2,h0,"#4a4d54",CAL.gunLo,{lw:0.3,mat:false,shadow:false})} // brackets
  prismX(frameCham(fr,-hL,hL,-hD,hD,0.5),h0,h1,"#45484f",kind==="monitor"?"#2c2f35":CAL.gun,{lw:0.4,shadow:false});
  const [a,b]=faces(fr,-hL,hL,-hD,hD).front;onFace(a,b,fr.f,h0,h1,(W,H)=>{
    if(kind==="monitor"){dScreenModule(1.8,1.1,W-3.6,H-2.4,false,null,"status");dLampPips(0.5,1.2,Math.max(1,Math.floor((H-2)/1.3)))}
    else if(kind==="cable"){dHatch(0.8,0.6,W*0.45,H-1.2);dAmber(W*0.6,1,1.2,0.5);dLoom(W*0.5,W-0.8,H*0.55,0.8)}
    else{dLouvrePair(0.9,0.8,W*0.55,H-1.8);dHatch(W*0.62,0.6,W*0.3,H-1.2);dLampPips(W-1.4,1,Math.max(1,Math.floor((H-2)/1.3)))}
    dRivets(0,0,W,H);dWear(W,H,seed||1)});
  capTop(fr,-hL,hL,-hD,hD,h1,seed)};
// ================================================================ FLOOR family (world units; X,Y = tile origin, T = tile size)
// panel: broad staggered plates (2 tiles long, offset per row) with bevel-ladder lips, corner rivets and per-plate tone variation
SV.floor={};
SV.floor.panel=(tc,tr,X,Y,fine,detail)=>{const pl=Math.floor((tc+(tr%2))/2);const ph=((pl*73856093)^(tr*19349663))>>>0;const q=rectPoly(X,Y,X+T,Y+T);
  ctx.fillStyle=ph%5===0?"#2d2e31":ph%7===0?"#323337":CAL.plate;ctx.fill(poly2(q,0));
  const leftSeam=(tc+(tr%2))%2===0,rightSeam=!((tc+1+(tr%2))%2);
  if(detail){line3([X,Y+0.9,0.01],[X+T,Y+0.9,0.01],"rgba(255,240,215,.07)",0.5);line3([X,Y+T-0.9,0.01],[X+T,Y+T-0.9,0.01],"rgba(0,0,0,.25)",0.5);
    if(leftSeam)line3([X+0.9,Y,0.01],[X+0.9,Y+T,0.01],"rgba(255,240,215,.07)",0.5);if(rightSeam)line3([X+T-0.9,Y,0.01],[X+T-0.9,Y+T,0.01],"rgba(0,0,0,.25)",0.5)}
  if(fine){ctx.fillStyle="rgba(150,135,105,.5)";for(const [dx,dy] of [[leftSeam?1.8:-1,1.8],[rightSeam?10.2:-1,1.8],[leftSeam?1.8:-1,10.2],[rightSeam?10.2:-1,10.2]]){if(dx<0)continue;const p=V.P(X+dx,Y+dy,0.02);ctx.fillRect(p[0]-0.28,p[1]-0.28,0.56,0.56)}
    if(ph%6===1){ctx.fillStyle="rgba(0,0,0,.1)";ctx.fill(poly2(rectPoly(X+3,Y+4,X+8,Y+7),0.015))}}
  ctx.strokeStyle=CAL.seam;ctx.lineWidth=0.55;ctx.beginPath();const a=V.P(X,Y,0),b=V.P(X+T,Y,0);ctx.moveTo(a[0],a[1]);ctx.lineTo(b[0],b[1]);if(leftSeam){const c=V.P(X,Y+T,0);ctx.moveTo(a[0],a[1]);ctx.lineTo(c[0],c[1])}ctx.stroke()};
SV.floor.grille=(X,Y)=>{ctx.fillStyle="#18191b";ctx.fill(poly2(rectPoly(X+2.5,Y+2.5,X+9.5,Y+9.5),0.01));for(let k=3.4;k<9.5;k+=1.2)line3([X+3,Y+k,0.02],[X+9,Y+k,0.02],"rgba(95,100,108,.5)",0.32)};
SV.floor.vent=(X,Y)=>{const b2=[X+1.6,Y+3,X+10.4,Y+9];ctx.fillStyle="#3a3c40";ctx.fill(poly2(rectPoly(b2[0]-0.6,b2[1]-0.6,b2[2]+0.6,b2[3]+0.6),0.02));ctx.fillStyle="#121315";ctx.fill(poly2(rectPoly(...b2),0.03));
  for(let k=b2[1]+0.8;k<b2[3];k+=1.1)line3([b2[0]+0.5,k,0.04],[b2[2]-0.5,k,0.04],"rgba(105,110,118,.6)",0.4);line3([(b2[0]+b2[2])/2,b2[1],0.05],[(b2[0]+b2[2])/2,b2[3],0.05],"#3a3c40",0.6)};
SV.floor.hatch=(X,Y,fine)=>{ctx.fillStyle="#232427";ctx.fill(poly2(rectPoly(X+2,Y+2,X+10,Y+10),0.02));ctx.strokeStyle="rgba(0,0,0,.55)";ctx.lineWidth=0.4;ctx.stroke(poly2(rectPoly(X+2,Y+2,X+10,Y+10),0.02));
  line3([X+2.2,Y+2.3,0.03],[X+9.8,Y+2.3,0.03],"rgba(255,240,215,.1)",0.3);ctx.fillStyle="#141517";ctx.fill(poly2(rectPoly(X+4.6,Y+7.6,X+7.4,Y+8.8),0.03));line3([X+4.9,Y+8.2,0.04],[X+7.1,Y+8.2,0.04],CAL.brass,0.3);
  if(fine){ctx.fillStyle="#8a7448";for(const [dx,dy] of [[2.8,2.8],[9.2,2.8],[2.8,9.2],[9.2,9.2]]){const p=V.P(X+dx,Y+dy,0.04);ctx.fillRect(p[0]-0.25,p[1]-0.25,0.5,0.5)}}};
SV.floor.conduit=(X,Y,vert,detail)=>{const box=vert?[X+3.4,Y,X+8.6,Y+T]:[X,Y+3.4,X+T,Y+8.6];ctx.fillStyle="#141517";ctx.fill(poly2(rectPoly(...box),0.02));
  const cols=["#a8402e","#c99a2e","#3c6f9a"];for(let k=0;k<3;k++){const o=1.2+k*1.4;if(vert)line3([box[0]+o,Y,0.03],[box[0]+o,Y+T,0.03],cols[k],0.9);else line3([X,box[1]+o,0.03],[X+T,box[1]+o,0.03],cols[k],0.9)}
  if(detail){const m=vert?[[box[0]-0.3,Y+6],[box[2]+0.3,Y+6]]:[[X+6,box[1]-0.3],[X+6,box[3]+0.3]];line3([...m[0],0.04],[...m[1],0.04],"#6a6d73",1.1)}};
SV.floor.junction=(X,Y)=>{ctx.fillStyle="#3a3c40";ctx.fill(poly2(rectPoly(X+1,Y+1,X+11,Y+11),0.05));ctx.fillStyle="#1a1b1e";ctx.fill(poly2(rectPoly(X+2,Y+2,X+10,Y+10),0.06));
  ["#a8402e","#c99a2e","#3c6f9a"].forEach((cl,k)=>{const p=V.P(X+4+k*2,Y+6,0.07);ctx.fillStyle=cl;ctx.beginPath();ctx.arc(p[0],p[1],0.6,0,TAU);ctx.fill()});ctx.fillStyle="#8a7448";for(const [dx,dy] of [[1.6,1.6],[10.4,1.6],[1.6,10.4],[10.4,10.4]]){const p=V.P(X+dx,Y+dy,0.07);ctx.fillRect(p[0]-0.3,p[1]-0.3,0.6,0.6)}};
SV.floor.hazard=(X,Y,x0,y0,x1,y1)=>{const q=rectPoly(x0,y0,x1,y1);ctx.save();ctx.clip(poly2(q,0.02));ctx.fillStyle="#1b1c1f";ctx.fill(poly2(q,0.02));for(let k=-14;k<=26;k+=3.2)line3([X+k,Y,0.03],[X+k+12,Y+12,0.03],"rgba(201,146,46,.72)",1.1);ctx.restore()};
SV.floor.beam=(X,Y,side,fine)=>{if(side==="W"){line3([X,Y,0.015],[X,Y+T,0.015],"#18191b",1.5);line3([X+0.75,Y,0.02],[X+0.75,Y+T,0.02],"rgba(255,240,215,.06)",0.3);if(fine){const p=V.P(X,Y+6,0.03);ctx.fillStyle="#8a7448";ctx.fillRect(p[0]-0.3,p[1]-0.3,0.6,0.6)}}
  else{line3([X,Y,0.015],[X+T,Y,0.015],"#18191b",1.5);line3([X,Y+0.75,0.02],[X+T,Y+0.75,0.02],"rgba(255,240,215,.06)",0.3);if(fine){const p=V.P(X+6,Y,0.03);ctx.fillStyle="#8a7448";ctx.fillRect(p[0]-0.3,p[1]-0.3,0.6,0.6)}}};
// ================================================================ TABLE family
// TBL-tactical: stepped plinth with access hatches, pedestals, octagonal frame segments with button panels and grilles,
// raised corner blocks with brass caps, an inner bezel lip and neutral grid glass (decorative, no data)
SV.table={};
SV.table.tactical=(cx,cy,h0)=>{const N=8,R0=29,R1=23.5;const fr={cx,cy,a:[1,0],f:[0,1]};return{h:36,draw(){
  prismX(circPoly(cx,cy,26.5,8).map(p=>p),h0,h0+0.9,"#2a2c31","#1d1f23",{lw:0.35});
  for(const s of [-1,1]){const r=frameRect(fr,s*15-4,s*15+4,-6,6);prismX(r,h0+0.9,h0+3.2,CAL.gunHi,CAL.gun);
    for(const [e0,e1,n] of [[r[3],r[2],[0,1]],[r[1],r[0],[0,-1]],[r[2],r[1],[1,0]],[r[0],r[3],[-1,0]]])onFace(e0,e1,n,h0+0.9,h0+3.2,(W,H)=>{dRecess(0.8,0.3,W-1.6,H-0.6,"#2b2d32");dHandle(W/2-1,H*0.45,2)})}
  prismX(frameCham(fr,-10,10,-10,10,4),h0+0.9,h0+3.2,CAL.gunHi,CAL.gunLo);
  const ring=(r,a)=>[cx+r*Math.cos(a),cy+r*Math.sin(a)];const off=Math.PI/8;
  const segs=[];for(let k=0;k<N;k++){const a0=k*TAU/N+off,a1=(k+1)*TAU/N+off;segs.push({k,a0,a1,d:V.depth(...ring(R0,(a0+a1)/2))})}segs.sort((p,q)=>p.d-q.d);
  for(const {k,a0,a1} of segs){const seg=[ring(R0,a0),ring(R0,a1),ring(R1,a1),ring(R1,a0)];const n=[Math.cos((a0+a1)/2),Math.sin((a0+a1)/2)];
    prismX(seg,h0+3.2,h0+7.9,k%2?CAL.gunHi:"#5e626a",k%2?CAL.gun:"#43464d");
    onFace(seg[0],seg[1],n,h0+3.2,h0+7.9,(W,H)=>{dRecess(1.6,0.6,W*0.3,H-1.2,"#1d1f23");dButtons(2,1.1,3,2,0.9,k);dGrille(W*0.4,0.9,W*0.2,H-1.8);dRecess(W*0.66,0.6,W*0.26,H-1.2,"#1d1f23");
      if(k%2)dToggles(W*0.68,1,3);else dButtons(W*0.68,1.1,3,2,0.9,k+3);dAmber(W*0.45,H-1,W*0.1,0.4);dWear(W,H,k)});
    const cp=ring(R0-1.6,a0);const cb=[ring(R0+0.2,a0-0.05),ring(R0+0.2,a0+0.05),ring(R0-3.2,a0+0.07),ring(R0-3.2,a0-0.07)];prismX(cb,h0+3.2,h0+8.6,"#6a6e76","#3a3d43",{lw:0.35});
    const p=V.P(cp[0],cp[1],h0+8.62);ctx.fillStyle=CAL.brassHi;ctx.fillRect(p[0]-0.8,p[1]-0.45,1.6,0.9)}
  const t=h0+7.6;const glass=[];for(let k=0;k<N;k++)glass.push(ring(R1,k*TAU/N+off));
  const lip=[];for(let k=0;k<N;k++)lip.push(ring(R1+0.9,k*TAU/N+off));ctx.fillStyle="#141517";ctx.fill(poly2(lip,t+0.32));ctx.strokeStyle="rgba(255,240,215,.18)";ctx.lineWidth=0.3;ctx.stroke(poly2(lip,t+0.32));
  ctx.fillStyle="#071319";ctx.fill(poly2(glass,t));
  ctx.save();ctx.clip(poly2(glass,t));const s=V.P(cx,cy,t);const g=ctx.createRadialGradient(s[0],s[1],0,s[0],s[1],V.kx*22);g.addColorStop(0,"rgba(60,200,225,.4)");g.addColorStop(1,"rgba(15,80,100,.18)");ctx.fillStyle=g;ctx.fillRect(s[0]-45,s[1]-45,90,90);
  for(let k=-24;k<=24;k+=3)line3([cx+k,cy-24,t],[cx+k,cy+24,t],"rgba(110,225,245,.2)",0.2),line3([cx-24,cy+k,t],[cx+24,cy+k,t],"rgba(110,225,245,.2)",0.2);
  for(const r of [5,10,15,20])ell(cx,cy,r,t,null,"rgba(130,235,250,.45)",0.28);line3([cx-24,cy,t],[cx+24,cy,t],"rgba(140,240,255,.55)",0.3);line3([cx,cy-24,t],[cx,cy+24,t],"rgba(140,240,255,.55)",0.3);ell(cx,cy,1.2,t,"rgba(170,245,255,.85)");
  ctx.fillStyle="rgba(0,0,0,.35)";ctx.fill(poly2(glass.map(p=>[p[0],p[1]-1.4]),t));ctx.restore();
  ctx.strokeStyle=CAL.out;ctx.lineWidth=0.5;ctx.stroke(poly2(glass,t));
  const gc=V.P(cx,cy,t+15);ctx.save();ctx.globalAlpha=0.55;ctx.strokeStyle="#8fdcf0";ctx.lineWidth=0.3;ctx.beginPath();ctx.arc(gc[0],gc[1],5,0,TAU);ctx.stroke();ctx.beginPath();ctx.ellipse(gc[0],gc[1],5,1.6,0,0,TAU);ctx.stroke();ctx.beginPath();ctx.ellipse(gc[0],gc[1],2,5,0,0,TAU);ctx.stroke();ctx.restore(); // DEC-007, decorative only
}}}
// ================================================================ DOOR family
// ONE OPENING = ONE ASSEMBLY. fr: {cx,cy,a (along the opening),f (toward the room it serves),L (clear width)}.
// Built from: threshold plate (door track, titanium edges, hazard bands) -> two layered jamb columns (chamfered body, inner
// leaf pocket with the retracted leaf edge, front panels with lamp column and bolts, a door control box on one side) ->
// lintel housing (mechanical drive housing: louvres, status lamp, destination plate, hazard band under it) -> crown cap.
// type: "standard" (A, compact corridor door) | "hub" (B, large hub access: wider, heavier jambs, twin amber beacons, crown)
//       | "restricted" (C, heavier frame, hazard-banded jambs, amber warning beacon; only where the layout marks restricted)
// o.closed: a segmented leaf across the opening (reserved doors). o.plate: destination text (no numbers). o.D: jamb depth
SV.door={};
SV.door.SPEC={standard:{jw:3.6,H:21,lh:4.6,depth:7},hub:{jw:5.2,H:24,lh:6,depth:10},restricted:{jw:4.8,H:23,lh:5.6,depth:9}};
SV.door.threshold=(fr,type,o={})=>{const sp=SV.door.SPEC[type];const hW=fr.L/2,dD=(o.D||sp.depth)/2;
  const q=frameRect(fr,-hW,hW,-dD-1,dD+1);ctx.fillStyle="#1d1e21";ctx.fill(poly2(q,0.03));
  const g=frameRect(fr,-hW+0.8,hW-0.8,-dD+0.6,dD-0.6);ctx.fillStyle="#141517";ctx.fill(poly2(g,0.035));
  for(let k=-hW+1.6;k<hW-1;k+=1.3){const a=[fr.cx+fr.a[0]*k+fr.f[0]*(-dD+0.8),fr.cy+fr.a[1]*k+fr.f[1]*(-dD+0.8)],b=[fr.cx+fr.a[0]*k+fr.f[0]*(dD-0.8),fr.cy+fr.a[1]*k+fr.f[1]*(dD-0.8)];line3([a[0],a[1],0.04],[b[0],b[1],0.04],"rgba(95,100,108,.55)",0.35)} // grating
  line3([fr.cx-fr.a[0]*hW,fr.cy-fr.a[1]*hW,0.05],[fr.cx+fr.a[0]*hW,fr.cy+fr.a[1]*hW,0.05],"#0a0b0c",1.1); // door track
  for(const sg of [-1,1]){const d=sg*(dD+0.5);const a=[fr.cx-fr.a[0]*hW+fr.f[0]*d,fr.cy-fr.a[1]*hW+fr.f[1]*d],b=[fr.cx+fr.a[0]*hW+fr.f[0]*d,fr.cy+fr.a[1]*hW+fr.f[1]*d];
    line3([a[0],a[1],0.05],[b[0],b[1],0.05],CAL.ti,0.5);const n=Math.floor(fr.L/2.4);for(let k=0;k<n;k++){if(k%2)continue;const t0=k/n,t1=(k+1)/n;line3([a[0]+(b[0]-a[0])*t0+fr.f[0]*sg*0.9,a[1]+(b[1]-a[1])*t0+fr.f[1]*sg*0.9,0.05],[a[0]+(b[0]-a[0])*t1+fr.f[0]*sg*0.9,a[1]+(b[1]-a[1])*t1+fr.f[1]*sg*0.9,0.05],CAL.hazard,1.1)}}};
SV.door.jamb=(fr,type,sg,o={})=>{const sp=SV.door.SPEC[type];const hW=fr.L/2,dD=(o.D||sp.depth)/2,H=sp.H;const s0=sg<0?-hW-sp.jw:hW,s1=s0+sp.jw;
  plinth(fr,s0,s1,-dD,dD,0.8);const body=frameCham(fr,s0,s1,-dD,dD,0.8);prismX(body,0.8,H,CAL.gunHi,"#34373d",{lw:0.45});
  const fc=faces(fr,s0,s1,-dD,dD);const inner=sg<0?fc.e2:fc.e1,front=fc.front,back=fc.back;
  onFace(inner[0],inner[1],inner[2],0.8,H,(W,HH)=>{dRecess(0.6,0.4,W-1.2,HH-0.9,"#121315");ctx.fillStyle="#3a3d43";ctx.fillRect(W*0.3,0.6,W*0.4,HH-1.3); // leaf pocket + retracted leaf edge
    for(let y=0.8;y<HH-1;y+=1.6){ctx.fillStyle=Math.floor(y/1.6)%2?"#1a1a1a":CAL.hazard;ctx.fillRect(W*0.3,y,W*0.4,0.8)}ctx.fillStyle="#0a0b0c";ctx.fillRect(W*0.28,0.6,0.25,HH-1.3);ctx.fillRect(W*0.72-0.25,0.6,0.25,HH-1.3)});
  for(const [f0,which] of [[front,"front"],[back,"back"]])onFace(f0[0],f0[1],f0[2],0.8,H,(W,HH)=>{ctx.strokeStyle="#1b1c1f";ctx.lineWidth=0.4;ctx.strokeRect(0.6,0.8,W-1.2,HH-2);
    dLampPips(W/2-0.3,1.6,Math.max(2,Math.floor(HH*0.35/1.3)),1.3);dRecess(0.9,HH*0.5,W-1.8,HH*0.22,"#24262a");dRivets(0,0,W,HH);
    if(type==="restricted")for(let y=HH-4.6;y<HH-0.8;y+=1.4){ctx.fillStyle=Math.floor(y/1.4)%2?"#1a1a1a":CAL.hazard;ctx.fillRect(0.4,y,W-0.8,0.7)}
    else{ctx.fillStyle="#1a1b1e";ctx.fillRect(0,HH-2.2,W,2.2);for(let x=0.4;x<W-0.4;x+=1.6){ctx.fillStyle=CAL.hazard;ctx.fillRect(x,HH-1.9,0.8,1.2)}}
    if(which==="front"&&sg>0&&W>=4)SV.small.controlBox(W/2-3.2,HH*0.3,{seed:3});dWear(W,HH,sg+5)});
  capTop(fr,s0,s1,-dD,dD,H,sg+7)};
SV.door.lintel=(fr,type,o={})=>{const sp=SV.door.SPEC[type];const hW=fr.L/2,dD=(o.D||sp.depth)/2,H=sp.H,s0=-hW-sp.jw,s1=hW+sp.jw;
  const lit=type==="restricted"?CAL.amber:o.closed?"#2b3a33":"#7fe6f6";
  prismX(frameCham(fr,s0,s1,-dD+0.6,dD-0.6,0.6),H-sp.lh,H+0.6,"#45484f",CAL.gun,{lw:0.45,shadow:false});
  for(const k of ["front","back"]){const [a,b,n]=faces(fr,s0,s1,-dD+0.6,dD-0.6)[k];onFace(a,b,n,H-sp.lh,H+0.6,(W,HH)=>{
    for(let x=0;x<W;x+=1.6){ctx.fillStyle=Math.floor(x/1.6)%2?"#1a1a1a":CAL.hazard;ctx.fillRect(x,HH-1.1,1.6,1.1)} // hazard band under the housing
    dLouvrePair(1.2,0.7,W*0.24,HH-2.4);dLouvrePair(W-1.2-W*0.24,0.7,W*0.24,HH-2.4);
    const pw=Math.min(16,W*0.42);dRecess(W/2-pw/2,0.5,pw,HH-2,"#121315");if(o.plate)dPlate(W/2-pw/2+0.8,1,pw-4.2,Math.min(1.8,HH-3.2),o.plate);
    ctx.fillStyle="#0f1011";ctx.fillRect(W/2+pw/2-3,0.9,2.2,HH-2.8);ctx.fillStyle=lit;ctx.fillRect(W/2+pw/2-2.6,1.3,1.4,HH-3.6); // status lamp (open / restricted / closed)
    if(type!=="standard")for(const x of [W*0.27,W*0.73-1.6])dAmber(x,HH*0.32,1.6,0.9);dRivets(0,0,W,HH-1.1);dWear(W,HH,9)})}
  if(type!=="standard"){prismX(frameRect(fr,s0+1,s1-1,-dD+1.4,dD-1.4),H+0.6,H+1.8,"#3d4046",CAL.gunLo,{lw:0.35,shadow:false,mat:false});capTop(fr,s0+1,s1-1,-dD+1.4,dD-1.4,H+1.8,4)
    for(const sg of [-1,1]){const p=[fr.cx+fr.a[0]*sg*(hW+sp.jw/2),fr.cy+fr.a[1]*sg*(hW+sp.jw/2)];cyl(p[0],p[1],0.9,H+1.8,H+3.2,type==="restricted"?CAL.amberHi:CAL.amber,"#5a3a14",{n:8})}} // beacons
  else capTop(fr,s0,s1,-dD+0.6,dD-0.6,H+0.6,4)};
SV.door.leaf=(fr,type,o={})=>{const sp=SV.door.SPEC[type];const hW=fr.L/2;for(const sg of [-1,1]){const s0=sg<0?-hW:0.15,s1=sg<0?-0.15:hW;prismX(frameRect(fr,s0,s1,-0.7,0.7),0.2,sp.H-sp.lh,"#4a4e56","#3a3e46",{lw:0.4,shadow:false});
  for(const k of ["front","back"]){const [a,b,n]=faces(fr,s0,s1,-0.7,0.7)[k];onFace(a,b,n,0.2,sp.H-sp.lh,(W,HH)=>{dRaised(0.8,1,W-1.6,HH*0.4,"#43474f");dRaised(0.8,HH*0.48,W-1.6,HH*0.4,"#43474f");
    const ex=sg<0?W-1:0;for(let y=0.4;y<HH;y+=1.4){ctx.fillStyle=Math.floor(y/1.4)%2?"#1a1a1a":CAL.hazard;ctx.fillRect(ex,y,1,0.7)}dWear(W,HH,sg+2)})}}};
// the whole assembly in camera order; returns nothing (items are split by the caller for depth sorting when needed)
SV.door.build=(fr,type,o={})=>{SV.door.threshold(fr,type,o);const order=[-1,1].sort((p,q)=>(p-q)*camAlong(fr.a));SV.door.jamb(fr,type,order[0],o);if(o.closed)SV.door.leaf(fr,type,o);SV.door.jamb(fr,type,order[1],o);SV.door.lintel(fr,type,o)};
// FLR-bigGrate: a large framed deck grate (n x n tiles): titanium frame with bolts, a recessed well, a grid of square holes with
// a lit lip, a centre cross-brace; the reference bridge's paired floor grates, built in Stellar's deck language
SV.floor.bigGrate=(X,Y,S,fine)=>{const q=rectPoly(X+1,Y+1,X+S-1,Y+S-1);ctx.fillStyle="#3a3c40";ctx.fill(poly2(q,0.03));ctx.strokeStyle=CAL.out;ctx.lineWidth=0.4;ctx.stroke(poly2(q,0.03));
  ctx.fillStyle="#101113";ctx.fill(poly2(rectPoly(X+2.4,Y+2.4,X+S-2.4,Y+S-2.4),0.04));const n=Math.round((S-5)/2.4);const st=(S-5)/n;
  for(let i=0;i<n;i++)for(let j=0;j<n;j++){const x0=X+2.5+i*st+0.35,y0=Y+2.5+j*st+0.35;ctx.fillStyle="#2a2c30";ctx.fill(poly2(rectPoly(x0,y0,x0+st-0.7,y0+st-0.7),0.05));ctx.fillStyle="#08090a";ctx.fill(poly2(rectPoly(x0+0.35,y0+0.35,x0+st-1.05,y0+st-1.05),0.055))}
  line3([X+S/2,Y+2.4,0.06],[X+S/2,Y+S-2.4,0.06],"#4a4d54",0.9);line3([X+2.4,Y+S/2,0.06],[X+S-2.4,Y+S/2,0.06],"#4a4d54",0.9);
  line3([X+1,Y+1.2,0.06],[X+S-1,Y+1.2,0.06],"rgba(255,240,215,.16)",0.35);
  if(fine){ctx.fillStyle="#8a7448";for(const [dx,dy] of [[1.7,1.7],[S-1.7,1.7],[1.7,S-1.7],[S-1.7,S-1.7],[S/2,1.7],[S/2,S-1.7],[1.7,S/2],[S-1.7,S/2]]){const p=V.P(X+dx,Y+dy,0.07);ctx.fillRect(p[0]-0.3,p[1]-0.3,0.6,0.6)}}};
// FLR-hatchBand: a wide framed band of diagonal hazard hatching along a closed polygon (zone borders, the table frame)
SV.floor.hatchBand=(poly,w,h)=>{const inner=poly;const cx=poly.reduce((a,p)=>a+p[0],0)/poly.length,cy=poly.reduce((a,p)=>a+p[1],0)/poly.length;
  const outer=poly.map(p=>{const d=Math.hypot(p[0]-cx,p[1]-cy)||1;return[p[0]+(p[0]-cx)/d*w*1.2,p[1]+(p[1]-cy)/d*w*1.2]});
  const path=new Path2D();path.addPath(poly2(outer,h));const ip=poly2(inner,h);ctx.save();ctx.beginPath();outer.forEach((p,i)=>{const s2=V.P(p[0],p[1],h);i?ctx.lineTo(s2[0],s2[1]):ctx.moveTo(s2[0],s2[1])});ctx.closePath();
  inner.slice().reverse().forEach((p,i)=>{const s2=V.P(p[0],p[1],h);i?ctx.lineTo(s2[0],s2[1]):ctx.moveTo(s2[0],s2[1])});ctx.closePath();ctx.fillStyle="#18191b";ctx.fill("evenodd");ctx.clip("evenodd");
  const xs=outer.map(p=>p[0]),ys=outer.map(p=>p[1]);const x0=Math.min(...xs),x1=Math.max(...xs),y0=Math.min(...ys),y1=Math.max(...ys);
  for(let k=x0-(y1-y0);k<x1;k+=3){line3([k,y0,h+0.005],[k+(y1-y0),y1,h+0.005],"rgba(201,146,46,.62)",0.9)}ctx.restore();
  ctx.strokeStyle="rgba(195,203,212,.38)";ctx.lineWidth=0.35;ctx.stroke(poly2(outer,h+0.01));ctx.stroke(ip)};
// SV.small.lampBox (wall face units): a large recessed wall lamp box (bright warm-white panel in a bolted housing with a glow)
SV.small.lampBox=(x,y,w,h)=>{ctx.fillStyle="rgba(255,226,180,.22)";ctx.fillRect(x-1.6,y-1.2,w+3.2,h+2.4);ctx.fillStyle="#1c1d20";ctx.fillRect(x-0.8,y-0.8,w+1.6,h+1.6);ctx.strokeStyle=CAL.out;ctx.lineWidth=0.3;ctx.strokeRect(x-0.8,y-0.8,w+1.6,h+1.6);
  const g=ctx.createLinearGradient(0,y,0,y+h);g.addColorStop(0,"#fff6e2");g.addColorStop(1,"#f0d6a8");ctx.fillStyle=g;ctx.fillRect(x,y,w,h);ctx.fillStyle="rgba(0,0,0,.18)";for(let k=x+1;k<x+w-0.4;k+=1.4)ctx.fillRect(k,y,0.25,h);dRivets(x-0.8,y-0.8,w+1.6,h+1.6,"#8a7448")};
// ================================================================ LAB equipment (adapted from the reference lab props)
// SCR-cluster: ONE cast column on a base plate, a crossbar, a wide status head on top and two lower heads hanging off the bar,
// each a different surface kind (never three identical cells). Dark: no display identity, no data
SV.screen.cluster=(fr,o={})=>{const sd=o.seed||0;const x=fr.cx,y=fr.cy;const F=fr.f,A=fr.a;
  prismX(frameCham(fr,-4.6,4.6,-4,4,1),0,1.1,"#2a2c31","#1d1f23",{lw:0.35,mat:false});capTop(fr,-4.6,4.6,-4,4,1.1,sd);
  prismX(frameCham(fr,-1.1,1.1,-1.6,0.6,0.4),1.1,17.5,CAL.gunHi,CAL.gun,{lw:0.4}); // column
  const head=(s0,s1,h0,h1,kind,dd)=>{const r=frameCham(fr,s0,s1,dd-1.6,dd+0.2,0.4);prismX(r,h0,h1,"#45484f","#2a2c31",{lw:0.4,shadow:false});
    const [a,b,n]=faces(fr,s0,s1,dd-1.6,dd+0.2).front;onFace(a,b,n,h0,h1,(W,H)=>{dScreenModule(1.4,1.2,W-2.8,H-2.6,false,null,kind);dIndicator(W-1.6,H-1,(sd+h0|0)%3===0)});
    const bk=faces(fr,s0,s1,dd-1.6,dd+0.2).back;onFace(bk[0],bk[1],bk[2],h0,h1,(W,H)=>{dGrille(1,1,W-2,H-2);dRivets(0,0,W,H)})};
  prismX(frameRect(fr,-5.4,5.4,-0.9,0.1),11.2,12.2,"#4a4d54",CAL.gunLo,{lw:0.35,shadow:false,mat:false}); // crossbar
  const lower=()=>{head(-5.6,-0.4,6.2,11.2,"instrument",0.9);head(0.4,5.6,6.2,11.2,"status",0.9)};const top=()=>head(-5.2,5.2,17.5,24.5,o.kind||"info",0.6);
  if(camAlong(F)>0){top();lower()}else{lower();top()}
  cable3([x-A[0]*0.6-F[0]*0.4,y-A[1]*0.6-F[1]*0.4,12],[x-A[0]*0.6-F[0]*2.4,y-A[1]*0.6-F[1]*2.4,0.8],1.2,"#16171a",0.5)};
// EQ-cart: a freestanding trolley (the reference sample cart): casters, four corner posts, two open shelves with a cross-brace,
// a vial rack on top (the vials carry the colour), printout stacks on the lower shelf (matte, no glow)
SV.eq.cart=(fr,o={})=>{const hL=fr.L/2||3.6,hD=fr.D/2||3,sd=o.seed||0;const posts=[[-hL,-hD],[hL-0.8,-hD],[-hL,hD-0.8],[hL-0.8,hD-0.8]];
  for(const [s,d] of posts){const p=[fr.cx+fr.a[0]*(s+0.4)+fr.f[0]*(d+0.4),fr.cy+fr.a[1]*(s+0.4)+fr.f[1]*(d+0.4)];ell(p[0],p[1],0.7,0.4,"#141518")}
  const shelf=(h)=>{prismX(frameRect(fr,-hL,hL,-hD,hD),h,h+0.6,"#4a4d54","#33363c",{lw:0.35,shadow:false,mat:false})};
  const far=posts.filter(([s,d])=>camAlong([fr.a[0]*s+fr.f[0]*d,fr.a[1]*s+fr.f[1]*d])<=0),near=posts.filter(p=>!far.includes(p));
  for(const [s,d] of far)prismX(frameRect(fr,s,s+0.8,d,d+0.8),0.8,10.4,CAL.gunHi,"#4a4d54",{lw:0.3,mat:false,shadow:false});
  shelf(1.2);onTop(fr,-hL+0.6,hL-0.6,-hD+0.6,hD-0.6,1.82,(W,Dd)=>{for(let k=0;k<3;k++){ctx.fillStyle=k%2?"#d8d2c2":"#c9c2b0";ctx.fillRect(0.6+k*0.4,0.6+k*0.3,W*0.45,Dd*0.6);ctx.strokeStyle="rgba(0,0,0,.3)";ctx.lineWidth=0.12;ctx.strokeRect(0.6+k*0.4,0.6+k*0.3,W*0.45,Dd*0.6)}
    ctx.fillStyle="#c9a24a";ctx.fillRect(W*0.58,Dd*0.3,W*0.32,Dd*0.5)});
  shelf(5.4);shelf(9.8);onTop(fr,-hL+0.5,hL-0.5,-hD+0.5,hD-0.5,10.42,(W,Dd)=>{dRecess(0.3,0.3,W-0.6,Dd-0.6,"#1d1f23");const C=["#7fd0e0","#e0b25a","#7fe0a8","#c86a5a","#9fb8e8"];
    for(let i=0;i<5;i++)for(let j=0;j<2;j++){ctx.fillStyle="#0e0f11";ctx.beginPath();ctx.arc(1+i*(W-2)/4,Dd*0.3+j*Dd*0.4,0.55,0,TAU);ctx.fill();ctx.fillStyle=C[(i+j+sd)%5];ctx.beginPath();ctx.arc(1+i*(W-2)/4,Dd*0.3+j*Dd*0.4,0.38,0,TAU);ctx.fill()}});
  for(const [s,d] of near)prismX(frameRect(fr,s,s+0.8,d,d+0.8),0.8,10.4,CAL.gunHi,"#4a4d54",{lw:0.3,mat:false,shadow:false});
  const [a,b]=faces(fr,-hL,hL,-hD,hD).front;onFace(a,b,fr.f,5.4,9.8,(W,H)=>{ctx.strokeStyle="#4a4d54";ctx.lineWidth=0.35;ctx.beginPath();ctx.moveTo(0.4,0.3);ctx.lineTo(W-0.4,H-0.3);ctx.moveTo(W-0.4,0.3);ctx.lineTo(0.4,H-0.3);ctx.stroke()})}; // cross-brace
// EQ-optics: a bolted sealed optics column: flared foot on a bolt ring, a cylindrical body lit warm on one flank and cool on the
// other, a ribbed collar, a lens housing whose lens is the ONLY light, and a cap. Decorative: the lens is constant
SV.eq.optics=(x,y,o={})=>{const H=o.h||22;cyl(x,y,3.6,0,0.8,"#2a2c31","#1d1f23",{n:12});ell(x,y,3.2,0.82,null,"#8a7448",0.35);cyl(x,y,2.6,0.8,2.4,"#45484f",CAL.gun,{n:12});
  cyl(x,y,1.9,2.4,H-5,null,CAL.gun,{n:14});const a=V.P(x-1.9*V.kx,y,2.4),b=V.P(x-1.9*V.kx,y,H-5);line3([x-1.6,y,2.6],[x-1.6,y,H-5.2],"rgba(255,224,176,.35)",0.5);line3([x+1.6,y,2.6],[x+1.6,y,H-5.2],"rgba(127,180,216,.3)",0.5);
  for(const h of [6,10,14])cyl(x,y,2.15,h,h+0.7,"#4a4d54","#3a3d43",{n:14});cyl(x,y,2.5,H-5,H-1.5,"#45484f","#2c2f35",{n:14});
  const lp=V.P(x,y+2.4*0.6,H-3.3);ctx.fillStyle="rgba(120,230,250,.25)";ctx.beginPath();ctx.ellipse(lp[0],lp[1],2.4,1.8,0,0,TAU);ctx.fill();ctx.fillStyle="#0e2a32";ctx.beginPath();ctx.ellipse(lp[0],lp[1],1.4,1.1,0,0,TAU);ctx.fill();ctx.fillStyle="#9ff0ff";ctx.beginPath();ctx.ellipse(lp[0]-0.2,lp[1]-0.2,0.6,0.45,0,0,TAU);ctx.fill();
  cyl(x,y,1.6,H-1.5,H,"#575a61","#3a3d43",{n:12})};
// EQ-tank: a glass specimen tank on a low stand: feet, a stand with a hatch and slot lamp, a pump housing on one end, curved glass
// with a lit surface line and caustic lines in the water, a rim lamp. Decorative, no data
SV.eq.tank=(fr,o={})=>{const hL=fr.L/2,hD=fr.D/2,sd=o.seed||0;feet(fr,-hL,hL,-hD,hD,0.9);prismX(frameCham(fr,-hL,hL,-hD,hD,0.6),0.9,5.4,CAL.gunHi,CAL.gun);
  {const [a,b]=faces(fr,-hL,hL,-hD,hD).front;onFace(a,b,fr.f,0.9,5.4,(W,H)=>{dHatch(1,0.6,W*0.4,H-1.2);dSlotLamp(W*0.6,H*0.45,W*0.25);dWear(W,H,sd)})}
  const pump=frameCham(fr,hL-4.6,hL-0.4,-hD+0.6,hD-0.6,0.5);const g=frameRect(fr,-hL+0.6,hL-5.2,-hD+0.8,hD-0.8);
  const water=()=>{const top=13;ctx.fillStyle="rgba(40,120,120,.42)";for(const [p,q,n] of Object.values(faces(fr,-hL+0.6,hL-5.2,-hD+0.8,hD-0.8))){if(n[0]*V.cam[0]+n[1]*V.cam[1]<=0)continue;
      const pts=[V.P(p[0],p[1],5.4),V.P(q[0],q[1],5.4),V.P(q[0],q[1],top),V.P(p[0],p[1],top)];ctx.beginPath();pts.forEach((s,i)=>i?ctx.lineTo(s[0],s[1]):ctx.moveTo(s[0],s[1]));ctx.closePath();ctx.fill()}
    ctx.fillStyle="rgba(70,170,165,.5)";ctx.fill(poly2(g,top));ctx.strokeStyle="rgba(190,250,240,.75)";ctx.lineWidth=0.4;ctx.stroke(poly2(g,top));
    for(let k=0;k<4;k++){const t=(k+1)/5;line3([g[0][0]+(g[1][0]-g[0][0])*t,g[0][1]+(g[1][1]-g[0][1])*t,top-1.5-k],[g[3][0]+(g[2][0]-g[3][0])*t,g[3][1]+(g[2][1]-g[3][1])*t,top-1-k*0.6],"rgba(190,250,240,.22)",0.35)}
    for(const pp of g)line3([pp[0],pp[1],5.4],[pp[0],pp[1],14.4],"rgba(220,240,245,.5)",0.4);ctx.strokeStyle="rgba(220,240,245,.55)";ctx.lineWidth=0.4;ctx.stroke(poly2(g,14.4))};
  const pumpDraw=()=>{prismX(pump,5.4,12,"#45484f",CAL.gun,{lw:0.4,shadow:false});const [a,b]=faces(fr,hL-4.6,hL-0.4,-hD+0.6,hD-0.6).front;onFace(a,b,fr.f,5.4,12,(W,H)=>{dGrille(0.8,0.8,W-1.6,H*0.4);dKnob(W/2,H*0.7,0.6);dAmber(0.8,H-1.2,1,0.45)});capTop(fr,hL-4.6,hL-0.4,-hD+0.6,hD-0.6,12,sd)};
  if(camAlong(fr.a)>0){water();pumpDraw()}else{pumpDraw();water()}
  prismX(frameRect(fr,-hL+0.4,hL-5,-hD+0.6,hD-0.6),14.4,15,"#4a4d54",CAL.gunLo,{lw:0.3,shadow:false,mat:false})};
// EQ-dome (EQP-005, hero): a stepped circular plinth, a ring of 12 instrument segments (vents, lamp pips, brass caps), an inner well
// lit cool, a slim core column and a glass dome with a highlight; the holo globe inside is decorative (DEC-007, no data)
SV.eq.dome=(cx,cy,R)=>{cyl(cx,cy,R+2,0,0.8,"#2a2c31","#1d1f23",{n:32});ell(cx,cy,R+1.4,0.82,null,"#8a7448",0.4);cyl(cx,cy,R,0.8,2,"#3a3d43",CAL.gun,{n:32});
  const N=12,ring=(r,a)=>[cx+r*Math.cos(a),cy+r*Math.sin(a)];const segs=[];for(let k=0;k<N;k++){const a0=k*TAU/N,a1=(k+1)*TAU/N;segs.push({k,a0,a1,d:V.depth(...ring(R,(a0+a1)/2))})}segs.sort((p,q)=>p.d-q.d);
  ell(cx,cy,R-3.6,2.05,"#0b1a20");const sp=V.P(cx,cy,2.1);const gg=ctx.createRadialGradient(sp[0],sp[1],0,sp[0],sp[1],V.kx*(R-3.6));gg.addColorStop(0,"rgba(120,230,250,.5)");gg.addColorStop(1,"rgba(20,90,110,.15)");ctx.fillStyle=gg;ctx.beginPath();ctx.ellipse(sp[0],sp[1],V.kx*(R-3.6),V.ky*(R-3.6),0,0,TAU);ctx.fill();
  const back=segs.filter(s=>Math.sin((s.a0+s.a1)/2)*V.cam[1]+Math.cos((s.a0+s.a1)/2)*V.cam[0]<0),front=segs.filter(s=>!back.includes(s));
  const seg=({k,a0,a1})=>{const q=[ring(R,a0),ring(R,a1),ring(R-3.4,a1),ring(R-3.4,a0)];const n=[Math.cos((a0+a1)/2),Math.sin((a0+a1)/2)];prismX(q,2,6.2,k%2?"#575a61":"#4a4d54",k%2?CAL.gun:"#3a3d43",{lw:0.4,shadow:false});
    onFace(q[0],q[1],n,2,6.2,(W,H)=>{dVents(W*0.12,0.7,W*0.32,H-1.4,3);dLampPips(W*0.62,0.9,2,1.3);ctx.fillStyle=CAL.brass;ctx.fillRect(0,0,0.5,H);dWear(W,H,k)});const cp=V.P(...ring(R-1.7,a0),6.25);ctx.fillStyle=CAL.brassHi;ctx.fillRect(cp[0]-0.6,cp[1]-0.35,1.2,0.7)};
  for(const s of back)seg(s);cyl(cx,cy,1.2,2,13,"#575a61","#3a3d43",{n:10});
  const gc=V.P(cx,cy,16);ctx.save();ctx.globalAlpha=0.6;ctx.strokeStyle="#8fdcf0";ctx.lineWidth=0.3;ctx.beginPath();ctx.arc(gc[0],gc[1],4,0,TAU);ctx.stroke();ctx.beginPath();ctx.ellipse(gc[0],gc[1],4,1.3,0,0,TAU);ctx.stroke();ctx.beginPath();ctx.ellipse(gc[0],gc[1],1.6,4,0,0,TAU);ctx.stroke();ctx.restore();
  const dc=V.P(cx,cy,6.2);ctx.save();ctx.fillStyle="rgba(170,225,240,.1)";ctx.strokeStyle="rgba(200,240,250,.45)";ctx.lineWidth=0.4;ctx.beginPath();ctx.ellipse(dc[0],dc[1],V.kx*(R-3.6),V.ky*(R-3.6),0,Math.PI,TAU);
  ctx.ellipse(dc[0],dc[1]-(R-3.6)*0.9,V.kx*(R-3.6),(R-3.6)*0.9+0.001,0,0,Math.PI,true);ctx.closePath();ctx.fill();ctx.stroke();ctx.fillStyle="rgba(255,255,255,.18)";ctx.beginPath();ctx.ellipse(dc[0]-(R-3.6)*0.35,dc[1]-(R-3.6)*0.55,(R-3.6)*0.18,(R-3.6)*0.32,-0.5,0,TAU);ctx.fill();ctx.restore();
  for(const s of front)seg(s)};
// EQ-projector (SCR-006 column): a bolted base, a chamfered column with a service hatch and lamp pips, an emitter head (constant)
SV.eq.projector=(fr,o={})=>{plinth(fr,-4.2,4.2,-4.2,4.2,0.8);prismX(frameCham(fr,-3,3,-3,3,0.8),0.8,12,CAL.gunHi,CAL.gun);for(const k of ["front","e1","e2","back"]){const [a,b,n]=faces(fr,-3,3,-3,3)[k];onFace(a,b,n,0.8,12,(W,H)=>{dHatch(0.8,H*0.45,W-1.6,H*0.4);dLampPips(W/2-0.3,1.2,3,1.3);dWear(W,H,k.length)})}
  cyl(fr.cx,fr.cy,2.6,12,13.6,"#575a61","#3a3d43",{n:12});const p=V.P(fr.cx,fr.cy,13.7);ctx.fillStyle="rgba(120,230,250,.6)";ctx.beginPath();ctx.ellipse(p[0],p[1],1.8*V.kx,1.8*V.ky,0,0,TAU);ctx.fill()};
// ================================================================ WING families (department rooms)
// TBL-chart: a rectangular tactical table (the octagonal table's construction on a rectangle): plinth, chamfered rim of segments
// with inset button panels and grilles, corner blocks with brass caps, bezel lip, neutral grid glass (decorative, no data)
SV.table.chart=(fr,o={})=>{const hL=fr.L/2,hD=fr.D/2,H=o.h||7.6;plinth(fr,-hL+2,hL-2,-hD+2,hD-2,1.2);prismX(frameCham(fr,-hL+3.5,hL-3.5,-hD+3.5,hD-3.5,1.2),1.2,3.4,CAL.gunHi,CAL.gunLo);
  const rim=frameCham(fr,-hL,hL,-hD,hD,2.4);prismX(rim,3.4,H,"#575a61",CAL.gun);
  for(const k of ["front","back","e1","e2"]){const ff=k==="e1"||k==="e2"?faces(fr,-hL,hL,-hD+2.4,hD-2.4)[k]:faces(fr,-hL+2.4,hL-2.4,-hD,hD)[k];onFace(ff[0],ff[1],ff[2],3.4,H,(W,HH)=>{const n2=Math.max(1,Math.floor(W/8));for(let i=0;i<n2;i++){const x=i*W/n2;dRecess(x+0.8,0.5,W/n2*0.45,HH-1,"#1d1f23");dButtons(x+1.2,0.9,2,2,0.85,i);dGrille(x+W/n2*0.55,0.8,W/n2*0.35,HH-1.6)}ctx.fillStyle=CAL.brass;ctx.fillRect(0,HH-0.5,W,0.3);dWear(W,HH,n2)})}
  for(const [s0,d0] of [[-hL,-hD],[hL-3,-hD],[-hL,hD-3],[hL-3,hD-3]]){prismX(frameCham(fr,s0,s0+3,d0,d0+3,0.8),3.4,H+0.8,"#6a6e76","#3a3d43",{lw:0.35,shadow:false});onTop(fr,s0+1,s0+2,d0+1,d0+2,H+0.82,(W,Dd)=>{ctx.fillStyle=CAL.brassHi;ctx.fillRect(0,0,W,Dd)})}
  const t=H-0.3;const glass=frameCham(fr,-hL+2.2,hL-2.2,-hD+2.2,hD-2.2,1.4);ctx.fillStyle="#141517";ctx.fill(poly2(frameCham(fr,-hL+1.4,hL-1.4,-hD+1.4,hD-1.4,1.8),H+0.02));ctx.fillStyle="#071319";ctx.fill(poly2(glass,t+0.3));
  ctx.save();ctx.clip(poly2(glass,t+0.3));for(let k=-hL;k<=hL;k+=3)line3([fr.cx+fr.a[0]*k-fr.f[0]*hD,fr.cy+fr.a[1]*k-fr.f[1]*hD,t+0.3],[fr.cx+fr.a[0]*k+fr.f[0]*hD,fr.cy+fr.a[1]*k+fr.f[1]*hD,t+0.3],"rgba(110,225,245,.2)",0.2);
  for(let k=-hD;k<=hD;k+=3)line3([fr.cx-fr.a[0]*hL+fr.f[0]*k,fr.cy-fr.a[1]*hL+fr.f[1]*k,t+0.3],[fr.cx+fr.a[0]*hL+fr.f[0]*k,fr.cy+fr.a[1]*hL+fr.f[1]*k,t+0.3],"rgba(110,225,245,.2)",0.2);
  const s2=V.P(fr.cx,fr.cy,t);const g=ctx.createRadialGradient(s2[0],s2[1],0,s2[0],s2[1],V.kx*hL);g.addColorStop(0,"rgba(60,200,225,.32)");g.addColorStop(1,"rgba(15,80,100,.1)");ctx.fillStyle=g;ctx.fillRect(s2[0]-60,s2[1]-60,120,120);ctx.restore();ctx.strokeStyle=CAL.out;ctx.lineWidth=0.45;ctx.stroke(poly2(glass,t+0.3))};
// TBL-stage: a low evidence stage: stepped plinth with a hatched apron, a bezel frame, a dark glass deck (no data), corner lamp posts
SV.table.stage=(fr,o={})=>{const hL=fr.L/2,hD=fr.D/2;prismX(frameCham(fr,-hL,hL,-hD,hD,2),0,1.2,"#2a2c31","#1d1f23",{lw:0.4});prismX(frameCham(fr,-hL+2,hL-2,-hD+2,hD-2,1.6),1.2,3.2,CAL.gunHi,CAL.gun);
  for(const k of ["front","back","e1","e2"]){const [a,b,n]=faces(fr,-hL+2,hL-2,-hD+2,hD-2)[k];onFace(a,b,n,1.2,3.2,(W,HH)=>{for(let x=0;x<W;x+=1.6){ctx.fillStyle=Math.floor(x/1.6)%2?"#1a1a1a":CAL.hazard;ctx.fillRect(x,0.4,1.6,HH-0.8)}})}
  ctx.fillStyle="#08141a";ctx.fill(poly2(frameCham(fr,-hL+3.2,hL-3.2,-hD+3.2,hD-3.2,1.2),3.25));ctx.strokeStyle="rgba(130,225,245,.35)";ctx.lineWidth=0.3;ctx.stroke(poly2(frameCham(fr,-hL+4.2,hL-4.2,-hD+4.2,hD-4.2,1),3.27));
  for(const [s0,d0] of [[-hL+0.6,-hD+0.6],[hL-1.6,-hD+0.6],[-hL+0.6,hD-1.6],[hL-1.6,hD-1.6]]){const p=[fr.cx+fr.a[0]*(s0+0.5)+fr.f[0]*(d0+0.5),fr.cy+fr.a[1]*(s0+0.5)+fr.f[1]*(d0+0.5)];cyl(p[0],p[1],0.6,1.2,7,"#575a61","#3a3d43",{n:8});const q=V.P(p[0],p[1],7.1);ctx.fillStyle="#f6ead2";ctx.fillRect(q[0]-0.5,q[1]-0.35,1,0.7)}};
// TBL-work: a work table: two pedestal legs on a plinth, a slab with a brass edge, a recessed task surface with paper stacks and
// one small dark status screen on a stand (no data)
SV.table.work=(fr,o={})=>{const hL=fr.L/2,hD=fr.D/2;for(const sg of [-1,1]){const s0=sg<0?-hL+1:hL-4;prismX(frameRect(fr,s0,s0+3,-hD+1,hD-1),0,7,CAL.gun,CAL.gun);const [a,b,n]=faces(fr,s0,s0+3,-hD+1,hD-1).front;onFace(a,b,n,0,7,(W,HH)=>{dVents(0.5,0.8,W-1,HH*0.4,3);dSlotLamp(0.6,HH*0.7,W-1.2)})}
  prismX(frameCham(fr,-hL,hL,-hD,hD,1),7,8,CAL.gunHi,CAL.gunLo);{const [a,b,n]=faces(fr,-hL+1,hL-1,-hD,hD).front;onFace(a,b,n,7,8,(W,HH)=>{ctx.fillStyle=CAL.brass;ctx.fillRect(0,HH*0.3,W,HH*0.4)})}
  onTop(fr,-hL+1,hL-1,-hD+1,hD-1,8.02,(W,Dd)=>{dRecess(0.3,0.3,W-0.6,Dd-0.6,"#202227");for(let k=0;k<3;k++){ctx.fillStyle=k%2?"#d8d2c2":"#c9c2b0";ctx.fillRect(1+k*0.4,1+k*0.3,W*0.28,Dd*0.5)}ctx.fillStyle="#c9a24a";ctx.fillRect(W*0.42,Dd*0.35,W*0.18,Dd*0.4)});
  const sx=fr.cx+fr.a[0]*hL*0.55-fr.f[0]*hD*0.3,sy=fr.cy+fr.a[1]*hL*0.55-fr.f[1]*hD*0.3;cyl(sx,sy,0.5,8,10.5,null,"#4a4d54",{n:6});const sf={cx:sx,cy:sy,a:fr.a,f:fr.f};prismX(frameRect(sf,-3,3,-0.5,0.5),10.5,14.5,"#45484f","#2a2c31",{lw:0.35,shadow:false});
  const [a,b,n]=faces(sf,-3,3,-0.5,0.5).front;onFace(a,b,n,10.5,14.5,(W,HH)=>dScreenModule(1.2,0.9,W-2.4,HH-1.8,false,null,"status"))};
// EQ-reactor: a tall column hero (L4): bolted plinth, stepped base, a ribbed body with a glass band whose light is constant
// (the registered pulse is driven by snapshot events, never invented), top cap with brass collar
SV.eq.reactor=(x,y,o={})=>{const H=o.h||30;cyl(x,y,5.6,0,1,"#2a2c31","#1d1f23",{n:16});ell(x,y,5,1.02,null,"#8a7448",0.4);cyl(x,y,4.6,1,3.4,"#45484f",CAL.gun,{n:16});cyl(x,y,3.6,3.4,H-4,null,CAL.gun,{n:16});
  for(const h of [6,9,22,25])cyl(x,y,3.9,h,h+0.8,"#4a4d54","#3a3d43",{n:16});ctx.globalAlpha=0.6;cyl(x,y,3.7,11,20,null,"#3fb7cc",{n:16});ctx.globalAlpha=1;line3([x-2.6,y,11.2],[x-2.6,y,19.8],"rgba(200,250,255,.6)",0.5);
  cyl(x,y,4.2,H-4,H-1.6,"#575a61","#3a3d43",{n:16});cyl(x,y,2.6,H-1.6,H,"#6a6e76","#45484f",{n:12});ell(x,y,4.2,H-1.58,null,CAL.brass,0.4)};
// EQ-podium: a debate podium / lectern on a plinth: chamfered body with a lit slot, a slanted top with a small dark screen
SV.eq.podium=(fr,o={})=>{plinth(fr,-4,4,-3.4,3.4,0.8);prismX(frameCham(fr,-3.2,3.2,-2.6,2.6,0.6),0.8,9.6,CAL.gunHi,CAL.gun);const [a,b,n]=faces(fr,-3.2,3.2,-2.6,2.6).front;
  onFace(a,b,n,0.8,9.6,(W,HH)=>{dRecess(0.8,0.8,W-1.6,HH*0.5,"#24262a");dSlotLamp(W/2-1.2,HH*0.68,2.4);dRivets(0,0,W,HH);dWear(W,HH,o.seed||1)});
  prismX(frameCham(fr,-3.6,3.6,-3,3,0.6),9.6,10.6,"#575a61",CAL.gunLo,{mat:false});onTop(fr,-2.8,2.8,-2.2,2.2,10.62,(W,Dd)=>{dScreenModule(0.6,0.6,W-1.2,Dd-1.6,false,null,"status");dButtons(0.6,Dd-0.9,3,1,0.8,o.seed||0)})};
// EQ-tube: a launch tube on a heavy base: bolted base with hazard bands, glass tube with lit rings, a top cap housing
SV.eq.tube=(fr,o={})=>{const hL=fr.L/2;plinth(fr,-hL,hL,-5,5,1);prismX(frameCham(fr,-hL+0.8,hL-0.8,-4.4,4.4,1),1,4,CAL.gunHi,CAL.gun);const [a,b,n]=faces(fr,-hL+0.8,hL-0.8,-4.4,4.4).front;
  onFace(a,b,n,1,4,(W,HH)=>{for(let x=0;x<W;x+=1.6){ctx.fillStyle=Math.floor(x/1.6)%2?"#1a1a1a":CAL.hazard;ctx.fillRect(x,0.5,1.6,HH-1)}});
  ctx.globalAlpha=0.38;cyl(fr.cx,fr.cy,3.8,4,24,"#cfeaf3","#a9d4e3",{n:16});ctx.globalAlpha=1;for(const h of [8,14,20])cyl(fr.cx,fr.cy,4,h,h+0.6,"#4a4d54","#3a3d43",{n:16});
  cyl(fr.cx,fr.cy,4.6,24,27,"#575a61","#3a3d43",{n:16});ell(fr.cx,fr.cy,4.6,27.02,null,CAL.amber,0.5)};
// ================================================================ HABITAT family (lounge, café, games, rest, recovery)
// The same construction language (plinths, chamfered castings, brass hardware, wear) with warm materials: wood, fabric, felt,
// cream. Lounge pieces share one softer edge tint instead of the near-black outline, so the lounge reads as one room.
SV.hab={};
const HAB_EDGE="#2a1d16";
const habX=(pts,h0,h1,top,side,o={})=>prismX(pts,h0,h1,top,side,{...o,lw:o.lw||0.4});
// bar counter: kick plinth, wood front with brass kick rail and fluted panels, stone top with a lip, back shelf of bottles (decorative)
SV.hab.bar=(fr,o={})=>{const hL=fr.L/2,hD=fr.D/2;plinth(fr,-hL,hL,-hD,hD,0.8);habX(frameCham(fr,-hL,hL,-hD+1,hD,0.8),0.8,9.4,CAL.woodHi,CAL.wood);
  const [a,b,n]=faces(fr,-hL,hL,-hD+1,hD).front;onFace(a,b,n,0.8,9.4,(W,H)=>{for(let x=1;x<W-1;x+=2.4){ctx.fillStyle="rgba(0,0,0,.18)";ctx.fillRect(x,1,0.5,H-3)}ctx.fillStyle=CAL.brass;ctx.fillRect(0,H-2.2,W,0.5);ctx.fillStyle=CAL.brassHi;ctx.fillRect(0,H-2.2,W,0.15);dWear(W,H,o.seed||2)});
  habX(frameCham(fr,-hL-0.4,hL+0.4,-hD+0.6,hD+0.5,1),9.4,10.4,"#cfc7b8","#a89f8f",{mat:false});onTop(fr,-hL,hL,-hD+1,hD,10.42,(W,Dd)=>{ctx.fillStyle="rgba(255,255,255,.12)";ctx.fillRect(0.4,0.4,W-0.8,0.4);for(let k=0;k<3;k++){ctx.fillStyle="#e8e1d4";ctx.beginPath();ctx.arc(W*(0.2+k*0.3),Dd*0.5,0.6,0,TAU);ctx.fill()}});
  const sh=frameRect(fr,-hL+0.6,hL-0.6,-hD-1.6,-hD+0.4);habX(sh,0,15,CAL.woodLo,CAL.woodLo,{mat:false,shadow:false});const [c,d,m]=faces(fr,-hL+0.6,hL-0.6,-hD-1.6,-hD+0.4).front;
  onFace(c,d,m,10.4,15,(W,H)=>{ctx.fillStyle="#2a1d16";ctx.fillRect(0.4,0.4,W-0.8,H-0.8);const C=["#3c8048","#8c3a2c","#c9a24a","#3c6f9a","#d8cdb8"];for(let x=1;x<W-1;x+=1.1){ctx.fillStyle=C[Math.floor(x*7)%5];ctx.fillRect(x,H*0.35,0.6,H*0.55)}ctx.fillStyle=CAL.brass;ctx.fillRect(0,H*0.92,W,0.3)})};
// dispenser / brewer: one chamfered column, an overhanging head cap, a lit alcove (the only warm emissive), a waiting mug
SV.hab.dispenser=(fr,o={})=>{plinth(fr,-3.6,3.6,-3.2,3.2,0.6);habX(frameCham(fr,-3,3,-2.6,2.6,0.9),0.6,13.6,"#4a4c52",CAL.gun);habX(frameCham(fr,-3.6,3.6,-3.2,3.2,1),13.6,15,"#575a61",CAL.gunLo,{mat:false});
  const [a,b,n]=faces(fr,-3,3,-2.6,2.6).front;onFace(a,b,n,0.6,13.6,(W,H)=>{ctx.fillStyle="#120d0a";ctx.fillRect(0.9,H*0.35,W-1.8,H*0.32);const g=ctx.createLinearGradient(0,H*0.35,0,H*0.67);g.addColorStop(0,"rgba(255,190,120,.85)");g.addColorStop(1,"rgba(255,150,80,.2)");ctx.fillStyle=g;ctx.fillRect(1.1,H*0.37,W-2.2,H*0.28);
    ctx.fillStyle=CAL.cream;ctx.fillRect(W/2-0.7,H*0.55,1.4,1.2);dButtons(1,H*0.15,3,1,0.9,o.seed||1);dGrille(1,H*0.78,W-2,H*0.14);dWear(W,H,3)})};
// café table: weighted base, slim column, round wood top with a brass edge
SV.hab.cafeTable=(x,y)=>{ell(x,y,3.2,0.02,"rgba(0,0,0,.3)");cyl(x,y,2.2,0,0.7,"#3a3d43","#2a2c31",{n:12});cyl(x,y,0.5,0.7,6.2,null,CAL.brass,{n:8});cyl(x,y,4.4,6.2,7,CAL.woodHi,CAL.wood,{n:18});ell(x,y,4.4,7.02,null,CAL.brass,0.35);ell(x,y,1,7.03,"rgba(232,225,212,.85)")};
// café chair / stool: moulded shell on a swivel pedestal (the pod-chair read: you see INSIDE the shell)
SV.hab.shellChair=(x,y,u,o={})=>{const fr={cx:x,cy:y,a:[-u[1],u[0]],f:u};ell(x,y,2.6,0.02,"rgba(0,0,0,.3)");cyl(x,y,1.6,0,0.5,"#3a3d43","#2a2c31",{n:10});cyl(x,y,0.4,0.5,3.6,null,"#9aa1a9",{n:6});
  habX(frameCham(fr,-2.4,2.4,-2.4,2.2,1),3.6,4.8,o.col||CAL.fabricHi,o.colLo||CAL.fabric,{mat:false});habX(frameCham(fr,-2.4,2.4,-2.8,-1.8,0.6),4.8,9,o.col||CAL.fabricHi,o.colLo||CAL.fabric,{mat:false});
  onTop(fr,-1.9,1.9,-1.8,1.8,4.82,(W,Dd)=>{ctx.fillStyle="rgba(255,240,215,.12)";ctx.beginPath();ctx.ellipse(W/2,Dd/2,W*0.42,Dd*0.4,0,0,TAU);ctx.fill()})};
// sofa: plinth with feet, frame, two seat cushions, back cushions, arms with brass caps (one softer edge tint)
SV.hab.sofa=(fr,o={})=>{const hL=fr.L/2,hD=fr.D/2;feet(fr,-hL,hL,-hD,hD,0.8);habX(frameCham(fr,-hL,hL,-hD,hD,0.8),0.8,3.6,CAL.fabric,"#4a3d3b");
  const n=Math.max(1,Math.round(fr.L/9));for(let i=0;i<n;i++){const s0=-hL+1.6+i*(fr.L-3.2)/n,s1=s0+(fr.L-3.2)/n-0.3;habX(frameCham(fr,s0,s1,-hD+2.4,hD-0.4,0.9),3.6,5.4,CAL.fabricHi,CAL.fabric,{mat:false});habX(frameCham(fr,s0,s1,-hD+0.4,-hD+2.6,0.6),3.6,10,CAL.fabricHi,CAL.fabric,{mat:false})}
  for(const sg of [-1,1]){const s0=sg<0?-hL:hL-1.6;habX(frameCham(fr,s0,s0+1.6,-hD,hD,0.5),3.6,7.4,CAL.fabricHi,CAL.fabric,{mat:false});onTop(fr,s0+0.3,s0+1.3,-hD+0.4,hD-0.4,7.42,(W,Dd)=>{ctx.fillStyle=CAL.brass;ctx.fillRect(0,0,W,0.4);ctx.fillRect(0,Dd-0.4,W,0.4)})}};
// glass coffee table: steel frame on four legs with a lower shelf seen THROUGH a translucent pane
SV.hab.glassTable=(fr)=>{const hL=fr.L/2,hD=fr.D/2;for(const [s,d] of [[-hL+0.4,-hD+0.4],[hL-1.2,-hD+0.4],[-hL+0.4,hD-1.2],[hL-1.2,hD-1.2]])habX(frameRect(fr,s,s+0.8,d,d+0.8),0,5,"#9aa1a9","#6a6d73",{mat:false,lw:0.3});
  habX(frameRect(fr,-hL+0.6,hL-0.6,-hD+0.6,hD-0.6),1.6,2.2,CAL.woodHi,CAL.wood,{mat:false,shadow:false});onTop(fr,-hL+1,hL-1,-hD+1,hD-1,2.22,(W,Dd)=>{ctx.fillStyle="#c9c2b0";ctx.fillRect(W*0.2,Dd*0.3,W*0.3,Dd*0.35);ctx.fillStyle="#3c6f9a";ctx.fillRect(W*0.6,Dd*0.35,W*0.2,Dd*0.25)});
  const top=frameCham(fr,-hL,hL,-hD,hD,0.8);ctx.fillStyle="rgba(170,215,225,.28)";ctx.fill(poly2(top,5.2));ctx.strokeStyle="rgba(225,245,250,.6)";ctx.lineWidth=0.35;ctx.stroke(poly2(top,5.2))};
// woven rug: soft bound rim (no black lip), a border band and a pile fleck
SV.hab.rug=(b)=>{const q=rectPoly(b[0]+1,b[1]+1,b[2]-1,b[3]-1);ctx.fillStyle="#7a5a48";ctx.fill(poly2(q,0.03));ctx.strokeStyle="#a2836a";ctx.lineWidth=1.1;ctx.stroke(poly2(rectPoly(b[0]+2.6,b[1]+2.6,b[2]-2.6,b[3]-2.6),0.035));
  ctx.strokeStyle="#5a3f30";ctx.lineWidth=0.5;ctx.stroke(poly2(rectPoly(b[0]+4.2,b[1]+4.2,b[2]-4.2,b[3]-4.2),0.035));ctx.fillStyle="rgba(255,235,210,.1)";for(let x=b[0]+3;x<b[2]-3;x+=2.2)for(let y=b[1]+3+((x*7)%3);y<b[3]-3;y+=3){const p=V.P(x,y,0.04);ctx.fillRect(p[0],p[1],0.5,0.5)}};
// billiard table: four turned legs, wood carcass with brass corner caps, rails, felt bed with pockets and a lit spot
SV.hab.pool=(fr)=>{const hL=fr.L/2,hD=fr.D/2;for(const [s,d] of [[-hL+1.4,-hD+1.4],[hL-3,-hD+1.4],[-hL+1.4,hD-3],[hL-3,hD-3]])habX(frameCham(fr,s,s+1.6,d,d+1.6,0.4),0,5.4,CAL.woodHi,CAL.wood,{mat:false});
  habX(frameCham(fr,-hL+0.6,hL-0.6,-hD+0.6,hD-0.6,1),5.4,7.4,CAL.woodHi,CAL.wood);habX(frameCham(fr,-hL,hL,-hD,hD,1.2),7.4,8.6,CAL.woodHi,CAL.woodLo,{mat:false});
  const bed=frameRect(fr,-hL+1.8,hL-1.8,-hD+1.8,hD-1.8);ctx.fillStyle=CAL.felt;ctx.fill(poly2(bed,8.62));ctx.fillStyle="rgba(120,220,180,.12)";ctx.fill(poly2(frameRect(fr,-hL*0.5,hL*0.5,-hD*0.5,hD*0.5),8.63));
  for(const [s,d] of [[-hL+1.8,-hD+1.8],[0,-hD+1.8],[hL-1.8,-hD+1.8],[-hL+1.8,hD-1.8],[0,hD-1.8],[hL-1.8,hD-1.8]])ell(fr.cx+fr.a[0]*s+fr.f[0]*d,fr.cy+fr.a[1]*s+fr.f[1]*d,0.9,8.64,"#0d1a16");
  for(const [s,d] of [[-hL+0.6,-hD+0.6],[hL-0.6,-hD+0.6],[-hL+0.6,hD-0.6],[hL-0.6,hD-0.6]]){const p=V.P(fr.cx+fr.a[0]*s+fr.f[0]*d,fr.cy+fr.a[1]*s+fr.f[1]*d,8.64);ctx.fillStyle=CAL.brassHi;ctx.fillRect(p[0]-0.6,p[1]-0.4,1.2,0.8)}};
// cue / shelf rack: wood frame, two shelves, upright cues in a brass rail
SV.hab.rack=(fr)=>{const hL=fr.L/2,hD=fr.D/2;habX(frameRect(fr,-hL,hL,-hD,hD),0,1,CAL.woodLo,CAL.woodLo,{mat:false});for(const sg of [-1,1])habX(frameRect(fr,sg<0?-hL:hL-1,sg<0?-hL+1:hL,-hD,hD),1,16,CAL.woodHi,CAL.wood,{mat:false});
  habX(frameRect(fr,-hL+1,hL-1,-hD,-hD+0.8),1,16,CAL.wood,CAL.woodLo,{mat:false,shadow:false});const [a,b,n]=faces(fr,-hL+1,hL-1,-hD,-hD+0.8).front;onFace(a,b,n,1,16,(W,H)=>{for(let x=1;x<W-0.6;x+=1.4){ctx.fillStyle=Math.floor(x)%3?"#d8b88a":"#7a5230";ctx.fillRect(x,1,0.45,H-3)}ctx.fillStyle=CAL.brass;ctx.fillRect(0,H*0.35,W,0.4);ctx.fillStyle="#2a1d16";ctx.fillRect(0,H-1.8,W,1.8)})};
// cosmetic rest pod: a reclined moulded shell (lining inset, cushion) on a pedestal; never shows vitals
SV.hab.restPod=(fr)=>{ell(fr.cx,fr.cy,4.2,0.02,"rgba(0,0,0,.3)");cyl(fr.cx,fr.cy,2.4,0,1.2,"#3a3d43","#2a2c31",{n:12});habX(frameCham(fr,-3.6,3.6,-4,4,1.6),1.2,4.4,CAL.cream,CAL.creamLo);
  habX(frameCham(fr,-3.6,3.6,-4.4,-1.6,1.2),4.4,10.6,CAL.cream,CAL.creamLo,{mat:false});onTop(fr,-2.8,2.8,-1.4,3.4,4.42,(W,Dd)=>{ctx.fillStyle="#8a6a5a";ctx.beginPath();ctx.ellipse(W/2,Dd/2,W*0.45,Dd*0.45,0,0,TAU);ctx.fill();ctx.fillStyle="rgba(255,240,215,.18)";ctx.beginPath();ctx.ellipse(W/2,Dd*0.3,W*0.3,Dd*0.18,0,0,TAU);ctx.fill()})};
// recovery pod (REAL cooldown, EQP-004): clinical base with service panels, a cream bed, a glass canopy, a status strip that stays
// dim (it shows a countdown only from agent.resting events, which this prototype does not have)
SV.hab.recoveryPod=(fr,o={})=>{const hL=fr.L/2,hD=fr.D/2;plinth(fr,-hL,hL,-hD,hD,1);habX(frameCham(fr,-hL+0.4,hL-0.4,-hD+0.4,hD-0.4,1.2),1,5.2,"#cfd4d8","#9aa3aa");
  const [a,b,n]=faces(fr,-hL+0.4,hL-0.4,-hD+0.4,hD-0.4).front;onFace(a,b,n,1,5.2,(W,H)=>{dHatch(1,0.6,W*0.3,H-1.2);ctx.fillStyle="#0f1c22";ctx.fillRect(W*0.4,H*0.3,W*0.5,H*0.35);ctx.fillStyle="rgba(95,224,160,.25)";ctx.fillRect(W*0.42,H*0.42,W*0.46,0.4)});
  habX(frameCham(fr,-hL+1.2,hL-1.2,-hD+1.2,hD-1.2,1),5.2,6.2,CAL.cream,CAL.creamLo,{mat:false});const can=frameCham(fr,-hL+1.4,hL-1.4,-hD+1.4,hD-1.4,1.6);
  ctx.fillStyle="rgba(170,225,240,.16)";ctx.fill(poly2(can,10.2));ctx.strokeStyle="rgba(210,245,250,.6)";ctx.lineWidth=0.4;ctx.stroke(poly2(can,10.2));for(const p of can.filter((_,i)=>i%2===0))line3([p[0],p[1],6.2],[p[0],p[1],10.2],"rgba(210,245,250,.35)",0.3)};
// central planter (hero): hexagonal bulkhead-built planter: plinth, wood seating ledge, brass rim, soil, a layered tree with lit canopy
SV.hab.planter=(cx,cy,R)=>{const hex=(r)=>{const p=[];for(let k=0;k<8;k++){const a=k*TAU/8+Math.PI/8;p.push([cx+r*Math.cos(a),cy+r*Math.sin(a)])}return p};
  habX(hex(R+2.4),0,1.2,"#2a2c31","#1d1f23");habX(hex(R+1.6),1.2,4.2,CAL.woodHi,CAL.wood);habX(hex(R),4.2,6.6,"#4a4c52",CAL.gun);ctx.strokeStyle=CAL.brass;ctx.lineWidth=0.6;ctx.stroke(poly2(hex(R),6.62));ctx.fillStyle="#2a2018";ctx.fill(poly2(hex(R-1.2),6.64));
  cyl(cx,cy,2,6.6,22,"#6b4f36","#5a4230",{n:10});for(const [dx,dy,hh,r,c] of [[0,0,20,13,CAL.leafLo],[-5,3,24,10,CAL.leaf],[5,-3,27,9.5,"#4a9156"],[2,4,23,8,CAL.leaf],[0,0,31,7,CAL.leafHi],[-3,-3,29,6,"#4a9156"]]){const s2=V.P(cx+dx,cy+dy,hh);ctx.fillStyle=c;ctx.beginPath();for(let k=0;k<9;k++){const a=k/9*TAU;const rr=r*(k%2?0.78:1);ctx.lineTo(s2[0]+rr*Math.cos(a)*1.1,s2[1]+rr*Math.sin(a)*0.72)}ctx.closePath();ctx.fill();ctx.strokeStyle="rgba(20,40,20,.35)";ctx.lineWidth=0.3;ctx.stroke()}
  for(let k=0;k<8;k++){const a=k*TAU/8;const p=V.P(cx+(R+0.6)*Math.cos(a),cy+(R+0.6)*Math.sin(a),6.7);ctx.fillStyle="rgba(255,226,170,.85)";ctx.fillRect(p[0]-0.4,p[1]-0.25,0.8,0.5)}};
// window bench: upholstered bench on a wood base with a low back
SV.hab.bench=(fr)=>{const hL=fr.L/2,hD=fr.D/2;habX(frameRect(fr,-hL+0.6,hL-0.6,-hD+0.8,hD-0.8),0,3,CAL.wood,CAL.woodLo);habX(frameCham(fr,-hL,hL,-hD,hD,0.6),3,4.6,CAL.fabricHi,CAL.fabric,{mat:false});habX(frameCham(fr,-hL,hL,-hD,-hD+1.4,0.4),4.6,8.6,CAL.fabricHi,CAL.fabric,{mat:false})};
// HAB wall faces: warm panel (wood inlay in a bulkhead frame with a brass sconce), viewport (framed windows onto the planet/star
// view, DEC-001/002), living wall (planted panel, PLT-004)
SV.wall.warm=(W,H,seed)=>{SV.wall.band(W,H);ctx.fillStyle=CAL.woodLo;ctx.fillRect(1.4,2.4,W-2.8,H-6);for(let x=2;x<W-1.6;x+=2.6){ctx.fillStyle=Math.floor(x)%2?CAL.wood:"#5e4129";ctx.fillRect(x,2.6,2.4,H-6.4)}
  ctx.fillStyle=CAL.brass;ctx.fillRect(1.4,2.4,W-2.8,0.3);ctx.fillRect(1.4,H-3.9,W-2.8,0.3);ctx.fillStyle="rgba(255,215,150,.35)";ctx.fillRect(W/2-2.4,3,4.8,2.4);ctx.fillStyle="#f6e2bc";ctx.fillRect(W/2-1,3.4,2,1);dWear(W,H-3,seed)};
SV.wall.viewport=(W,H,seed)=>{SV.wall.band(W,H);ctx.fillStyle="#1d1f23";ctx.fillRect(0.6,2,W-1.2,H-5);const g=ctx.createLinearGradient(0,2.6,0,H-3.6);g.addColorStop(0,"#0a1430");g.addColorStop(1,"#1d3a66");ctx.fillStyle=g;ctx.fillRect(1.4,2.8,W-2.8,H-6.6);
  ctx.fillStyle="rgba(220,235,255,.8)";for(let k=0;k<6;k++){const x=1.8+((seed*37+k*53)%100)/100*(W-3.6),y=3.2+((seed*11+k*29)%100)/100*(H-7.6);ctx.fillRect(x,y,0.3,0.3)}
  ctx.fillStyle="rgba(120,180,230,.22)";ctx.beginPath();ctx.ellipse(W*0.7,H-3.2,W*0.5,(H-6)*0.35,0,Math.PI,TAU);ctx.fill();ctx.fillStyle="#2e3137";ctx.fillRect(W/2-0.4,2.8,0.8,H-6.6);ctx.fillStyle="rgba(255,255,255,.08)";ctx.fillRect(1.6,3,W*0.25,H-7);dRivets(0.6,2,W-1.2,H-5)};
SV.wall.living=(W,H,seed)=>{SV.wall.band(W,H);ctx.fillStyle="#1d1f23";ctx.fillRect(0.8,2.2,W-1.6,H-5.4);ctx.fillStyle="#2a2018";ctx.fillRect(1.4,2.8,W-2.8,H-6.6);const C=[CAL.leafLo,CAL.leaf,CAL.leafHi,"#4a9156"];
  for(let k=0;k<26;k++){const x=1.6+((seed*13+k*41)%100)/100*(W-3.2),y=3+((seed*7+k*61)%100)/100*(H-7.4);ctx.fillStyle=C[k%4];ctx.beginPath();ctx.ellipse(x,y,1.3,0.9,(k%5)*0.6,0,TAU);ctx.fill()}ctx.fillStyle=CAL.brass;ctx.fillRect(0.8,H-3.6,W-1.6,0.35)};
// ---- HABITAT PARK: fountain, park tree, garden bed, dog corner, resident dog (the same construction language, organic materials)
// fountain (hero): a stone-capped octagonal basin with a bolted metal skirt and recessed lights, water with a lit surface and ripple
// rings, a two-tier central column (lower bowl, upper bowl, finial) with falling water arcs. Decorative; no data
SV.hab.fountain=(cx,cy,R,t)=>{const oct=(r)=>{const p=[];for(let k=0;k<8;k++){const a=k*TAU/8+Math.PI/8;p.push([cx+r*Math.cos(a),cy+r*Math.sin(a)])}return p};const ph=((t||0)/900)%1;
  prismX(oct(R+1.4),0,0.8,"#2a2c31","#1d1f23",{lw:0.4});prismX(oct(R+0.6),0.8,3.6,"#3d4046","#2f3237");for(let k=0;k<8;k++){const a=k*TAU/8+Math.PI/8+TAU/16;const p=V.P(cx+(R+0.62)*Math.cos(a),cy+(R+0.62)*Math.sin(a),2.2);ctx.fillStyle="rgba(150,230,240,.8)";ctx.fillRect(p[0]-0.4,p[1]-0.25,0.8,0.5)}
  prismX(oct(R+0.9),3.6,4.6,"#cfc7b8","#a89f8f",{mat:false});ctx.fillStyle="#0e3a44";ctx.fill(poly2(oct(R-0.6),3.9));
  ctx.save();ctx.clip(poly2(oct(R-0.6),3.95));const s=V.P(cx,cy,3.95);const g=ctx.createRadialGradient(s[0],s[1],0,s[0],s[1],V.kx*R);g.addColorStop(0,"rgba(120,225,235,.55)");g.addColorStop(1,"rgba(30,110,125,.35)");ctx.fillStyle=g;ctx.fillRect(s[0]-R*1.5,s[1]-R*1.5,R*3,R*3);
  for(let k=0;k<3;k++){const rr=(k/3+ph)%1*(R-1);ell(cx,cy,rr,3.96,null,`rgba(220,250,255,${0.55*(1-rr/R)})`,0.35)}ctx.restore();ctx.strokeStyle="rgba(230,250,255,.6)";ctx.lineWidth=0.35;ctx.stroke(poly2(oct(R-0.6),3.97));
  cyl(cx,cy,1.6,3.9,6.6,"#cfc7b8","#a89f8f",{n:12});cyl(cx,cy,R*0.42,6.6,7.4,"#cfc7b8","#a89f8f",{n:16});ell(cx,cy,R*0.38,7.42,"rgba(120,220,232,.7)");cyl(cx,cy,0.8,7.4,10.4,"#b8904e","#8a6a36",{n:10});cyl(cx,cy,1.6,10.4,10.9,"#cfc7b8","#a89f8f",{n:12});cyl(cx,cy,0.5,10.9,12.4,null,"#e1bb72",{n:8});
  ctx.strokeStyle="rgba(210,245,250,.7)";ctx.lineWidth=0.35;for(let k=0;k<8;k++){const a=k*TAU/8;const p0=V.P(cx,cy,12.2),p1=V.P(cx+R*0.42*Math.cos(a),cy+R*0.42*Math.sin(a),7.6);ctx.beginPath();ctx.moveTo(p0[0],p0[1]);ctx.quadraticCurveTo((p0[0]+p1[0])/2,p0[1]-1.2,p1[0],p1[1]);ctx.stroke();
    const q1=V.P(cx+R*0.6*Math.cos(a),cy+R*0.6*Math.sin(a),4.1);ctx.beginPath();ctx.moveTo(p1[0],p1[1]);ctx.quadraticCurveTo((p1[0]+q1[0])/2,p1[1]+0.2,q1[0],q1[1]);ctx.stroke()}};
// park tree: a stone ring with soil, a tapering trunk, and a layered canopy (lit top, darker underside)
SV.hab.tree=(x,y,o={})=>{const sd=o.seed||0;cyl(x,y,4.2,0,1.6,"#cfc7b8","#a89f8f",{n:12});ell(x,y,3.6,1.62,"#2a2018");cyl(x,y,0.9,1.6,12,null,"#6b4f36",{n:8});
  const C=["#2f6a3c","#3c8048","#4d9a58","#5aa765"];for(const [dx,dy,h,r,c] of [[0,0,12,6.4,0],[-2,1.4,14.5,4.8,1],[2,-1.2,15.5,4.6,2],[0.4,0.2,18,3.6,3],[-1,-1.6,16.6,3.2,2]]){const p=V.P(x+dx,y+dy,h+(sd%3)*0.4);ctx.fillStyle=C[c];ctx.beginPath();for(let k=0;k<9;k++){const a=k/9*TAU;const rr=r*(k%2?0.8:1);ctx.lineTo(p[0]+rr*Math.cos(a)*1.05,p[1]+rr*Math.sin(a)*0.75)}ctx.closePath();ctx.fill();ctx.strokeStyle="rgba(20,40,20,.35)";ctx.lineWidth=0.3;ctx.stroke()}};
// garden bed: a low stone-edged planter with soil and mixed low planting (ferns, grasses, a few flowers)
SV.hab.bed=(fr,o={})=>{const hL=fr.L/2,hD=fr.D/2,sd=o.seed||0;prismX(frameCham(fr,-hL,hL,-hD,hD,1.2),0,2.2,"#cfc7b8","#a89f8f");ctx.fillStyle="#2a2018";ctx.fill(poly2(frameCham(fr,-hL+0.8,hL-0.8,-hD+0.8,hD-0.8,0.9),2.22));
  const C=["#2f6a3c","#3c8048","#4d9a58","#5aa765"],F=["#e0b25a","#c86a5a","#d8cdb8","#9fb8e8"];let r=(sd*16807+11)%2147483647;const R=()=>{r=(r*16807)%2147483647;return r/2147483647};
  for(let k=0;k<14;k++){const s0=(R()*2-1)*(hL-1.4),d0=(R()*2-1)*(hD-1.2);const p=V.P(fr.cx+fr.a[0]*s0+fr.f[0]*d0,fr.cy+fr.a[1]*s0+fr.f[1]*d0,2.4+R()*2.6);ctx.fillStyle=C[k%4];ctx.beginPath();ctx.ellipse(p[0],p[1],1.4+R(),0.9+R()*0.6,R()*3,0,TAU);ctx.fill()}
  for(let k=0;k<5;k++){const s0=(R()*2-1)*(hL-1.6),d0=(R()*2-1)*(hD-1.4);const p=V.P(fr.cx+fr.a[0]*s0+fr.f[0]*d0,fr.cy+fr.a[1]*s0+fr.f[1]*d0,4.6);ctx.fillStyle=F[k%4];ctx.beginPath();ctx.arc(p[0],p[1],0.45,0,TAU);ctx.fill()}};
// resident station dog: compact, outlined like the crew (large head, strong outline), sitting, tan coat, a teal collar with a tag
SV.hab.dog=(x,y,o={})=>{const s=V.P(x,y,0);ell(x,y,2.8,0.02,"rgba(0,0,0,.35)");ctx.save();ctx.translate(s[0],s[1]);const O="#2a1d16",coat=o.coat||"#c9965a",dark="#8a5e34",lw=0.55;ctx.lineJoin="round";ctx.strokeStyle=O;ctx.lineWidth=lw;
  ctx.fillStyle=coat;ctx.beginPath();ctx.ellipse(0.8,-2.4,2.4,2.2,0,0,TAU);ctx.fill();ctx.stroke(); // haunch
  ctx.beginPath();ctx.moveTo(2.6,-2.6);ctx.quadraticCurveTo(4.8,-3.2,4.6,-5.4);ctx.lineWidth=0.9;ctx.stroke();ctx.strokeStyle=coat;ctx.lineWidth=0.5;ctx.stroke();ctx.strokeStyle=O;ctx.lineWidth=lw; // tail
  ctx.fillStyle=coat;ctx.beginPath();ctx.moveTo(-1.6,-1);ctx.lineTo(-1.2,-5.6);ctx.lineTo(1.2,-5.8);ctx.lineTo(1,-1);ctx.closePath();ctx.fill();ctx.stroke(); // chest
  ctx.fillStyle="#efe0c4";ctx.beginPath();ctx.ellipse(-0.2,-3.4,0.9,1.4,0,0,TAU);ctx.fill();
  for(const px of [-1.2,0.4]){ctx.fillStyle=coat;ctx.fillRect(px,-1.8,0.9,1.8);ctx.strokeRect(px,-1.8,0.9,1.8);ctx.fillStyle="#efe0c4";ctx.fillRect(px,-0.5,0.9,0.5)}
  ctx.fillStyle="#3fb7cc";ctx.fillRect(-1.4,-5.9,2.7,0.6);ctx.fillStyle="#e1bb72";ctx.beginPath();ctx.arc(0,-5.1,0.35,0,TAU);ctx.fill(); // collar + tag
  ctx.fillStyle=coat;ctx.beginPath();ctx.ellipse(-0.2,-7.6,2.1,1.9,0,0,TAU);ctx.fill();ctx.stroke(); // head
  ctx.fillStyle="#efe0c4";ctx.beginPath();ctx.ellipse(-1.4,-7,1.2,0.85,0,0,TAU);ctx.fill();ctx.strokeStyle=O;ctx.lineWidth=0.35;ctx.stroke();ctx.fillStyle="#1a1a1a";ctx.beginPath();ctx.arc(-2.4,-7.2,0.35,0,TAU);ctx.fill(); // muzzle + nose
  ctx.fillStyle=dark;for(const ex of [-1.2,1.3]){ctx.beginPath();ctx.ellipse(ex,-8.6,0.7,1.5,ex<0?0.5:-0.5,0,TAU);ctx.fill();ctx.lineWidth=0.4;ctx.stroke()}
  ctx.fillStyle="#1a1a1a";ctx.beginPath();ctx.arc(-0.9,-8,0.28,0,TAU);ctx.fill();ctx.beginPath();ctx.arc(0.5,-8,0.28,0,TAU);ctx.fill();ctx.restore()};
// ================================================================ RECREATION family (habitat rooms R1 zen, R2 cinema, R3 decompression)
SV.rec={};
// meditation mat + round cushion (walk-over)
SV.rec.mat=(fr,o={})=>{const hL=fr.L/2||5,hD=fr.D/2||3.4;prismX(frameCham(fr,-hL,hL,-hD,hD,0.8),0,0.5,o.col||"#7a8a6a",o.colLo||"#5e6b52",{lw:0.3,mat:false});
  onTop(fr,-hL+0.6,hL-0.6,-hD+0.6,hD-0.6,0.52,(W,Dd)=>{ctx.strokeStyle="rgba(0,0,0,.18)";ctx.lineWidth=0.2;for(let x=1;x<W;x+=1.4){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,Dd);ctx.stroke()}});
  const c=[fr.cx+fr.a[0]*(-hL*0.45),fr.cy+fr.a[1]*(-hL*0.45)];cyl(c[0],c[1],1.8,0.5,1.8,"#c9a77c","#8c6239",{n:14});ell(c[0],c[1],1.2,1.82,null,"rgba(255,240,215,.4)",0.25)};
// ambient speaker column: a slim wood-clad column with a fabric grille and a warm status pip (world-building: no audio)
SV.rec.speaker=(x,y)=>{prismX(rectPoly(x-2.2,y-2.2,x+2.2,y+2.2),0,0.8,"#2a2c31","#1d1f23",{lw:0.3,mat:false,hi:false});prismX(rectPoly(x-1.7,y-1.7,x+1.7,y+1.7),0.8,13,"#8c6239","#6b4a2f",{lw:0.35});
  for(const [n,a,b] of [[[0,1],[x-1.7,y+1.7],[x+1.7,y+1.7]],[[1,0],[x+1.7,y+1.7],[x+1.7,y-1.7]]])onFace(a,b,n,0.8,13,(W,H)=>{ctx.fillStyle="#2a2420";ctx.fillRect(0.5,1,W-1,H-3);ctx.fillStyle="rgba(255,240,215,.08)";for(let k=1.4;k<H-2;k+=0.7)ctx.fillRect(0.6,k,W-1.2,0.2);ctx.fillStyle="#3a302a";ctx.beginPath();ctx.arc(W/2,H*0.3,W*0.28,0,TAU);ctx.fill();ctx.beginPath();ctx.arc(W/2,H*0.62,W*0.2,0,TAU);ctx.fill();ctx.fillStyle="#f0b860";ctx.fillRect(W/2-0.2,H-1.6,0.4,0.3)})};
// zen sand garden: a low wood-framed bed of raked sand with three stones and a small tree
SV.rec.garden=(fr)=>{const hL=fr.L/2,hD=fr.D/2;prismX(frameCham(fr,-hL,hL,-hD,hD,1),0,1.6,"#8c6239","#6b4a2f");const sand=frameRect(fr,-hL+1,hL-1,-hD+1,hD-1);ctx.fillStyle="#d8cdb8";ctx.fill(poly2(sand,1.62));
  ctx.save();ctx.clip(poly2(sand,1.62));for(let k=-hD;k<hD;k+=1.1)line3([fr.cx-fr.a[0]*hL+fr.f[0]*k,fr.cy-fr.a[1]*hL+fr.f[1]*k,1.63],[fr.cx+fr.a[0]*hL+fr.f[0]*k,fr.cy+fr.a[1]*hL+fr.f[1]*k,1.63],"rgba(140,120,95,.45)",0.25);ctx.restore();
  for(const [s,d,r] of [[-hL*0.45,-hD*0.2,2.2],[-hL*0.2,hD*0.35,1.4],[hL*0.1,-hD*0.3,1.1]]){const x=fr.cx+fr.a[0]*s+fr.f[0]*d,y=fr.cy+fr.a[1]*s+fr.f[1]*d;ell(x,y,r+1.6,1.64,null,"rgba(140,120,95,.5)",0.25);cyl(x,y,r,1.6,1.6+r*1.1,"#8a8f96","#5e636a",{n:9})}
  SV.hab.tree(fr.cx+fr.a[0]*hL*0.55,fr.cy+fr.a[1]*hL*0.55,{seed:4})};
// cinema screen: a wide physical screen on wall brackets, with masking borders; dark, no display identity, no content
SV.rec.screen=(fr,h0,h1)=>{const hL=fr.L/2;prismX(frameRect(fr,-hL-1.6,hL+1.6,-1.6,0),h0-1.2,h1+1.2,"#1d1f23","#141517",{lw:0.4,shadow:false});
  const [a,b,n]=faces(fr,-hL-1.6,hL+1.6,-1.6,0).front;onFace(a,b,n,h0-1.2,h1+1.2,(W,H)=>{ctx.fillStyle="#0a0b0d";ctx.fillRect(0,0,W,H);ctx.fillStyle="#1d2630";ctx.fillRect(2.4,1.6,W-4.8,H-3.2);const g=ctx.createLinearGradient(0,1.6,0,H-1.6);g.addColorStop(0,"rgba(180,200,220,.10)");g.addColorStop(1,"rgba(0,0,0,0)");ctx.fillStyle=g;ctx.fillRect(2.4,1.6,W-4.8,H-3.2);
    ctx.fillStyle="rgba(255,255,255,.05)";ctx.beginPath();ctx.moveTo(W*0.1,1.6);ctx.lineTo(W*0.3,1.6);ctx.lineTo(W*0.15,H-1.6);ctx.lineTo(W*-0.05,H-1.6);ctx.closePath();ctx.fill();dRivets(0.4,0.4,W-0.8,H-0.8,"#3a3d43")})};
// cinema recliner pair on a stepped riser: carpeted riser with an aisle-light strip, two upholstered recliners with cup-holder arms
SV.rec.recliners=(fr,h0,n)=>{const hL=fr.L/2,hD=fr.D/2;if(h0>0.05){prismX(frameRect(fr,-hL-1,hL+1,-hD-1,hD+1),0,h0,"#3a2a30","#2a1f24",{lw:0.35,shadow:false});const [a,b,nn]=faces(fr,-hL-1,hL+1,-hD-1,hD+1).front;onFace(a,b,nn,0,h0,(W,H)=>{for(let x=1;x<W;x+=3){ctx.fillStyle="rgba(255,190,110,.75)";ctx.fillRect(x,H*0.4,0.8,0.4)}})}
  const seatW=(fr.L-1)/n;for(let i=0;i<n;i++){const s0=-hL+0.5+i*seatW;const sf={cx:fr.cx+fr.a[0]*(s0+seatW/2),cy:fr.cy+fr.a[1]*(s0+seatW/2),a:fr.a,f:fr.f};const w=seatW/2-0.9;
    prismX(frameCham(sf,-w,w,-hD+0.6,hD-0.6,0.8),h0,h0+3,"#7a3a44","#5a2a32");prismX(frameCham(sf,-w,w,-hD+0.4,-hD+2,0.6),h0+3,h0+8.4,"#7a3a44","#5a2a32",{mat:false});
    for(const sg of [-1,1])prismX(frameRect(sf,sg*w+(sg<0?-0.9:0),sg*w+(sg<0?0:0.9),-hD+0.6,hD-0.6),h0,h0+4.4,"#3a3d43","#26282c",{lw:0.3,mat:false});const cp=V.P(sf.cx+sf.a[0]*(w+0.45)+sf.f[0]*(hD-1.2),sf.cy+sf.a[1]*(w+0.45)+sf.f[1]*(hD-1.2),h0+4.45);ctx.fillStyle="#0e0f11";ctx.beginPath();ctx.arc(cp[0],cp[1],0.35,0,TAU);ctx.fill()}};
// projector stand: a low cabinet with a lens hood; the lens is dark (no content is projected)
SV.rec.projector=(fr)=>{plinth(fr,-4,4,-3,3,0.8);prismX(frameCham(fr,-3.4,3.4,-2.6,2.6,0.6),0.8,9,"#45484f",CAL.gun);prismX(frameCham(fr,-3,3,-2.4,2.4,0.8),9,12.4,"#2a2c31","#1d1f23");
  const lp=[fr.cx+fr.f[0]*2.8,fr.cy+fr.f[1]*2.8];cyl(lp[0],lp[1],1.1,10,11.6,"#0e0f11","#2a2c31",{n:10});const [a,b,n]=faces(fr,-3.4,3.4,-2.6,2.6).front;onFace(a,b,n,0.8,9,(W,H)=>{dGrille(0.8,0.8,W-1.6,H*0.3);dRecess(0.8,H*0.5,W-1.6,H*0.4,"#24262a");dIndicator(W-1.6,H*0.55,false)})};
// padded bench (R3): a low upholstered block on a recessed plinth
SV.rec.padBench=(fr)=>{const hL=fr.L/2,hD=fr.D/2;prismX(frameRect(fr,-hL+0.6,hL-0.6,-hD+0.6,hD-0.6),0,1,"#26282c","#1d1f23",{lw:0.3,mat:false});prismX(frameCham(fr,-hL,hL,-hD,hD,1),1,4.4,"#6e6a74","#55515c");
  onTop(fr,-hL+0.6,hL-0.6,-hD+0.6,hD-0.6,4.42,(W,Dd)=>{ctx.fillStyle="rgba(0,0,0,.18)";for(let x=1.4;x<W;x+=2.6)for(let y=1;y<Dd;y+=2.2){ctx.beginPath();ctx.arc(x,y,0.25,0,TAU);ctx.fill()}})};
// ================================================================ CANINE family (R4 dog play room): compact agility set built like station equipment
// Steel frames, bolted feet, rubber-coated decks and fabric tunnels in the station palette (slate-teal decks, amber contact zones,
// gunmetal frames). Scaled to the resident dog (about 10 units sitting): A-frame apex 11, jump bar 4.5, weave poles 9, tunnel Ø 8.4
SV.dog={};
const dogP=(fr,s,d)=>[fr.cx+fr.a[0]*s+fr.f[0]*d,fr.cy+fr.a[1]*s+fr.f[1]*d];
const dog3=(fr,s,d,h)=>[...dogP(fr,s,d),h];
function q3(pts,fill,o={}){ctx.beginPath();pts.forEach((p,i)=>{const s=V.P(p[0],p[1],p[2]);i?ctx.lineTo(s[0],s[1]):ctx.moveTo(s[0],s[1])});ctx.closePath();if(fill){ctx.fillStyle=fill;ctx.fill()}
  if(o.out!==false){ctx.strokeStyle=o.out||CAL.out;ctx.lineWidth=o.lw||0.4;ctx.lineJoin="round";ctx.stroke()}}
function bar3(a,b,w,col){line3(a,b,CAL.out,w+0.55);line3(a,b,col,w)}
// a sloped deck from (s0,h0) to (s1,h1), slats across it, an amber contact zone over the last share near the floor
function dogDeck(fr,s0,h0,s1,h1,hD,col,zone){const len=Math.hypot(s1-s0,h1-h0)||1;const sg=Math.sign(s0-s1)*Math.sign(h1-h0);const hz=(fr.a[0]*LIGHT[0]+fr.a[1]*LIGHT[1])*sg*Math.abs(h1-h0)/len;const k=0.72+0.28*Math.max(0,Math.min(1,hz+0.6*Math.abs(s1-s0)/len));
  q3([dog3(fr,s0,-hD,h0),dog3(fr,s1,-hD,h1),dog3(fr,s1,hD,h1),dog3(fr,s0,hD,h0)],shade(col,k));
  if(zone){const z=zone,sa=s0+(s1-s0)*(h0<h1?0:1-z),sb=s0+(s1-s0)*(h0<h1?z:1),ha=h0+(h1-h0)*(h0<h1?0:1-z),hb=h0+(h1-h0)*(h0<h1?z:1);q3([dog3(fr,sa,-hD,ha),dog3(fr,sb,-hD,hb),dog3(fr,sb,hD,hb),dog3(fr,sa,hD,ha)],shade("#d8a64a",k),{lw:0.3})}
  const n=Math.max(2,Math.round(Math.hypot(s1-s0,h1-h0)/1.6));for(let i=1;i<n;i++){const t=i/n;line3(dog3(fr,s0+(s1-s0)*t,-hD,h0+(h1-h0)*t),dog3(fr,s0+(s1-s0)*t,hD,h0+(h1-h0)*t),"rgba(0,0,0,.32)",0.28)}
  for(const d of [-hD,hD])bar3(dog3(fr,s0,d,h0),dog3(fr,s1,d,h1),0.55,"#5d636b")}
// soft ball / toy (sphere with a lit cap and a contact shadow)
SV.dog.ball=(x,y,r,col)=>{ell(x,y,r*1.1,0.02,"rgba(0,0,0,.3)");const s=V.P(x,y,r);ctx.fillStyle=col;ctx.beginPath();ctx.arc(s[0],s[1],r*1.1,0,TAU);ctx.fill();ctx.strokeStyle=CAL.out;ctx.lineWidth=0.3;ctx.stroke();
  ctx.fillStyle="rgba(255,250,235,.55)";ctx.beginPath();ctx.arc(s[0]-r*0.35,s[1]-r*0.4,r*0.35,0,TAU);ctx.fill()};
// scattered toys: balls, a knotted rope toy and a ring toy
SV.dog.toys=(x,y,seed)=>{const C=["#e0b25a","#c86a5a","#5aa765","#3fb7cc"];let r=(seed*16807+7)%2147483647;const R=()=>{r=(r*16807)%2147483647;return r/2147483647};
  {const a=R()*TAU,p=[x+Math.cos(a)*4,y+Math.sin(a)*4];const q=[p[0]+Math.cos(a+1.2)*3.4,p[1]+Math.sin(a+1.2)*3.4];line3([...p,0.35],[...q,0.35],CAL.out,1.1);line3([...p,0.35],[...q,0.35],"#d8cdb8",0.7);for(const e of [p,q])SV.dog.ball(e[0],e[1],0.45,"#c86a5a")}
  {const a=R()*TAU;const c=[x+Math.cos(a)*5,y+Math.sin(a)*5];ell(c[0],c[1],1.1,0.2,null,CAL.out,0.75);ell(c[0],c[1],1.1,0.2,null,"#3fb7cc",0.45)}
  for(let k=0;k<3;k++){const a=R()*TAU,d=1.5+R()*5;SV.dog.ball(x+Math.cos(a)*d,y+Math.sin(a)*d,0.7,C[k%4])}};
// fabric tunnel on a curved line: steel hoops every few units, alternating amber and cream bays, ground straps with weights
SV.dog.tunnel=(fr,o={})=>{const hL=fr.L/2,bend=o.bend||0,r=o.r||4.2,hc=r*0.9,N=Math.max(24,Math.round(fr.L/0.6));
  const C=k=>dogP(fr,-hL+fr.L*k/N,bend*Math.sin(Math.PI*k/N));const disc=[];
  for(let k=0;k<=N;k++){const p=C(k),q=C(Math.min(N,k+1)),m=C(Math.max(0,k-1));let tx=q[0]-m[0],ty=q[1]-m[1];const L=Math.hypot(tx,ty)||1;tx/=L;ty/=L;
    const pts=[];for(let j=0;j<20;j++){const th=j/20*TAU;pts.push([p[0]-ty*r*Math.cos(th),p[1]+tx*r*Math.cos(th),Math.max(0,hc+r*Math.sin(th))])}disc.push({k,p,t:[tx,ty],pts})}
  const weights=[];for(const k of [Math.round(N*0.2),Math.round(N*0.8)]){const dd=disc[k];for(const sg of [-1,1]){const w=[dd.p[0]-dd.t[1]*(r+1.4)*sg,dd.p[1]+dd.t[0]*(r+1.4)*sg];weights.push({w,t:dd.t,near:camAlong([-dd.t[1]*sg,dd.t[0]*sg])>0})}}
  const wt=(q)=>{const f2={cx:q.w[0],cy:q.w[1],a:q.t,f:[-q.t[1],q.t[0]]};prismX(frameCham(f2,-1.6,1.6,-1.1,1.1,0.5),0,1.4,"#4a4f46","#383c35",{lw:0.3,mat:false})};
  for(const q of weights)if(!q.near)wt(q);
  // each bay between two neighbouring hoops is filled as the convex hull of both projected rings, so the skin stays closed edge-on
  const hull=(P)=>{P=P.slice().sort((A,B)=>A[0]-B[0]||A[1]-B[1]);const cr=(o,a,b)=>(a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0]);const lo=[],up=[];
    for(const q of P){while(lo.length>1&&cr(lo[lo.length-2],lo[lo.length-1],q)<=0)lo.pop();lo.push(q)}for(const q of P.slice().reverse()){while(up.length>1&&cr(up[up.length-2],up[up.length-1],q)<=0)up.pop();up.push(q)}return lo.slice(0,-1).concat(up.slice(0,-1))};
  const scr=d=>d.pts.map(q=>V.P(q[0],q[1],q[2]));const seg=[];for(let k=0;k<N;k++)seg.push({k,m:[(disc[k].p[0]+disc[k+1].p[0])/2,(disc[k].p[1]+disc[k+1].p[1])/2],h:hull(scr(disc[k]).concat(scr(disc[k+1])))});
  const ord=seg.sort((A,B)=>V.depth(...A.m)-V.depth(...B.m));const path=h=>{ctx.beginPath();h.forEach((q,i)=>i?ctx.lineTo(q[0],q[1]):ctx.moveTo(q[0],q[1]));ctx.closePath()};
  for(const g of ord){const c=V.P(g.m[0],g.m[1],hc);ctx.fillStyle=CAL.out;path(g.h.map(q=>[c[0]+(q[0]-c[0])*1.07,c[1]+(q[1]-c[1])*1.07]));ctx.fill()}
  const bays=Math.max(1,Math.round(N/7));
  for(const g of ord){const top=V.P(g.m[0],g.m[1],hc+r),bot=V.P(g.m[0],g.m[1],0);const band=Math.floor(g.k/bays)%2;const gr=ctx.createLinearGradient(0,top[1],0,bot[1]);
    gr.addColorStop(0,band?"#e8d7b2":"#e2a44c");gr.addColorStop(0.55,band?"#c4b08a":"#c4822f");gr.addColorStop(1,band?"#857556":"#7e521d");ctx.fillStyle=gr;path(g.h);ctx.fill();
    for(const kk of [g.k,g.k+1])if(kk%bays===0&&kk>0&&kk<N){ctx.strokeStyle="#3a3d43";ctx.lineWidth=0.55;path(scr(disc[kk]));ctx.stroke()}}
  for(const k of [0,N]){const d=disc[k];const out=k===0?[-d.t[0],-d.t[1]]:d.t;if(camAlong(out)<=0)continue;ctx.beginPath();d.pts.forEach((q,i)=>{const s=V.P(q[0],q[1],q[2]);i?ctx.lineTo(s[0],s[1]):ctx.moveTo(s[0],s[1])});ctx.closePath();ctx.strokeStyle=CAL.out;ctx.lineWidth=0.9;ctx.stroke();ctx.strokeStyle="#5d636b";ctx.lineWidth=0.5;ctx.stroke();
    ctx.fillStyle="#17120e";ctx.beginPath();d.pts.forEach((q,i)=>{const s=V.P(d.p[0]+(q[0]-d.p[0])*0.78,d.p[1]+(q[1]-d.p[1])*0.78,hc+(q[2]-hc)*0.78);i?ctx.lineTo(s[0],s[1]):ctx.moveTo(s[0],s[1])});ctx.closePath();ctx.fill()}
  for(const q of weights)if(q.near)wt(q)};
// A-frame: two slatted decks hinged at the apex, steel stringers, amber contact zones, chain braces, bolted floor rails
SV.dog.aframe=(fr,o={})=>{const hL=fr.L/2,hD=fr.D/2,H=o.h||11;const near=camAlong(fr.a)>0?1:-1;
  for(const sg of [-1,1])prismX(frameRect(fr,sg>0?hL-2.2:-hL,sg>0?hL:-hL+2.2,-hD-0.8,hD+0.8),0,0.6,"#3a3d43","#26282c",{lw:0.3,mat:false});
  const side=(sg)=>dogDeck(fr,sg*hL,0.6,0,H,hD,"#4f7378",0.32);
  side(-near);for(const d of [-hD+0.3,hD-0.3])line3(dog3(fr,-hL*0.45,d,H*0.5),dog3(fr,hL*0.45,d,H*0.5),"#9aa1a9",0.3,[0.6,0.4]);side(near);
  bar3(dog3(fr,0,-hD-0.4,H+0.2),dog3(fr,0,hD+0.4,H+0.2),0.9,"#5d636b")};
// low ramp to a pause platform: a slatted ramp with a contact zone, a riveted steel platform with a rubber top and a paw plate
SV.dog.ramp=(fr,o={})=>{const hL=fr.L/2,hD=fr.D/2,H=o.h||4,s1=o.top??hL-10;
  const plat=()=>{prismX(frameCham(fr,s1,hL,-hD-0.6,hD+0.6,0.6),0,H,"#5a4a3e","#4f5359");const fc=faces(fr,s1,hL,-hD-0.6,hD+0.6);for(const k of ["front","back","e2"]){const [a,b,n]=fc[k];onFace(a,b,n,0,H,(W,Hh)=>{dRecess(0.6,0.6,W-1.2,Hh-1.2,"#3a3d43");dRivets(0.6,0.6,W-1.2,Hh-1.2,"#7d7a70")})}
    onTop(fr,s1+0.8,hL-0.8,-hD+0.2,hD-0.2,H+0.02,(W,Dd)=>{ctx.fillStyle="rgba(0,0,0,.2)";for(let x=0.8;x<W;x+=1.6)ctx.fillRect(x,0,0.25,Dd);ctx.fillStyle="rgba(232,215,178,.5)";ctx.beginPath();ctx.ellipse(W/2,Dd/2+0.5,1,0.8,0,0,TAU);ctx.fill();for(const [dx,dy] of [[-1.1,-0.9],[-0.4,-1.5],[0.4,-1.5],[1.1,-0.9]]){ctx.beginPath();ctx.arc(W/2+dx,Dd/2+dy,0.35,0,TAU);ctx.fill()}})};
  const ramp=()=>{for(const d of [-hD,hD]){const n=[fr.f[0]*Math.sign(d),fr.f[1]*Math.sign(d)];if(camAlong(n)>0)q3([dog3(fr,-hL,d,0),dog3(fr,s1,d,0),dog3(fr,s1,d,H)],shade("#4f5359",0.8),{lw:0.35})}dogDeck(fr,-hL,0.2,s1,H,hD,"#4f7378",0.35)};
  if(camAlong(fr.a)>0){ramp();plat()}else{plat();ramp()}};
// suspended ring: two posts on bolted foot bars, a top beam, an amber ring hung on cables with side tension lines
SV.dog.ring=(fr,o={})=>{const hL=fr.L/2,Hp=o.h||16,R=o.ring||3.6,hc=o.hc||8.5;
  for(const sg of [-1,1])prismX(frameRect(fr,sg*hL-1,sg*hL+1,-4,4),0,0.8,"#3a3d43","#26282c",{lw:0.3,mat:false});
  const post=(sg)=>{prismX(frameRect(fr,sg*hL-0.6,sg*hL+0.6,-0.6,0.6),0.8,Hp,"#5d636b","#3a3d43",{lw:0.35});for(const d of [-1,1])bar3(dog3(fr,sg*hL,d*3.4,0.8),dog3(fr,sg*hL,d*0.5,4.5),0.4,"#5d636b")};
  const near=camAlong(fr.a)>0?1:-1;post(-near);
  for(const sg of [-1,1]){line3(dog3(fr,sg*R*0.7,0,Hp),dog3(fr,sg*R*0.7,0,hc+R*0.72),"#9aa1a9",0.3);line3(dog3(fr,sg*R,0,hc),dog3(fr,sg*(hL-0.6),0,hc),"#9aa1a9",0.3)}
  const pts=[];for(let j=0;j<=32;j++){const th=j/32*TAU;pts.push(V.P(...dogP(fr,R*Math.cos(th),0),hc+R*Math.sin(th)))}
  const ring=(col,w)=>{ctx.strokeStyle=col;ctx.lineWidth=w;ctx.beginPath();pts.forEach((p,i)=>i?ctx.lineTo(p[0],p[1]):ctx.moveTo(p[0],p[1]));ctx.stroke()};ring(CAL.out,1.9);ring("#d8a64a",1.25);ring("rgba(255,240,200,.5)",0.3);
  for(let k=0;k<8;k++){const th=k/8*TAU;const p=V.P(...dogP(fr,R*Math.cos(th),0),hc+R*Math.sin(th));ctx.fillStyle="#3a3d43";ctx.fillRect(p[0]-0.25,p[1]-0.25,0.5,0.5)}
  post(near);prismX(frameRect(fr,-hL-0.7,hL+0.7,-0.7,0.7),Hp,Hp+1.2,"#5d636b","#3a3d43",{lw:0.35})};
// weave poles: a bolted base rail with end feet, cream poles with alternating amber bands and dark caps
SV.dog.weave=(fr,o={})=>{const hL=fr.L/2,n=o.n||6,H=o.h||9;
  for(const sg of [-1,1])prismX(frameRect(fr,sg>0?hL-1.2:-hL,sg>0?hL:-hL+1.2,-3,3),0,0.6,"#3a3d43","#26282c",{lw:0.3,mat:false});
  prismX(frameCham(fr,-hL,hL,-0.9,0.9,0.4),0,0.8,"#5d636b","#3a3d43",{lw:0.35,mat:false});
  const ps=[];for(let i=0;i<n;i++){const s=-hL+1.6+i*(fr.L-3.2)/(n-1);ps.push({i,p:dogP(fr,s,0)})}ps.sort((A,B)=>V.depth(...A.p)-V.depth(...B.p));
  for(const {i,p} of ps){cyl(p[0],p[1],0.45,0.8,H,"#efe2c4","#c9bfae",{n:8});for(const b of i%2?[2.4,5.8]:[4.1,7.5])cyl(p[0],p[1],0.47,b,b+1.4,null,"#d8a64a",{n:8});cyl(p[0],p[1],0.55,H,H+0.5,"#2a2c31","#1d1f23",{n:8})}};
// low jump: two lattice wing panels on foot bars, a striped bar resting in dark cups, a ground bar beneath
SV.dog.jump=(fr,o={})=>{const hL=fr.L/2,hb=o.bar||4.5,Hw=o.h||8;
  const wing=(sg)=>{const s0=sg*hL-0.5,s1=sg*hL+0.5;prismX(frameRect(fr,s0-0.4,s1+0.4,-3.2,3.2),0,0.6,"#3a3d43","#26282c",{lw:0.3,mat:false});prismX(frameRect(fr,s0,s1,-2.6,2.6),0.6,Hw,"#5d636b","#3a3d43",{lw:0.35,mat:false});
    const fc=faces(fr,s0,s1,-2.6,2.6);for(const k of ["e1","e2"]){const [a,b,n]=fc[k];onFace(a,b,n,0.6,Hw,(W,H)=>{ctx.fillStyle="#2a2c31";ctx.fillRect(0.6,0.6,W-1.2,H-1.2);ctx.strokeStyle="#d8a64a";ctx.lineWidth=0.4;ctx.beginPath();ctx.moveTo(0.8,0.8);ctx.lineTo(W-0.8,H-0.8);ctx.moveTo(W-0.8,0.8);ctx.lineTo(0.8,H-0.8);ctx.stroke();dRivets(0.6,0.6,W-1.2,H-1.2,"#7d7a70")})}};
  const near=camAlong(fr.a)>0?1:-1;wing(-near);
  bar3(dog3(fr,-hL+0.5,0,0.9),dog3(fr,hL-0.5,0,0.9),0.5,"#5d636b");
  const K=6;for(let k=0;k<K;k++){const s0=-hL+0.5+(fr.L-1)*k/K,s1=-hL+0.5+(fr.L-1)*(k+1)/K;line3(dog3(fr,s0,0,hb),dog3(fr,s1,0,hb),CAL.out,1.35)}for(let k=0;k<K;k++){const s0=-hL+0.5+(fr.L-1)*k/K,s1=-hL+0.5+(fr.L-1)*(k+1)/K;line3(dog3(fr,s0,0,hb),dog3(fr,s1,0,hb),k%2?"#efe2c4":"#d8a64a",0.85)}
  for(const sg of [-1,1]){const p=V.P(...dogP(fr,sg*(hL-0.7),0),hb-0.6);ctx.fillStyle="#1d1f23";ctx.fillRect(p[0]-0.6,p[1]-0.2,1.2,0.9)}wing(near)};
// curved balance bridge: an arched run of wood planks with amber contact ends on steel trestles
SV.dog.bridge=(fr,o={})=>{const hL=fr.L/2,hD=o.w||1.9,H=o.h||5,N=o.n||14;const hs=s=>0.5+(H-0.5)*Math.sin(Math.PI*(s+hL)/fr.L);
  const seg=[];for(let k=0;k<N;k++){const s0=-hL+fr.L*k/N,s1=-hL+fr.L*(k+1)/N;seg.push({k,s0,s1,m:dogP(fr,(s0+s1)/2,0)})}seg.sort((A,B)=>V.depth(...A.m)-V.depth(...B.m));
  for(const g of seg){const {k,s0,s1}=g,h0=hs(s0),h1=hs(s1);if(k%3===1&&k<N-1){const sm=(s0+s1)/2,hm=hs(sm);prismX(frameRect(fr,sm-0.5,sm+0.5,-hD-0.8,hD+0.8),0,0.5,"#3a3d43","#26282c",{lw:0.3,mat:false});for(const d of [-hD+0.4,hD-0.9])prismX(frameRect(fr,sm-0.25,sm+0.25,d,d+0.5),0.5,hm-0.6,"#5d636b","#3a3d43",{lw:0.3,mat:false})}
    const dv=camAlong(fr.f)>0?hD:-hD;q3([dog3(fr,s0,dv,h0-0.7),dog3(fr,s1,dv,h1-0.7),dog3(fr,s1,dv,h1),dog3(fr,s0,dv,h0)],"#6b4a2f",{lw:0.3});
    const zone=k===0||k===N-1;q3([dog3(fr,s0,-hD,h0),dog3(fr,s1,-hD,h1),dog3(fr,s1,hD,h1),dog3(fr,s0,hD,h0)],zone?"#d8a64a":(k%2?"#9a6e44":"#8c6239"),{lw:0.3})}};
// raised rest bed: a steel cot frame on feet, a deep cushion, a U-shaped bolster open to the front and a folded blanket
SV.dog.bed=(fr)=>{const hL=fr.L/2,hD=fr.D/2;feet(fr,-hL,hL,-hD,hD,1.4);prismX(frameCham(fr,-hL,hL,-hD,hD,1.2),1.4,2.4,"#5d636b","#3a3d43",{lw:0.35,mat:false});
  prismX(frameCham(fr,-hL+0.5,hL-0.5,-hD+0.5,hD-0.5,1.4),2.4,3.8,"#8a6a5a","#6e5446",{mat:false,lw:0.35});
  const parts=[[-hL+0.5,hL-0.5,-hD+0.5,-hD+2.6],[-hL+0.5,-hL+2.6,-hD+2.6,hD-0.8],[hL-2.6,hL-0.5,-hD+2.6,hD-0.8]].map(b=>({b,m:dogP(fr,(b[0]+b[1])/2,(b[2]+b[3])/2)}));parts.sort((A,B)=>V.depth(...A.m)-V.depth(...B.m));
  const blanket=()=>onTop(fr,-hL+3.2,hL-3.2,-hD+3,hD-1,3.82,(W,Dd)=>{ctx.fillStyle="#a2836a";ctx.beginPath();ctx.ellipse(W/2,Dd/2,W*0.42,Dd*0.38,0,0,TAU);ctx.fill();ctx.fillStyle="#c9a77c";ctx.fillRect(W*0.55,Dd*0.15,W*0.3,Dd*0.7);ctx.fillStyle="rgba(255,240,215,.35)";for(let y=Dd*0.2;y<Dd*0.85;y+=1)ctx.fillRect(W*0.55,y,W*0.3,0.2)});
  blanket();for(const p of parts)prismX(frameCham(fr,...p.b,0.9),3.8,6,"#9a7a68","#7a5e50",{mat:false,lw:0.35})};
// low privacy screen for the rest corner: a felt-faced steel frame panel on feet with a small REST plate
SV.dog.screen=(fr,o={})=>{const hL=fr.L/2,H=o.h||7;feet(fr,-hL,hL,-1.2,1.2,0.6);prismX(frameRect(fr,-hL,hL,-0.7,0.7),0.6,H,"#5d636b","#3a3d43",{lw:0.35,mat:false});
  const fc=faces(fr,-hL,hL,-0.7,0.7);for(const k of ["front","back"]){const [a,b,n]=fc[k];onFace(a,b,n,0.6,H,(W,Hh)=>{const m=Math.max(1,Math.round(W/8));for(let j=0;j<m;j++){const x=j*W/m;ctx.fillStyle="#6e5a48";ctx.fillRect(x+0.6,0.6,W/m-1.2,Hh-1.2);ctx.strokeStyle="rgba(255,240,215,.18)";ctx.lineWidth=0.2;ctx.setLineDash([0.4,0.4]);ctx.strokeRect(x+1,1,W/m-2,Hh-2);ctx.setLineDash([])}
    ctx.fillStyle="#1d1f23";ctx.fillRect(W/2-2.2,1.1,4.4,1.5);ctx.fillStyle="#efe2c4";ctx.font="700 0.9px system-ui";ctx.textAlign="center";ctx.textBaseline="middle";ctx.fillText("REST",W/2,1.88)})}};
// water station: a steel stand with two bowls, a refill post with a tap and a supply line into the floor, a blue status pip
SV.dog.water=(fr)=>{ctx.fillStyle="#2f3a3e";ctx.fill(poly2(frameCham(fr,-4,4,-2.8,2.8,0.8),0.03));
  const post=()=>{const p=dogP(fr,0,-2.2);cyl(p[0],p[1],0.45,0,6,"#9aa1a9","#5d636b",{n:8});prismX(frameCham({...fr,cx:p[0],cy:p[1]},-0.9,0.9,-0.6,1.3,0.3),5.4,6.4,"#5d636b","#3a3d43",{lw:0.3,mat:false});const q=V.P(...dogP(fr,0,0.9),5.6);ctx.fillStyle="#7fd0e0";ctx.fillRect(q[0]-0.2,q[1],0.4,0.6);const pp=V.P(p[0],p[1],3.6);ctx.fillStyle="#3fb7cc";ctx.fillRect(pp[0]-0.3,pp[1]-0.3,0.6,0.6)};
  const stand=()=>{prismX(frameCham(fr,-3,3,-1.4,1.8,0.5),0,1.8,"#4f5359","#3a3d43",{lw:0.35,mat:false});for(const s of [-1.5,1.5]){const p=dogP(fr,s,0.2);cyl(p[0],p[1],1.15,1.8,2.5,"#d8d2c2","#9aa1a9",{n:12});ell(p[0],p[1],0.85,2.52,s<0?"#7fd0e0":"#c9a24a")}};
  if(camAlong(fr.f)>0){post();stand()}else{stand();post()}};
// toy bin: an open wood crate with slatted sides and toys showing above the rim
SV.dog.toyBin=(fr)=>{const hL=fr.L/2,hD=fr.D/2;prismX(frameCham(fr,-hL,hL,-hD,hD,0.5),0,3.6,"#8c6239","#6b4a2f",{lw:0.35});ctx.fillStyle="#2a2018";ctx.fill(poly2(frameCham(fr,-hL+0.6,hL-0.6,-hD+0.6,hD-0.6,0.4),3.62));
  const fc=faces(fr,-hL,hL,-hD,hD);for(const k of ["front","back","e1","e2"]){const [a,b,n]=fc[k];onFace(a,b,n,0,3.6,(W,H)=>{ctx.fillStyle="rgba(0,0,0,.28)";for(let y=1.1;y<H;y+=1.2)ctx.fillRect(0,y,W,0.22)})}
  for(const [s,d,c] of [[-hL*0.4,0,"#e0b25a"],[hL*0.2,-hD*0.3,"#c86a5a"],[hL*0.45,hD*0.25,"#5aa765"]]){const p=V.P(...dogP(fr,s,d),3.9);ctx.fillStyle=c;ctx.beginPath();ctx.arc(p[0],p[1],0.7,0,TAU);ctx.fill();ctx.strokeStyle=CAL.out;ctx.lineWidth=0.25;ctx.stroke()}};
// paw print on the floor (main pad and four toes), heading ang in world radians
SV.dog.paw=(x,y,h,ang,sc,col)=>{const c=Math.cos(ang),s=Math.sin(ang);ctx.fillStyle=col;for(const [u,v,r] of [[0,0,0.9],[1.3,-0.9,0.38],[1.6,-0.3,0.38],[1.6,0.3,0.38],[1.3,0.9,0.38]]){const p=V.P(x+(u*c-v*s)*sc,y+(u*s+v*c)*sc,h);ctx.beginPath();ctx.ellipse(p[0],p[1],V.kx*r*sc,V.ky*r*sc*1.1,0,0,TAU);ctx.fill()}};
// wall face (R4): warm acoustic slats above a padded bumper dado (dog-height), brass rail between
SV.wall.kennel=(W,H,seed)=>{SV.wall.acoustic(W,H,seed);const y0=H-10.4;ctx.fillStyle="#2a2420";ctx.fillRect(0.6,y0,W-1.2,7.4);const cw=W/Math.max(1,Math.round(W/4.4));
  for(let x=0.6;x<W-0.8;x+=cw){ctx.fillStyle="#6e5a48";chamRect(x+0.25,y0+0.4,cw-0.5,6.6,0.9);ctx.fill();ctx.fillStyle="rgba(0,0,0,.25)";ctx.beginPath();ctx.arc(x+cw/2,y0+3.7,0.3,0,TAU);ctx.fill()}
  ctx.fillStyle=CAL.brass;ctx.fillRect(0.6,y0-0.5,W-1.2,0.45)};
// wall faces for the recreation rooms
SV.wall.acoustic=(W,H,seed,o={})=>{const dark=!!o.dark;SV.wall.band(W,H);ctx.fillStyle=dark?"#15161a":"#4a3626";ctx.fillRect(0.6,2,W-1.2,H-5);for(let x=1;x<W-0.8;x+=1.2){ctx.fillStyle=dark?(Math.floor(x)%2?"#24232b":"#1d1c23"):(Math.floor(x)%2?"#8c6239":"#7a5530");ctx.fillRect(x,2.4,0.9,H-5.8)}
  ctx.fillStyle=dark?"rgba(255,190,110,.35)":"rgba(255,215,150,.28)";ctx.fillRect(0.6,H-3.4,W-1.2,0.6);dWear(W,H-3,seed)};
SV.wall.padded=(W,H,seed)=>{SV.wall.band(W,H);ctx.fillStyle="#55515c";ctx.fillRect(0.4,1.8,W-0.8,H-4.6);const cw=W/Math.max(1,Math.round(W/4.6));
  for(let x=0.4;x<W-0.5;x+=cw)for(let y=1.8;y<H-3;y+=4.2){ctx.fillStyle="#6e6a74";chamRect(x+0.3,y+0.3,cw-0.6,3.6,1);ctx.fill();ctx.fillStyle="rgba(0,0,0,.25)";ctx.beginPath();ctx.arc(x+cw/2,y+2.1,0.35,0,TAU);ctx.fill()}
  ctx.fillStyle="#2a2c31";for(let x=0.4;x<W;x+=cw)ctx.fillRect(x-0.2,1.8,0.4,H-4.6)};
// ================================================================ VOCABULARY CATALOGUE (?vocab=1): every family on a plain deck, for review and reuse
const SV_CATALOGUE=[
  {name:"WS-standard",w:40,d:14,draw:(fr)=>SV.ws.build({...fr,L:35,D:12},{variant:"standard",seed:1,lit:true})},
  {name:"WS-compact",w:28,d:14,draw:(fr)=>SV.ws.build({...fr,L:23,D:12},{variant:"compact",seed:2})},
  {name:"WS-heavy",w:40,d:14,draw:(fr)=>SV.ws.build({...fr,L:35,D:12},{variant:"heavy",seed:3,lit:true})},
  {name:"WS-rear",w:40,d:14,draw:(fr)=>SV.ws.build({...fr,f:[0,-1],L:35,D:12},{variant:"standard",seed:4})},
  {name:"CON-single",w:16,d:12,draw:(fr)=>SV.con.bank({...fr,L:12,D:10},{bays:1,seed:0,kits:["screen"]})},
  {name:"CON-double",w:28,d:12,draw:(fr)=>SV.con.bank({...fr,L:24,D:10},{bays:2,seed:1,kits:["stack","instrument"]})},
  {name:"CON-wide",w:40,d:12,draw:(fr)=>SV.con.bank({...fr,L:36,D:10},{bays:3,seed:2,kits:["screen","switch","readout"]})},
  {name:"CON-instrument",w:16,d:12,draw:(fr)=>SV.con.bank({...fr,L:12,D:10},{bays:1,kits:["instrument"]})},
  {name:"EQ-rack",w:14,d:12,draw:(fr)=>SV.eq.rack({...fr,L:8,D:8},{seed:1})},
  {name:"EQ-relay",w:14,d:12,draw:(fr)=>SV.eq.relay({...fr,L:8,D:8},{seed:2})},
  {name:"EQ-bay",w:28,d:12,draw:(fr)=>SV.eq.bay({...fr,L:22,D:8},{seed:3})},
  {name:"EQ-service",w:14,d:12,draw:(fr)=>SV.eq.service({...fr,L:7.6,D:7},{tone:"red"})},
  {name:"EQ-service olive",w:14,d:12,draw:(fr)=>SV.eq.service({...fr,L:7.6,D:7},{tone:"olive",seed:2})},
  {name:"EQ-storage locker",w:16,d:12,draw:(fr)=>SV.eq.locker({...fr,L:10.5,D:7})},
  {name:"EQ-storage drawers",w:28,d:12,draw:(fr)=>SV.eq.drawers({...fr,L:22,D:8})},
  {name:"CH-standard",w:10,d:12,draw:(fr)=>{const c=SV.chair.build(fr.cx,fr.cy,0,[0,-1]);c.base();c.seat();c.backPart()}},
  {name:"CH-operator",w:10,d:12,draw:(fr)=>{const c=SV.chair.build(fr.cx,fr.cy,0,[0,-1],{variant:"operator"});c.base();c.seat();c.backPart()}},
  {name:"CH-command",w:12,d:12,draw:(fr)=>{const c=SV.chair.build(fr.cx,fr.cy,0,[0,-1],{variant:"command"});c.base();c.seat();c.backPart()}},
  {name:"TBL-tactical",w:72,d:62,draw:(fr)=>{const t=SV.table.tactical(fr.cx,fr.cy+6,0);t.draw()}},
  {name:"DOOR-A standard",w:34,d:14,draw:(fr)=>SV.door.build({...fr,L:22},"standard",{plate:"CORRIDOR"})},
  {name:"DOOR-B hub access",w:40,d:16,draw:(fr)=>SV.door.build({...fr,L:24},"hub",{plate:"H-HAB"})},
  {name:"DOOR-C restricted",w:38,d:16,draw:(fr)=>SV.door.build({...fr,L:22},"restricted",{plate:"RESTRICTED"})},
  {name:"DOOR closed (reserved)",w:34,d:14,draw:(fr)=>SV.door.build({...fr,L:22},"standard",{closed:true,plate:"RESERVED"})},
  {name:"FLR big grate + hatched band",w:40,d:30,draw:(fr)=>{const k=4;const q=[[fr.cx-17+k,fr.cy-13],[fr.cx+17-k,fr.cy-13],[fr.cx+17,fr.cy-13+k],[fr.cx+17,fr.cy+13-k],[fr.cx+17-k,fr.cy+13],[fr.cx-17+k,fr.cy+13],[fr.cx-17,fr.cy+13-k],[fr.cx-17,fr.cy-13+k]];SV.floor.hatchBand(q,2,0.02);SV.floor.bigGrate(fr.cx-12,fr.cy-12,24,true)}},
  {name:"SCR-cluster",w:16,d:12,draw:(fr)=>SV.screen.cluster({...fr,L:8,D:8},{seed:1})},
  {name:"EQ-cart",w:12,d:12,draw:(fr)=>SV.eq.cart({...fr,L:7.2,D:6})},
  {name:"EQ-optics",w:12,d:12,draw:(fr)=>SV.eq.optics(fr.cx,fr.cy)},
  {name:"EQ-tank",w:28,d:12,draw:(fr)=>SV.eq.tank({...fr,L:22,D:8})},
  {name:"EQ-dome (hero)",w:40,d:40,draw:(fr)=>SV.eq.dome(fr.cx,fr.cy,16)},
  {name:"TBL-chart",w:44,d:52,draw:(fr)=>SV.table.chart({...fr,L:34,D:46})},
  {name:"TBL-stage",w:40,d:40,draw:(fr)=>SV.table.stage({...fr,L:34,D:34})},
  {name:"TBL-work",w:28,d:12,draw:(fr)=>SV.table.work({...fr,L:22,D:9})},
  {name:"EQ-reactor",w:14,d:14,draw:(fr)=>SV.eq.reactor(fr.cx,fr.cy)},
  {name:"EQ-podium",w:12,d:12,draw:(fr)=>SV.eq.podium({...fr})},
  {name:"EQ-tube",w:14,d:14,draw:(fr)=>SV.eq.tube({...fr,L:10})},
  {name:"HAB bar + dispenser",w:44,d:14,draw:(fr)=>{SV.hab.bar({...fr,cx:fr.cx-5,L:30,D:9});SV.hab.dispenser({...fr,cx:fr.cx+16})}},
  {name:"HAB café table + shells",w:20,d:14,draw:(fr)=>{SV.hab.shellChair(fr.cx-7,fr.cy,[1,0]);SV.hab.cafeTable(fr.cx,fr.cy);SV.hab.shellChair(fr.cx+7,fr.cy,[-1,0])}},
  {name:"HAB sofa + glass table",w:44,d:14,draw:(fr)=>{SV.hab.sofa({...fr,cx:fr.cx-8,L:22,D:9});SV.hab.glassTable({...fr,cx:fr.cx+14,L:12,D:8})}},
  {name:"HAB pool table",w:44,d:28,draw:(fr)=>SV.hab.pool({...fr,L:34,D:22})},
  {name:"HAB rest pod / recovery pod",w:36,d:16,draw:(fr)=>{SV.hab.restPod({...fr,cx:fr.cx-10,f:[0,1],a:[1,0]});SV.hab.recoveryPod({...fr,cx:fr.cx+8,L:12,D:20})}},
  {name:"HAB planter (hero)",w:44,d:44,draw:(fr)=>SV.hab.planter(fr.cx,fr.cy,13)},
  {name:"HAB fountain (hero)",w:44,d:40,draw:(fr)=>SV.hab.fountain(fr.cx,fr.cy,14,0)},
  {name:"HAB park tree + bed",w:34,d:16,draw:(fr)=>{SV.hab.bed({...fr,cx:fr.cx-6,L:18,D:8},{seed:2});SV.hab.tree(fr.cx+12,fr.cy)}},
  {name:"HAB resident dog (H-HAB + R4 only)",w:14,d:14,draw:(fr)=>SV.hab.dog(fr.cx,fr.cy+2)},
  {name:"REC zen: mats, speaker, garden",w:48,d:22,draw:(fr)=>{SV.rec.garden({...fr,cx:fr.cx-12,L:20,D:14});SV.rec.mat({...fr,cx:fr.cx+8,L:10,D:6.8});SV.rec.speaker(fr.cx+20,fr.cy)}},
  {name:"REC cinema: recliners, projector",w:44,d:16,draw:(fr)=>{SV.rec.recliners({...fr,cx:fr.cx-6,f:[0,-1],L:24,D:8},1.6,2);SV.rec.projector({...fr,cx:fr.cx+16,f:[0,-1]})}},
  {name:"REC padded bench",w:26,d:12,draw:(fr)=>SV.rec.padBench({...fr,L:18,D:7})},
  {name:"DOG A-frame + ramp (dog for scale)",w:66,d:16,draw:(fr)=>{SV.dog.aframe({...fr,cx:fr.cx-20,L:26,D:7});SV.dog.ramp({...fr,cx:fr.cx+14,L:22,D:6});SV.hab.dog(fr.cx+30,fr.cy+5)}},
  {name:"DOG tunnel + weave poles",w:62,d:28,draw:(fr)=>{SV.dog.tunnel({...fr,cx:fr.cx-14,cy:fr.cy-2,L:30,D:9},{bend:6});SV.dog.weave({...fr,cx:fr.cx+16,L:26,D:2})}},
  {name:"DOG ring + jump + bridge",w:66,d:16,draw:(fr)=>{SV.dog.ring({...fr,cx:fr.cx-24,L:14,D:2});SV.dog.jump({...fr,cx:fr.cx-6,L:12,D:2});SV.dog.bridge({...fr,cx:fr.cx+18,L:26,D:4})}},
  {name:"DOG rest: bed, screen, water, toy bin, toys",w:66,d:18,draw:(fr)=>{SV.dog.bed({...fr,cx:fr.cx-20,L:18,D:12});SV.dog.water({...fr,cx:fr.cx-4,L:8,D:6});SV.dog.toyBin({...fr,cx:fr.cx+8,L:7,D:5});SV.dog.screen({...fr,cx:fr.cx+22,L:16,D:2});SV.dog.toys(fr.cx+8,fr.cy+9,3)}},
  {name:"instrument pod + service box",w:20,d:12,draw:(fr)=>{SV.small.serviceBox(fr,-9,-3.5,-3.5,3.5,{seed:1});SV.small.instrumentPod(fr,1,6.5,-3.5,3.5,{seed:2})}}];
function drawVocabCatalogue(){const rowW=210,gap=12,x0=-rowW/2,y0=-120;const rows=[];let cur=[],w=0;
  for(const s of SV_CATALOGUE){if(cur.length&&w+s.w>rowW){rows.push(cur);cur=[];w=0}cur.push(s);w+=s.w+gap}if(cur.length)rows.push(cur);
  let y=y0;const placed=[];for(const r of rows){const rh=Math.max(...r.map(s=>s.d))+34;let x=x0;for(const s of r){placed.push([s,x+s.w/2,y+rh*0.5]);x+=s.w+gap}y+=rh}
  for(let r=-1;r<=(y-y0)/T+1;r++)for(let c=-1;c<=rowW/T+2;c++)SV.floor.panel(c,r,x0+c*T,y0+r*T,true,true);
  for(const [s,cx,cy] of placed.slice().sort((p,q)=>V.depth(p[1],p[2])-V.depth(q[1],q[2])))s.draw({cx,cy,a:[1,0],f:[0,1]});
  for(const [s,cx,cy] of placed){const p=V.P(cx,cy+s.d/2+5,0);ctx.font="600 2.4px system-ui";ctx.textAlign="center";ctx.textBaseline="middle";const w=ctx.measureText(s.name).width+2;
    ctx.fillStyle="rgba(8,10,14,.7)";ctx.fillRect(p[0]-w/2,p[1]-1.6,w,3.2);ctx.fillStyle="rgba(230,235,242,.95)";ctx.fillText(s.name,p[0],p[1])}
  return[x0,y0,x0+rowW,y]}
