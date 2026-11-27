#!/usr/bin/env node
// Dependency-free offline publication renderer. Node is optional, not an inference dependency.
const fs=require("node:fs"),path=require("node:path"),crypto=require("node:crypto");
const root=path.resolve(__dirname,"..");
function generate(dataText,prefixText,comparisonText) {
 const d=JSON.parse(dataText),a=d.b2,b=d.hybrid,arms=[a,b],labels=["B2 NVFP4","H2 FP8 hybrid"],colors=["#44b9ef","#ffbd69"],C={bg:"#101c2c",panel:"#192c42",text:"#eef5fc",muted:"#b2c5d9",line:"#3c5269",blue:colors[0],orange:colors[1],green:"#48d8af",red:"#ff8585"};
 const out={};const fmt=(n,k=2)=>Number(n).toFixed(k);
 const esc=s=>String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
 const num=(s,re)=>{const m=s.match(re);if(!m)throw Error("Missing source metric "+re);return Number(m[1]);};
 const prefixRows=prefixText.match(/Median TTFT, first request \| \*\*([\d.]+) s\*\* \| \*\*([\d.]+) s\*\*/);
 const repeatRows=prefixText.match(/Median TTFT, follow-up \| \*\*([\d.]+) s\*\* \| \*\*([\d.]+) s\*\*/);
 const ratios=prefixText.match(/Median of five \*paired\* TTFT ratios \| \*\*([\d.]+)×\*\* \| \*\*([\d.]+)×\*\*/);
 if(!prefixRows||!repeatRows||!ratios)throw Error("Prefix source format changed");
 const rates=arms.map(x=>x.forum_c1.mean_two_pass_end_to_end_tokens_s);
 const suite=(x,k)=>x.suites[k].summary;
 const repair=arms.map(x=>suite(x,"agent-generalization").cases.repair_regression);
 const rows=["tool-routing","agent-multiturn","agent-generalization"].map((k,i)=>({label:["First tool decision","Fixed multi-turn","Seeded workflows"][i],v:arms.map(x=>suite(x,k).passed),total:arms.map(x=>suite(x,k).total)}));
 function board(w,h,title,subtitle,footer){
  const p=[`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${w} ${h}" role="img" aria-labelledby="title desc"><title id="title">${esc(title)}</title><desc id="desc">${esc(subtitle+" "+footer)}</desc><rect width="${w}" height="${h}" rx="14" fill="${C.bg}"/>`];
  const rect=(x,y,w,h,fill,r=5)=>p.push(`<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${r}" fill="${fill}"/>`);
  const txt=(x,y,t,size=20,fill=C.text,weight=400,anchor="start")=>p.push(`<text x="${x}" y="${y}" font-family="Arial, Helvetica, sans-serif" font-size="${size}" font-weight="${weight}" fill="${fill}" text-anchor="${anchor}">${esc(t)}</text>`);
  txt(32,48,title,32,C.text,700);txt(32,78,subtitle,17,C.muted);txt(32,h-21,footer,14,C.muted);
  return {rect,txt,done:()=>p.join("\n")+"\n</svg>\n"};
 }
 function legend(g,x=32,y=112){labels.forEach((l,i)=>{g.rect(x+i*230,y-13,15,15,colors[i]);g.txt(x+24+i*230,y,l,17,C.muted,600)})}
 function paired(g,{label,v,total},y,max,x=320,w=540,unit=""){g.txt(32,y+19,label,20,C.text,600);for(let i=0;i<2;i++){let len=w*v[i]/(total?total[i]:max);g.rect(x,y+i*28,w,19,C.panel);g.rect(x,y+i*28,len,19,colors[i]);g.txt(x+len+9,y+16+i*28,total?`${v[i]}/${total[i]}`:fmt(v[i])+unit,17,C.text,600);}}
 const headline=board(1000,560,"Faster inference. Different agent behavior.","Qwen3.8 Flash Next · Jetson AGX Thor · 8 Nov 2026","Synthetic workflow gates; deployment-level comparison, not precision-only. C1: two passes per arm.");
 legend(headline);paired(headline,{label:"C1 end-to-end rate",v:rates},142,60,320,540," tok/s");
 headline.txt(32,236,`${fmt(rates[1]/rates[0])}× observed throughput`,32,C.green,700);
 rows.forEach((r,i)=>paired(headline,r,263+i*81,100,320,540));
 out["results-overview.svg"]=headline.done();
 const throughput=board(1000,645,"Throughput by workload","Two C1 request rates averaged per workload · 8 Nov 2026","End-to-end completion rate includes prefill; response correctness is not graded.");
 legend(throughput);
 for(const [i,k] of ["Q&A","Code","JSON","Math","LongCode"].entries()){const v=arms.map(x=>{const z=x.forum_c1.requests.filter(r=>r.category===k);if(z.length!==2)throw Error("Unexpected C1 denominator");return z.reduce((s,r)=>s+r.completion_tokens/r.elapsed_s,0)/z.length;});paired(throughput,{label:k,v},139+i*94,60,320,540," tok/s");}
 out["throughput-by-workload.svg"]=throughput.done();
 const heat=board(1000,575,"Where the seeded workflows failed","Same seed · scorer 0.7.3 · five variants per public task family","Both arms failed all five no-tool brevity gates; the three extra H2 failures omit pre-edit test evidence.");
 heat.txt(600,119,labels[0],22,C.blue,700,"middle");heat.txt(820,119,labels[1],22,C.orange,700,"middle");
 const families=["symbol_origin","repair_regression","moved_runbook","transient_read","environment_disambiguation","no_tool_needed"];
 const names=["Symbol origin","Repair regression","Moved runbook","Transient read","Environment disambiguation","No-tool brevity gate"];
 families.forEach((k,i)=>{const y=137+i*59;heat.txt(32,y+30,names[i],22,C.text,600);arms.forEach((x,j)=>{const c=suite(x,"agent-generalization").cases[k];heat.rect(506+j*220,y,188,46,c.passed===c.total?"#194b46":c.passed===0?"#633643":"#694a2b");heat.txt(600+j*220,y+31,`${c.passed}/${c.total}`,25,C.text,700,"middle");});});
 out["seeded-outcomes.svg"]=heat.done();
 const mem=board(1000,535,"Memory and energy trade-offs","Observed during the November 8 deployment comparison","Energy includes warmups, excludes startup and C1. Not an equal-correctness energy comparison.");
 legend(mem);
 const memory=arms.map((x,i)=>num(comparisonText,i===0?/model-loading memory \| ([\d.]+) GiB/:/model-loading memory \| [\d.]+ GiB \| ([\d.]+) GiB/));
 paired(mem,{label:"Model-loading memory",v:memory},142,120,320,510," GiB");
 paired(mem,{label:"Peak host RAM",v:arms.map(x=>x.telemetry.peak_tegrastats_ram_mb)},230,130000,320,510," MB");
 paired(mem,{label:"Mean board input",v:arms.map(x=>x.telemetry.mean_board_input_w)},318,85,320,510," W");
 paired(mem,{label:"Board-input energy",v:arms.map(x=>x.telemetry.estimated_board_input_wh)},406,34,320,510," Wh");
 out["memory-energy.svg"]=mem.done();
 const pr=board(1000,460,"Shared context, faster first output","November 7 · five first/follow-up pairs per suite","Positive server-wide cache-hit deltas: 10/10 follow-ups. Per-request attribution is not established.");
 pr.rect(32,100,15,15,C.blue);pr.txt(56,113,"First request",18,C.muted);pr.rect(260,100,15,15,C.orange);pr.txt(284,113,"Follow-up",18,C.muted);
 ["Identical prefix","Agent-style prefix"].forEach((l,i)=>{paired(pr,{label:l,v:[Number(prefixRows[i+1]),Number(repeatRows[i+1])]},150+i*130,5.5,320,500," s");pr.txt(320,222+i*130,`${ratios[i+1]}× median paired TTFT ratio`,22,C.green,700)});
 out["prefix-overview.svg"]=pr.done();
 const steps=[["Source + failing test","Either order"],["Simulated edit","In-memory fixture"],["Passing simulated test","Post-edit observation"],["PASS","Evidence gate satisfied"]];
 const failed=[["Source read","Conceptual sequence"],["Pre-edit test omitted","Required evidence missing"],["Simulated edit + test pass","Post-edit observation"],["FAIL","Evidence gate rejected"]];
 const wf=board(1000,520,"A passing test is not the whole workflow","Conceptual reconstruction of a documented failure pattern · not an episode trace","Three H2 repair episodes omitted the required pre-edit failing test. No real code ran.");
 wf.txt(250,119,"Required workflow",23,C.blue,700,"middle");wf.txt(750,119,"Observed omission pattern",23,C.orange,700,"middle");
 [steps,failed].forEach((list,j)=>list.forEach((s,i)=>{let x=32+j*500,y=140+i*83;wf.rect(x,y,436,66,j===1&&(i===1||i===3)?"#603543":i===3?"#194b46":C.panel,8);wf.txt(x+16,y+26,s[0],22,C.text,700);wf.txt(x+16,y+48,s[1],16,C.muted);if(i<3)wf.txt(x+218,y+80,"↓",18,C.muted,600,"middle");}));
 out["verification-workflow.svg"]=wf.done();
 // Compact bitmap font for dependency-free PNG/GIF exports (uppercase).
 const font={
 A:"01110/10001/10001/11111/10001/10001/10001",B:"11110/10001/10001/11110/10001/10001/11110",C:"01111/10000/10000/10000/10000/10000/01111",D:"11110/10001/10001/10001/10001/10001/11110",E:"11111/10000/10000/11110/10000/10000/11111",F:"11111/10000/10000/11110/10000/10000/10000",G:"01111/10000/10000/10111/10001/10001/01111",H:"10001/10001/10001/11111/10001/10001/10001",I:"11111/00100/00100/00100/00100/00100/11111",J:"00111/00010/00010/00010/10010/10010/01100",K:"10001/10010/10100/11000/10100/10010/10001",L:"10000/10000/10000/10000/10000/10000/11111",M:"10001/11011/10101/10101/10001/10001/10001",N:"10001/11001/10101/10011/10001/10001/10001",O:"01110/10001/10001/10001/10001/10001/01110",P:"11110/10001/10001/11110/10000/10000/10000",Q:"01110/10001/10001/10001/10101/10010/01101",R:"11110/10001/10001/11110/10100/10010/10001",S:"01111/10000/10000/01110/00001/00001/11110",T:"11111/00100/00100/00100/00100/00100/00100",U:"10001/10001/10001/10001/10001/10001/01110",V:"10001/10001/10001/10001/10001/01010/00100",W:"10001/10001/10001/10101/10101/11011/10001",X:"10001/10001/01010/00100/01010/10001/10001",Y:"10001/10001/01010/00100/00100/00100/00100",Z:"11111/00001/00010/00100/01000/10000/11111",
 "0":"01110/10001/10011/10101/11001/10001/01110","1":"00100/01100/00100/00100/00100/00100/01110","2":"01110/10001/00001/00010/00100/01000/11111","3":"11110/00001/00001/01110/00001/00001/11110","4":"00010/00110/01010/10010/11111/00010/00010","5":"11111/10000/10000/11110/00001/00001/11110","6":"01110/10000/10000/11110/10001/10001/01110","7":"11111/00001/00010/00100/01000/01000/01000","8":"01110/10001/10001/01110/10001/10001/01110","9":"01110/10001/10001/01111/00001/00001/01110",".":"00000/00000/00000/00000/00000/00110/00110","/":"00001/00001/00010/00100/01000/10000/10000","-":"00000/00000/00000/11111/00000/00000/00000",":":"00000/00110/00110/00000/00110/00110/00000","?":"01110/10001/00001/00010/00100/00000/00100","+":"00000/00100/00100/11111/00100/00100/00000","%":"11001/11010/00100/01000/10110/00110/00000"," ":"00000/00000/00000/00000/00000/00000/00000"};
 const pal=[C.bg,C.panel,C.text,C.muted,C.blue,C.orange,C.green,C.red,"#194b46","#603543",C.line,"#694a2b"].map(x=>[1,3,5].map(i=>parseInt(x.slice(i,i+2),16)));
 function raster(scale=1){const w=800*scale,h=450*scale,p=new Uint8Array(w*h);function rect(x,y,ww,hh,c){x=Math.round(x*scale);y=Math.round(y*scale);ww=Math.round(ww*scale);hh=Math.round(hh*scale);if(x<0||y<0||x+ww>w||y+hh>h)throw Error("Raster clipping");for(let yy=y;yy<y+hh;yy++)p.fill(c,yy*w+x,yy*w+x+ww);}
 function txt(x,y,s,z=2,c=2){s=s.toUpperCase();if(x+(s.length*6-1)*z>800)throw Error("Text clipping: "+s);for(const [i,ch] of [...s].entries()){const bits=(font[ch]||font["?"]).split("/");bits.forEach((r,j)=>[...r].forEach((b,k)=>{if(b==="1")rect(x+(i*6+k)*z,y+j*z,z,z,c)}));}}
 return {w,h,p,rect,txt};}
 const u16=n=>[n&255,(n>>>8)&255],be=n=>[(n>>>24)&255,(n>>>16)&255,(n>>>8)&255,n&255],asc=s=>[...s].map(c=>c.charCodeAt(0));
 function bits(){let a=[],v=0,n=0;return{put(x,k){v|=x<<n;n+=k;while(n>=8){a.push(v&255);v>>>=8;n-=8}},end(){if(n)a.push(v&255);return a}}}
 function reverse(v,n){let r=0;while(n--){r=(r<<1)|(v&1);v>>>=1}return r}
 function png(r){
 const raw=new Uint8Array((r.w+1)*r.h);for(let y=0;y<r.h;y++)raw.set(r.p.subarray(y*r.w,(y+1)*r.w),y*(r.w+1)+1);
 const bit=bits();bit.put(1,1);bit.put(1,2);
 function sym(s){if(s<=143)bit.put(reverse(48+s,8),8);else if(s<=255)bit.put(reverse(400+s-144,9),9);else if(s<=279)bit.put(reverse(s-256,7),7);else bit.put(reverse(192+s-280,8),8)}
 const bases=[3,4,5,6,7,8,9,10,11,13,15,17,19,23,27,31,35,43,51,59,67,83,99,115,131,163,195,227,258],extra=[0,0,0,0,0,0,0,0,1,1,1,1,2,2,2,2,3,3,3,3,4,4,4,4,5,5,5,5,0];
 for(let i=0;i<raw.length;){let n=0;if(i&&raw[i]===raw[i-1])while(n<258&&i+n<raw.length&&raw[i+n]===raw[i-1])n++;if(n>=3){let k=bases.length-1;while(bases[k]>n)k--;sym(257+k);if(extra[k])bit.put(n-bases[k],extra[k]);bit.put(0,5);i+=n}else{sym(raw[i]);i++}}
 sym(256);let ad1=1,ad2=0;for(const x of raw){ad1=(ad1+x)%65521;ad2=(ad2+ad1)%65521;}
 const z=[120,1,...bit.end(),...be((ad2<<16)|ad1)];
 function chunk(t,data){let c=0xffffffff;for(const v of [...asc(t),...data]){c^=v;for(let j=0;j<8;j++)c=(c>>>1)^((c&1)?0xedb88320:0)}return [...be(data.length),...asc(t),...data,...be((c^0xffffffff)>>>0)]}
 return new Uint8Array([137,80,78,71,13,10,26,10,...chunk("IHDR",[...be(r.w),...be(r.h),8,3,0,0,0]),...chunk("PLTE",pal.flat()),...chunk("IDAT",z),...chunk("IEND",[])]);
 }
 function gif(frames,delays){
 const {w,h}=frames[0];let out=[...asc("GIF89a"),...u16(w),...u16(h),0xf7,0,0,...pal.flat(),...Array((256-pal.length)*3).fill(0),0x21,0xff,11,...asc("NETSCAPE2.0"),3,1,0,0,0];
 for(let f=0;f<frames.length;f++){out.push(0x21,0xf9,4,4,...u16(delays[f]),0,0,0x2c,0,0,0,0,...u16(w),...u16(h),0,8);const bit=bits();let dict=new Map(),next=258;bit.put(256,9);let cur=frames[f].p[0];for(let i=1;i<frames[f].p.length;i++){const val=frames[f].p[i],key=cur*256+val;if(dict.has(key)){cur=dict.get(key);continue}bit.put(cur,9);if(next<510){dict.set(key,next++);}else{bit.put(256,9);dict=new Map();next=258}cur=val;}bit.put(cur,9);bit.put(257,9);const packed=bit.end();for(let i=0;i<packed.length;i+=255){const b=packed.slice(i,i+255);out.push(b.length,...b)}out.push(0);}
 out.push(0x3b);return new Uint8Array(out);
 }
 const social=raster(2);social.txt(30,24,"JETSON THOR LLM BENCH",3,3);social.txt(30,64,"FASTER INFERENCE.",5);social.txt(30,110,"BETTER AGENT?",5);
 social.rect(30,164,360,151,1);social.rect(410,164,360,151,1);
 social.txt(45,178,"B2 NVFP4",3,4);social.txt(425,178,"H2 FP8 HYBRID",3,5);
 social.txt(45,216,fmt(rates[0]),6);social.txt(425,216,fmt(rates[1]),6);social.txt(45,265,"TOK/S",3,3);social.txt(425,265,"TOK/S",3,3);
 social.txt(30,331,"SEEDED REPAIR",3,3);social.txt(322,324,`${repair[0].passed}/${repair[0].total}`,5,4);social.txt(550,324,`${repair[1].passed}/${repair[1].total}`,5,5);
 social.rect(30,377,740,2,10);social.txt(30,391,`${fmt(rates[1]/rates[0])}X THROUGHPUT / SYNTHETIC WORKFLOWS`,2,6);social.txt(30,416,"DEPLOYMENT COMPARISON - NOT PRECISION ONLY",2,3);
 out["social-preview.png"]=png(social);
 const wfFrames=[];for(let frame=0;frame<5;frame++){const r=raster();r.txt(25,19,"VERIFICATION MATTERS",4);r.txt(25,58,"CONCEPTUAL RECONSTRUCTION - NOT LIVE",2,3);r.txt(25,90,"REQUIRED WORKFLOW",3,4);r.txt(415,90,"OMISSION PATTERN",3,5);
 const l=["SOURCE + FAILING TEST","SIMULATED EDIT","POST-EDIT TEST PASS","WORKFLOW PASS"],rr=["SOURCE READ","PRE-EDIT TEST SKIPPED","EDIT + POST-EDIT PASS","WORKFLOW FAIL"];
 for(let i=0;i<4;i++){const y=126+i*65;for(let j=0;j<2;j++){const x=25+j*390;let active=i<=frame;let color=active?(i===3?(j===0?8:9):(j===1&&i===1?9:1)):0;r.rect(x,y,360,52,color);r.txt(x+9,y+17,(j?rr:l)[i],2,active?2:10);}}
 r.txt(25,405,"3 H2 EPISODES OMITTED THE REQUIRED TEST",2,3);r.txt(25,428,"NO GENERATED CODE OR REAL TESTS EXECUTED",2,3);wfFrames.push(r);}
 out["verification-workflow.gif"]=gif(wfFrames,[140,140,140,200,220]);
 const prFrames=[];for(let frame=0;frame<4;frame++){const r=raster();r.txt(25,20,"SHARED CONTEXT",4);r.txt(25,59,"ANIMATION OF NOV 7 MEASURED MEDIANS",2,3);
 for(let i=0;i<2;i++){let y=100+i*132;r.txt(25,y,i?"AGENT FOLLOW-UP":"IDENTICAL PREFIX",3,2);for(let j=0;j<2;j++){let v=Number((j?repeatRows:prefixRows)[i+1]);r.rect(25,y+34+j*32,470,24,1);if(frame>=j+i){r.rect(25,y+34+j*32,Math.round(470*v/5),24,j?5:4);r.txt(510,y+38+j*32,`${fmt(v)} S`,2);}}if(frame>=i+1)r.txt(645,y+45,`${ratios[i+1]}X`,2,6);}
 r.txt(25,379,"5 PAIRS PER SUITE / MEDIAN PAIRED RATIOS",2,3);r.txt(25,405,"SERVER-WIDE HIT DELTAS: 10/10 FOLLOW-UPS",2,3);r.txt(25,428,"NOT VERIFIED PER-REQUEST CACHE HITS",2,3);prFrames.push(r);}
 out["prefix-responsiveness.gif"]=gif(prFrames,[140,150,180,240]);
 return out;
}
const sources=["docs/data/fp8-hybrid-comparison.json","docs/benchmarks/2026-11-07-shockwave-five-pair-prefix-agent.md","docs/benchmarks/2026-11-08-fp8-hybrid-comparison.md"];
const raw=sources.map(s=>fs.readFileSync(path.join(root,s),"utf8"));
const files=generate(...raw);
for(const [name,content] of Object.entries(files))fs.writeFileSync(path.join(root,"docs/figures",name),content);
const manifest={renderer:"scripts/render_publication.cjs",version:1,source_sha256:Object.fromEntries(sources.map((s,i)=>[s,crypto.createHash("sha256").update(raw[i]).digest("hex")])),figures:Object.fromEntries(Object.keys(files).map(name=>[name,{type:name==="verification-workflow.gif"||name==="verification-workflow.svg"?"conceptual reconstruction":name.endsWith(".gif")?"animated measured summary":"measured summary",sha256:crypto.createHash("sha256").update(files[name]).digest("hex")}]))};
fs.writeFileSync(path.join(root,"docs/figures/publication-sha256.json"),JSON.stringify(manifest,null,2)+"\n");
