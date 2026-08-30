import app from "./app";
import { logger } from "./lib/logger";
import path from "path";
import fs from "fs";

const rawPort = process.env["PORT"];

if (!rawPort) {
  throw new Error(
    "PORT environment variable is required but was not provided.",
  );
}

const port = Number(rawPort);

if (Number.isNaN(port) || port <= 0) {
  throw new Error(`Invalid PORT value: "${rawPort}"`);
}

// Log paths for debugging
const cwd = process.cwd();
const frontendDistPath = path.resolve(cwd, "artifacts/localfood-ai/dist/public");
const indexHtmlPath = path.join(frontendDistPath, "index.html");
const indexHtmlExists = fs.existsSync(indexHtmlPath);

logger.info(
  {
    cwd,
    frontendDistPath,
    indexHtmlExists,
    indexHtmlPath,
  },
  "Startup: Frontend path configuration"
);

app.listen(port, (err) => {
  if (err) {
    logger.error({ err }, "Error listening on port");
    process.exit(1);
  }

  logger.info({ port }, "Server listening");
});
