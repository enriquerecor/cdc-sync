import {
  ActionIcon,
  Badge,
  Group,
  ScrollArea,
  Stack,
  Table,
  Text,
  Tooltip,
} from "@mantine/core";
import { Pencil, Trash2 } from "lucide-react";

import type {
  Destination,
  SourceConnection,
  SyncConfig,
} from "../../../../api/controlPlaneAdmin";

type ConfigurationsTableProps = {
  configs: SyncConfig[];
  sourceConnections: SourceConnection[];
  destinations: Destination[];
  isDeleting: boolean;
  onEdit: (config: SyncConfig) => void;
  onDelete: (config: SyncConfig) => void;
};

export function ConfigurationsTable({
  configs,
  sourceConnections,
  destinations,
  isDeleting,
  onEdit,
  onDelete,
}: ConfigurationsTableProps) {
  const sourceNamesById = buildNameIndex(sourceConnections);
  const destinationNamesById = buildNameIndex(destinations);

  return (
    <ScrollArea>
      <Table striped highlightOnHover withTableBorder verticalSpacing="sm">
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Nombre</Table.Th>
            <Table.Th>Origen</Table.Th>
            <Table.Th>Destino</Table.Th>
            <Table.Th>Tablas</Table.Th>
            <Table.Th>Modo</Table.Th>
            <Table.Th>Estado</Table.Th>
            <Table.Th ta="right">Acciones</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {configs.map((config) => (
            <Table.Tr key={config.id}>
              <Table.Td>
                <Text fw={500}>{config.name}</Text>
              </Table.Td>
              <Table.Td>
                {sourceNamesById.get(config.source_connection_id) ??
                  config.source_connection_id}
              </Table.Td>
              <Table.Td>
                {destinationNamesById.get(config.destination_id) ??
                  config.destination_id}
              </Table.Td>
              <Table.Td>
                <Stack gap={2}>
                  <Text size="sm">{config.tables.length}</Text>
                  <Text size="xs" c="dimmed">
                    {enabledTablesLabel(config)}
                  </Text>
                </Stack>
              </Table.Td>
              <Table.Td>{config.sync_mode}</Table.Td>
              <Table.Td>
                <Badge color={config.enabled ? "teal" : "gray"} variant="light">
                  {config.enabled ? "Activa" : "Inactiva"}
                </Badge>
              </Table.Td>
              <Table.Td>
                <Group justify="flex-end" gap="xs" wrap="nowrap">
                  <Tooltip label="Editar configuración">
                    <ActionIcon
                      variant="subtle"
                      aria-label="Editar configuración"
                      onClick={() => onEdit(config)}
                    >
                      <Pencil size={16} strokeWidth={1.8} />
                    </ActionIcon>
                  </Tooltip>
                  <Tooltip label="Eliminar configuración">
                    <ActionIcon
                      color="red"
                      variant="subtle"
                      aria-label="Eliminar configuración"
                      loading={isDeleting}
                      onClick={() => onDelete(config)}
                    >
                      <Trash2 size={16} strokeWidth={1.8} />
                    </ActionIcon>
                  </Tooltip>
                </Group>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </ScrollArea>
  );
}

function buildNameIndex(
  entities: Array<{ id: string; name: string }>,
): Map<string, string> {
  return new Map(entities.map((entity) => [entity.id, entity.name]));
}

function enabledTablesLabel(config: SyncConfig): string {
  const enabledCount = config.tables.filter((table) => table.enabled).length;
  return `${enabledCount} habilitadas`;
}
