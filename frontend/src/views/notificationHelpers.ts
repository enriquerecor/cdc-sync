import { notifications } from "@mantine/notifications";

import { normalizeApiError } from "../api/errors";

export function showApiErrorNotification(error: unknown): void {
  const apiError = normalizeApiError(error);

  notifications.show({
    color: "red",
    title: apiError.title,
    message: apiError.message,
  });
}

export function showFormErrorNotification(error: unknown): void {
  notifications.show({
    color: "red",
    title: "No se pudo preparar la petición",
    message: getFormErrorMessage(error),
  });
}

export function showSuccessNotification(
  title: string,
  message: string,
): void {
  notifications.show({
    color: "teal",
    title,
    message,
  });
}

function getFormErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }

  return "Revisa los campos del formulario antes de guardar";
}
