import ResetLinkView from "@/components/ResetLinkView";

// Rendered on every request so the Content-Security-Policy nonce is fresh each time.
export const dynamic = "force-dynamic";

export default function ResetPage() {
  return (
    <main>
      <ResetLinkView />
    </main>
  );
}
