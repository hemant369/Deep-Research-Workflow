export type SourceKind = "academic" | "web" | "code";

export type PlanStep = {
  id: string;
  text: string;
  source: SourceKind;
};

export type ResearchPlan = {
  title: string;
  steps: PlanStep[];
};

export type Passage = {
  passage_id?: string;
  citation?: string;
  text?: string;
};

export type EvidenceSource = {
  source: string;
  title: string;
  content: string;
  url: string;
  metadata?: {
    [key: string]: unknown;
    validation?: {
      relevance?: string;
      support?: string;
      rationale?: string;
      key_claims?: string[];
    };
    passages?: Passage[];
  };
  confidence?: number;
  citation?: string;
  reference?: string;
};

export type SearchError = {
  provider: string;
  query: string;
  message: string;
};

export type ResearchRound = {
  round: number;
  queries: string[];
  new_sources: number;
  gaps: string;
};

export type ResearchResult = {
  report: string;
  status: string;
  fatal_error: string;
  search_errors: SearchError[];
  results: EvidenceSource[];
  synthesized_text: string;
  sub_questions: string[];
  research_round?: number;
  research_log?: ResearchRound[];
};

export type ActivityKind = "plan" | "search" | "validate" | "think" | "write";

export type ActivityItem = {
  id: number;
  kind: ActivityKind;
  text: string;
  detail?: string;
  round: number;
};

/** One finished LangGraph node, as streamed by the backend. */
export type StageEvent = {
  stage: string;
  round: number;
  continue_research?: boolean;
  sub_questions?: string[];
  sources_count?: number;
  research_log?: ResearchRound[];
};

export type Phase = "idle" | "planning" | "review" | "researching" | "done" | "error";
