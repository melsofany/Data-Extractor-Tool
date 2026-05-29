import { Router, type IRouter } from "express";

const router: IRouter = Router();

const HTML = `<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>مستخرج بيانات شركات مصر</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:"Segoe UI",Tahoma,Arial,sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh;padding:24px}
  h1{text-align:center;font-size:1.6rem;font-weight:700;color:#f8fafc;margin-bottom:24px}
  h1 span{color:#38bdf8}
  .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:16px;margin-bottom:24px}
  .card{background:#1e293b;border-radius:12px;padding:20px;text-align:center;border:1px solid #334155}
  .card .val{font-size:2rem;font-weight:800;color:#38bdf8;margin-bottom:4px}
  .card .lbl{font-size:.8rem;color:#94a3b8}
  .status-bar{background:#1e293b;border-radius:12px;padding:16px 20px;margin-bottom:24px;display:flex;align-items:center;justify-content:space-between;border:1px solid #334155;flex-wrap:wrap;gap:12px}
  .badge{display:inline-flex;align-items:center;gap:6px;padding:6px 14px;border-radius:20px;font-size:.85rem;font-weight:600}
  .badge.running{background:#14532d;color:#4ade80}
  .badge.stopped{background:#1e293b;color:#94a3b8;border:1px solid #475569}
  .badge.done{background:#1e3a5f;color:#38bdf8}
  .dot{width:8px;height:8px;border-radius:50%;background:currentColor;animation:pulse 1.2s infinite}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
  .btn{padding:10px 24px;border-radius:8px;border:none;cursor:pointer;font-size:.9rem;font-weight:700;transition:.2s}
  .btn-start{background:#16a34a;color:#fff}
  .btn-start:hover{background:#15803d}
  .btn-stop{background:#dc2626;color:#fff}
  .btn-stop:hover{background:#b91c1c}
  .btn:disabled{opacity:.45;cursor:not-allowed}
  .phase{font-size:.8rem;color:#94a3b8}
  .phase span{color:#fbbf24;font-weight:600}
  .log-box{background:#0f172a;border:1px solid #1e293b;border-radius:12px;padding:16px;height:360px;overflow-y:auto;font-family:"Cascadia Code","Consolas",monospace;font-size:.78rem;line-height:1.6;direction:ltr;text-align:left}
  .log-box .line{padding:1px 0;white-space:pre-wrap;word-break:break-all}
  .log-box .line.err{color:#f87171}
  .log-box .line.ok{color:#4ade80}
  .log-box .line.info{color:#94a3b8}
  .log-box .line.title{color:#fbbf24;font-weight:700}
  .log-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}
  .log-header h2{font-size:1rem;color:#cbd5e1}
  .chk{display:flex;align-items:center;gap:6px;font-size:.8rem;color:#94a3b8;cursor:pointer}
  .dl-btn{display:none;padding:8px 18px;border-radius:8px;background:#0369a1;color:#fff;border:none;cursor:pointer;font-size:.85rem;font-weight:600;text-decoration:none}
  .dl-btn.show{display:inline-block}
  .dl-btn:hover{background:#0284c7}
  .time-info{font-size:.78rem;color:#64748b;margin-top:8px;text-align:center}
  .err-msg{background:#450a0a;color:#f87171;border-radius:8px;padding:8px 14px;font-size:.8rem;margin-top:8px;display:none}
  .err-msg.show{display:block}
</style>
</head>
<body>
<h1>🗂️ مستخرج بيانات <span>شركات مصر</span></h1>

<div class="status-bar">
  <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">
    <div id="badge" class="badge stopped">⬤ متوقف</div>
    <div class="phase">المرحلة: <span id="phase">—</span></div>
  </div>
  <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">
    <a id="dlBtn" class="dl-btn" href="/api/scraper/download" download="Egypt_Companies.xlsx">⬇ تحميل النتائج</a>
    <button id="startBtn" class="btn btn-start" onclick="startScraper()">▶ تشغيل</button>
    <button id="stopBtn" class="btn btn-stop" onclick="stopScraper()" disabled>■ إيقاف</button>
  </div>
</div>

<div id="errMsg" class="err-msg"></div>

<div class="grid">
  <div class="card"><div class="val" id="cFound">0</div><div class="lbl">شركة تم جمعها</div></div>
  <div class="card"><div class="val" id="cIds">0</div><div class="lbl">ID تم فحصه</div></div>
  <div class="card"><div class="val" id="cSpeed">0</div><div class="lbl">req/s</div></div>
  <div class="card"><div class="val" id="cElapsed">—</div><div class="lbl">وقت التشغيل</div></div>
</div>

<div class="log-header">
  <h2>📋 السجل المباشر</h2>
  <label class="chk"><input type="checkbox" id="autoScroll" checked/> تمرير تلقائي</label>
</div>
<div class="log-box" id="logBox"></div>
<div class="time-info" id="timeInfo"></div>

<script>
let logOffset=0, polling=null, startTime=null;

const NO_CACHE = { cache: 'no-store', headers: { 'Cache-Control': 'no-cache' } };

function showErr(msg){ const e=document.getElementById('errMsg'); e.textContent=msg; e.classList.add('show'); }
function hideErr(){ document.getElementById('errMsg').classList.remove('show'); }

function colorLine(l){
  if(l.startsWith('[ERR]')) return 'err';
  if(l.includes('✅')||l.includes('انتهى')) return 'ok';
  if(l.includes('=')||l.includes('─')) return 'title';
  if(l.includes('شركة')||l.includes('req/s')) return 'ok';
  return 'info';
}

function appendLines(lines){
  const box=document.getElementById('logBox');
  lines.forEach(l=>{
    const d=document.createElement('div');
    d.className='line '+colorLine(l);
    d.textContent=l;
    box.appendChild(d);
  });
  if(document.getElementById('autoScroll').checked){
    box.scrollTop=box.scrollHeight;
  }
}

function fmt(sec){
  const h=Math.floor(sec/3600), m=Math.floor((sec%3600)/60), s=sec%60;
  if(h>0) return h+'h '+m+'m';
  if(m>0) return m+'m '+s+'s';
  return s+'s';
}

function phaseLabel(p){
  return {idle:'—',yellowpages:'🟡 YellowPages',facebook:'🔵 Facebook',done:'✅ اكتمل'}[p]||p;
}

async function fetchStatus(){
  try{
    const r=await fetch('/api/scraper/status?_='+Date.now(), NO_CACHE);
    if(!r.ok) return;
    const d=await r.json();
    const running=d.running;
    const s=d.stats;

    document.getElementById('badge').className='badge '+(running?'running':(d.exitCode===0&&d.finishedAt?'done':'stopped'));
    document.getElementById('badge').innerHTML=(running?'<span class="dot"></span> جاري التشغيل':(d.exitCode===0&&d.finishedAt?'✅ اكتمل':'⬤ متوقف'));
    document.getElementById('phase').textContent=phaseLabel(s.phase);
    document.getElementById('cFound').textContent=s.companiesFound.toLocaleString('ar-EG');
    document.getElementById('cIds').textContent=s.idsProcessed.toLocaleString('ar-EG');
    document.getElementById('cSpeed').textContent=s.speed.toFixed(1);

    if(running&&startTime){
      const elapsed=Math.floor((Date.now()-startTime)/1000);
      document.getElementById('cElapsed').textContent=fmt(elapsed);
    } else if(d.startedAt&&d.finishedAt){
      const elapsed=Math.floor((new Date(d.finishedAt)-new Date(d.startedAt))/1000);
      document.getElementById('cElapsed').textContent=fmt(elapsed);
    }

    document.getElementById('startBtn').disabled=running;
    document.getElementById('stopBtn').disabled=!running;
    if(d.hasOutput) document.getElementById('dlBtn').classList.add('show');

    if(d.startedAt){
      const si=new Date(d.startedAt).toLocaleString('ar-EG');
      const fi=d.finishedAt?(' | انتهى: '+new Date(d.finishedAt).toLocaleString('ar-EG')):'';
      document.getElementById('timeInfo').textContent='بدأ: '+si+fi;
    }
  }catch(e){ console.error('status error',e); }
}

async function fetchLogs(){
  try{
    const r=await fetch('/api/scraper/logs?since='+logOffset+'&_='+Date.now(), NO_CACHE);
    if(!r.ok) return;
    const d=await r.json();
    if(d.lines.length>0){
      appendLines(d.lines);
      logOffset=d.total;
    }
  }catch(e){ console.error('logs error',e); }
}

async function startScraper(){
  hideErr();
  document.getElementById('startBtn').disabled=true;
  document.getElementById('logBox').innerHTML='';
  logOffset=0;
  startTime=Date.now();
  try{
    const r=await fetch('/api/scraper/start',{ method:'POST', ...NO_CACHE });
    const d=await r.json();
    if(!r.ok){ showErr('خطأ: '+(d.error||r.status)); document.getElementById('startBtn').disabled=false; return; }
    startPolling();
  }catch(e){
    showErr('تعذر الاتصال بالسيرفر: '+e.message);
    document.getElementById('startBtn').disabled=false;
  }
}

async function stopScraper(){
  try{
    await fetch('/api/scraper/stop',{ method:'POST', ...NO_CACHE });
  }catch(e){}
}

function startPolling(){
  if(polling) clearInterval(polling);
  polling=setInterval(async()=>{
    await fetchLogs();
    await fetchStatus();
  },1500);
}

(async()=>{
  await fetchStatus();
  await fetchLogs();
  startPolling();
})();
</script>
</body>
</html>`;

router.get("/", (_req, res) => {
  res.setHeader("Content-Type", "text/html; charset=utf-8");
  res.setHeader("Cache-Control", "no-store");
  res.send(HTML);
});

export default router;
