import { forward } from "@/lib/proxy";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const body = await request.text();
  if (body.length > 20_000) {
    return Response.json(
      { error: { code: "invalid_request", message: "The request is too large." } },
      { status: 413 },
    );
  }
  return forward("/api/v1/ask", { method: "POST", body });
}
