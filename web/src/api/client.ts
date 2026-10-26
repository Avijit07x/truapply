import type { ApiError } from "./types";

const UNREACHABLE = "Can't reach the tracker. Is `satyaapply tracker` still running?";

export class RequestFailed extends Error {
  readonly status: number;
  readonly problems: readonly string[];

  constructor(status: number, body: ApiError) {
    super(body.error);
    this.name = "RequestFailed";
    this.status = status;
    this.problems = body.problems ?? [];
  }
}

function isApiError(body: unknown): body is ApiError {
  return typeof body === "object" && body !== null && typeof (body as ApiError).error === "string";
}

async function request<T>(path: string, init: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, init);
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw error;
    }
    throw new RequestFailed(0, { error: UNREACHABLE });
  }
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    throw new RequestFailed(response.status, isApiError(body) ? body : { error: UNREACHABLE });
  }
  return body as T;
}

export function get<T>(path: string, signal?: AbortSignal): Promise<T> {
  return request<T>(path, { headers: { Accept: "application/json" }, signal: signal ?? null });
}

export function post<T>(path: string, body: object = {}): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function messageOf(error: unknown): string {
  if (error instanceof RequestFailed) {
    return error.message;
  }
  if (
    error instanceof Error &&
    /dynamically imported module|Importing a module script/.test(error.message)
  ) {
    return "The tracker was updated. Reload the page to get the new version.";
  }
  return "Something went wrong. Try again.";
}
