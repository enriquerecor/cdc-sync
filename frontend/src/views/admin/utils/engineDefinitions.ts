export type EngineDefinition = {
  value: string;
  label: string;
  defaultPort: number;
  databaseLabel: string;
  credentialsLabel: string;
  enabled: boolean;
};

export const SOURCE_ENGINE_DEFINITIONS = [
  {
    value: "postgresql",
    label: "PostgreSQL",
    defaultPort: 5432,
    databaseLabel: "Base de datos",
    credentialsLabel: "Credenciales del origen",
    enabled: true,
  },
  {
    value: "mysql",
    label: "MySQL",
    defaultPort: 3306,
    databaseLabel: "Base de datos",
    credentialsLabel: "Credenciales del origen",
    enabled: false,
  },
  {
    value: "sql-server",
    label: "SQL Server",
    defaultPort: 1433,
    databaseLabel: "Base de datos",
    credentialsLabel: "Credenciales del origen",
    enabled: false,
  },
  {
    value: "oracle",
    label: "Oracle",
    defaultPort: 1521,
    databaseLabel: "Servicio",
    credentialsLabel: "Credenciales del origen",
    enabled: false,
  },
] as const satisfies readonly EngineDefinition[];

export const DESTINATION_ENGINE_DEFINITIONS = [
  {
    value: "clickhouse",
    label: "ClickHouse",
    defaultPort: 9000,
    databaseLabel: "Base de datos",
    credentialsLabel: "Credenciales del destino",
    enabled: true,
  },
  {
    value: "bigquery",
    label: "BigQuery",
    defaultPort: 443,
    databaseLabel: "Dataset",
    credentialsLabel: "Credenciales del destino",
    enabled: false,
  },
  {
    value: "snowflake",
    label: "Snowflake",
    defaultPort: 443,
    databaseLabel: "Base de datos",
    credentialsLabel: "Credenciales del destino",
    enabled: false,
  },
  {
    value: "redshift",
    label: "Redshift",
    defaultPort: 5439,
    databaseLabel: "Base de datos",
    credentialsLabel: "Credenciales del destino",
    enabled: false,
  },
] as const satisfies readonly EngineDefinition[];

export function getEngineOptions(
  definitions: readonly EngineDefinition[],
): { value: string; label: string; disabled: boolean }[] {
  return definitions.map((definition) => ({
    value: definition.value,
    label: definition.label,
    disabled: !definition.enabled,
  }));
}

export function findEngineDefinition(
  definitions: readonly EngineDefinition[],
  value: string,
): EngineDefinition | null {
  return definitions.find((definition) => definition.value === value) ?? null;
}

export function requireEnabledEngineDefinition(
  definitions: readonly EngineDefinition[],
  value: string,
): EngineDefinition {
  const definition = findEngineDefinition(definitions, value);

  if (!definition) {
    throw new Error(`No existe definición para el motor "${value}"`);
  }

  if (!definition.enabled) {
    throw new Error(`El motor "${definition.label}" todavía no está soportado`);
  }

  return definition;
}
