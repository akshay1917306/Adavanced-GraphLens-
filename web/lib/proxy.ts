// The browser only talks to this web server; the web server talks to the API.
// That keeps the API address and the visitor token out of the browser's JavaScript:
// the token lives in an HttpOnly cookie that only this server reads and sets.

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";
const TIMEOUT_MS = 60_000;
const COOKIE = "gl_visitor";
const SECURE = process.env.COOKIE_SECURE === "1";
const PROXY_SECRET = process.env.PROXY_SECRET ?? "";

type Method = "GET" | "POST" | "PUT" | "DELETE";

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

// The API trusts the client address only when this shared secret comes with it.
function clientIp(request: Request): string {
  const forwarded = request.headers.get("x-forwarded-for") ?? "";
  return forwarded.split(",")[0].trim() || request.headers.get("x-real-ip") || "unknown";
}

function callApi(path: string, method: Method, ip: string, body?: string, token?: string) {
  const headers: Record<string, string> = {};
  if (PROXY_SECRET) {
    headers["X-Proxy-Secret"] = PROXY_SECRET;
    headers["X-Client-Ip"] = ip;
  }
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

// What the browser gets back: the API's status and JSON, and its Retry-After when it sent one.
async function pass(res: Response, issued: Issued | null): Promise<Response> {
  const headers = new Headers({ "Content-Type": "application/json" });
  const retry = res.headers.get("retry-after");
  if (retry) headers.set("Retry-After", retry);
  if (issued) headers.append("Set-Cookie", cookieHeader(issued));
  return new Response(await res.text(), { status: res.status, headers });
}

// Asks the API for a signed token: a renewed one for a known visitor, else a new visitor.
// A refusal (for example 429) is returned as it is so the browser can show it.
async function issueToken(existing: string | null, ip: string): Promise<Issued | Response> {
  const res = await callApi(
    "/api/v1/visitor",
    "POST",
    ip,
    JSON.stringify(existing ? { token: existing } : {}),
  );
  if (!res.ok) return pass(res, null);
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
  method?: Method;
  body?: string;
  needsVisitor?: boolean;
}

export async function forward(request: Request, path: string, options: Options = {}) {
  const method = options.method ?? "GET";
  const sendsJson = method === "POST" || method === "PUT";
  if (sendsJson && !(request.headers.get("content-type") ?? "").startsWith("application/json")) {
    return jsonError("invalid_request", "The request must be JSON.", 415);
  }
  const ip = clientIp(request);
  try {
    let token: string | null = null;
    let issued: Issued | null = null;
    if (options.needsVisitor !== false) {
      token = readCookie(request, COOKIE);
      if (!token) {
        const first = await issueToken(null, ip);
        if (first instanceof Response) return first;
        issued = first;
        token = issued.token;
      }
    }
    let res = await callApi(path, method, ip, options.body, token ?? undefined);
    if (res.status === 401 && token && !issued) {
      // an old, forged or deleted token: start over once with a valid one
      const renewed = await issueToken(token, ip);
      if (renewed instanceof Response) return renewed;
      issued = renewed;
      res = await callApi(path, method, ip, options.body, issued.token);
    }
    return pass(res, issued);
  } catch {
    return jsonError("api_unreachable", "The API is not reachable right now.", 502);
  }
}
