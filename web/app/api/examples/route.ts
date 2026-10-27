import { forward } from "@/lib/proxy";

export const dynamic = "force-dynamic";

export async function GET() {
  return forward("/api/v1/examples");
}
