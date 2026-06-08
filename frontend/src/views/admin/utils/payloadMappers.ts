import type {
  DestinationCreateRequest,
  DestinationUpdateRequest,
  SyncConfig,
  SyncConfigRequest,
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
  DestinationColumnFormValues,
  DestinationFormValues,
  EntityFormMode,
  SyncConfigFormValues,
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

export function buildSyncConfigPayload(
  values: SyncConfigFormValues,
): SyncConfigRequest {
  const tables = values.tables.map(buildConfiguredTablePayload);

  if (tables.length === 0) {
    throw new Error("La configuración debe incluir al menos una tabla");
  }

  return {
    name: values.name.trim(),
    source_connection_id: values.sourceConnectionId,
    destination_id: values.destinationId,
    sync_mode: values.syncMode.trim(),
    tables,
    enabled: values.enabled,
  };
}

export function buildSyncConfigFormValues(
  config: SyncConfig | null,
): SyncConfigFormValues {
  if (!config) {
    return {
      name: "",
      sourceConnectionId: "",
      destinationId: "",
      syncMode: "realtime",
      tables: [],
      enabled: true,
    };
  }

  return {
    name: config.name,
    sourceConnectionId: config.source_connection_id,
    destinationId: config.destination_id,
    syncMode: config.sync_mode,
    tables: config.tables.map((table) => ({
      logicalName: table.logical_name,
      sourceSchema: table.source_schema,
      sourceTable: table.source_table,
      cdcTopic: table.cdc_topic,
      destinationTable: table.destination_table,
      primaryKeyFields: table.primary_key_fields.join(", "),
      destinationColumns: table.destination_columns.map((column) => ({
        name: column.name,
        destinationType: column.destination_type,
        nullable: column.nullable,
      })),
      enabled: table.enabled,
    })),
    enabled: config.enabled,
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

function buildConfiguredTablePayload(
  table: SyncConfigFormValues["tables"][number],
): SyncConfigRequest["tables"][number] {
  const primaryKeyFields = splitCommaSeparatedText(table.primaryKeyFields);
  const destinationColumns = table.destinationColumns.map(
    buildDestinationColumnPayload,
  );

  if (primaryKeyFields.length === 0) {
    throw new Error("Cada tabla debe incluir al menos una clave primaria");
  }

  if (destinationColumns.length === 0) {
    throw new Error("Cada tabla debe incluir al menos una columna destino");
  }

  return {
    logical_name: table.logicalName.trim(),
    source_schema: table.sourceSchema.trim(),
    source_table: table.sourceTable.trim(),
    cdc_topic: table.cdcTopic.trim(),
    destination_table: table.destinationTable.trim(),
    primary_key_fields: primaryKeyFields,
    destination_columns: destinationColumns,
    enabled: table.enabled,
  };
}

function buildDestinationColumnPayload(
  column: DestinationColumnFormValues,
): SyncConfigRequest["tables"][number]["destination_columns"][number] {
  return {
    name: column.name.trim(),
    destination_type: column.destinationType.trim(),
    nullable: column.nullable,
  };
}

function splitCommaSeparatedText(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
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
