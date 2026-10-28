"use client";

import "./globals.css";

// The last safety net: it replaces the whole page when even the layout fails, so it brings its
// own html and body. No inline styles (the CSP forbids them); the stylesheet is imported above.
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body>
        <main className="shell">
          <section className="card" role="alert">
            <h1>Something went wrong</h1>
            <p>GraphLens could not start. Please try again.</p>
            {error.digest ? <p className="muted">Reference: {error.digest}</p> : null}
            <button type="button" className="primary" onClick={() => reset()}>
              Try again
            </button>
          </section>
        </main>
      </body>
    </html>
  );
}
