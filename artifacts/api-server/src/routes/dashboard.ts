import { Router, type IRouter } from "express";
import { writeFile } from "node:fs/promises";
import { doStart, doStop, isRunning, readLogLines, parseStats, outputFileExists, getScraperState } from "./scraper";

const router: IRouter = Router();

function fmt(sec: number): string {
  const h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60), s = sec % 60;
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

function phaseLabel(p: string): string {
  return ({ idle: "—", yellowpages: "🟡 YellowPages", facebook: "🔵 Facebook", done: "✅ اكتمل" } as Record<string,string>)[p] ?? p;
}

function colorClass(l: string): string {
  if (l.includes("[ERR]")) return "err";
  if (l.includes("✅") || l.includes("انتهى")) return "ok";
  if (l.includes("=") || l.includes("─")) return "title";
  if (l.includes("شركة") || l.includes("req/s") || l.includes("📧")) return "ok";
  return "info";
}

function escHtml(s: string): string {
  return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}

async function renderPage(running: boolean): Promise<string> {
  const lines  = await readLogLines();
  const stats  = parseStats(lines);
  const state  = getScraperState();
  const hasOut = await outputFileExists();

  const logLines = lines.slice(-80);
  const logHtml  = logLines.map(l =>
    `<div class="line ${colorClass(l)}">${escHtml(l)}</div>`
  ).join("");

  let elapsed = "—";
  if (running && state.startedAt) {
    elapsed = fmt(Math.floor((Date.now() - state.startedAt.getTime()) / 1000));
  } else if (state.startedAt && state.finishedAt) {
    elapsed = fmt(Math.floor((state.finishedAt.getTime() - state.startedAt.getTime()) / 1000));
  }

  const timeInfo = state.startedAt
    ? `بدأ: ${state.startedAt.toLocaleString("ar-EG")}${state.finishedAt ? " | انتهى: " + state.finishedAt.toLocaleString("ar-EG") : ""}`
    : "";

  const badgeClass = running ? "running" : (state.exitCode === 0 && state.finishedAt ? "done" : "stopped");
  const badgeText  = running ? '<span class="dot"></span> جاري التشغيل' :
                     (state.exitCode === 0 && state.finishedAt ? "✅ اكتمل" : "⬤ متوقف");

  const metaRefresh = "";

  const dlBtn = hasOut
    ? `<a class="dl-btn show" href="/api/scraper/download" download="Egypt_Companies.xlsx">⬇ تحميل النتائج</a>`
    : `<a class="dl-btn" href="#">⬇ تحميل النتائج</a>`;

  const startBtn = running
    ? `<button class="btn btn-start" disabled>▶ تشغيل</button>`
    : `<a class="btn btn-start" href="/?action=start" style="text-decoration:none;display:inline-block">▶ تشغيل</a>`;

  const stopBtn = running
    ? `<a class="btn btn-stop" href="/?action=stop" style="text-decoration:none;display:inline-block">■ إيقاف</a>`
    : `<button class="btn btn-stop" disabled>■ إيقاف</button>`;

  return `<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
${metaRefresh}
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
  .log-box{background:#0f172a;border:1px solid #1e293b;border-radius:12px;padding:16px;height:340px;overflow-y:auto;font-family:"Cascadia Code","Consolas",monospace;font-size:.78rem;line-height:1.6;direction:ltr;text-align:left}
  .log-box .line{padding:1px 0;white-space:pre-wrap;word-break:break-all}
  .log-box .line.err{color:#f87171}
  .log-box .line.ok{color:#4ade80}
  .log-box .line.info{color:#94a3b8}
  .log-box .line.title{color:#fbbf24;font-weight:700}
  .log-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}
  .log-header h2{font-size:1rem;color:#cbd5e1}
  .dl-btn{display:none;padding:8px 18px;border-radius:8px;background:#0369a1;color:#fff;border:none;cursor:pointer;font-size:.85rem;font-weight:600;text-decoration:none}
  .dl-btn.show{display:inline-block}
  .dl-btn:hover{background:#0284c7}
  .time-info{font-size:.78rem;color:#64748b;margin-top:8px;text-align:center}
  .refresh-note{font-size:.72rem;color:#64748b;text-align:center;margin-top:6px}
  .btn-refresh{padding:6px 16px;border-radius:8px;background:#1e293b;color:#94a3b8;border:1px solid #334155;font-size:.8rem;cursor:pointer;text-decoration:none;display:inline-block}
  .btn-refresh:hover{border-color:#38bdf8;color:#38bdf8}
</style>
</head>
<body>
<h1>🗂️ مستخرج بيانات <span>شركات مصر</span></h1>

<div class="status-bar">
  <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">
    <div class="badge ${badgeClass}">${badgeText}</div>
    <div class="phase">المرحلة: <span>${phaseLabel(stats.phase)}</span></div>
  </div>
  <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">
    ${dlBtn}
    ${startBtn}
    ${stopBtn}
  </div>
</div>

<div class="grid">
  <div class="card"><div class="val">${stats.companiesFound.toLocaleString("ar-EG")}</div><div class="lbl">شركة تم جمعها</div></div>
  <div class="card"><div class="val">${stats.idsProcessed.toLocaleString("ar-EG")}</div><div class="lbl">ID تم فحصه</div></div>
  <div class="card"><div class="val">${stats.speed.toFixed(1)}</div><div class="lbl">req/s</div></div>
  <div class="card"><div class="val">${elapsed}</div><div class="lbl">وقت التشغيل</div></div>
</div>

<div class="log-header">
  <h2>📋 السجل المباشر</h2>
  <span style="font-size:.75rem;color:#475569">${lines.length} سطر</span>
</div>
<div class="log-box" id="logBox">
${logHtml || '<div class="line info">في انتظار بدء التشغيل...</div>'}
</div>
${timeInfo ? `<div class="time-info">${timeInfo}</div>` : ""}
<div class="refresh-note" style="margin-top:12px">
  <a class="btn-refresh" href="/">🔄 تحديث الصفحة</a>
  ${running ? `&nbsp;&nbsp;<span style="color:#475569;font-size:.72rem">يعمل ← اضغط تحديث لرؤية التقدم</span>` : ""}
</div>

<script>
document.getElementById('logBox').scrollTop = document.getElementById('logBox').scrollHeight;
${running ? `setTimeout(function(){ try{ window.location.href='/'; }catch(e){ window.location.reload(); } }, 3000);` : ""}
</script>
</body>
</html>`;
}

router.get("/", async (req, res) => {
  res.setHeader("Content-Type", "text/html; charset=utf-8");
  res.setHeader("Cache-Control", "no-store, no-cache, must-revalidate, private");
  res.setHeader("Pragma", "no-cache");

  const action = req.query["action"];

  if (action === "start") {
    await writeFile("/tmp/scraper_config.json", JSON.stringify({ categories: null, governorates: null }), "utf8").catch(() => {});
    await doStart().catch(() => {});
    res.redirect(302, "/");
    return;
  } else if (action === "stop") {
    await doStop().catch(() => {});
    res.redirect(302, "/");
    return;
  }

  const running = await isRunning();
  const html = await renderPage(running);
  res.send(html);
});

export default router;
