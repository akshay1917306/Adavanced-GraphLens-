// The browser only talks to this web server; the web server talks to the API.
// That keeps the API address (and any future key) out of the browser.

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";
const TIMEOUT_MS = 60_000;

export async function forward(path: string, init?: { method: "GET" | "POST"; body?: string }) {
  try {
    const res = await fetch(`${API_URL}${path}`, {
      method: init?.method ?? "GET",
      headers: init?.body ? { "Content-Type": "application/json" } : undefined,
      body: init?.body,
      cache: "no-store",
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
    const text = await res.text();
    return new Response(text, {
      status: res.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch {
    return Response.json(
      { error: { code: "api_unreachable", message: "The API is not reachable right now." } },
      { status: 502 },
    );
  }
}
