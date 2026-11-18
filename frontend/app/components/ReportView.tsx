import { useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import { KIND_LABEL, prepareReport } from "../lib/format";
import type { ResearchPlan, ResearchResult } from "../lib/types";
import { CopyIcon, DownloadIcon, PenIcon, PlusIcon } from "./icons";
import SourcesPanel, { type ActiveCitation } from "./SourcesPanel";

type Props = {
  result: ResearchResult;
  plan: ResearchPlan;
  elapsed: number;
  onEditPlan: () => void;
  onNew: () => void;
};

export default function ReportView({ result, plan, elapsed, onEditPlan, onNew }: Props) {
  const [active, setActive] = useState<ActiveCitation>(null);
  const [copied, setCopied] = useState(false);
  const markdown = useMemo(() => prepareReport(result.report), [result.report]);
  const rounds = result.research_round ?? result.research_log?.length ?? 1;

  async function copy() {
    await navigator.clipboard.writeText(result.report);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  }

  function download() {
    const url = URL.createObjectURL(new Blob([result.report], { type: "text/markdown" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "deep-research-report.md";
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <section className="screen wide">
      <div className="run-head">
        <div>
          <p className="eyebrow">
            Report ready · {result.results.length} sources · {rounds} {rounds === 1 ? "round" : "rounds"}
            {elapsed ? ` · ${Math.max(1, Math.round(elapsed / 60))} min` : ""}
          </p>
          <h1 className="plan-title">{plan.title}</h1>
        </div>
        <div className="actions">
          <button type="button" className="btn secondary" onClick={copy}>
            <CopyIcon size={16} />
            {copied ? "Copied" : "Copy"}
          </button>
          <button type="button" className="btn secondary" onClick={download}>
            <DownloadIcon size={16} />
            Download
          </button>
          <button type="button" className="btn secondary" onClick={onEditPlan}>
            <PenIcon size={16} />
            Edit plan
          </button>
          <button type="button" className="btn primary" onClick={onNew}>
            <PlusIcon size={16} />
            New research
          </button>
        </div>
      </div>

      {result.search_errors.length ? (
        <details className="banner warn">
          <summary>{result.search_errors.length} search(es) failed — the report may be missing sources</summary>
          <ul>
            {result.search_errors.map((error, index) => (
              <li key={`${error.provider}-${index}`}>
                <strong>{error.provider}</strong>: {error.message}
              </li>
            ))}
          </ul>
        </details>
      ) : null}

      <div className="workspace">
        <article className="card document">
          <ReactMarkdown
            components={{
              a: ({ href, children }) => {
                if (href?.startsWith("#cite-")) {
                  const [source, passage] = href.slice("#cite-".length).split("-");
                  return (
                    <button
                      type="button"
                      className="cite"
                      onClick={() =>
                        setActive({ source: Number(source), passage: passage ? `${source}.${passage}` : undefined })
                      }
                    >
                      {children}
                    </button>
                  );
                }
                return (
                  <a href={href} target="_blank" rel="noopener noreferrer">
                    {children}
                  </a>
                );
              }
            }}
          >
            {markdown}
          </ReactMarkdown>
        </article>

        <aside className="side-col" aria-label="Sources">
          <div className="card">
            <div className="card-head">
              <h2>Sources</h2>
              <span className="muted small">Click a citation to see its passage</span>
            </div>
            <SourcesPanel sources={result.results} active={active} onSelect={setActive} />
          </div>

          <details className="card plan-details">
            <summary>Research plan used</summary>
            <ol className="plan-readonly">
              {plan.steps.map((step) => (
                <li key={step.id}>
                  <span>{step.text}</span>
                  <em>{KIND_LABEL[step.source]}</em>
                </li>
              ))}
            </ol>
          </details>
        </aside>
      </div>
    </section>
  );
}
