import { Router, type IRouter } from "express";
import { spawn, type ChildProcess } from "node:child_process";
import { access, readFile, truncate, writeFile } from "node:fs/promises";
import { openSync, closeSync, appendFileSync } from "node:fs";
import path from "node:path";

const router: IRouter = Router();

const SCRIPT_PATH = "/home/runner/workspace/scripts/scraper/egypt_companies_scraper.py";
const OUTPUT_FILE = "/home/runner/workspace/Egypt_Companies_Real_Data.xlsx";
const LOG_FILE    = "/tmp/scraper_live.log";
const PID_FILE    = "/tmp/scraper.pid";

let scraperProcess: ChildProcess | null = null;
let startedAt: Date | null = null;
let finishedAt: Date | null = null;
let exitCode: number | null = null;

/** يُستدعى مرة واحدة عند بدء السيرفر لإنهاء أي سكريبت قديم تلقائياً */
export async function killOrphanedScraper(): Promise<void> {
  try {
    const pid = parseInt((await readFile(PID_FILE, "utf8")).trim());
    if (!pid) return;
    const cmdline = await readFile(`/proc/${pid}/cmdline`, "utf8");
    if (!cmdline.includes("egypt_companies_scraper")) return;
    try { process.kill(pid, "SIGKILL"); } catch { /* already gone */ }
  } catch { /* no PID file */ }
  try { await writeFile(PID_FILE, "", "utf8"); } catch { /* ignore */ }
}

