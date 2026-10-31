import { anonymousToken, authForward } from "@/lib/proxy";

export const dynamic = "force-dynamic";

interface Rule {
  method: "GET" | "POST" | "DELETE";
  path: string;
  mode: "start" | "session";
  clearsSession?: boolean;
  signsOut?: boolean;
  clearsVisitor?: boolean;
}

// One door for the sign-in actions; anything not listed here is a 404.
const ACTIONS: Record<string, Rule> = {
  signup: { method: "POST", path: "/api/v1/auth/signup", mode: "start" },
  login: { method: "POST", path: "/api/v1/auth/login", mode: "start" },
  reset: { method: "POST", path: "/api/v1/auth/reset", mode: "start" },
  "reset-with-link": { method: "POST", path: "/api/v1/auth/reset-with-link", mode: "start" },
  logout: { method: "POST", path: "/api/v1/auth/logout", mode: "session", signsOut: true },
  "logout-all": {
    method: "POST",
    path: "/api/v1/auth/logout-all",
    mode: "session",
    clearsSession: true,
  },
  "recovery-codes": { method: "POST", path: "/api/v1/auth/recovery-codes", mode: "session" },
  claim: { method: "POST", path: "/api/v1/auth/claim", mode: "session", clearsVisitor: true },
  me: { method: "GET", path: "/api/v1/auth/me", mode: "session" },
  account: { method: "DELETE", path: "/api/v1/auth/account", mode: "session", clearsSession: true },
};

function problem(code: string, message: string, status: number) {
  return Response.json({ error: { code, message } }, { status });
}

async function handle(request: Request, context: { params: Promise<{ action: string }> }) {
  const { action } = await context.params;
  const rule = Object.hasOwn(ACTIONS, action) ? ACTIONS[action] : undefined;
  if (!rule || rule.method !== request.method) return problem("not_found", "Not found.", 404);
  let body: string | undefined;
  if (rule.method !== "GET" && action !== "logout") {
    body = await request.text();
    if (body.length > 2_000) return problem("invalid_request", "The request is too large.", 413);
    if (action === "claim") {
      // the page never sees the anonymous token; this server adds it from its own cookie
      try {
        const parsed = JSON.parse(body) as { password?: unknown };
        body = JSON.stringify({
          password: parsed.password,
          anonymous_token: anonymousToken(request) ?? "",
        });
      } catch {
        return problem("invalid_request", "Invalid request.", 422);
      }
    }
  }
  return authForward(request, rule.path, { ...rule, body });
}

export const GET = handle;
export const POST = handle;
export const DELETE = handle;
