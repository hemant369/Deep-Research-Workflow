"use client";

import { useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";

type ResearchResult = {
  report: string;
  results: EvidenceSource[];
  synthesized_text: string;
  sub_questions: string[];
  academic_questions: string[];
  general_questions: string[];
  coding_questions: string[];
};

type EvidenceSource = {
  source: string;
  title: string;
  content: string;
  url: string;
  metadata?: {
    validation?: {
      relevance?: string;
      support?: string;
      rationale?: string;
      key_claims?: string[];
    };
    passages?: Array<{
      passage_id?: string;
      citation?: string;
      text?: string;
    }>;
  };
  confidence?: number;
  citation?: string;
  reference?: string;
};

type StreamEvent =
  | { type: "start"; state: Record<string, unknown> }
  | { type: "stage"; stage: string; state: Record<string, unknown> }
  | { type: "complete"; response: ResearchResult };

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const STAGES = [
  ["planner", "Planning", "Created search strategy"],
  ["academic", "Academic Search", "Retrieving papers and citations"],
  ["general", "Web Search", "Finding trusted articles"],
  ["coding", "GitHub Search", "Scanning repositories"],
  ["merge", "Merge Results", "Removing duplicates"],
  ["validator", "Validation", "Checking evidence quality"],
  ["citation", "Citation Mapping", "Linking claims to sources"],
  ["writer", "Writing Report", "Drafting the final answer"],
  ["memory_save", "Complete", "Saving the research run"]
] as const;

type SourceTab = "all" | "academic" | "web" | "github" | "pdf" | "books";

function stageLabel(stage: string) {
  if (stage === "memory_load") return "Planning";
  if (stage === "synthesizer") return "Writing Report";
  return STAGES.find(([key]) => key === stage)?.[1] ?? stage;
}

function normalizedStage(stage: string) {
  if (stage === "memory_load" || stage === "router") return "planner";
  if (stage === "synthesizer") return "writer";
  return stage;
}

function hostFromUrl(url: string) {
  try {
    return new URL(url).host || "unknown";
  } catch {
    return "unknown";
  }
}

async function readNdjson(response: Response, onEvent: (event: StreamEvent) => void) {
  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error("Streaming response was empty.");
  }

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (line.trim()) {
        onEvent(JSON.parse(line) as StreamEvent);
      }
    }
  }

  if (buffer.trim()) {
    onEvent(JSON.parse(buffer) as StreamEvent);
  }
}

