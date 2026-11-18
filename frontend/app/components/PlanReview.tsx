import { useState } from "react";
import { KIND_LABEL } from "../lib/format";
import type { PlanStep, ResearchPlan, SourceKind } from "../lib/types";
import { ArrowIcon, PlusIcon, RefreshIcon, TrashIcon } from "./icons";

type Props = {
  query: string;
  plan: ResearchPlan;
  onChange: (plan: ResearchPlan) => void;
  onApprove: () => void;
  onRevise: (feedback: string) => void;
  onCancel: () => void;
  revising: boolean;
  error: string;
};

const KINDS: SourceKind[] = ["academic", "web", "code"];

export default function PlanReview({
  query,
  plan,
  onChange,
  onApprove,
  onRevise,
  onCancel,
  revising,
  error
}: Props) {
  const [feedback, setFeedback] = useState("");
  const hasSteps = plan.steps.some((step) => step.text.trim());

  const updateStep = (id: string, patch: Partial<PlanStep>) =>
    onChange({ ...plan, steps: plan.steps.map((step) => (step.id === id ? { ...step, ...patch } : step)) });

  const removeStep = (id: string) => onChange({ ...plan, steps: plan.steps.filter((step) => step.id !== id) });

  const addStep = () =>
    onChange({
      ...plan,
      steps: [...plan.steps, { id: `step-${Date.now()}`, text: "", source: "web" }]
    });

  return (
    <section className="screen narrow">
      <p className="eyebrow">Step 1 of 2 · Review the plan</p>
      <h1 className="plan-title">{plan.title}</h1>
      <p className="muted question">&ldquo;{query}&rdquo;</p>

      <div className="card">
        <div className="card-head">
          <h2>Research plan</h2>
          <span className="muted small">Edit, remove or add steps before approving</span>
        </div>

        <ol className="steps">
          {plan.steps.map((step, index) => (
            <li key={step.id} className="step">
              <span className="step-num">{index + 1}</span>
              <div className="step-body">
                <textarea
                  aria-label={`Step ${index + 1}`}
                  value={step.text}
                  rows={2}
                  placeholder="Describe what to look for"
                  onChange={(event) => updateStep(step.id, { text: event.target.value })}
                />
                <div className="step-meta">
                  <label className="select">
                    <span className="sr-only">Source for step {index + 1}</span>
                    <select
                      value={step.source}
                      onChange={(event) => updateStep(step.id, { source: event.target.value as SourceKind })}
                    >
                      {KINDS.map((kind) => (
                        <option key={kind} value={kind}>
                          {KIND_LABEL[kind]}
                        </option>
                      ))}
                    </select>
                  </label>
                  <button
                    type="button"
                    className="icon-btn"
                    aria-label={`Remove step ${index + 1}`}
                    onClick={() => removeStep(step.id)}
                  >
                    <TrashIcon size={16} />
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ol>

        <button type="button" className="btn ghost" onClick={addStep}>
          <PlusIcon size={16} />
          Add step
        </button>
      </div>

      <div className="card">
        <div className="card-head">
          <h2>Want a different plan?</h2>
        </div>
        <label htmlFor="feedback" className="sr-only">
          Feedback on the plan
        </label>
        <textarea
          id="feedback"
          className="plain"
          rows={2}
          value={feedback}
          disabled={revising}
          placeholder="e.g. Focus on 2023 onwards, and include open-source implementations"
          onChange={(event) => setFeedback(event.target.value)}
        />
        <button
          type="button"
          className="btn secondary"
          disabled={revising || !feedback.trim()}
          onClick={() => {
            onRevise(feedback.trim());
            setFeedback("");
          }}
        >
          <RefreshIcon size={16} />
          {revising ? "Updating plan…" : "Update plan"}
        </button>
      </div>

      {error ? (
        <div className="banner danger" role="alert">
          {error}
        </div>
      ) : null}

      <div className="approve-bar">
        <button type="button" className="btn ghost" onClick={onCancel}>
          Cancel
        </button>
        <button type="button" className="btn primary large" disabled={!hasSteps || revising} onClick={onApprove}>
          Start research
          <ArrowIcon size={18} />
        </button>
      </div>
    </section>
  );
}
