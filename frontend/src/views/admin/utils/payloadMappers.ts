import type {
  DestinationCreateRequest,
  DestinationUpdateRequest,
  SourceConnectionCreateRequest,
  SourceConnectionUpdateRequest,
  WorkerRequest,
} from "../../../api/controlPlaneAdmin";
import {
  DESTINATION_ENGINE_DEFINITIONS,
  SOURCE_ENGINE_DEFINITIONS,
  requireEnabledEngineDefinition,
} from "./engineDefinitions";
import {
  getValidatedPort,
  optionalText,
} from "./formValidation";
import type {
  CredentialsFormValues,
  DestinationFormValues,
  EntityFormMode,
  SourceConnectionFormValues,
  WorkerFormValues,
} from "../types/forms";

export function buildWorkerPayload(values: WorkerFormValues): WorkerRequest {
  return {
    worker_id: values.workerId.trim(),
    name: values.name.trim(),
    description: optionalText(values.description),
    kafka_group_id: optionalText(values.kafkaGroupId),
    enabled: values.enabled,
  };
}

export function buildSourceConnectionCreatePayload(
  values: SourceConnectionFormValues,
): SourceConnectionCreateRequest {
  const basePayload = buildSourceConnectionBasePayload(values);
  const credentials = buildCredentials(values, "create");

  if (!credentials) {
    throw new Error("Las credenciales del origen son obligatorias");
  }

  return {
    ...basePayload,
    credentials,
  };
}

export function buildSourceConnectionUpdatePayload(
  values: SourceConnectionFormValues,
): SourceConnectionUpdateRequest {
  const basePayload = buildSourceConnectionBasePayload(values);
  const credentials = buildCredentials(values, "edit");

  if (!credentials) {
    return basePayload;
  }

  return {
    ...basePayload,
    credentials,
  };
}

export function buildDestinationCreatePayload(
  values: DestinationFormValues,
): DestinationCreateRequest {
  const basePayload = buildDestinationBasePayload(values);
  const credentials = buildCredentials(values, "create");

  if (!credentials) {
    throw new Error("Las credenciales del destino son obligatorias");
  }

  return {
    ...basePayload,
    credentials,
  };
}

export function buildDestinationUpdatePayload(
  values: DestinationFormValues,
): DestinationUpdateRequest {
  const basePayload = buildDestinationBasePayload(values);
  const credentials = buildCredentials(values, "edit");

  if (!credentials) {
    return basePayload;
  }

  return {
    ...basePayload,
    credentials,
  };
}

function buildSourceConnectionBasePayload(
  values: SourceConnectionFormValues,
): Omit<SourceConnectionUpdateRequest, "credentials"> {
  const engine = requireEnabledEngineDefinition(
    SOURCE_ENGINE_DEFINITIONS,
    values.sourceType,
  );

  return {
    name: values.name.trim(),
    source_type: engine.value,
    host: values.host.trim(),
    port: getValidatedPort(values.port),
    database_name: values.databaseName.trim(),
  };
}

function buildDestinationBasePayload(
  values: DestinationFormValues,
): Omit<DestinationUpdateRequest, "credentials"> {
  const engine = requireEnabledEngineDefinition(
    DESTINATION_ENGINE_DEFINITIONS,
    values.destinationType,
  );

  return {
    name: values.name.trim(),
    destination_type: engine.value,
    host: values.host.trim(),
    port: getValidatedPort(values.port),
    secure: values.secure,
    database_name: values.databaseName.trim(),
  };
}

function buildCredentials(
  values: CredentialsFormValues,
  mode: EntityFormMode,
):
  | SourceConnectionCreateRequest["credentials"]
  | SourceConnectionUpdateRequest["credentials"]
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
