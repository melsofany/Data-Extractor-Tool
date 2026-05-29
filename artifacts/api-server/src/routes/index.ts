import { Router, type IRouter } from "express";
import healthRouter from "./health";
import scraperRouter from "./scraper";
import dashboardRouter from "./dashboard";

const router: IRouter = Router();

router.use(healthRouter);
router.use(scraperRouter);

export default router;

export { dashboardRouter };
