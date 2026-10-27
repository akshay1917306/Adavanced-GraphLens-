import AskApp from "@/components/AskApp";

// Rendered on every request so the Content-Security-Policy nonce is fresh each time.
export const dynamic = "force-dynamic";

export default function Home() {
  return (
    <main>
      <AskApp />
    </main>
  );
}
