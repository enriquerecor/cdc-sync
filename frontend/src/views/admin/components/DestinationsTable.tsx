import {ActionIcon, Badge, Group, ScrollArea, Table, Text, Tooltip,} from "@mantine/core";
import {Pencil, Trash2} from "lucide-react";

import type {Destination} from "../../../api/controlPlaneAdmin";
import {getDestinationEngineLabel} from "../utils/engineLabels";

type DestinationsTableProps = {
  destinations: Destination[];
  isDeleting: boolean;
  onEdit: (destination: Destination) => void;
  onDelete: (destination: Destination) => void;
};

export function DestinationsTable({
  destinations,
  isDeleting,
  onEdit,
  onDelete,
}: DestinationsTableProps) {
  return (
    <ScrollArea>
      <Table striped highlightOnHover withTableBorder verticalSpacing="sm">
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Nombre</Table.Th>
            <Table.Th>Motor</Table.Th>
            <Table.Th>Host</Table.Th>
            <Table.Th>Base de datos</Table.Th>
            <Table.Th>Seguridad</Table.Th>
            <Table.Th>Credenciales</Table.Th>
            <Table.Th ta="right">Acciones</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {destinations.map((destination) => (
            <Table.Tr key={destination.id}>
              <Table.Td>
                <Text fw={500}>{destination.name}</Text>
              </Table.Td>
              <Table.Td>
                <Badge variant="light">
                  {getDestinationEngineLabel(destination.destination_type)}
                </Badge>
              </Table.Td>
              <Table.Td>
                {destination.host}:{destination.port}
              </Table.Td>
              <Table.Td>{destination.database_name}</Table.Td>
              <Table.Td>
                <Badge color={destination.secure ? "teal" : "gray"} variant="light">
                  {destination.secure ? "Segura" : "Sin TLS"}
                </Badge>
              </Table.Td>
              <Table.Td>
                <Badge
                  color={destination.credentials_configured ? "teal" : "red"}
                  variant="light"
                >
                  {destination.credentials_configured
                    ? "Configuradas"
                    : "Pendientes"}
                </Badge>
              </Table.Td>
              <Table.Td>
                <Group justify="flex-end" gap="xs" wrap="nowrap">
                  <Tooltip label="Editar destino">
                    <ActionIcon
                      variant="subtle"
                      aria-label="Editar destino"
                      onClick={() => onEdit(destination)}
                    >
                      <Pencil size={16} strokeWidth={1.8} />
                    </ActionIcon>
                  </Tooltip>
                  <Tooltip label="Eliminar destino">
                    <ActionIcon
                      color="red"
                      variant="subtle"
                      aria-label="Eliminar destino"
                      loading={isDeleting}
                      onClick={() => onDelete(destination)}
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
