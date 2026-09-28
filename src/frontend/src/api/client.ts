import createClient from "openapi-fetch";
import type { paths } from "./schema";

const BASE_URL = "http://localhost:8010";

export type Role = "STATION_OFFICER" | "DISTRICT_SP" | "STATE_DGP";

export interface AuthState {
  role: Role;
  stationId: number | null;
}

// Tiny in-memory store the Navbar's Role Switcher writes to. This is the whole
// "auth" system for the demo — a judge picks a role/station and every request
// after that is scoped server-side by the X-User-Role / X-User-Station headers
// this client injects. There is no token, no login: RBAC is proven by the data
// that comes back changing when the switcher changes, not by a login screen.
let currentAuth: AuthState = { role: "STATE_DGP", stationId: null };

export function setAuth(next: AuthState) {
  currentAuth = next;
}

export function getAuth(): AuthState {
  return currentAuth;
}

/** The OpenAPI schema (correctly) marks X-User-Role as a required header on every
 * scoped read, since the backend genuinely 400s without it — so the generated
 * typed client requires callers to pass it explicitly. The onRequest middleware
 * below is what actually sets the live header value on the outgoing request, but
 * this getter keeps every call site's second argument both type-correct AND
 * accurate (not a dummy placeholder), by reading the same in-memory auth state. */
export function authHeaders() {
  return {
    "X-User-Role": currentAuth.role,
    ...(currentAuth.stationId !== null ? { "X-User-Station": currentAuth.stationId } : {}),
  };
}

export const api = createClient<paths>({ baseUrl: BASE_URL });

api.use({
  onRequest({ request }) {
    request.headers.set("X-User-Role", currentAuth.role);
    if (currentAuth.stationId !== null) {
      request.headers.set("X-User-Station", String(currentAuth.stationId));
    }
    return request;
  },
});
