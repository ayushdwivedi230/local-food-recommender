import express, { type Express, type Request, type Response } from "express";
import cors from "cors";
import path from "path";
import fs from "fs";
import pinoHttp from "pino-http";
import router from "./routes";
import { logger } from "./lib/logger";

const app: Express = express();

// Resolve frontend dist path relative to current working directory
// Works in both development and production (Render)
const frontendDistPath = path.resolve(
  process.cwd(),
  "artifacts/localfood-ai/dist/public"
);

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

// Serve API routes
app.use("/api", router);

// Serve static files from built React frontend
app.use(express.static(frontendDistPath));

// SPA fallback: serve index.html for all non-API routes
app.get("*", (_req: Request, res: Response): void => {
  const indexPath = path.join(frontendDistPath, "index.html");
  
  if (!fs.existsSync(indexPath)) {
    logger.error(
      { indexPath, frontendDistPath },
      "Frontend index.html not found"
    );
    res.status(404).json({
      error: "Frontend not found",
      path: indexPath,
      frontendDistPath,
    });
    return;
  }

  res.sendFile(indexPath);
});

export default app;
