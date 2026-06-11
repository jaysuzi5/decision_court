import { useEffect, useRef, useState } from "react";
import type { CourtState } from "../lib/useCourtroom";
import type { Role } from "../lib/api";
import RichText from "./RichText";

const LABEL: Record<Role, string> = {
  prosecutor: "Prosecutor",
  defender: "Defender",
  judge: "Judge",
  user: "You, on the stand",
};

const SIDE: Record<Role, string> = {
  prosecutor: "left",
  defender: "right",
  judge: "center",
  user: "center",
};

export default function Courtroom({
  state,
  onReply,
}: {
  state: CourtState;
  onReply: (text: string) => void;
}) {
  const [text, setText] = useState("");
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [state.turns, state.awaitingReply, state.verdict]);

  function submit() {
    const t = text.trim();
    if (!t) return;
    setText("");
    onReply(t);
  }

  return (
    <div className="courtroom">
      <header className="bench">
        <span className="gavel-sm">⚖</span> Decision Court — in session
      </header>

      {state.wrappingUp && (
        <div className="banner wrap">The session is wrapping up — the Judge will rule shortly.</div>
      )}

      <div className="transcript">
        {state.turns.map((t, i) => (
          <div key={i} className={`turn ${SIDE[t.role]} role-${t.role}`}>
            <div className="speaker">{LABEL[t.role]}</div>
            <div className="bubble">
              <RichText text={t.content} />
              {t.streaming && <span className="caret" />}
            </div>
          </div>
        ))}

        {state.speaking && !state.awaitingReply && (
          <div className="now-speaking">{LABEL[state.speaking]} is speaking…</div>
        )}

        <div ref={endRef} />
      </div>

      {state.awaitingReply && !state.done && (
        <div className="witness-stand">
          <div className="stand-label">
            The witness stand · question {state.questionNumber} of up to {state.maxQuestions}
          </div>
          <textarea
            autoFocus
            rows={3}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submit();
            }}
            placeholder="Answer the Judge honestly… (⌘/Ctrl+Enter to submit)"
          />
          <button className="primary" onClick={submit} disabled={!text.trim()}>
            Answer the court
          </button>
        </div>
      )}

      {state.error && <div className="banner err">{state.error}</div>}
    </div>
  );
}
