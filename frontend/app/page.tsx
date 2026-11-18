"use client";

import { useEffect, useRef, useState } from "react";
import PlanReview from "./components/PlanReview";
import PromptScreen from "./components/PromptScreen";
import ReportView from "./components/ReportView";
import ResearchProgress from "./components/ResearchProgress";
import { SparkIcon } from "./components/icons";
import { describeStage } from "./lib/activity";
import { DEMO_MODE, requestPlan, streamResearch } from "./lib/api";
import type { ActivityItem, Phase, ResearchPlan, ResearchResult } from "./lib/types";

const isAbort = (error: unknown) => error instanceof DOMException && error.name === "AbortError";
const messageOf = (error: unknown) => (error instanceof Error ? error.message : "Something went wrong.");

export default function Home() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [query, setQuery] = useState("");
  const [useMemory, setUseMemory] = useState(false);
  const [plan, setPlan] = useState<ResearchPlan | null>(null);
  const [revising, setRevising] = useState(false);
  const [error, setError] = useState("");

  const [activity, setActivity] = useState<ActivityItem[]>([]);
  const [round, setRound] = useState(1);
  const [sourcesCount, setSourcesCount] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const [result, setResult] = useState<ResearchResult | null>(null);

  const abortRef = useRef<AbortController | null>(null);
  const nextId = useRef(0);

  useEffect(() => {
    if (phase !== "researching") return;
    const startedAt = Date.now();
    const timer = window.setInterval(() => setElapsed(Math.floor((Date.now() - startedAt) / 1000)), 1000);
    return () => window.clearInterval(timer);
  }, [phase]);

  function newController() {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    return controller;
  }

  async function createPlan() {
    const trimmed = query.trim();
    if (!trimmed) return;

    setError("");
    setPhase("planning");
    const controller = newController();

    try {
      setPlan(await requestPlan(trimmed, undefined, controller.signal));
      setPhase("review");
    } catch (err) {
      if (isAbort(err)) return;
      setError(messageOf(err));
      setPhase("idle");
    }
  }

  async function revisePlan(feedback: string) {
    if (!plan) return;

    // Send the plan as the user currently has it (edits included), without blank steps.
    const current: ResearchPlan = {
      ...plan,
      steps: plan.steps.map((step) => ({ ...step, text: step.text.trim() })).filter((step) => step.text)
    };
    if (!current.steps.length) {
      setError("Add at least one step before asking for changes.");
      return;
    }

    setError("");
    setRevising(true);
    const controller = newController();

    try {
      setPlan(await requestPlan(query.trim(), { feedback, previousPlan: current }, controller.signal));
    } catch (err) {
      if (!isAbort(err)) setError(messageOf(err));
    } finally {
      setRevising(false);
    }
  }

  async function approvePlan() {
    if (!plan) return;

    const approved: ResearchPlan = {
      ...plan,
      steps: plan.steps.map((step) => ({ ...step, text: step.text.trim() })).filter((step) => step.text)
    };

    setPlan(approved);
    setError("");
    setActivity([]);
    setRound(1);
    setSourcesCount(0);
    setElapsed(0);
    setResult(null);
    setPhase("researching");
    const controller = newController();

    try {
      const research = await streamResearch({
        query: query.trim(),
        plan: approved,
        useMemory,
        signal: controller.signal,
        onStage: (event) => {
          setRound((current) => Math.max(current, event.round || 1));
          if (event.sources_count !== undefined) setSourcesCount(event.sources_count);

          const item = describeStage(event);
          if (item) setActivity((items) => [...items, { ...item, id: nextId.current++ }]);
        }
      });

      if (research.status === "completed" && research.report) {
        setResult(research);
        setPhase("done");
      } else {
        setError(research.fatal_error || `The run ended without a report (status: ${research.status}).`);
        setPhase("review");
      }
    } catch (err) {
      if (!isAbort(err)) setError(messageOf(err));
      setPhase("review");
    }
  }

  function stopResearch() {
    abortRef.current?.abort();
  }

  function backToPlan() {
    setResult(null);
    setError("");
    setPhase("review");
  }

  function startOver() {
    abortRef.current?.abort();
    setPhase("idle");
    setPlan(null);
    setResult(null);
    setError("");
    setActivity([]);
    setQuery("");
  }

  return (
    <div className="app">
      <header className="topbar">
        <button type="button" className="brand" onClick={startOver} aria-label="Deep Research home">
          <span className="brand-mark">
            <SparkIcon size={16} />
          </span>
          Deep Research
        </button>
        {DEMO_MODE ? <span className="demo-pill">Demo mode · sample data</span> : null}
      </header>

      <main>
        {phase === "idle" ? (
          <PromptScreen
            query={query}
            onQueryChange={setQuery}
            useMemory={useMemory}
            onUseMemoryChange={setUseMemory}
            onSubmit={createPlan}
            error={error}
          />
        ) : null}

        {phase === "planning" ? (
          <section className="screen narrow center">
            <span className="spinner" aria-hidden="true" />
            <h1 className="plan-title">Drafting a research plan…</h1>
            <p className="muted">{query}</p>
            <button type="button" className="btn ghost" onClick={startOver}>
              Cancel
            </button>
          </section>
        ) : null}

        {phase === "review" && plan ? (
          <PlanReview
            query={query}
            plan={plan}
            onChange={setPlan}
            onApprove={approvePlan}
            onRevise={revisePlan}
            onCancel={startOver}
            revising={revising}
            error={error}
          />
        ) : null}

        {phase === "researching" && plan ? (
          <ResearchProgress
            plan={plan}
            activity={activity}
            round={round}
            sourcesCount={sourcesCount}
            elapsed={elapsed}
            onStop={stopResearch}
          />
        ) : null}

        {phase === "done" && plan && result ? (
          <ReportView result={result} plan={plan} elapsed={elapsed} onEditPlan={backToPlan} onNew={startOver} />
        ) : null}
      </main>
    </div>
  );
}
