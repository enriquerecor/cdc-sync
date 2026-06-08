import type {
  ConfiguredTableFormValues,
  DestinationColumnFormValues,
} from "../types/forms";

const DEFAULT_CDC_TOPIC_PREFIX = "cdc_sync";

export function createEmptyDestinationColumn(
  values: Partial<DestinationColumnFormValues> = {},
): DestinationColumnFormValues {
  return {
    name: "",
    destinationType: "",
    nullable: false,
    ...values,
  };
}

export function createConfiguredTableFromName(
  tableName: string,
  sourceNamespace: string,
  existingTables: ConfiguredTableFormValues[],
): ConfiguredTableFormValues {
  const trimmedTableName = tableName.trim();
  const trimmedSourceNamespace = sourceNamespace.trim();
  const cdcTopic = inferCdcTopic(
    existingTables,
    trimmedSourceNamespace,
    trimmedTableName,
  );

  return {
    logicalName: trimmedTableName,
    sourceSchema: trimmedSourceNamespace,
    sourceTable: trimmedTableName,
    cdcTopic,
    destinationTable: trimmedTableName,
    primaryKeyFields: "id",
    destinationColumns: [createEmptyDestinationColumn({ name: "id" })],
    enabled: true,
  };
}

function inferCdcTopic(
  tables: ConfiguredTableFormValues[],
  sourceNamespace: string,
  tableName: string,
): string {
  if (!sourceNamespace || !tableName) {
    return "";
  }

  for (const table of tables) {
    const topicSuffix = `${table.sourceSchema.trim()}.${table.sourceTable.trim()}`;
    const hasReusablePattern =
      table.sourceSchema.trim() &&
      table.sourceTable.trim() &&
      table.cdcTopic.endsWith(topicSuffix);

    if (!hasReusablePattern) {
      continue;
    }

    const prefix = table.cdcTopic
      .slice(0, -topicSuffix.length)
      .replace(/\.$/, "");
    if (!prefix) {
      continue;
    }

    return `${prefix}.${sourceNamespace}.${tableName}`;
  }

  return `${DEFAULT_CDC_TOPIC_PREFIX}.${sourceNamespace}.${tableName}`;
}