export default function Home() {
  const [query, setQuery] = useState("");
  const [useMemory, setUseMemory] = useState(false);
  const [activeSourceTab, setActiveSourceTab] = useState<SourceTab>("all");
  const [expandedStages, setExpandedStages] = useState<string[]>(["planner"]);
  const [completedStages, setCompletedStages] = useState<string[]>([]);
  const [currentStage, setCurrentStage] = useState("Ready");
  const [result, setResult] = useState<ResearchResult | null>(null);
  const [debugEvents, setDebugEvents] = useState<StreamEvent[]>([]);
  const [selectedSourceIndex, setSelectedSourceIndex] = useState(0);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState("");
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  const sources = result?.results ?? [];
  const selectedSource = sources[selectedSourceIndex] ?? sources[0];

  const progress = useMemo(() => {
    return Math.min((completedStages.length / STAGES.length) * 100, 100);
  }, [completedStages]);

  useEffect(() => {
    if (!isRunning || !startedAt) return;

    const timer = window.setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - startedAt) / 1000));
    }, 1000);

    return () => window.clearInterval(timer);
  }, [isRunning, startedAt]);

  const stats = useMemo(() => {
    const passageCount = sources.reduce((total, source) => {
      return total + (source.metadata?.passages?.length ?? 0);
    }, 0);

    const averageConfidence = sources.length
      ? sources.reduce((total, source) => total + (source.confidence ?? 0), 0) / sources.length
      : 0;

    return {
      sources: sources.length,
      academic: sources.filter((source) => sourceKind(source) === "academic").length,
      repositories: sources.filter((source) => sourceKind(source) === "github").length,
      web: sources.filter((source) => sourceKind(source) === "web").length,
      selectedEvidence: passageCount,
      tokens: debugEvents.length ? `${debugEvents.length * 720}` : "0",
      cost: debugEvents.length ? `$${(debugEvents.length * 0.002).toFixed(2)}` : "$0.00",
      memory: useMemory ? "Enabled" : "Off",
      averageConfidence
    };
  }, [debugEvents.length, sources, useMemory]);

  const filteredSources = useMemo(() => {
    if (activeSourceTab === "all") return sources;
    return sources.filter((source) => sourceKind(source) === activeSourceTab);
  }, [activeSourceTab, sources]);

  const estimateRemaining = useMemo(() => {
    if (!isRunning) return result ? "Complete" : "Ready";
    const remainingStages = Math.max(STAGES.length - completedStages.length, 1);
    return `~${Math.max(remainingStages * 12, 15)}s`;
  }, [completedStages.length, isRunning, result]);

  async function runResearch() {
    if (!query.trim() || isRunning) return;

    setIsRunning(true);
    setError("");
    setResult(null);
    setDebugEvents([]);
    setCompletedStages([]);
    setSelectedSourceIndex(0);
    setStartedAt(Date.now());
    setElapsedSeconds(0);
    setCurrentStage("Starting");

    try {
      const response = await fetch(`${API_BASE}/api/research/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          query,
          use_memory: useMemory
        })
      });

      if (!response.ok) {
        throw new Error(`Research request failed: ${response.status}`);
      }

      await readNdjson(response, (event) => {
        setDebugEvents((events) => [...events, event]);

        if (event.type === "stage") {
          const stageKey = normalizedStage(event.stage);
          setCurrentStage(stageLabel(stageKey));
          setCompletedStages((stages) => {
            return stages.includes(stageKey) ? stages : [...stages, stageKey];
          });
        }

        if (event.type === "complete") {
          setResult(event.response);
          setCurrentStage("Completed");
          setCompletedStages(STAGES.map(([key]) => key));
        }
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
      setCurrentStage("Error");
    } finally {
      setIsRunning(false);
    }
  }

  function toggleStage(stage: string) {
    setExpandedStages((stages) => {
      return stages.includes(stage) ? stages.filter((item) => item !== stage) : [...stages, stage];
    });
  }

  function downloadReport() {
    if (!result?.report) return;
    const blob = new Blob([result.report], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "deep-research-report.md";
    anchor.click();
    URL.revokeObjectURL(url);
  }

  async function copyReport() {
    if (!result?.report) return;
    await navigator.clipboard.writeText(result.report);
  }

  const runLabel = isRunning ? runningLabel(currentStage) : result ? "Completed" : "Run research";
  const queryTitle = query.trim() || "Compare recent retrieval augmented generation evaluation methods";

  return (
    <main className={`app-shell ${isRunning ? "is-running" : ""}`}>
      <TopNav />

      <div className="workspace-grid">
        <aside className="progress-sidebar" aria-label="Research progress">
          <section className="timeline-panel">
            <div className="panel-heading">
              <p className="eyebrow">Research Progress</p>
              <h2>Agent Timeline</h2>
            </div>

            <div className="timeline" style={{ "--timeline-progress": `${progress}%` } as React.CSSProperties}>
              {STAGES.map(([key, label, description], index) => {
                const done = completedStages.includes(key);
                const active = currentStage === label || (currentStage === "Starting" && index === 0);
                const expanded = expandedStages.includes(key);
                const eventCount = debugEvents.filter((event) => {
                  return event.type === "stage" && normalizedStage(event.stage) === key;
                }).length;

                return (
                  <button
                    className={`timeline-item ${done ? "done" : ""} ${active ? "active" : ""}`}
                    key={key}
                    onClick={() => toggleStage(key)}
                    type="button"
                  >
                    <span className="stage-node">{done ? "OK" : active ? "..." : ""}</span>
                    <span className="stage-index">{index + 1}</span>
                    <span className="stage-body">
                      <span className="stage-title-row">
                        <strong>{label}</strong>
                        <span>{active ? "Live" : done ? timestampFor(index) : "Pending"}</span>
                      </span>
                      <span className="stage-description">{active ? liveStageDescription(key) : description}</span>
                      {expanded ? (
                        <span className="stage-log">
                          {eventCount ? `${eventCount} event${eventCount === 1 ? "" : "s"} captured` : logPreview(key)}
                        </span>
                      ) : null}
                    </span>
                  </button>
                );
              })}
            </div>
          </section>

          <section className="progress-card">
            <ProgressRing progress={progress} />
            <div className="progress-copy">
              <strong>{Math.round(progress)}% researched</strong>
              <span>{isRunning ? currentStage : result ? "Final report ready" : "Waiting for a query"}</span>
            </div>
            <div className="stat-grid">
              <StatRow label="Elapsed Time" value={`${elapsedSeconds}s`} />
              <StatRow label="Remaining" value={estimateRemaining} />
              <StatRow label="Sources Found" value={String(stats.sources)} />
              <StatRow label="Academic Papers" value={String(stats.academic)} />
              <StatRow label="Repositories" value={String(stats.repositories)} />
              <StatRow label="Web Pages" value={String(stats.web)} />
              <StatRow label="Evidence Selected" value={String(stats.selectedEvidence)} />
              <StatRow label="Tokens Used" value={stats.tokens} />
              <StatRow label="Estimated Cost" value={stats.cost} />
              <StatRow label="Current Model" value="API default" />
              <StatRow label="Memory Usage" value={stats.memory} />
            </div>
          </section>
        </aside>

        <section className="research-workspace" aria-label="Research workspace">
          <section className="query-panel">
            <div className="query-heading">
              <div>
                <p className="eyebrow">New Research</p>
              </div>
              <span className="api-pill">{API_BASE}</span>
            </div>

            <div className="research-composer">
              <textarea
                className="query-input"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Ask a focused research question..."
                rows={3}
              />
              <div className="query-actions">
                <label className="memory-toggle">
                  <input
                    type="checkbox"
                    checked={useMemory}
                    onChange={(event) => setUseMemory(event.target.checked)}
                  />
                  <span>Memory</span>
                </label>
                <button className="run-button" disabled={isRunning || !query.trim()} onClick={runResearch} type="button">
                  <span className="play-mark">{isRunning ? "" : "Play"}</span>
                  <span>{runLabel}</span>
                </button>
              </div>
            </div>

            {error ? <div className="error-banner">{error}</div> : null}
          </section>

          <section className="report-panel">
            <div className="report-toolbar">
              <div>
                <p className="eyebrow">Research Report</p>
                <h2>Live Report</h2>
              </div>
              <div className="toolbar-actions">
                <button disabled={!result?.report} onClick={copyReport} type="button">Copy</button>
                <button disabled={!result?.report} onClick={downloadReport} type="button">Markdown</button>
                <button disabled type="button">PDF</button>
                <button disabled type="button">DOCX</button>
                <button disabled type="button">Share</button>
                <button disabled type="button">History</button>
              </div>
            </div>

            <article className={`report ${isRunning ? "streaming" : ""}`}>
              {result?.report ? (
                <ReactMarkdown>{result.report}</ReactMarkdown>
              ) : isRunning ? (
                <StreamingSkeleton currentStage={currentStage} />
              ) : (
                <EmptyState title="Your research report will appear here" text="The agent is working on gathering and analyzing information." />
              )}
            </article>
          </section>
        </section>

        <aside className="evidence-sidebar" aria-label="Evidence explorer">
          <div className="panel-heading">
            <p className="eyebrow">Evidence Explorer</p>
            <h2>Sources</h2>
          </div>

          <section className="source-metrics">
            <Metric label="Total Sources" value={String(stats.sources)} />
            <Metric label="Evidence Selected" value={String(stats.selectedEvidence)} />
            <Metric label="Avg Confidence" value={stats.averageConfidence ? `${Math.round(stats.averageConfidence * 100)}%` : "n/a"} />
          </section>

          <nav className="source-tabs" aria-label="Evidence source filters">
            {(["all", "academic", "web", "github", "pdf", "books"] as const).map((tab) => (
              <button
                className={activeSourceTab === tab ? "active" : ""}
                key={tab}
                onClick={() => setActiveSourceTab(tab)}
                type="button"
              >
                {tab === "pdf" ? "PDF" : tab[0].toUpperCase() + tab.slice(1)}
              </button>
            ))}
          </nav>

          <div className="right-source-list">
            {filteredSources.length ? filteredSources.map((source, index) => (
              <EvidenceCard
                key={`${source.url}-right-${index}`}
                source={source}
                selected={selectedSource === source}
                onSelect={() => setSelectedSourceIndex(sources.indexOf(source))}
              />
            )) : <EmptyState title="No sources yet" text="Evidence cards will appear as the agent collects and validates sources." />}
          </div>

          <div className="inspector-heading">
            <p className="eyebrow">Citation Inspector</p>
            <h2>Selection Details</h2>
          </div>
          {selectedSource ? (
            <SourceInspector source={selectedSource} />
          ) : (
            <EmptyState title="No source selected" text="Select a source to inspect passages, metadata, and citation usage." />
          )}
        </aside>
      </div>
    </main>
  );
}

function TopNav() {
  return (
    <header className="top-nav">
      <div className="brand-lockup">
        <span className="brand-mark">DR</span>
        <strong>Deep Research Agent</strong>
      </div>
      <button className="workspace-selector" type="button">
        Research Workspace
        <span>v</span>
      </button>
      <div className="nav-actions">
        <span className="avatar" aria-label="User avatar">H</span>
      </div>
    </header>
  );
}

function runningLabel(currentStage: string) {
  const labels: Record<string, string> = {
    "Academic Search": "Searching Academic Papers...",
    "Web Search": "Searching Web...",
    "GitHub Search": "Searching GitHub...",
    "Writing Report": "Writing Report...",
    Completed: "Completed"
  };

  return labels[currentStage] ?? "Running Research...";
}

function liveStageDescription(stage: string) {
  const descriptions: Record<string, string> = {
    planner: "Planning the search paths",
    academic: "Searching arXiv and scholarly indexes",
    general: "Reviewing trusted web evidence",
    coding: "Ranking repositories and code references",
    merge: "Deduplicating and embedding documents",
    validator: "Scoring source support and relevance",
    citation: "Selecting top citation passages",
    writer: "Streaming the final report",
    memory_save: "Persisting the completed run"
  };

  return descriptions[stage] ?? "Working...";
}

function logPreview(stage: string) {
  const logs: Record<string, string> = {
    planner: "Creating search strategy...",
    academic: "Searching academic sources...",
    general: "Searching trusted web sources...",
    coding: "Ranking repositories...",
    merge: "Removing duplicates...",
    validator: "Validating evidence...",
    citation: "Mapping citations...",
    writer: "Preparing report stream...",
    memory_save: "Waiting for completion..."
  };

  return logs[stage] ?? "Waiting for agent logs";
}

function timestampFor(index: number) {
  return `${12 + Math.floor(index / 3)}:${String(15 + index).padStart(2, "0")}`;
}

function sourceKind(source: EvidenceSource): SourceTab {
  const label = `${source.source} ${source.url} ${source.title}`.toLowerCase();
  if (label.includes("github")) return "github";
  if (label.includes("pdf")) return "pdf";
  if (label.includes("book")) return "books";
  if (label.includes("academic") || label.includes("paper") || label.includes("arxiv") || label.includes("doi")) return "academic";
  return "web";
}

function ProgressRing({ progress }: { progress: number }) {
  const value = Math.round(progress);

  return (
    <div className="progress-ring" style={{ "--progress": `${value * 3.6}deg` } as React.CSSProperties}>
      <div>
        <strong>{value}%</strong>
        <span>Complete</span>
      </div>
    </div>
  );
}

function StatRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="stat-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function EmptyState({ title, text }: { title: string; text: string }) {
  return (
    <div className="empty-state">
      <div className="empty-illustration" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
      <h3>{title}</h3>
      <p>{text}</p>
    </div>
  );
}

function EvidenceCard({
  source,
  selected,
  onSelect
}: {
  source: EvidenceSource;
  selected: boolean;
  onSelect: () => void;
}) {
  const validation = source.metadata?.validation;
  const passages = source.metadata?.passages ?? [];
  const firstAuthor = source.metadata?.passages?.[0]?.citation?.split(",")[0] ?? hostFromUrl(source.url);
  const yearMatch = `${source.title} ${source.citation ?? ""}`.match(/\b(19|20)\d{2}\b/);
  const confidence = source.confidence ?? 0;

  return (
    <button className={`source-item ${selected ? "selected" : ""}`} onClick={onSelect} type="button">
      <div className="source-card-top">
        <span className="source-icon">{sourceIcon(source)}</span>
        <div>
          <p className="source-title">
            {source.citation ?? ""} {source.title}
            {source.url && (
              <a
                href={source.url}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                style={{ marginLeft: '8px', fontSize: '12px', color: 'var(--primary)' }}
              >
                🔗
              </a>
            )}
          </p>
          <div className="source-meta">{firstAuthor} <span>/</span> {yearMatch?.[0] ?? "n.d."} <span>/</span> {source.source}</div>
        </div>
        <span className={`confidence ${confidenceClass(confidence)}`}>{source.confidence ?? "n/a"}</span>
      </div>
      <p className="source-summary">{source.content || validation?.rationale || "Evidence source selected for citation support."}</p>
      <div className="badge-row">
        {validation?.relevance ? <span className="badge">{validation.relevance}</span> : null}
        {validation?.support ? <span className="badge">{validation.support}</span> : null}
        <span className="badge">{passages.length} passages</span>
        <span className="bookmark" aria-hidden="true">*</span>
      </div>
    </button>
  );
}

function sourceIcon(source: EvidenceSource) {
  const kind = sourceKind(source);
  if (kind === "github") return "Git";
  if (kind === "pdf") return "PDF";
  if (kind === "academic") return "Aca";
  if (kind === "books") return "Book";
  return "Web";
}

function confidenceClass(confidence: number) {
  if (confidence >= 0.75) return "high";
  if (confidence >= 0.45) return "medium";
  return "low";
}

function SourceInspector({ source }: { source: EvidenceSource }) {
  const validation = source.metadata?.validation;
  const passages = source.metadata?.passages ?? [];

  return (
    <div className="inspector-stack">
      <section className="inspector-card">
        <p className="eyebrow">Highlighted Passage</p>
        {passages[0]?.text ? (
          <blockquote className="passage">
            <strong>{passages[0].citation ?? passages[0].passage_id}</strong>
            <span>{passages[0].text}</span>
          </blockquote>
        ) : (
          <p className="empty-copy">No highlighted passage available yet.</p>
        )}
      </section>

      <section className="inspector-card">
        <p className="eyebrow">Reason Selected</p>
        <p className="source-meta">{validation?.rationale ?? "Selected because it supports one or more claims in the generated report."}</p>
      </section>

      <section className="inspector-card">
        <p className="eyebrow">Metadata</p>
        <dl className="definition-list">
          <div>
            <dt>Source</dt>
            <dd>{source.source}</dd>
          </div>
          <div>
            <dt>Confidence</dt>
            <dd>{source.confidence ?? "n/a"}</dd>
          </div>
          <div>
            <dt>Publication</dt>
            <dd>
              {source.url ? (
                <a href={source.url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--primary)', textDecoration: 'underline' }}>
                  {hostFromUrl(source.url)}
                </a>
              ) : (
                hostFromUrl(source.url)
              )}
            </dd>
          </div>
          <div>
            <dt>Citation Used In</dt>
            <dd>{source.citation ?? "Pending"}</dd>
          </div>
          <div>
            <dt>URL</dt>
            <dd>
              {source.url ? (
                <a href={source.url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--primary)', textDecoration: 'underline', wordBreak: 'break-all' }}>
                  View Source
                </a>
              ) : (
                "N/A"
              )}
            </dd>
          </div>
        </dl>
      </section>
    </div>
  );
}

function StreamingSkeleton({ currentStage }: { currentStage: string }) {
  return (
    <div className="stream-skeleton">
      <div className="stream-title">
        <span>Generating report</span>
        <i>{currentStage}</i>
      </div>
      <div className="skeleton-line wide" />
      <div className="skeleton-line" />
      <div className="skeleton-line mid" />
      <div className="skeleton-block" />
      <p className="typing-line">Writing findings<span className="typing-cursor" /></p>
    </div>
  );
}