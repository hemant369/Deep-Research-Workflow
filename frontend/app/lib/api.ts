import { mockPlan, mockStream } from "./mock";
import type { ResearchPlan, ResearchResult, StageEvent } from "./types";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
export const DEMO_MODE = process.env.NEXT_PUBLIC_DEMO_MODE === "true";

async function failure(response: Response) {
  let detail = "";
  try {
    const body = await response.json();
    if (typeof body?.detail === "string") {
      detail = body.detail;
    } else if (Array.isArray(body?.detail)) {
      detail = body.detail
        .map((item: { msg?: unknown }) => (typeof item?.msg === "string" ? item.msg : ""))
        .filter(Boolean)
        .join("; ");
    }
  } catch {
    // The body was not JSON; the status code is all we have.
  }
  return new Error(detail || `Request failed (${response.status})`);
}

/**
 * Ask the agent for a research plan.
 * Backend contract: POST /api/research/plan { query, feedback?, previous_plan? } -> ResearchPlan
 */
export async function requestPlan(
  query: string,
  revision?: { feedback: string; previousPlan: ResearchPlan },
  signal?: AbortSignal
): Promise<ResearchPlan> {
  if (DEMO_MODE) return mockPlan(query, revision?.feedback);

  const response = await fetch(`${API_BASE}/api/research/plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      feedback: revision?.feedback,
      previous_plan: revision?.previousPlan
    }),
    signal
  });
  if (!response.ok) throw await failure(response);
  return (await response.json()) as ResearchPlan;
}

type StreamOptions = {
  query: string;
  plan: ResearchPlan;
  useMemory: boolean;
  signal: AbortSignal;
  onStage: (event: StageEvent) => void;
};

/**
 * Run the approved plan and stream progress.
 * Backend contract: POST /api/research/stream { query, plan, use_memory } -> SSE
 * with `stage` events, then one `complete` (ResearchResult) or `error` event.
 */
export async function streamResearch({
  query,
  plan,
  useMemory,
  signal,
  onStage
}: StreamOptions): Promise<ResearchResult> {
  if (DEMO_MODE) return mockStream(query, plan, onStage, signal);

  const response = await fetch(`${API_BASE}/api/research/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, plan, use_memory: useMemory }),
    signal
  });
  if (!response.ok || !response.body) throw await failure(response);

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let result: ResearchResult | null = null;

  const handle = (block: string) => {
    const event = block.match(/^event:\s*(\S+)/m)?.[1];
    const data = block.match(/^data:\s*(.+)$/m)?.[1];
    if (!event || !data) return;

    const payload = JSON.parse(data);
    if (event === "stage") onStage(payload as StageEvent);
    else if (event === "complete") result = payload as ResearchResult;
    else if (event === "error") throw new Error(String(payload.message ?? "The research run failed."));
  };

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");

    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() ?? "";
    blocks.forEach(handle);
  }
  if (buffer.trim()) handle(buffer);

  if (!result) throw new Error("The connection closed before the research finished.");
  return result;
}
