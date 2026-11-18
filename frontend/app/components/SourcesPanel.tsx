import { useEffect, useRef } from "react";
import { KIND_LABEL, hostFromUrl, sourceKind } from "../lib/format";
import type { EvidenceSource } from "../lib/types";
import { BookIcon, CodeIcon, ExternalIcon, GlobeIcon } from "./icons";

export type ActiveCitation = { source: number; passage?: string } | null;

type Props = {
  sources: EvidenceSource[];
  active: ActiveCitation;
  onSelect: (citation: ActiveCitation) => void;
};

const KIND_ICON = {
  academic: <BookIcon size={15} />,
  web: <GlobeIcon size={15} />,
  code: <CodeIcon size={15} />
};

export default function SourcesPanel({ sources, active, onSelect }: Props) {
  const refs = useRef<Record<number, HTMLElement | null>>({});

  useEffect(() => {
    if (active) refs.current[active.source]?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [active]);

  if (!sources.length) {
    return <p className="muted">No sources were kept for this report.</p>;
  }

  return (
    <div className="sources">
      {sources.map((source, index) => {
        const number = index + 1;
        const open = active?.source === number;
        const kind = sourceKind(source);
        const validation = source.metadata?.validation;
        const passages = source.metadata?.passages ?? [];

        return (
          <article
            key={`${source.url}-${number}`}
            ref={(node) => {
              refs.current[number] = node;
            }}
            className={`source ${open ? "open" : ""}`}
          >
            <button
              type="button"
              className="source-head"
              aria-expanded={open}
              onClick={() => onSelect(open ? null : { source: number })}
            >
              <span className="source-num">{number}</span>
              <span className="source-title">{source.title || hostFromUrl(source.url)}</span>
              <span className="source-sub">
                <span className="kind" title={KIND_LABEL[kind]}>
                  {KIND_ICON[kind]}
                </span>
                {hostFromUrl(source.url)}
                {validation?.relevance ? <em className="badge">{validation.relevance}</em> : null}
              </span>
            </button>

            {open ? (
              <div className="source-body">
                {validation?.rationale ? <p className="muted small">{validation.rationale}</p> : null}
                {passages.map((passage, passageIndex) => {
                  const id = passage.passage_id || `${number}.${passageIndex + 1}`;
                  return (
                    <blockquote key={id} className={active?.passage === id ? "passage hit" : "passage"}>
                      <strong>[{id}]</strong> {passage.text}
                    </blockquote>
                  );
                })}
                {source.url ? (
                  <a className="open-link" href={source.url} target="_blank" rel="noopener noreferrer">
                    Open source <ExternalIcon size={14} />
                  </a>
                ) : null}
              </div>
            ) : null}
          </article>
        );
      })}
    </div>
  );
}
