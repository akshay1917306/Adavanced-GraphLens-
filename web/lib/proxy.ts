// The browser only talks to this web server; the web server talks to the API.
// That keeps the API address and the visitor token out of the browser's JavaScript:
// the token lives in an HttpOnly cookie that only this server reads and sets.

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";
const TIMEOUT_MS = 60_000;
const COOKIE = "gl_visitor";
const SESSION_COOKIE = "gl_session"; // a signed-in session; same rules as the visitor cookie
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
// A streamed answer (lines of JSON) is passed on as it arrives; anything else is read whole.
async function pass(
  res: Response,
  issued: Issued | null,
  stream = false,
  extraCookies: string[] = [],
): Promise<Response> {
  const streaming = stream && res.ok && res.body !== null;
  const headers = new Headers({
    "Content-Type": streaming ? "application/x-ndjson" : "application/json",
  });
  const retry = res.headers.get("retry-after");
  if (retry) headers.set("Retry-After", retry);
  if (streaming) headers.set("Cache-Control", "no-store");
  if (issued) headers.append("Set-Cookie", cookieHeader(issued));
  for (const cookie of extraCookies) headers.append("Set-Cookie", cookie);
  return new Response(streaming ? res.body : await res.text(), { status: res.status, headers });
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

function sessionCookieHeader(token: string, maxAge: number): string {
  return `${SESSION_COOKIE}=${token}; Path=/; Max-Age=${maxAge}; HttpOnly; SameSite=Lax${SECURE ? "; Secure" : ""}`;
}

function clearCookieHeader(name: string): string {
  return `${name}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax${SECURE ? "; Secure" : ""}`;
}

// A request that changes something must come from a page of this site: the browser says so with
// Sec-Fetch-Site, and where it sends an Origin it must match the address that was asked.
function foreignRequest(request: Request): boolean {
  if (request.headers.get("sec-fetch-site") === "cross-site") return true;
  const origin = request.headers.get("origin");
  const host = request.headers.get("host");
  if (!origin || !host) return false;
  try {
    return new URL(origin).host !== host;
  } catch {
    return true;
  }
}

function jsonError(code: string, message: string, status: number) {
  return Response.json({ error: { code, message } }, { status });
}

interface Options {
  method?: Method;
  body?: string;
  needsVisitor?: boolean;
  stream?: boolean; // pass a streamed reply on as it arrives
}

export async function forward(request: Request, path: string, options: Options = {}) {
  const method = options.method ?? "GET";
  const sendsJson = method === "POST" || method === "PUT";
  if (sendsJson && !(request.headers.get("content-type") ?? "").startsWith("application/json")) {
    return jsonError("invalid_request", "The request must be JSON.", 415);
  }
  // A page on another site must not be able to change this visitor's data.
  if (method !== "GET" && foreignRequest(request)) {
    return jsonError("forbidden", "Cross-site requests are not allowed.", 403);
  }
  const ip = clientIp(request);
  try {
    let token: string | null = null;
    let issued: Issued | null = null;
    let dropSession = false;
    const session = options.needsVisitor !== false ? readCookie(request, SESSION_COOKIE) : null;
    if (session) {
      const signedIn = await callApi(path, method, ip, options.body, session);
      if (signedIn.status !== 401) return pass(signedIn, null, options.stream === true);
      await signedIn.body?.cancel();
      dropSession = true; // expired or ended: carry on as an anonymous visitor
    }
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
      await res.body?.cancel();
      res = await callApi(path, method, ip, options.body, issued.token);
    }
    const dropped = dropSession ? [clearCookieHeader(SESSION_COOKIE)] : [];
    return pass(res, issued, options.stream === true, dropped);
  } catch {
    return jsonError("api_unreachable", "The API is not reachable right now.", 502);
  }
}

// ---- sign-in routes ---------------------------------------------------------------------------
// The session token never reaches the browser's JavaScript: it is kept in an HttpOnly cookie, and
// the reply to the page carries only the email (and the recovery codes, once, at sign-up).

export function anonymousToken(request: Request): string | null {
  return readCookie(request, COOKIE);
}

interface AuthOptions {
  method: Method;
  body?: string;
  // "start": no session needed, a good reply starts one. "session": needs the session cookie.
  mode: "start" | "session";
  clearsSession?: boolean; // after success: delete account, sign out everywhere
  signsOut?: boolean; // plain sign-out: the cookie goes even when the session was already gone
  clearsVisitor?: boolean; // after claiming the anonymous history
}

export async function authForward(request: Request, path: string, options: AuthOptions) {
  const hasBody = options.body !== undefined;
  if (hasBody && !(request.headers.get("content-type") ?? "").startsWith("application/json")) {
    return jsonError("invalid_request", "The request must be JSON.", 415);
  }
  if (options.method !== "GET" && foreignRequest(request)) {
    return jsonError("forbidden", "Cross-site requests are not allowed.", 403);
  }
  const session = readCookie(request, SESSION_COOKIE);
  if (options.mode === "session" && !session) {
    if (options.signsOut) return Response.json({ ok: true });
    return jsonError("visitor_required", "You are not signed in.", 401);
  }
  try {
    const res = await callApi(
      path,
      options.method,
      clientIp(request),
      options.body,
      options.mode === "session" ? (session ?? undefined) : undefined,
    );
    if (options.mode === "start" && res.ok) {
      const data = (await res.json()) as { token: string; max_age_seconds: number };
      const { token, max_age_seconds: maxAge, ...rest } = data;
      const started = new Response(JSON.stringify(rest), { status: res.status });
      return pass(started, null, false, [sessionCookieHeader(token, maxAge)]);
    }
    const cookies: string[] = [];
    if ((options.clearsSession && res.ok) || (options.signsOut && (res.ok || res.status === 401))) {
      cookies.push(clearCookieHeader(SESSION_COOKIE));
    }
    if (options.clearsVisitor && res.ok) cookies.push(clearCookieHeader(COOKIE));
    return pass(res, null, false, cookies);
  } catch {
    return jsonError("api_unreachable", "The API is not reachable right now.", 502);
  }
}