async function isRunning(): Promise<boolean> {
  if (scraperProcess && scraperProcess.exitCode === null) return true;
  try {
    const pid = parseInt((await readFile(PID_FILE, "utf8")).trim());
    if (!pid) return false;
    // Verify the PID belongs to our scraper script, not just any process
    const cmdline = await readFile(`/proc/${pid}/cmdline`, "utf8");
    if (!cmdline.includes("egypt_companies_scraper")) return false;
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}

async function outputFileExists() {
  try { await access(OUTPUT_FILE); return true; } catch { return false; }
}

function parseStats(lines: string[]) {
  const stats = { companiesFound: 0, idsProcessed: 0, speed: 0, phase: "idle" as string };
  let statsFound = false;
  for (let i = lines.length - 1; i >= 0; i--) {
    const line = lines[i] ?? "";
    if (!statsFound) {
      const m = line.match(/(\d+)\s+شركة\s*\|\s*فحص\s*([\d,]+)\s*\|\s*([\d.]+)\s*req\/s/);
      if (m) {
        statsFound = true;
        stats.companiesFound = parseInt(m[1] ?? "0");
        stats.idsProcessed   = parseInt((m[2] ?? "0").replace(/,/g, ""));
        stats.speed          = parseFloat(m[3] ?? "0");
      }
    }
    if (line.includes("🟡 YellowPages"))  stats.phase = "yellowpages";
    if (line.includes("🔵 Facebook"))     stats.phase = "facebook";
    if (line.includes("الملف النهائي")) stats.phase = "done";
    if (statsFound && stats.phase !== "idle") break;
  }
  return stats;
}

async function readLogLines(): Promise<string[]> {
  try {
    const raw = await readFile(LOG_FILE, "utf8");
    return raw.split("\n").filter((l) => l.trim());
  } catch { return []; }
}

export async function doStart(): Promise<{ ok: boolean; error?: string; pid?: number }> {
  // إذا كان شغّالاً، اقتله مباشرة بدون setTimeout حتى لا يقتل السكريبت الجديد
  if (scraperProcess && scraperProcess.exitCode === null) {
    scraperProcess.kill("SIGKILL");
    scraperProcess = null;
    await new Promise((r) => setTimeout(r, 300));
  } else {
    try {
      const pid = parseInt((await readFile(PID_FILE, "utf8")).trim());
      if (pid) {
        const cmdline = await readFile(`/proc/${pid}/cmdline`, "utf8").catch(() => "");
        if (cmdline.includes("egypt_companies_scraper")) {
          process.kill(pid, "SIGKILL");
          await new Promise((r) => setTimeout(r, 300));
        }
      }
    } catch { /* no old process */ }
  }
  try { await writeFile(PID_FILE, "", "utf8"); } catch { /* ignore */ }

  try { await truncate(LOG_FILE, 0); } catch { /* first run */ }
  try { await writeFile(LOG_FILE, "", "utf8"); } catch { /* ignore */ }

  startedAt  = new Date();
  finishedAt = null;
  exitCode   = null;

  const logFd = openSync(LOG_FILE, "a");
  scraperProcess = spawn("python3", ["-u", SCRIPT_PATH], {
    cwd: "/home/runner/workspace",
    env: { ...process.env, PYTHONUNBUFFERED: "1" },
    stdio: ["ignore", logFd, logFd],
    detached: false,
  });
  closeSync(logFd);

  await writeFile(PID_FILE, String(scraperProcess.pid ?? ""), "utf8");

  scraperProcess.on("exit", (code) => {
    finishedAt     = new Date();
    exitCode       = code;
    scraperProcess = null;
    try { appendFileSync(LOG_FILE, `\n✅ انتهى السكريبت بكود: ${code}\n`); } catch { /* ignore */ }
  });

  return { ok: true, pid: scraperProcess.pid };
}

export async function doStop(): Promise<{ ok: boolean; error?: string }> {
  if (!(await isRunning())) return { ok: false, error: "السكريبت مش شغّال" };

  if (scraperProcess) {
    scraperProcess.kill("SIGTERM");
    setTimeout(() => { try { scraperProcess?.kill("SIGKILL"); } catch {} }, 3000);
  } else {
    try {
      const pid = parseInt((await readFile(PID_FILE, "utf8")).trim());
      process.kill(pid, "SIGTERM");
      setTimeout(() => { try { process.kill(pid, "SIGKILL"); } catch {} }, 3000);
    } catch { /* already gone */ }
  }

  return { ok: true };
}

// ─── Start (GET + POST) ───────────────────────────────────────────────────────
async function handleStart(_req: any, res: any) {
  try {
    const result = await doStart();
    if (!result.ok) { res.status(409).json({ error: result.error }); return; }
    res.json({ ok: true, pid: result.pid });
  } catch (e) {
    res.status(500).json({ error: String(e) });
  }
}
router.get("/scraper/start", handleStart);
router.post("/scraper/start", handleStart);

// ─── Stop (GET + POST) ────────────────────────────────────────────────────────
async function handleStop(_req: any, res: any) {
  try {
    const result = await doStop();
    res.json(result);
  } catch (e) {
    res.status(500).json({ error: String(e) });
  }
}
router.get("/scraper/stop", handleStop);
router.post("/scraper/stop", handleStop);

// ─── Status (q=1 → start, q=0 → stop) ───────────────────────────────────────
router.get("/scraper/status", async (req, res) => {
  const q = req.query["q"];

  if (q === "1") {
    try {
      const result = await doStart();
      if (!result.ok) { res.status(409).json({ error: result.error }); return; }
    } catch (e) {
      res.status(500).json({ error: String(e) }); return;
    }
  } else if (q === "0") {
    try { await doStop(); } catch { /* ignore */ }
  }

  const running   = await isRunning();
  const lines     = await readLogLines();
  const stats     = parseStats(lines);
  const hasOutput = await outputFileExists();
  res.json({
    running,
    startedAt:  startedAt?.toISOString()  ?? null,
    finishedAt: finishedAt?.toISOString() ?? null,
    exitCode,
    stats,
    hasOutput,
    logCount: lines.length,
  });
});

// ─── Logs ─────────────────────────────────────────────────────────────────────
router.get("/scraper/logs", async (req, res) => {
  const since = parseInt(String(req.query["since"] ?? "0"));
  const lines = await readLogLines();
  res.json({ lines: lines.slice(since), total: lines.length });
});

// ─── Download ─────────────────────────────────────────────────────────────────
router.get("/scraper/download", async (_req, res) => {
  if (!(await outputFileExists())) { res.status(404).json({ error: "الملف غير موجود" }); return; }
  res.download(OUTPUT_FILE, path.basename(OUTPUT_FILE));
});

export default router;
