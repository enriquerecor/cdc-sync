import {
  DESTINATION_ENGINE_DEFINITIONS,
  SOURCE_ENGINE_DEFINITIONS,
  findEngineDefinition,
  requireEnabledEngineDefinition,
} from "./engineDefinitions";

export const DEFAULT_SOURCE_TYPE = "postgresql";
export const DEFAULT_DESTINATION_TYPE = "clickhouse";

export function getSourceEngineLabel(sourceType: string): string {
  return (
    findEngineDefinition(SOURCE_ENGINE_DEFINITIONS, sourceType)?.label ??
    sourceType
  );
}

export function getDestinationEngineLabel(destinationType: string): string {
  return (
    findEngineDefinition(DESTINATION_ENGINE_DEFINITIONS, destinationType)
      ?.label ?? destinationType
  );
}

export function getDefaultSourcePort(): number {
  return requireEnabledEngineDefinition(
    SOURCE_ENGINE_DEFINITIONS,
    DEFAULT_SOURCE_TYPE,
  ).defaultPort;
}

export function getDefaultDestinationPort(): number {
  return requireEnabledEngineDefinition(
    DESTINATION_ENGINE_DEFINITIONS,
    DEFAULT_DESTINATION_TYPE,
  ).defaultPort;
}
