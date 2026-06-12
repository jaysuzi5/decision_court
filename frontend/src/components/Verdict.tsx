import { useState } from "react";
import type { VerdictOut } from "../lib/api";
import { createShare } from "../lib/api";
import RichText from "./RichText";

export default function VerdictPanel({
  verdict,
  sessionId,
  onReset,
  onDelete,
}: {
  verdict: VerdictOut;
  sessionId?: string;
  onReset?: () => void;
  onDelete?: () => void;
}) {
  const [checked, setChecked] = useState<Record<number, boolean>>({});
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const [shareFull, setShareFull] = useState(false);
  const [copied, setCopied] = useState(false);

  async function share() {
    if (!sessionId) return;
    const { token } = await createShare(sessionId, shareFull ? "full" : "verdict_only");
    setShareUrl(`${window.location.origin}/share/${token}`);
  }

  function copy(text: string) {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  const asText =
    `VERDICT\n\n${verdict.recommendation}\n\nREASONING\n${verdict.reasoning}\n\n` +
    `DISSENT\n${verdict.dissent}\n\nNEXT ACTIONS\n` +
    verdict.next_actions.map((a) => `- ${a}`).join("\n") +
    `\n\nOPEN QUESTION\n${verdict.open_question}`;

  return (
    <div className="verdict">
      <div className="verdict-seal">⚖ THE VERDICT</div>

      <section className="recommendation">
        <h2>Recommendation</h2>
        <RichText text={verdict.recommendation} />
      </section>

      {verdict.reasoning && (
        <section>
          <h3>Reasoning</h3>
          <RichText text={verdict.reasoning} />
        </section>
      )}

      <section className="dissent">
        <h3>Dissent — the road not taken</h3>
        <RichText text={verdict.dissent} />
      </section>

      {verdict.next_actions.length > 0 && (
        <section>
          <h3>Next actions</h3>
          <ul className="actions">
            {verdict.next_actions.map((a, i) => (
              <li key={i}>
                <label>
                  <input
                    type="checkbox"
                    checked={!!checked[i]}
                    onChange={() => setChecked((c) => ({ ...c, [i]: !c[i] }))}
                  />
                  <span className={checked[i] ? "struck" : ""}>{a}</span>
                </label>
              </li>
            ))}
          </ul>
        </section>
      )}

      {verdict.open_question && (
        <section className="open-question">
          <h3>The question only you can answer</h3>
          <blockquote>{verdict.open_question}</blockquote>
        </section>
      )}

      <div className="verdict-actions">
        <button onClick={() => copy(asText)}>{copied ? "Copied ✓" : "Copy verdict"}</button>
        {sessionId && (
          <a className="btn" href={`/api/session/${sessionId}/markdown`} download={`verdict-${sessionId}.md`}>
            Download transcript (.md)
          </a>
        )}
        {sessionId && (
          <button onClick={share}>Share verdict</button>
        )}
        {onReset && (
          <button className="ghost" onClick={onReset}>
            New case
          </button>
        )}
        {onDelete && (
          <button className="ghost danger" onClick={onDelete}>
            Delete case
          </button>
        )}
      </div>

      {sessionId && (
        <label className="share-scope">
          <input type="checkbox" checked={shareFull} onChange={(e) => setShareFull(e.target.checked)} />
          Include the full trial in the shared link (off = verdict + dissent only, keeps your
          intake private)
        </label>
      )}

      {shareUrl && (
        <div className="share-url">
          <input readOnly value={shareUrl} onFocus={(e) => e.target.select()} />
          <button onClick={() => copy(shareUrl)}>Copy link</button>
        </div>
      )}
    </div>
  );
}
