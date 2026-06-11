export interface SSEvent {
  event: string;
  data: any;
}

/** Parse an SSE byte stream from fetch(), yielding {event,data} objects.
 * Unlike EventSource this lets us stop cleanly when the court pauses. */
export async function* readSSE(
  url: string,
  signal: AbortSignal
): AsyncGenerator<SSEvent> {
  const resp = await fetch(url, { signal, headers: { Accept: "text/event-stream" } });
  if (!resp.body) return;
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let idx;
    while ((idx = buf.indexOf("\n\n")) >= 0) {
      const raw = buf.slice(0, idx);
      buf = buf.slice(idx + 2);
      let event = "message";
      let data = "";
      for (const line of raw.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) data += line.slice(5).trim();
      }
      if (data) {
        try {
          yield { event, data: JSON.parse(data) };
        } catch {
          /* ignore malformed frame */
        }
      }
    }
  }
}
