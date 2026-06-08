import {ActionIcon, Badge, Group, ScrollArea, Table, Text, Tooltip,} from "@mantine/core";
import {Pencil, Trash2} from "lucide-react";

import type {SourceConnection} from "../../../api/controlPlaneAdmin";
import {getSourceEngineLabel} from "../utils/engineLabels";

type SourceConnectionsTableProps = {
  sourceConnections: SourceConnection[];
  isDeleting: boolean;
  onEdit: (sourceConnection: SourceConnection) => void;
  onDelete: (sourceConnection: SourceConnection) => void;
};

export function SourceConnectionsTable({
  sourceConnections,
  isDeleting,
  onEdit,
  onDelete,
}: SourceConnectionsTableProps) {
  return (
    <ScrollArea>
      <Table striped highlightOnHover withTableBorder verticalSpacing="sm">
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Nombre</Table.Th>
            <Table.Th>Motor</Table.Th>
            <Table.Th>Host</Table.Th>
            <Table.Th>Base de datos</Table.Th>
            <Table.Th>Credenciales</Table.Th>
            <Table.Th ta="right">Acciones</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {sourceConnections.map((sourceConnection) => (
            <Table.Tr key={sourceConnection.id}>
              <Table.Td>
                <Text fw={500}>{sourceConnection.name}</Text>
              </Table.Td>
              <Table.Td>
                <Badge variant="light">
                  {getSourceEngineLabel(sourceConnection.source_type)}
                </Badge>
              </Table.Td>
              <Table.Td>
                {sourceConnection.host}:{sourceConnection.port}
              </Table.Td>
              <Table.Td>{sourceConnection.database_name}</Table.Td>
              <Table.Td>
                <Badge
                  color={sourceConnection.credentials_configured ? "teal" : "red"}
                  variant="light"
                >
                  {sourceConnection.credentials_configured
                    ? "Configuradas"
                    : "Pendientes"}
                </Badge>
              </Table.Td>
              <Table.Td>
                <Group justify="flex-end" gap="xs" wrap="nowrap">
                  <Tooltip label="Editar origen">
                    <ActionIcon
                      variant="subtle"
                      aria-label="Editar origen"
                      onClick={() => onEdit(sourceConnection)}
                    >
                      <Pencil size={16} strokeWidth={1.8} />
                    </ActionIcon>
                  </Tooltip>
                  <Tooltip label="Eliminar origen">
                    <ActionIcon
                      color="red"
                      variant="subtle"
                      aria-label="Eliminar origen"
                      loading={isDeleting}
                      onClick={() => onDelete(sourceConnection)}
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
