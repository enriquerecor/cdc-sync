export type ApiError = {
  title: string;
  message: string;
  status?: number;
};

type HttpErrorPayload = {
  detail?: unknown;
  message?: unknown;
};

export function normalizeApiError(error: unknown): ApiError {
  if (error instanceof Error) {
    return {
      title: "Error de comunicación",
      message: error.message,
    };
  }

  if (isHttpErrorPayload(error)) {
    return {
      title: "La API rechazó la petición",
      message: extractPayloadMessage(error),
    };
  }

  return {
    title: "Error inesperado",
    message: "No se pudo interpretar la respuesta de la API",
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
