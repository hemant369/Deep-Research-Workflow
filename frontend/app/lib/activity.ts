import type { ActivityItem, StageEvent } from "./types";

type Described = Omit<ActivityItem, "id">;

/**
 * Turn a finished graph node into a line for the activity feed.
 * Returns null for internal nodes that are not worth showing.
 */
export function describeStage(event: StageEvent): Described | null {
  const round = event.round || 1;
  const make = (kind: Described["kind"], text: string, detail?: string): Described => ({
    kind,
    text,
    detail,
    round
  });

  switch (event.stage) {
    case "planner":
      return make("plan", "Prepared search queries", event.sub_questions?.join("  ·  "));
    case "academic":
      return make("search", "Searched academic papers (arXiv)");
    case "general":
      return make("search", "Searched the web and read the top pages");
    case "coding":
      return make("search", "Searched GitHub repositories and READMEs");
    case "merge":
      return make("validate", "Merged results and removed duplicates");
    case "validator":
      return make("validate", `Checked source relevance · ${event.sources_count ?? 0} kept so far`);
    case "citation":
      return make("validate", "Mapped citations to passages");
    case "synthesizer":
      return make("think", "Summarised facts, conflicts and gaps");
    case "reflect": {
      if (!event.continue_research) {
        return make("think", "Research is complete — writing the report");
      }
      const log = event.research_log ?? [];
      const gaps = log[log.length - 1]?.gaps?.replace(/\s+/g, " ").trim();
      // The backend has already advanced to the next round when it reports "continue".
      return { ...make("think", "Found gaps — starting a follow-up round", gaps?.slice(0, 220)), round: Math.max(round - 1, 1) };
    }
    case "writer":
      return make("write", "Wrote the report");
    default:
      return null;
  }
}
