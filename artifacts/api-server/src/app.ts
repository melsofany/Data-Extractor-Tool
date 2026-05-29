import express, { type Express } from "express";
import cors from "cors";
import pinoHttp from "pino-http";
import router, { dashboardRouter } from "./routes";
import { logger } from "./lib/logger";
import { createReadStream } from "node:fs";
import { access } from "node:fs/promises";
import path from "node:path";

const app: Express = express();
app.set("etag", false);

app.use(
  pinoHttp({
    logger,
    serializers: {
      req(req) {
        return {
          id: req.id,
          method: req.method,
          url: req.url?.split("?")[0],
        };
      },
      res(res) {
        return {
          statusCode: res.statusCode,
        };
      },
    },
  }),
);
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

app.use("/api", (_req, res, next) => {
  res.setHeader("Cache-Control", "no-store, no-cache, must-revalidate, private");
  res.setHeader("Pragma", "no-cache");
  res.setHeader("Expires", "0");
  next();
});

app.use("/api", router);

app.get("/api/scraper/download", async (_req, res) => {
  const filePath = path.resolve("/home/runner/workspace/Egypt_Companies_Real_Data.xlsx");
  try {
    await access(filePath);
    res.setHeader("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
    res.setHeader("Content-Disposition", 'attachment; filename="Egypt_Companies_Real_Data.xlsx"');
    createReadStream(filePath).pipe(res);
  } catch {
    res.status(404).json({ error: "الملف غير موجود بعد" });
  }
});

app.use("/", dashboardRouter);

export default app;
