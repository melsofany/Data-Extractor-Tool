import { createServer } from "node:http";
import { WebSocketServer } from "ws";
import app from "./app";
import { logger } from "./lib/logger";
import { doStart, doStop } from "./routes/scraper";

const rawPort = process.env["PORT"];

if (!rawPort) {
  throw new Error("PORT environment variable is required but was not provided.");
}

const port = Number(rawPort);

if (Number.isNaN(port) || port <= 0) {
  throw new Error(`Invalid PORT value: "${rawPort}"`);
}

const server = createServer(app);

const wss = new WebSocketServer({ server });

wss.on("connection", (ws) => {
  ws.on("message", async (data) => {
    try {
      const msg = JSON.parse(data.toString()) as { cmd?: string };
      if (msg.cmd === "go") {
        const result = await doStart();
        ws.send(JSON.stringify(result));
      } else if (msg.cmd === "off") {
        const result = await doStop();
        ws.send(JSON.stringify(result));
      }
    } catch (e) {
      try { ws.send(JSON.stringify({ ok: false, error: String(e) })); } catch {}
    }
  });
});

server.listen(port, () => {
  logger.info({ port }, "Server listening");
});
