import { createApiResponseError } from "./errors";

export function assertSuccessfulResponse(
  response: Response,
  error: unknown,
  fallbackMessage: string,
): void {
  if (response.ok) {
    return;
  }

  throw createApiResponseError(response.status, error, fallbackMessage);
}

export function requireData<T>(data: T | undefined, label: string): T {
  if (data === undefined) {
    throw new Error(`La API no devolvió ${label}`);
  }

  return data;
}
