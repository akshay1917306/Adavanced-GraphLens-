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
