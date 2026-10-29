// Only a real UUID may be placed into an API path: nothing else can reach the upstream URL.
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function validId(value: string): boolean {
  return UUID.test(value);
}

export function badId() {
  return Response.json(
    { error: { code: "invalid_request", message: "That id is not valid." } },
    { status: 422 },
  );
}
