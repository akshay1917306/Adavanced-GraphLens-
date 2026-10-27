import { forward } from "@/lib/proxy";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  return forward(request, "/api/v1/history");
}
