import { useCallback, useRef, useState } from "react";
import { readSSE } from "./sse";
import type { Role, TurnOut, VerdictOut } from "./api";

export interface LiveTurn {
  role: Role;
  content: string;
  sequence: number;
  streaming: boolean;
}

export interface CourtState {
  turns: LiveTurn[];
  speaking: Role | null;
  awaitingReply: boolean;
  questionNumber: number;
  maxQuestions: number;
  verdict: VerdictOut | null;
  done: boolean;
  crisis: boolean;
  wrappingUp: boolean;
  error: string | null;
}

const initial: CourtState = {
  turns: [],
  speaking: null,
  awaitingReply: false,
  questionNumber: 0,
  maxQuestions: 5,
  verdict: null,
  done: false,
  crisis: false,
  wrappingUp: false,
  error: null,
};

export function useCourtroom() {
  const [state, setState] = useState<CourtState>(initial);
  const abortRef = useRef<AbortController | null>(null);
  const liveRef = useRef<LiveTurn | null>(null);

  const connect = useCallback((sessionId: string) => {
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;

    (async () => {
      try {
        for await (const { event, data } of readSSE(
          `/api/session/${sessionId}/stream`,
          ac.signal
        )) {
          switch (event) {
            case "history":
              liveRef.current = null;
              setState((s) => ({
                ...s,
                turns: (data.turns as TurnOut[]).map((t) => ({ ...t, streaming: false })),
                verdict: data.verdict ?? s.verdict,
                done: data.status === "done",
                crisis: data.status === "crisis",
                error: null,
              }));
              break;
            case "phase_start":
              liveRef.current = { role: data.role, content: "", sequence: -1, streaming: true };
              setState((s) => ({
                ...s,
                speaking: data.role,
                turns: [...s.turns, liveRef.current!],
              }));
              break;
            case "delta":
              if (liveRef.current) {
                liveRef.current.content += data.text;
                const snap = liveRef.current.content;
                setState((s) => {
                  const turns = [...s.turns];
                  if (turns.length) turns[turns.length - 1] = { ...turns[turns.length - 1], content: snap };
                  return { ...s, turns };
                });
              }
              break;
            case "turn_complete":
              if (liveRef.current) {
                liveRef.current.streaming = false;
                liveRef.current.sequence = data.sequence;
                const done = liveRef.current;
                setState((s) => {
                  const turns = [...s.turns];
                  if (turns.length) turns[turns.length - 1] = { ...done };
                  return { ...s, turns, speaking: null };
                });
                liveRef.current = null;
              }
              break;
            case "await_reply":
              setState((s) => ({
                ...s,
                awaitingReply: true,
                speaking: null,
                questionNumber: data.question_number,
                maxQuestions: data.max_questions,
              }));
              return;
            case "wrapping_up":
              setState((s) => ({ ...s, wrappingUp: true }));
              break;
            case "verdict":
              setState((s) => ({ ...s, verdict: data as VerdictOut }));
              break;
            case "done":
              setState((s) => ({ ...s, done: true, speaking: null }));
              return;
            case "crisis":
              setState((s) => ({ ...s, crisis: true, speaking: null }));
              return;
            case "busy":
              setState((s) => ({ ...s, error: "The court is already in session in another tab." }));
              return;
            case "error":
              setState((s) => ({ ...s, error: data.message }));
              return;
          }
        }
      } catch (e: any) {
        if (e?.name !== "AbortError") {
          setState((s) => ({ ...s, error: "Connection lost. Reconnecting will resume." }));
        }
      }
    })();
  }, []);

  const afterReply = useCallback(
    (sessionId: string) => {
      setState((s) => ({ ...s, awaitingReply: false }));
      connect(sessionId);
    },
    [connect]
  );

  const reset = useCallback(() => {
    abortRef.current?.abort();
    liveRef.current = null;
    setState(initial);
  }, []);

  return { state, connect, afterReply, reset };
}
