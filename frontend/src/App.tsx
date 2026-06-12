import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import IntakeForm from "./components/Intake";
import Courtroom from "./components/Courtroom";
import VerdictPanel from "./components/Verdict";
import { useCourtroom } from "./lib/useCourtroom";
import { createSession, sendReply, deleteSession, CrisisError, type Intake } from "./lib/api";

export default function App() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const { state, connect, afterReply, reset } = useCourtroom();
  const [busy, setBusy] = useState(false);
  const [crisis, setCrisis] = useState<string | null>(null);

  useEffect(() => {
    if (sessionId) connect(sessionId);
  }, [sessionId, connect]);

  const start = useCallback(
    async (intake: Intake) => {
      setBusy(true);
      try {
        const r = await createSession(intake);
        if (r.crisis) {
          setCrisis(r.crisis_message);
          return;
        }
        navigate(`/c/${r.id}`);
      } catch (e: any) {
        alert(e.message ?? "Could not open the case.");
      } finally {
        setBusy(false);
      }
    },
    [navigate]
  );

  const reply = useCallback(
    async (text: string) => {
      if (!sessionId) return;
      try {
        await sendReply(sessionId, text);
        afterReply(sessionId);
      } catch (e) {
        if (e instanceof CrisisError) setCrisis(e.message);
        else alert("Your answer was not accepted.");
      }
    },
    [sessionId, afterReply]
  );

  function newCase() {
    reset();
    navigate("/");
  }

  async function deleteCase() {
    if (!sessionId) return;
    if (!window.confirm("Permanently delete this case and its transcript? This cannot be undone.")) return;
    try {
      await deleteSession(sessionId);
    } finally {
      newCase();
    }
  }

  if (crisis || state.crisis) {
    return (
      <div className="page">
        <div className="crisis-card">
          <h2>Let's pause the trial.</h2>
          <p style={{ whiteSpace: "pre-wrap" }}>
            {crisis ??
              "What you wrote matters more than any decision. Please reach out to someone who can support you right now — in the US, call or text 988, or text HOME to 741741. If you're in immediate danger, call 911."}
          </p>
          <button className="ghost" onClick={newCase}>
            Return
          </button>
        </div>
      </div>
    );
  }

  if (!sessionId) {
    return (
      <div className="page">
        <IntakeForm onSubmit={start} busy={busy} />
      </div>
    );
  }

  return (
    <div className="page wide">
      <Courtroom state={state} onReply={reply} onDelete={deleteCase} />
      {state.verdict && (
        <VerdictPanel
          verdict={state.verdict}
          sessionId={sessionId}
          onReset={newCase}
          onDelete={deleteCase}
        />
      )}
    </div>
  );
}
