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

import type { Worker } from "../../../api/controlPlaneAdmin";

type WorkersTableProps = {
  workers: Worker[];
  isDeleting: boolean;
  onEdit: (worker: Worker) => void;
  onDelete: (worker: Worker) => void;
};

export function WorkersTable({
  workers,
  isDeleting,
  onEdit,
  onDelete,
}: WorkersTableProps) {
  return (
    <ScrollArea>
      <Table striped highlightOnHover withTableBorder verticalSpacing="sm">
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Nombre</Table.Th>
            <Table.Th>WORKER_ID</Table.Th>
            <Table.Th>Grupo Kafka</Table.Th>
            <Table.Th>Estado</Table.Th>
            <Table.Th ta="right">Acciones</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {workers.map((worker) => (
            <Table.Tr key={worker.id}>
              <Table.Td>
                <Stack gap={2}>
                  <Text fw={500}>{worker.name}</Text>
                  {worker.description ? (
                    <Text size="xs" c="dimmed">
                      {worker.description}
                    </Text>
                  ) : null}
                </Stack>
              </Table.Td>
              <Table.Td>{worker.worker_id}</Table.Td>
              <Table.Td>{worker.kafka_group_id ?? "Derivado por runtime"}</Table.Td>
              <Table.Td>
                <Badge color={worker.enabled ? "teal" : "gray"} variant="light">
                  {worker.enabled ? "Activo" : "Inactivo"}
                </Badge>
              </Table.Td>
              <Table.Td>
                <Group justify="flex-end" gap="xs" wrap="nowrap">
                  <Tooltip label="Editar worker">
                    <ActionIcon
                      variant="subtle"
                      aria-label="Editar worker"
                      onClick={() => onEdit(worker)}
                    >
                      <Pencil size={16} strokeWidth={1.8} />
                    </ActionIcon>
                  </Tooltip>
                  <Tooltip label="Eliminar worker">
                    <ActionIcon
                      color="red"
                      variant="subtle"
                      aria-label="Eliminar worker"
                      loading={isDeleting}
                      onClick={() => onDelete(worker)}
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
