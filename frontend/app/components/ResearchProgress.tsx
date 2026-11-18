import { useEffect, useRef } from "react";
import { formatElapsed } from "../lib/format";
import type { ActivityItem, ActivityKind, ResearchPlan } from "../lib/types";
import { KIND_LABEL } from "../lib/format";
import { ListIcon, PenIcon, SearchIcon, ShieldIcon, SparkIcon, StopIcon } from "./icons";

type Props = {
  plan: ResearchPlan;
  activity: ActivityItem[];
  round: number;
  sourcesCount: number;
  elapsed: number;
  onStop: () => void;
};

const ICONS: Record<ActivityKind, React.ReactNode> = {
  plan: <ListIcon size={16} />,
  search: <SearchIcon size={16} />,
  validate: <ShieldIcon size={16} />,
  think: <SparkIcon size={16} />,
  write: <PenIcon size={16} />
};

export default function ResearchProgress({ plan, activity, round, sourcesCount, elapsed, onStop }: Props) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [activity.length]);

  const rounds = Array.from(new Set(activity.map((item) => item.round)));
  const finishedWriting = activity.some((item) => item.kind === "write");

  return (
    <section className="screen wide">
      <div className="workspace">
        <div className="main-col">
          <div className="run-head">
            <div>
              <p className="eyebrow">Step 2 of 2 · Researching</p>
              <h1 className="plan-title">{plan.title}</h1>
            </div>
            <button type="button" className="btn secondary" onClick={onStop}>
              <StopIcon size={16} />
              Stop
            </button>
          </div>

          <div className="card">
            <div className="card-head">
              <h2>Live activity</h2>
              <span className="muted small">Each line is a step the agent has finished</span>
            </div>

            <div className="feed" aria-live="polite">
              {activity.length === 0 ? (
                <p className="muted pending">
                  <span className="dot pulse" /> Starting up…
                </p>
              ) : null}

              {rounds.map((roundNumber) => (
                <div key={roundNumber} className="round">
                  <p className="round-label">Round {roundNumber}</p>
                  {activity
                    .filter((item) => item.round === roundNumber)
                    .map((item) => (
                      <div key={item.id} className={`event ${item.kind}`}>
                        <span className="event-icon">{ICONS[item.kind]}</span>
                        <div>
                          <p className="event-text">{item.text}</p>
                          {item.detail ? <p className="event-detail">{item.detail}</p> : null}
                        </div>
                      </div>
                    ))}
                </div>
              ))}

              {activity.length > 0 && !finishedWriting ? (
                <p className="muted pending">
                  <span className="dot pulse" /> Working on the next step…
                </p>
              ) : null}
              <div ref={endRef} />
            </div>
          </div>
        </div>

        <aside className="side-col" aria-label="Run details">
          <div className="card stats">
            <div>
              <strong>{formatElapsed(elapsed)}</strong>
              <span>Elapsed</span>
            </div>
            <div>
              <strong>{round}</strong>
              <span>Round</span>
            </div>
            <div>
              <strong>{sourcesCount}</strong>
              <span>Sources kept</span>
            </div>
          </div>

          <div className="card">
            <div className="card-head">
              <h2>Approved plan</h2>
            </div>
            <ol className="plan-readonly">
              {plan.steps.map((step) => (
                <li key={step.id}>
                  <span>{step.text}</span>
                  <em>{KIND_LABEL[step.source]}</em>
                </li>
              ))}
            </ol>
          </div>
        </aside>
      </div>
    </section>
  );
}
