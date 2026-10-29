import { forward } from "@/lib/proxy";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  return forward(request, "/api/v1/preferences");
}

export async function PUT(request: Request) {
  const body = await request.text();
  if (body.length > 2_000) {
    return Response.json(
      { error: { code: "invalid_request", message: "The request is too large." } },
      { status: 413 },
    );
  }
  return forward(request, "/api/v1/preferences", { method: "PUT", body });
}
