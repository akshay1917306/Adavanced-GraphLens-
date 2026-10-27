// The browser only talks to this web server; the web server talks to the API.
// That keeps the API address and the visitor token out of the browser's JavaScript:
// the token lives in an HttpOnly cookie that only this server reads and sets.

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";
const TIMEOUT_MS = 60_000;
const COOKIE = "gl_visitor";
const SECURE = process.env.COOKIE_SECURE === "1";

interface Issued {
  token: string;
  maxAge: number;
}

function readCookie(request: Request, name: string): string | null {
  for (const part of (request.headers.get("cookie") ?? "").split(";")) {
    const [key, ...rest] = part.trim().split("=");
    if (key === name) return rest.join("=");
  }
  return null;
}

function callApi(path: string, method: "GET" | "POST", body?: string, token?: string) {
  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (token) headers["X-Visitor-Token"] = token;
  return fetch(`${API_URL}${path}`, {
    method,
    headers,
    body,
    cache: "no-store",
    signal: AbortSignal.timeout(TIMEOUT_MS),
  });
}

// Asks the API for a signed token: a renewed one for a known visitor, else a new visitor.
async function issueToken(existing: string | null): Promise<Issued | null> {
  const res = await callApi("/api/v1/visitor", "POST", JSON.stringify(existing ? { token: existing } : {}));
  if (!res.ok) return null;
  const data = (await res.json()) as { token: string; max_age_seconds: number };
  return { token: data.token, maxAge: data.max_age_seconds };
}

function cookieHeader(issued: Issued): string {
  return `${COOKIE}=${issued.token}; Path=/; Max-Age=${issued.maxAge}; HttpOnly; SameSite=Lax${SECURE ? "; Secure" : ""}`;
}

function jsonError(code: string, message: string, status: number) {
  return Response.json({ error: { code, message } }, { status });
}

interface Options {
  method?: "GET" | "POST";
  body?: string;
  needsVisitor?: boolean;
}

export async function forward(request: Request, path: string, options: Options = {}) {
  const method = options.method ?? "GET";
  if (method === "POST" && !(request.headers.get("content-type") ?? "").startsWith("application/json")) {
    return jsonError("invalid_request", "The request must be JSON.", 415);
  }
  try {
    let token: string | null = null;
    let issued: Issued | null = null;
    if (options.needsVisitor !== false) {
      token = readCookie(request, COOKIE);
      if (!token) {
        issued = await issueToken(null);
        if (!issued) return jsonError("api_unreachable", "The API is not reachable right now.", 502);
        token = issued.token;
      }
    }
    let res = await callApi(path, method, options.body, token ?? undefined);
    if (res.status === 401 && token && !issued) {
      // an old, forged or deleted token: start over once with a valid one
      issued = await issueToken(token);
      if (issued) res = await callApi(path, method, options.body, issued.token);
    }
    const headers = new Headers({ "Content-Type": "application/json" });
    if (issued) headers.append("Set-Cookie", cookieHeader(issued));
    return new Response(await res.text(), { status: res.status, headers });
  } catch {
    return jsonError("api_unreachable", "The API is not reachable right now.", 502);
  }
}
