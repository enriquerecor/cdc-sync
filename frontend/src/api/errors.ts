export type ApiError = {
  title: string;
  message: string;
  status?: number;
};

type HttpErrorPayload = {
  detail?: unknown;
  message?: unknown;
  status?: unknown;
};

export function normalizeApiError(error: unknown): ApiError {
  if (error instanceof Error) {
    return {
      title: "Error de comunicación",
      message: error.message,
    };
  }

  if (isHttpErrorPayload(error)) {
    const status = extractStatus(error.status);

    return {
      title: status
        ? `La API rechazó la petición (${status})`
        : "La API rechazó la petición",
      message: extractPayloadMessage(error),
      status,
    };
  }

  return {
    title: "Error inesperado",
    message: "No se pudo interpretar la respuesta de la API",
  };
}

export function createApiResponseError(
  status: number,
  payload: unknown,
  fallbackMessage: string,
): HttpErrorPayload {
  if (isHttpErrorPayload(payload)) {
    return {
      ...payload,
      status,
    };
  }

  return {
    status,
    message: fallbackMessage,
  };
}

function isHttpErrorPayload(value: unknown): value is HttpErrorPayload {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  return "detail" in value || "message" in value;
}

function extractPayloadMessage(payload: HttpErrorPayload): string {
  const detailMessage = stringifyUnknownMessage(payload.detail);

  if (detailMessage) {
    return detailMessage;
  }

  const fallbackMessage = stringifyUnknownMessage(payload.message);

  if (fallbackMessage) {
    return fallbackMessage;
  }

  return "La API devolvió un error sin detalle";
}

function extractStatus(value: unknown): number | undefined {
  if (typeof value !== "number") {
    return undefined;
  }

  return value;
}

function stringifyUnknownMessage(value: unknown): string | null {
  if (typeof value === "string" && value.trim()) {
    return value;
  }

  if (Array.isArray(value) && value.length > 0) {
    return value.map((item) => JSON.stringify(item)).join("; ");
  }

  if (typeof value === "object" && value !== null) {
    return JSON.stringify(value);
  }

  return null;
}
