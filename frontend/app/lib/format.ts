import type { EvidenceSource, SourceKind } from "./types";

export const KIND_LABEL: Record<SourceKind, string> = {
  academic: "Academic papers",
  web: "Web",
  code: "Code repositories"
};

export function hostFromUrl(url: string) {
  try {
    return new URL(url).host.replace(/^www\./, "") || "unknown";
  } catch {
    return "unknown";
  }
}

export function sourceKind(source: EvidenceSource): SourceKind {
  const label = `${source.source} ${source.url}`.toLowerCase();
  if (label.includes("github")) return "code";
  if (label.includes("arxiv")) return "academic";
  return "web";
}

export function formatElapsed(totalSeconds: number) {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

/** Remove a wrapping ```markdown fence and any indentation shared by every line. */
function normalizeMarkdown(report: string) {
  let markdown = report.trim();

  const fenced = markdown.match(/^```(?:markdown|md)?\s*\n([\s\S]*?)\n```$/i);
  if (fenced?.[1]) markdown = fenced[1].trim();

  const lines = markdown.split("\n");
  const commonIndent = lines
    .filter((line) => line.trim())
    .reduce((min, line) => Math.min(min, line.match(/^ */)?.[0].length ?? 0), Number.POSITIVE_INFINITY);

  if (Number.isFinite(commonIndent) && commonIndent > 0) {
    markdown = lines.map((line) => line.slice(commonIndent)).join("\n");
  }
  return markdown;
}

/**
 * Prepare a report for display: the references list is shown in the sources panel
 * instead, and every [n] / [n.m] marker becomes a clickable citation link (#cite-n-m).
 */
export function prepareReport(report: string) {
  const body = normalizeMarkdown(report).split(/^# References\s*$/im)[0].trimEnd();

  return body.replace(/\[(\d+)(?:\.(\d+))?\](?!\()/g, (_match, source: string, passage?: string) => {
    const label = passage ? `${source}.${passage}` : source;
    const target = passage ? `${source}-${passage}` : source;
    return `[${label}](#cite-${target})`;
  });
}
