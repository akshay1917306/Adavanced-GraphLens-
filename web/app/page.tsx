// Phase 0 placeholder. The real Ask screen is built in Phase 5.
// The API is called from the server side, so the browser never talks to the API directly.

type Health = { status: string; services: Record<string, string> };

export const dynamic = "force-dynamic";

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";

async function getHealth(): Promise<Health | null> {
  try {
    const res = await fetch(`${API_URL}/api/v1/health`, {
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });
    return (await res.json()) as Health;
  } catch {
    return null;
  }
}

export default async function Home() {
  const health = await getHealth();
  return (
    <main>
      <h1>GraphLens</h1>
      <p>Phase 0 placeholder. This page only shows whether the backend services are running.</p>
      <h2>Service status</h2>
      {health === null ? (
        <p>API not reachable at {API_URL}. Is <code>docker compose up</code> running?</p>
      ) : (
        <ul>
          {Object.entries(health.services).map(([name, state]) => (
            <li key={name}>
              {name}: <strong>{state}</strong>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
