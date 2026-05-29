import { Router, type IRouter } from "express";
import { spawn, type ChildProcess } from "node:child_process";
import { readFile, access } from "node:fs/promises";
import path from "node:path";

const router: IRouter = Router();

let scraperProcess: ChildProcess | null = null;
let logLines: string[] = [];
let startedAt: Date | null = null;
let finishedAt: Date | null = null;
let exitCode: number | null = null;

const MAX_LOG_LINES = 500;
const SCRIPT_PATH = path.resolve("/home/runner/workspace/scripts/scraper/egypt_companies_scraper.py");
const OUTPUT_FILE = path.resolve("/home/runner/workspace/Egypt_Companies_Real_Data.xlsx");
const BACKUP_FILE = path.resolve("/home/runner/workspace/backup_temp.xlsx");

function appendLog(line: string) {
  logLines.push(line);
  if (logLines.length > MAX_LOG_LINES) {
    logLines = logLines.slice(-MAX_LOG_LINES);
  }
}

function parseStats() {
  const stats = {
    companiesFound: 0,
    idsProcessed: 0,
    speed: 0,
    phase: "idle" as "idle" | "yellowpages" | "facebook" | "done",
  };

  for (let i = logLines.length - 1; i >= 0; i--) {
    const line = logLines[i] ?? "";

    if (stats.companiesFound === 0) {
      const m = line.match(/(\d+)\s+شركة\s*\|\s*فحص\s*([\d,]+)\s*\|\s*([\d.]+)\s*req\/s/);
      if (m) {
        stats.companiesFound = parseInt(m[1] ?? "0");
        stats.idsProcessed = parseInt((m[2] ?? "0").replace(/,/g, ""));
        stats.speed = parseFloat(m[3] ?? "0");
      }
    }

    if (line.includes("YellowPages")) stats.phase = "yellowpages";
    if (line.includes("Facebook")) stats.phase = "facebook";
    if (line.includes("الملف النهائي")) stats.phase = "done";

    if (stats.companiesFound > 0 && stats.phase !== "idle") break;
  }

  return stats;
}

async function outputFileExists() {
  try {
    await access(OUTPUT_FILE);
    return true;
  } catch {
    return false;
  }
}

router.get("/scraper/status", async (_req, res) => {
  const running = scraperProcess !== null && scraperProcess.exitCode === null;
  const stats = parseStats();
  const hasOutput = await outputFileExists();

  res.json({
    running,
    startedAt: startedAt?.toISOString() ?? null,
    finishedAt: finishedAt?.toISOString() ?? null,
    exitCode,
    stats,
    hasOutput,
    logCount: logLines.length,
  });
});

router.get("/scraper/logs", (req, res) => {
  const since = parseInt(String(req.query["since"] ?? "0"));
  const lines = logLines.slice(since);
  res.json({ lines, total: logLines.length });
});

router.post("/scraper/start", (_req, res) => {
  if (scraperProcess && scraperProcess.exitCode === null) {
    res.status(409).json({ error: "السكريبت شغّال بالفعل" });
    return;
  }

  logLines = [];
  startedAt = new Date();
  finishedAt = null;
  exitCode = null;

  scraperProcess = spawn("python3", [SCRIPT_PATH], {
    cwd: "/home/runner/workspace",
    env: { ...process.env },
  });

  scraperProcess.stdout?.on("data", (chunk: Buffer) => {
    const text = chunk.toString();
    const lines = text.split("\n").filter((l) => l.trim());
    lines.forEach(appendLog);
  });

  scraperProcess.stderr?.on("data", (chunk: Buffer) => {
    const text = chunk.toString();
    const lines = text.split("\n").filter((l) => l.trim());
    lines.forEach((l) => appendLog(`[ERR] ${l}`));
  });

  scraperProcess.on("exit", (code) => {
    finishedAt = new Date();
    exitCode = code;
    scraperProcess = null;
    appendLog(`\n✅ انتهى السكريبت بكود: ${code}`);
  });

  res.json({ started: true, startedAt: startedAt.toISOString() });
});

router.post("/scraper/stop", (_req, res) => {
  if (!scraperProcess || scraperProcess.exitCode !== null) {
    res.status(409).json({ error: "السكريبت مش شغّال" });
    return;
  }

  scraperProcess.kill("SIGTERM");
  setTimeout(() => {
    if (scraperProcess) scraperProcess.kill("SIGKILL");
  }, 3000);

  appendLog("⛔ تم إيقاف السكريبت يدوياً");
  res.json({ stopped: true });
});

export default router;
