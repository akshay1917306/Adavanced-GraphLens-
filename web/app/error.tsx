"use client";

// Shown when a page fails while it is drawn. It never prints the error text: that could hold
// internal details. The digest is a short reference that can be matched to the server log.
export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main className="shell">
      <section className="card" role="alert">
        <h1>Something went wrong</h1>
        <p>This page could not be shown. Your saved questions and answers are not affected.</p>
        {error.digest ? <p className="muted">Reference: {error.digest}</p> : null}
        <button type="button" className="primary" onClick={() => reset()}>
          Try again
        </button>
      </section>
    </main>
  );
}
