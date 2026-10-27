import { forward } from "@/lib/proxy";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  return forward(request, "/api/v1/saved");
}

export async function POST(request: Request) {
  const body = await request.text();
  if (body.length > 5_000) {
    return Response.json(
      { error: { code: "invalid_request", message: "The request is too large." } },
      { status: 413 },
    );
  }
  return forward(request, "/api/v1/saved", { method: "POST", body });
}
