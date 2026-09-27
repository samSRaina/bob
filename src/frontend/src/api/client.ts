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
