import { forward } from "@/lib/proxy";
import { badId, validId } from "@/lib/routeid";

export const dynamic = "force-dynamic";

type Ctx = { params: Promise<{ id: string }> };

export async function GET(request: Request, { params }: Ctx) {
  const { id } = await params;
  if (!validId(id)) return badId();
  return forward(request, `/api/v1/history/${id}`);
}

export async function DELETE(request: Request, { params }: Ctx) {
  const { id } = await params;
  if (!validId(id)) return badId();
  return forward(request, `/api/v1/history/${id}`, { method: "DELETE" });
}
