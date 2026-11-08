import type { HelloResponse } from "./types";

export const FALLBACK_ERROR_MESSAGE = "Could not reach the server";
export const HELLO_PATH = "/api/v1/hello";

/** Raised for any failed API call; `message` is safe to show to the visitor. */
export class ApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiError";
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function envelopeMessage(body: unknown): string | null {
  if (!isRecord(body) || !isRecord(body.error)) return null;
  const { message } = body.error;
  return typeof message === "string" && message !== "" ? message : null;
}

async function readJson(response: Response): Promise<unknown> {
  try {
    return (await response.json()) as unknown;
  } catch {
    return undefined;
  }
}

/** GET `${VITE_API_BASE_URL}/api/v1/hello?name=<name>`; throws ApiError on any failure. */
export async function getHello(name: string): Promise<HelloResponse> {
  const base = import.meta.env.VITE_API_BASE_URL ?? "";
  const url = `${base}${HELLO_PATH}?name=${encodeURIComponent(name)}`;

  let response: Response;
  try {
    response = await fetch(url);
  } catch {
    throw new ApiError(FALLBACK_ERROR_MESSAGE);
  }

  const body = await readJson(response);
  if (!response.ok) {
    throw new ApiError(envelopeMessage(body) ?? FALLBACK_ERROR_MESSAGE);
  }
  if (!isRecord(body) || typeof body.message !== "string") {
    throw new ApiError(FALLBACK_ERROR_MESSAGE);
  }
  return { message: body.message };
}
