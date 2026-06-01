const API_URL = process.env.API_URL ?? "http://localhost:8000";
const API_V1 = `${API_URL}/v1`;

export function getBackendUrl(path: string): string {
  return `${API_V1}${path}`;
}

export async function backendFetch(
  path: string,
  init?: RequestInit,
): Promise<Response> {
  return fetch(getBackendUrl(path), {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });
}
