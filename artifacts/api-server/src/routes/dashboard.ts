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
  .status-bar{background:#1e293b;border-radius:12px;padding:16px 20px;margin-bottom:16px;display:flex;align-items:center;justify-content:space-between;border:1px solid #334155;flex-wrap:wrap;gap:12px}
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
  .log-box{background:#0f172a;border:1px solid #1e293b;border-radius:12px;padding:16px;height:320px;overflow-y:auto;font-family:"Cascadia Code","Consolas",monospace;font-size:.78rem;line-height:1.6;direction:ltr;text-align:left}
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
  /* ── لوحة الإعدادات ───────────────── */
  .settings-panel{background:#1e293b;border-radius:12px;margin-bottom:20px;border:1px solid #334155;overflow:hidden}
  .settings-header{display:flex;align-items:center;justify-content:space-between;padding:12px 18px;cursor:pointer;user-select:none}
  .settings-header:hover{background:#263044}
  .settings-header h3{font-size:.9rem;color:#94a3b8;font-weight:600}
  .settings-arrow{color:#64748b;transition:transform .2s;font-size:.75rem}
  .settings-arrow.open{transform:rotate(180deg)}
  .settings-body{padding:16px 18px;border-top:1px solid #334155;display:none}
  .settings-body.open{display:block}
  .settings-section{margin-bottom:16px}
  .settings-section:last-child{margin-bottom:0}
  .settings-section h4{font-size:.8rem;color:#94a3b8;margin-bottom:10px;font-weight:600;letter-spacing:.03em}
  .cb-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:6px}
  .cb-item{display:flex;align-items:center;gap:7px;padding:6px 10px;border-radius:7px;background:#0f172a;border:1px solid #334155;cursor:pointer;font-size:.78rem;color:#cbd5e1;transition:border-color .15s}
  .cb-item:hover{border-color:#38bdf8}
  .cb-item input{accent-color:#38bdf8;cursor:pointer;flex-shrink:0}
  .mini-btns{display:flex;gap:8px;margin-top:8px}
  .mini-btn{padding:4px 12px;border-radius:6px;border:1px solid #334155;background:transparent;color:#94a3b8;font-size:.75rem;cursor:pointer}
  .mini-btn:hover{border-color:#38bdf8;color:#38bdf8}
  .settings-summary{font-size:.75rem;color:#64748b;margin-top:4px}
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

<!-- ─── لوحة الإعدادات ─────────────────────────────────── -->
<div class="settings-panel">
  <div class="settings-header" onclick="toggleSettings()">
    <h3>⚙️ إعدادات الجمع</h3>
    <span class="settings-arrow" id="sArrow">▼</span>
  </div>
  <div class="settings-body" id="sBody">
    <div class="settings-section">
      <h4>التصنيفات المستهدفة</h4>
      <div class="cb-grid" id="catGrid"></div>
      <div class="mini-btns">
        <button class="mini-btn" onclick="selAll('cat',true)">تحديد الكل</button>
        <button class="mini-btn" onclick="selAll('cat',false)">إلغاء الكل</button>
      </div>
      <div class="settings-summary" id="catSummary"></div>
    </div>
    <div class="settings-section">
      <h4>المحافظات</h4>
      <div class="cb-grid" id="govGrid"></div>
      <div class="mini-btns">
        <button class="mini-btn" onclick="selAll('gov',true)">تحديد الكل</button>
        <button class="mini-btn" onclick="selAll('gov',false)">إلغاء الكل</button>
      </div>
      <div class="settings-summary" id="govSummary"></div>
    </div>
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
/* ─── بيانات التصنيفات والمحافظات ─────────────────────────── */
const CATEGORIES = [
  {id:"الصحة والسلامة ومقاومة الحريق",         label:"🔥 الحريق والسلامة",        def:true},
  {id:"الكهرباء والكابلات والأسلاك",            label:"⚡ الكهرباء والكابلات",       def:true},
  {id:"الميكانيكا",                             label:"⚙️ الميكانيكا",              def:true},
  {id:"الإلكترونيات",                           label:"📱 الإلكترونيات",             def:true},
  {id:"أدوات النظافة",                          label:"🧹 أدوات النظافة",            def:true},
  {id:"معدات المطابخ الكبيرة الفندقية وقطع غيارها",label:"🍽️ مطابخ فندقية",        def:true},
  {id:"الأثاث المكتبي",                         label:"🪑 الأثاث المكتبي",           def:true},
  {id:"تكنولوجيا المعلومات (IT)",               label:"💻 تقنية المعلومات",          def:true},
  {id:"مواد البناء والمقاولات",                 label:"🏗️ مواد البناء",              def:false},
  {id:"المعدات الطبية والصيدلانية",             label:"🏥 المعدات الطبية",           def:false},
  {id:"السيارات وقطع الغيار",                   label:"🚗 السيارات وقطع الغيار",     def:false},
  {id:"الأمن والحراسة وأنظمة المراقبة",         label:"🔒 الأمن والمراقبة",          def:false},
  {id:"التكييف والتبريد",                       label:"❄️ التكييف والتبريد",          def:false},
  {id:"معالجة المياه والصرف الصحي",             label:"💧 معالجة المياه",             def:false},
  {id:"الطباعة والنشر والإعلان",                label:"🖨️ الطباعة والإعلان",          def:false},
  {id:"الأغذية والمشروبات",                     label:"🍔 أغذية ومشروبات",           def:false},
  {id:"النسيج والملابس",                        label:"👕 نسيج وملابس",              def:false},
  {id:"الشحن والنقل واللوجستيات",               label:"🚛 شحن ونقل",                 def:false},
  {id:"الزراعة والري",                          label:"🌱 الزراعة والري",              def:false},
  {id:"العقارات والمقاولات",                    label:"🏢 العقارات",                  def:false},
  {id:"معدات البترول والطاقة",                  label:"🛢️ معدات البترول والطاقة",      def:true},
  {id:"معدات الحفر والتنقيب",                   label:"⛏️ معدات الحفر والتنقيب",       def:true},
  {id:"المعدات البحرية والملاحة",               label:"⚓ المعدات البحرية والملاحة",    def:true},
];

const GOVERNORATES = [
  {id:"cairo",         label:"القاهرة",       def:true},
  {id:"alexandria",    label:"الإسكندرية",   def:true},
  {id:"giza",          label:"الجيزة",        def:true},
  {id:"qalyubia",      label:"القليوبية",     def:false},
  {id:"sharkia",       label:"الشرقية",       def:false},
  {id:"dakahlia",      label:"الدقهلية",      def:false},
  {id:"gharbia",       label:"الغربية",       def:false},
  {id:"beheira",       label:"البحيرة",       def:false},
  {id:"menoufia",      label:"المنوفية",      def:false},
  {id:"kafr-elsheikh", label:"كفر الشيخ",    def:false},
  {id:"damietta",      label:"دمياط",         def:false},
  {id:"ismailia",      label:"الإسماعيلية",  def:false},
  {id:"port-said",     label:"بورسعيد",       def:false},
  {id:"suez",          label:"السويس",        def:false},
  {id:"beni-suef",     label:"بني سويف",     def:false},
  {id:"faiyum",        label:"الفيوم",        def:false},
  {id:"minya",         label:"المنيا",        def:false},
  {id:"asyut",         label:"أسيوط",         def:false},
  {id:"sohag",         label:"سوهاج",         def:false},
  {id:"qena",          label:"قنا",           def:false},
  {id:"luxor",         label:"الأقصر",        def:false},
  {id:"aswan",         label:"أسوان",         def:false},
  {id:"red-sea",       label:"البحر الأحمر",  def:false},
  {id:"north-sinai",   label:"شمال سيناء",   def:false},
  {id:"south-sinai",   label:"جنوب سيناء",   def:false},
  {id:"matrouh",       label:"مطروح",         def:false},
  {id:"new-valley",    label:"الوادي الجديد", def:false},
];

/* ─── رسم الإعدادات ────────────────────────────────────────── */
function buildGrid(items, gridId, storageKey){
  const saved = (() => { try{ return JSON.parse(localStorage.getItem(storageKey)||'null'); }catch{return null;} })();
  const grid = document.getElementById(gridId);
  items.forEach(item => {
    const checked = saved ? saved.includes(item.id) : item.def;
    const label = document.createElement('label');
    label.className = 'cb-item';
    label.innerHTML = '<input type="checkbox" value="'+item.id+'"'+(checked?' checked':'')+'> '+item.label;
    label.querySelector('input').addEventListener('change', () => updateSummary(items, gridId, storageKey));
    grid.appendChild(label);
  });
  updateSummary(items, gridId, storageKey);
}

function updateSummary(items, gridId, storageKey){
  const checked = getChecked(gridId);
  localStorage.setItem(storageKey, JSON.stringify(checked));
  const summaryId = gridId === 'catGrid' ? 'catSummary' : 'govSummary';
  const total = items.length;
  const n = checked.length;
  document.getElementById(summaryId).textContent =
    n === total ? 'كل التصنيفات محددة' :
    n === 0     ? 'لم يُحدد شيء — سيتم تضمين الكل' :
    n+' من '+total+' محدد';
}

function getChecked(gridId){
  return [...document.querySelectorAll('#'+gridId+' input:checked')].map(i=>i.value);
}

function selAll(type, state){
  const gridId = type==='cat' ? 'catGrid' : 'govGrid';
  document.querySelectorAll('#'+gridId+' input').forEach(i => i.checked = state);
  const items = type==='cat' ? CATEGORIES : GOVERNORATES;
  const storageKey = type==='cat' ? 'scraper_cats' : 'scraper_govs';
  updateSummary(items, gridId, storageKey);
}

function toggleSettings(){
  const body = document.getElementById('sBody');
  const arrow = document.getElementById('sArrow');
  const open = body.classList.toggle('open');
  arrow.classList.toggle('open', open);
}

function collectConfig(){
  const cats = getChecked('catGrid');
  const govs = getChecked('govGrid');
  return {
    categories: cats.length > 0 ? cats : null,
    governorates: govs.length > 0 ? govs : null,
  };
}

buildGrid(CATEGORIES, 'catGrid', 'scraper_cats');
buildGrid(GOVERNORATES, 'govGrid', 'scraper_govs');

/* ─── منطق الداشبورد ───────────────────────────────────────── */
let logOffset=0, polling=null, startTime=null;
const NC = { cache: 'no-store' };

function showErr(msg){ const e=document.getElementById('errMsg'); e.textContent=msg; e.classList.add('show'); }
function hideErr(){ document.getElementById('errMsg').classList.remove('show'); }

function colorLine(l){
  if(l.includes('[ERR]')) return 'err';
  if(l.includes('✅')||l.includes('انتهى')) return 'ok';
  if(l.includes('=')||l.includes('─')) return 'title';
  if(l.includes('شركة')||l.includes('req/s')||l.includes('📧')) return 'ok';
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
    if(window.__pendingStart){
      document.cookie='__sc='+window.__pendingStart.c+','+window.__pendingStart.v+';path=/;max-age=10';
      window.__pendingStart=null;
    }
    const r=await fetch('/api/scraper/status?_='+Date.now(), NC);
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
      document.getElementById('cElapsed').textContent=fmt(Math.floor((Date.now()-startTime)/1000));
    } else if(d.startedAt&&d.finishedAt){
      document.getElementById('cElapsed').textContent=fmt(Math.floor((new Date(d.finishedAt)-new Date(d.startedAt))/1000));
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
    const r=await fetch('/api/scraper/logs?since='+logOffset+'&_='+Date.now(), NC);
    if(!r.ok) return;
    const d=await r.json();
    // لو الملف اتمسح وبدأ من أول (بعد تشغيل جديد)، صفّر الـ offset وامسح الـ log box
    if(d.total < logOffset){
      logOffset=0;
      document.getElementById('logBox').innerHTML='';
    }
    if(d.lines.length>0){ appendLines(d.lines); logOffset=d.total; }
  }catch(e){ console.error('logs error',e); }
}

async function startScraper(){
  hideErr();
  document.getElementById('startBtn').disabled=true;
  document.getElementById('logBox').innerHTML='';
  logOffset=0;
  startTime=Date.now();
  document.getElementById('badge').className='badge running';
  document.getElementById('badge').innerHTML='<span class="dot"></span> جاري التشغيل';
  const config=collectConfig();
  const catBits=CATEGORIES.reduce((b,c,i)=>b|((!config.categories||config.categories.includes(c.id))?(1<<i):0),0);
  const govBits=GOVERNORATES.reduce((b,g,i)=>b|((!config.governorates||config.governorates.includes(g.id))?(1<<i):0),0);
  // نبعت أمر التشغيل عن طريق الـ polling interval — مش عن طريق fetch منفصل
  window.__pendingStart={c:catBits,v:govBits};
  startPolling();
}

async function stopScraper(){
  try{ await fetch('/api/scraper/stop?_='+Date.now(),{method:'POST',cache:'no-store'}); }catch{ /* ignore */ }
}

function startPolling(){
  if(polling) clearInterval(polling);
  polling=setInterval(async()=>{
    await fetchLogs();
    await fetchStatus();
  },1000);
}

(async()=>{ await fetchStatus(); await fetchLogs(); startPolling(); })();
</script>
</body>
</html>`;

router.get("/", (_req, res) => {
  res.setHeader("Content-Type", "text/html; charset=utf-8");
  res.setHeader("Cache-Control", "no-store");
  res.send(HTML);
});

export default router;
