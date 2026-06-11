import { useState } from "react";
import type { Intake } from "../lib/api";

const empty: Intake = {
  one_sentence: "",
  leaning: "",
  afraid_of: "",
  values: "",
  constraints: "",
  everything: "",
};

export default function IntakeForm({
  onSubmit,
  busy,
}: {
  onSubmit: (i: Intake) => void;
  busy: boolean;
}) {
  const [form, setForm] = useState<Intake>(empty);
  const [paste, setPaste] = useState(false);

  const set = (k: keyof Intake) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const valid =
    form.everything.trim().length > 0 ||
    (form.one_sentence.trim().length > 0 && form.leaning.trim().length > 0);

  return (
    <div className="intake">
      <div className="gavel">⚖</div>
      <h1>Decision Court</h1>
      <p className="tagline">Put your decision on trial.</p>
      <p className="blurb">
        A Prosecutor, a Defender, and a Judge will argue your hard call — then
        cross-examine you and hand down a verdict you can keep.
      </p>

      <div className="mode-toggle">
        <button className={!paste ? "on" : ""} onClick={() => setPaste(false)} type="button">
          Guided
        </button>
        <button className={paste ? "on" : ""} onClick={() => setPaste(true)} type="button">
          Just paste everything
        </button>
      </div>

      {paste ? (
        <label className="field">
          <span>Tell the court everything — the decision, the context, the mess.</span>
          <textarea
            rows={10}
            value={form.everything}
            onChange={set("everything")}
            placeholder="I'm trying to decide whether to..."
          />
        </label>
      ) : (
        <>
          <label className="field">
            <span>The decision, in one sentence</span>
            <input value={form.one_sentence} onChange={set("one_sentence")} placeholder="Should I take the job in Denver?" />
          </label>
          <label className="field">
            <span>What you're leaning toward</span>
            <input value={form.leaning} onChange={set("leaning")} placeholder="Taking it" />
          </label>
          <label className="field">
            <span>What you're afraid of</span>
            <textarea rows={2} value={form.afraid_of} onChange={set("afraid_of")} placeholder="Uprooting my family for a job that might not last" />
          </label>
          <label className="field">
            <span>What matters most to you (your values)</span>
            <textarea rows={2} value={form.values} onChange={set("values")} placeholder="Time with my kids, doing work that means something" />
          </label>
          <label className="field">
            <span>Hard constraints (money, time, people affected)</span>
            <textarea rows={2} value={form.constraints} onChange={set("constraints")} placeholder="Partner has a job here; lease ends in March" />
          </label>
        </>
      )}

      <button className="primary big" disabled={!valid || busy} onClick={() => onSubmit(form)}>
        {busy ? "Opening the case…" : "Call the court to order"}
      </button>
      <p className="disclaimer">
        Decision Court is a thinking tool — not medical, legal, financial, or mental-health
        advice. Your intake stays private and is never shared by default.
      </p>
    </div>
  );
}
