import { Toggle } from "@base-ui/react/toggle";
import { ToggleGroup } from "@base-ui/react/toggle-group";
import { useJobChange } from "../../api/mutations";
import type { JobDetail } from "../../api/types";
import { cx } from "../../lib/cx";
import { listedOnly, sourceLabel } from "../../domain/sources";
import styles from "./Job.module.css";

function MatchFeedback({ job }: { job: JobDetail }) {
  const change = useJobChange(job.id);
  return (
    <section className={styles.sideSection} aria-labelledby="match-title">
      <h2 id="match-title" className={styles.sideTitle}>
        Was it a good match?
      </h2>
      <ToggleGroup
        className={styles.toggles}
        value={job.feedback === 0 ? [] : [String(job.feedback)]}
        disabled={change.isPending}
        onValueChange={(value) => {
          const picked = value[0];
          if (picked) {
            change.mutate({ action: "thumbs", body: { value: Number(picked) } });
          }
        }}
      >
        <Toggle value="1" className={styles.toggle}>
          Good match
        </Toggle>
        <Toggle value="-1" className={styles.toggle}>
          Bad match
        </Toggle>
      </ToggleGroup>
      <p className={styles.sideNote}>Teaches the scorer.</p>
    </section>
  );
}

const RING = 2 * Math.PI * 26;
const MOST_POINTS = 4;
const BREAKS = /(;\s*|\.\s+|,?\s+but\s+)/i;
const LOW_SCORE = /^score \d+:\s*/i;
const SIGNED = /^([+\-−])\s*/;

type Sign = "plus" | "minus";
type Point = { sign: Sign | null; text: string };

const SIGN_LOOK: Record<Sign, string | undefined> = { plus: styles.plus, minus: styles.minus };

function keyPoints(reason: string): Point[] {
  const pieces = reason.replace(LOW_SCORE, "").split(BREAKS);
  const points: Point[] = [];
  for (let at = 0; at < pieces.length; at += 2) {
    const raw = (pieces[at] ?? "").trim().replace(/\.$/, "");
    if (!raw) continue;
    const mark = SIGNED.exec(raw)?.[1];
    const afterBut = /but/i.test(pieces[at - 1] ?? "");
    const sign: Sign | null = mark ? (mark === "+" ? "plus" : "minus") : afterBut ? "minus" : null;
    const text = raw.replace(SIGNED, "");
    points.push({ sign, text: text.charAt(0).toUpperCase() + text.slice(1) });
  }
  return points.slice(0, MOST_POINTS);
}

function strength(score: number): { label: string; tone: string | undefined } {
  if (score >= 80) return { label: "Strong match", tone: styles.ringStrong };
  if (score >= 70) return { label: "Good match", tone: styles.ringFair };
  return { label: "Weak match", tone: undefined };
}

function ScoreCard({ job }: { job: JobDetail }) {
  if (job.score === null && listedOnly(job)) {
    return (
      <section className={styles.sideSection} aria-labelledby="why-title">
        <h2 id="why-title" className={styles.sideTitle}>
          From {sourceLabel(job.source)}
        </h2>
        <p className={styles.sideText}>
          TruApply finds these jobs for you but doesn't score them or tailor your resume. Read the
          job, then apply on {sourceLabel(job.source)} with your own resume.
        </p>
      </section>
    );
  }
  if (job.score === null) {
    return (
      <section className={styles.sideSection} aria-labelledby="why-title">
        <h2 id="why-title" className={styles.sideTitle}>
          Match score
        </h2>
        <p className={styles.sideNote}>Not scored yet.</p>
      </section>
    );
  }
  const { label, tone } = strength(job.score);
  return (
    <section className={styles.sideSection} aria-labelledby="why-title">
      <h2 id="why-title" className={styles.sideTitle}>
        Match score
      </h2>
      <div className={cx(styles.scoreRow, tone)}>
        <span className={styles.ring} role="img" aria-label={`Score ${String(job.score)} of 100`}>
          <svg viewBox="0 0 60 60" aria-hidden="true">
            <circle cx="30" cy="30" r="26" className={styles.ringTrack} />
            <circle
              cx="30"
              cy="30"
              r="26"
              className={styles.ringFill}
              strokeDasharray={RING}
              strokeDashoffset={RING * (1 - job.score / 100)}
            />
          </svg>
          <b>{job.score}</b>
        </span>
        <span className={styles.strength}>{label}</span>
      </div>
      {job.reason && (
        <ul className={styles.points}>
          {keyPoints(job.reason).map(({ sign, text }) => (
            <li key={text}>
              <span className={cx(styles.sign, sign && SIGN_LOOK[sign])} aria-hidden="true">
                {sign === "minus" ? "−" : sign === "plus" ? "+" : "•"}
              </span>
              {text}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export function AboutMatch({ job }: { job: JobDetail }) {
  const lastStep = job.note && job.note !== job.reason ? job.note : "";
  return (
    <aside className={styles.side} aria-label="About this match">
      <ScoreCard job={job} />
      {job.actions.includes("thumbs") && <MatchFeedback job={job} />}
      {lastStep && (
        <section className={styles.sideSection} aria-labelledby="step-title">
          <h2 id="step-title" className={styles.sideTitle}>
            Last step
          </h2>
          <p className={styles.sideText}>{lastStep}</p>
        </section>
      )}
    </aside>
  );
}
