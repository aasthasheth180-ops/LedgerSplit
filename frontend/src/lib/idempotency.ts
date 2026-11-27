// Keep one key per unchanged logical submission until success or explicit reset.
export function createIdempotencyTracker(makeKey: () => string = () => crypto.randomUUID()) {
  const keys = new Map<string, string>();
  return {
    keyFor(scope: string, payload: unknown): string {
      const fingerprint = JSON.stringify([scope, payload]);
      const existing = keys.get(fingerprint);
      if (existing) return existing;
      const key = makeKey();
      keys.set(fingerprint, key);
      return key;
    },
    complete(scope: string, payload: unknown): void {
      keys.delete(JSON.stringify([scope, payload]));
    },
    reset(): void { keys.clear(); },
  };
}
export function idempotentPost(payload: unknown, key: string): RequestInit {
  return { method: 'POST', headers: { 'Idempotency-Key': key }, body: JSON.stringify(payload) };
}
