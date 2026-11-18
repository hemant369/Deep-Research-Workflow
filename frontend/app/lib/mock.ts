/**
 * Demo data so the interface can be tried without the backend.
 * Enabled with NEXT_PUBLIC_DEMO_MODE=true. Nothing here is real research.
 */
import type { EvidenceSource, ResearchPlan, ResearchResult, StageEvent } from "./types";

const wait = (ms: number, signal?: AbortSignal) =>
  new Promise<void>((resolve, reject) => {
    const timer = setTimeout(resolve, ms);
    signal?.addEventListener("abort", () => {
      clearTimeout(timer);
      reject(new DOMException("Aborted", "AbortError"));
    });
  });

export async function mockPlan(query: string, feedback?: string): Promise<ResearchPlan> {
  await wait(1400);
  const topic = query.trim().replace(/[?.!]+$/, "");
  const steps: ResearchPlan["steps"] = [
    { id: "s1", text: `Find peer-reviewed papers and surveys on: ${topic}`, source: "academic" },
    { id: "s2", text: `Collect recent articles, reports and expert analysis on: ${topic}`, source: "web" },
    { id: "s3", text: "Look for real-world implementations, benchmarks and open-source projects", source: "code" },
    { id: "s4", text: "Cross-check claims between sources and flag disagreements" , source: "web" },
    { id: "s5", text: "Identify what is still unanswered and run a follow-up search for it", source: "web" }
  ];
  if (feedback) {
    steps.splice(2, 0, {
      id: "s-feedback",
      text: `Added from your feedback: ${feedback.slice(0, 120)}`,
      source: "web"
    });
  }
  return { title: topic.length > 70 ? `${topic.slice(0, 67)}…` : topic, steps };
}

const SOURCES: EvidenceSource[] = [
  {
    source: "arxiv",
    title: "A Survey of Retrieval-Augmented Generation",
    content: "",
    url: "https://arxiv.org/abs/2312.10997",
    confidence: 0.9,
    citation: "[1]",
    metadata: {
      validation: { relevance: "Relevant", support: "Strong", rationale: "Directly surveys the topic." },
      passages: [
        { citation: "[1.1]", text: "Retrieval-augmented generation grounds a language model in external documents, reducing hallucination on knowledge-intensive tasks." },
        { citation: "[1.2]", text: "Evaluation commonly measures answer faithfulness, context relevance and answer relevance separately." }
      ]
    }
  },
  {
    source: "ddgs",
    title: "Building production retrieval systems — engineering notes",
    content: "",
    url: "https://example.com/engineering/retrieval-notes",
    confidence: 0.7,
    citation: "[2]",
    metadata: {
      validation: { relevance: "Partially Relevant", support: "Moderate", rationale: "Practical, but a single vendor's view." },
      passages: [
        { citation: "[2.1]", text: "Chunk size and re-ranking had a larger effect on answer quality than the choice of embedding model in our tests." }
      ]
    }
  },
  {
    source: "github",
    title: "example-org/rag-eval",
    content: "",
    url: "https://github.com/example-org/rag-eval",
    confidence: 0.7,
    citation: "[3]",
    metadata: {
      validation: { relevance: "Partially Relevant", support: "Moderate", rationale: "Open-source evaluation harness." },
      passages: [
        { citation: "[3.1]", text: "The toolkit scores faithfulness and context recall using an LLM judge and ships reproducible benchmarks." }
      ]
    }
  }
];

const REPORT = `> **Demo data.** This report is a placeholder shown in demo mode. No search was run.

# Executive Summary
Retrieval-augmented generation (RAG) grounds model answers in retrieved documents [1.1]. Evaluation is usually split into faithfulness, context relevance and answer relevance [1.2].

# Key Findings
## Quality drivers
- Chunking and re-ranking mattered more than the embedding model in one engineering team's tests [2.1].

## Tooling
- Open-source harnesses score faithfulness and context recall with an LLM judge [3.1].

# Conflicts & Caveats
- The engineering notes [2] come from a single organisation and may not generalise.

# Research Gaps
- No source compared evaluation methods on the same dataset.

# Conclusion
Grounding and layered evaluation are well supported [1], while practical tuning advice rests on thinner evidence [2][3].
`;

export async function mockStream(
  query: string,
  plan: ResearchPlan,
  onStage: (event: StageEvent) => void,
  signal: AbortSignal
): Promise<ResearchResult> {
  const queries = plan.steps.slice(0, 3).map((step) => step.text.slice(0, 60));
  const log: ResearchResult["research_log"] = [];
  const emit = async (stage: string, round: number, extra: Partial<StageEvent> = {}, ms = 900) => {
    await wait(ms, signal);
    onStage({ stage, round, sub_questions: queries, research_log: log, ...extra });
  };

  await emit("planner", 1);
  await emit("academic", 1);
  await emit("general", 1, {}, 1500);
  await emit("coding", 1);
  await emit("merge", 1);
  await emit("validator", 1, { sources_count: 3 }, 1400);
  await emit("citation", 1);
  await emit("synthesizer", 1, {}, 1300);

  log.push({ round: 1, queries, new_sources: 3, gaps: "No source compared evaluation methods on the same dataset." });
  await emit("reflect", 2, { continue_research: true });

  await emit("academic", 2);
  await emit("general", 2, {}, 1200);
  await emit("merge", 2);
  await emit("validator", 2, { sources_count: 3 });
  await emit("synthesizer", 2);

  log.push({ round: 2, queries: ["evaluation methods comparison"], new_sources: 0, gaps: "" });
  await emit("reflect", 2, { continue_research: false });
  await emit("writer", 2, {}, 1600);

  return {
    report: REPORT,
    status: "completed",
    fatal_error: "",
    search_errors: [],
    results: SOURCES,
    synthesized_text: "",
    sub_questions: queries,
    research_round: 2,
    research_log: log
  };
}
