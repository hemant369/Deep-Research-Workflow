import { ArrowIcon, SparkIcon } from "./icons";

const EXAMPLES = [
  "Compare recent approaches to evaluating retrieval-augmented generation systems",
  "How do solid-state batteries differ from lithium-ion, and what blocks mass production?",
  "What are the main open problems in long-term memory for LLM agents?"
];

type Props = {
  query: string;
  onQueryChange: (value: string) => void;
  useMemory: boolean;
  onUseMemoryChange: (value: boolean) => void;
  onSubmit: () => void;
  error: string;
};

export default function PromptScreen({
  query,
  onQueryChange,
  useMemory,
  onUseMemoryChange,
  onSubmit,
  error
}: Props) {
  const canSubmit = query.trim().length > 0;

  return (
    <section className="screen narrow">
      <div className="hero">
        <span className="hero-mark">
          <SparkIcon size={22} />
        </span>
        <h1>What do you want to research?</h1>
      </div>

      <div className="composer">
        <label htmlFor="query" className="sr-only">
          Research question
        </label>
        <textarea
          id="query"
          value={query}
          rows={4}
          maxLength={2000}
          placeholder="Ask a detailed question. The more specific it is, the better the plan."
          onChange={(event) => onQueryChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && (event.ctrlKey || event.metaKey) && canSubmit) onSubmit();
          }}
        />
        <div className="composer-bar">
          <label className="check">
            <input
              type="checkbox"
              checked={useMemory}
              onChange={(event) => onUseMemoryChange(event.target.checked)}
            />
            <span>Reuse a similar past report if one exists</span>
          </label>
          <button className="btn primary" type="button" disabled={!canSubmit} onClick={onSubmit}>
            Create plan
            <ArrowIcon size={16} />
          </button>
        </div>
      </div>

      {error ? (
        <div className="banner danger" role="alert">
          {error}
        </div>
      ) : null}

      <div className="examples">
        <p className="eyebrow">Try an example</p>
        {EXAMPLES.map((example) => (
          <button key={example} className="example" type="button" onClick={() => onQueryChange(example)}>
            {example}
          </button>
        ))}
      </div>
    </section>
  );
}
