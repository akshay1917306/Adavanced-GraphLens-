import { forward } from "@/lib/proxy";
import { badId, validId } from "@/lib/routeid";

export const dynamic = "force-dynamic";

export async function DELETE(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!validId(id)) return badId();
  return forward(request, `/api/v1/saved/${id}`, { method: "DELETE" });
}
