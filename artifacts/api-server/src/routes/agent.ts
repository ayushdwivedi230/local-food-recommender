import { Router, type IRouter } from "express";
import { spawn } from "node:child_process";
import path from "node:path";
import {
  ClearAgentMemoryParams,
  GetAgentMemoryParams,
  RunAgentBody,
  RunAgentResponse,
} from "@workspace/api-zod";

const router: IRouter = Router();
const pythonScript = path.resolve(process.cwd(), "../../backend/main.py");

function invokePython(payload: Record<string, unknown>): Promise<unknown> {
  return new Promise((resolve, reject) => {
    const child = spawn(process.env.LOCALFOOD_PYTHON ?? "python3", [pythonScript], {
      cwd: path.dirname(pythonScript),
      stdio: ["pipe", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk: Buffer) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk: Buffer) => {
      stderr += chunk.toString();
    });
    child.on("error", reject);
    child.on("close", (code) => {
      if (code !== 0) {
        reject(new Error(stderr || `Python agent exited with code ${code}`));
        return;
      }
      try {
        resolve(JSON.parse(stdout));
      } catch {
        reject(new Error("Python agent returned invalid JSON."));
      }
    });
    child.stdin.end(JSON.stringify(payload));
  });
}

router.post("/agent/chat", async (req, res) => {
  const parsed = RunAgentBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: "Please provide a non-empty message and sessionId." });
    return;
  }
  try {
    const result = RunAgentResponse.parse(
      await invokePython({ action: "chat", ...parsed.data }),
    );
    req.log.info(
      { sessionId: parsed.data.sessionId, mode: result.mode },
      "LocalFood agent completed turn",
    );
    res.json(result);
  } catch (error) {
    req.log.error({ err: error }, "LocalFood agent failed");
    res.status(500).json({ error: "The agent could not complete this turn. Please try again." });
  }
});

router.get("/agent/memory/:sessionId", async (req, res) => {
  const parsed = GetAgentMemoryParams.safeParse(req.params);
  if (!parsed.success) {
    res.status(400).json({ error: "Invalid session." });
    return;
  }
  try {
    res.json(await invokePython({ action: "memory", sessionId: parsed.data.sessionId }));
  } catch (error) {
    req.log.error({ err: error }, "Could not read LocalFood memory");
    res.status(500).json({ error: "Memory is temporarily unavailable." });
  }
});

router.delete("/agent/memory/:sessionId", async (req, res) => {
  const parsed = ClearAgentMemoryParams.safeParse(req.params);
  if (!parsed.success) {
    res.status(400).json({ error: "Invalid session." });
    return;
  }
  try {
    res.json(await invokePython({ action: "clear", sessionId: parsed.data.sessionId }));
  } catch (error) {
    req.log.error({ err: error }, "Could not clear LocalFood memory");
    res.status(500).json({ error: "Memory could not be cleared." });
  }
});

export default router;