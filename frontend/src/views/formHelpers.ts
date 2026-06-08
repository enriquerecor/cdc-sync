import type {
  DestinationCreateRequest,
  DestinationUpdateRequest,
  SourceConnectionCreateRequest,
  SourceConnectionUpdateRequest,
} from "../api/controlPlaneAdmin";

export type CredentialsFormValues = {
  credentialsUser: string;
  credentialsPassword: string;
};

export type EntityFormMode = "create" | "edit";

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

export function buildSourceCredentials(
  values: CredentialsFormValues,
  mode: EntityFormMode,
):
  | SourceConnectionCreateRequest["credentials"]
  | SourceConnectionUpdateRequest["credentials"] {
  const user = values.credentialsUser.trim();
  const password = values.credentialsPassword.trim();

  if (mode === "edit" && !user && !password) {
    return undefined;
  }

  if (!user || !password) {
    throw new Error("Las credenciales deben incluir usuario y contraseña");
  }

  return {
    user,
    password,
  };
}

export function buildDestinationCredentials(
  values: CredentialsFormValues,
  mode: EntityFormMode,
):
  | DestinationCreateRequest["credentials"]
  | DestinationUpdateRequest["credentials"] {
  const user = values.credentialsUser.trim();
  const password = values.credentialsPassword.trim();

  if (mode === "edit" && !user && !password) {
    return undefined;
  }

  if (!user || !password) {
    throw new Error("Las credenciales deben incluir usuario y contraseña");
  }

  return {
    user,
    password,
  };
}
