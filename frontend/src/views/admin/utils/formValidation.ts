import type {
  CredentialsFormValues,
  EntityFormMode,
} from "../types/forms";

export function requiredText(value: string): string | null {
  if (value.trim()) {
    return null;
  }

  return "Campo obligatorio";
}

export function optionalText(value: string): string | null {
  const trimmedValue = value.trim();

  if (!trimmedValue) {
    return null;
  }

  return trimmedValue;
}

export function validatePort(value: number | ""): string | null {
  if (typeof value !== "number" || !Number.isInteger(value)) {
    return "El puerto debe ser un número entero";
  }

  if (value < 1 || value > 65535) {
    return "El puerto debe estar entre 1 y 65535";
  }

  return null;
}

export function getValidatedPort(value: number | ""): number {
  const error = validatePort(value);

  if (error) {
    throw new Error(error);
  }

  if (typeof value !== "number") {
    throw new Error("El puerto debe ser un número entero");
  }

  return value;
}

export function validateCredentialsUser(
  value: string,
  values: CredentialsFormValues,
  mode: EntityFormMode,
): string | null {
  if (mode === "create") {
    return requiredText(value);
  }

  if (value.trim() || !values.credentialsPassword.trim()) {
    return null;
  }

  return "Indica también el usuario";
}

export function validateCredentialsPassword(
  value: string,
  values: CredentialsFormValues,
  mode: EntityFormMode,
): string | null {
  if (mode === "create") {
    return requiredText(value);
  }

  if (value.trim() || !values.credentialsUser.trim()) {
    return null;
  }

  return "Indica también la contraseña";
}
