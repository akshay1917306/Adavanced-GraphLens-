import { forward } from "@/lib/proxy";

export const dynamic = "force-dynamic";

// Same rules as /api/ask; the answer text arrives while it is written (lines of JSON).
export async function POST(request: Request) {
  const body = await request.text();
  if (body.length > 20_000) {
    return Response.json(
      { error: { code: "invalid_request", message: "The request is too large." } },
      { status: 413 },
    );
  }
  return forward(request, "/api/v1/ask/stream", { method: "POST", body, stream: true });
}
