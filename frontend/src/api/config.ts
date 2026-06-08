const API_BASE_URL_ENV = import.meta.env.VITE_API_BASE_URL;

export function getApiBaseUrl(): string {
  if (!API_BASE_URL_ENV) {
    throw new Error("VITE_API_BASE_URL debe estar configurada");
  }

  const normalizedApiBaseUrl = API_BASE_URL_ENV.trim().replace(/\/+$/, "");

  if (!normalizedApiBaseUrl) {
    throw new Error("VITE_API_BASE_URL no puede estar vacía");
  }

  try {
    return new URL(normalizedApiBaseUrl).toString().replace(/\/+$/, "");
  } catch {
    throw new Error("VITE_API_BASE_URL debe ser una URL válida");
  }
}
