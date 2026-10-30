import type { ApiError } from "./types";

export interface Result<T> {
  ok: boolean;
  status: number;
  data: T | null;
  message: string;
}

// One small wrapper for every call to this web server. Errors become a plain message
// (a 429 carries the API's "try again in N seconds" text).
export async function call<T>(
  path: string,
  method: "GET" | "POST" | "PUT" | "DELETE" = "GET",
  body?: unknown,
): Promise<Result<T>> {
  try {
    const res = await fetch(path, {
      method,
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const json = (await res.json()) as T | ApiError;
    if (!res.ok) {
      const message =
        typeof json === "object" && json !== null && "error" in json
          ? (json as ApiError).error.message
          : "Something went wrong.";
      return { ok: false, status: res.status, data: null, message };
    }
    return { ok: true, status: res.status, data: json as T, message: "" };
  } catch {
    return { ok: false, status: 0, data: null, message: "Could not reach the server. Is it running?" };
  }
}

// Ask with a streamed answer: `onDelta` gets each new piece of the draft text while it is written,
// the result is the final, checked answer (which may replace or refuse the draft). A service that
// cannot stream sends the final answer alone, so this works in replay mode too.
export async function askStream<T>(
  body: unknown,
  onDelta: (text: string) => void,
): Promise<Result<T>> {
  const fail = (status: number, message: string): Result<T> => ({
    ok: false,
    status,
    data: null,
    message,
  });
  try {
    const res = await fetch("/api/ask/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok || !res.body) {
      const json = (await res.json().catch(() => null)) as ApiError | null;
      return fail(res.status, json?.error?.message ?? "Something went wrong.");
    }
    const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
    let buffer = "";
    for (;;) {
      const { done, value } = await reader.read();
      if (value) buffer += value;
      let end = buffer.indexOf("\n");
      while (end >= 0) {
        const line = buffer.slice(0, end).trim();
        buffer = buffer.slice(end + 1);
        end = buffer.indexOf("\n");
        if (!line) continue;
        const event = JSON.parse(line) as {
          type: string;
          text?: string;
          response?: T;
          message?: string;
        };
        if (event.type === "delta" && event.text) onDelta(event.text);
        else if (event.type === "final" && event.response) {
          return { ok: true, status: 200, data: event.response, message: "" };
        } else if (event.type === "error") {
          return fail(502, event.message ?? "The answer could not be completed.");
        }
      }
      if (done) break;
    }
    return fail(502, "The answer ended early. Please try again.");
  } catch {
    return fail(0, "Could not reach the server. Is it running?");
  }
}
