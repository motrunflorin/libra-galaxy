/**
 * The single place the frontend talks to the backend.
 *
 * Responsibilities: base URL, auth header, locale header, request id, and
 * unwrapping the response envelope into either data or a typed error. No
 * banking rules live here — the backend owns them.
 */

import type { ApiErrorCode, Envelope } from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  constructor(
    readonly code: ApiErrorCode,
    message: string,
    readonly status: number,
    readonly requestId: string | null,
    readonly details: Record<string, unknown> | null = null,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  /** Access token. Server-side rendering passes it explicitly. */
  token?: string;
  locale?: string;
  signal?: AbortSignal;
}

export async function apiRequest<TBody>(
  path: string,
  options: RequestOptions = {},
): Promise<TBody> {
  const { method = "GET", body, token, locale = "ro", signal } = options;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "Accept-Language": locale,
    // Lets one user-visible failure be traced through every backend layer.
    "X-Request-ID": `req_web_${crypto.randomUUID().replace(/-/g, "").slice(0, 16)}`,
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
    cache: "no-store",
  });

  let envelope: Envelope<TBody>;
  try {
    envelope = (await response.json()) as Envelope<TBody>;
  } catch {
    throw new ApiError("INTERNAL_ERROR", "Unreadable response.", response.status, null);
  }

  if (!envelope.success) {
    throw new ApiError(
      envelope.error.code,
      envelope.error.message,
      response.status,
      envelope.request_id,
      envelope.error.details,
    );
  }

  return envelope.body;
}
