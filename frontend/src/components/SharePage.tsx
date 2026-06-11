import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import RichText from "./RichText";
import type { VerdictOut, TurnOut } from "../lib/api";

interface Shared {
  scope: string;
  verdict: VerdictOut | null;
  turns: TurnOut[] | null;
  decision: string;
}

const LABEL: Record<string, string> = {
  prosecutor: "Prosecutor",
  defender: "Defender",
  judge: "Judge",
  user: "Petitioner",
};

export default function SharePage() {
  const { token } = useParams();
  const [data, setData] = useState<Shared | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    fetch(`/api/share/${token}`)
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then(setData)
      .catch(() => setErr("This shared verdict was not found."));
  }, [token]);

  if (err) return <div className="page"><div className="crisis-card"><p>{err}</p></div></div>;
  if (!data) return <div className="page"><p style={{ textAlign: "center" }}>Loading…</p></div>;

  const v = data.verdict;
  return (
    <div className="page wide">
      {data.turns && (
        <div className="courtroom">
          <header className="bench"><span className="gavel-sm">⚖</span> {data.decision || "Decision Court"}</header>
          <div className="transcript">
            {data.turns.map((t, i) => (
              <div key={i} className={`turn role-${t.role}`}>
                <div className="speaker">{LABEL[t.role] ?? t.role}</div>
                <div className="bubble"><RichText text={t.content} /></div>
              </div>
            ))}
          </div>
        </div>
      )}
      {v && (
        <div className="verdict">
          <div className="verdict-seal">⚖ THE VERDICT</div>
          <section className="recommendation"><h2>Recommendation</h2><RichText text={v.recommendation} /></section>
          {v.reasoning && <section><h3>Reasoning</h3><RichText text={v.reasoning} /></section>}
          <section className="dissent"><h3>Dissent — the road not taken</h3><RichText text={v.dissent} /></section>
          {v.next_actions.length > 0 && (
            <section>
              <h3>Next actions</h3>
              <ul className="actions">{v.next_actions.map((a, i) => <li key={i}>{a}</li>)}</ul>
            </section>
          )}
          {v.open_question && (
            <section className="open-question">
              <h3>The question only you can answer</h3>
              <blockquote>{v.open_question}</blockquote>
            </section>
          )}
        </div>
      )}
      <p className="disclaimer" style={{ textAlign: "center" }}>
        Shared from Decision Court · <a href="/">put your own decision on trial</a>
      </p>
    </div>
  );
}
