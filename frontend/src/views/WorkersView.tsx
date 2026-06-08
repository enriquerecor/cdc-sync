import {
  ActionIcon,
  Badge,
  Button,
  Group,
  Modal,
  ScrollArea,
  Stack,
  Switch,
  Table,
  Text,
  TextInput,
  Textarea,
  Tooltip,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { modals } from "@mantine/modals";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { useState } from "react";

import { normalizeApiError } from "../api/errors";
import {
  createWorker,
  deleteWorker,
  listWorkers,
  updateWorker,
  type Worker,
  type WorkerRequest,
} from "../api/controlPlaneAdmin";
import { AdministrativeViewHeader } from "../components/AdministrativeViewHeader";
import { ErrorState, LoadingState } from "../components/FeedbackState";
import { optionalText, requiredText } from "./formHelpers";
import {
  showApiErrorNotification,
  showSuccessNotification,
} from "./notificationHelpers";

const WORKERS_QUERY_KEY = ["control-plane-admin", "workers"] as const;

type WorkerFormValues = {
  workerId: string;
  name: string;
  description: string;
  kafkaGroupId: string;
  enabled: boolean;
};

type WorkerFormProps = {
  worker: Worker | null;
  isSaving: boolean;
  onCancel: () => void;
  onSubmit: (values: WorkerFormValues) => void;
};

export function WorkersView() {
  const queryClient = useQueryClient();
  const [workerBeingEdited, setWorkerBeingEdited] = useState<Worker | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const workersQuery = useQuery({
    queryKey: WORKERS_QUERY_KEY,
    queryFn: listWorkers,
  });

  const createWorkerMutation = useMutation({
    mutationFn: createWorker,
    onSuccess: () => {
      closeModal();
      void queryClient.invalidateQueries({ queryKey: WORKERS_QUERY_KEY });
      showSuccessNotification("Worker creado", "El worker se guardó correctamente");
    },
    onError: showApiErrorNotification,
  });

  const updateWorkerMutation = useMutation({
    mutationFn: ({
      workerInternalId,
      payload,
    }: {
      workerInternalId: string;
      payload: WorkerRequest;
    }) => updateWorker(workerInternalId, payload),
    onSuccess: () => {
      closeModal();
      void queryClient.invalidateQueries({ queryKey: WORKERS_QUERY_KEY });
      showSuccessNotification(
        "Worker actualizado",
        "Los cambios se guardaron correctamente",
      );
    },
    onError: showApiErrorNotification,
  });

  const deleteWorkerMutation = useMutation({
    mutationFn: deleteWorker,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: WORKERS_QUERY_KEY });
      showSuccessNotification("Worker eliminado", "El worker se eliminó");
    },
    onError: showApiErrorNotification,
  });

  function openCreateModal(): void {
    setWorkerBeingEdited(null);
    setIsModalOpen(true);
  }

  function openEditModal(worker: Worker): void {
    setWorkerBeingEdited(worker);
    setIsModalOpen(true);
  }

  function closeModal(): void {
    setIsModalOpen(false);
    setWorkerBeingEdited(null);
  }

  function handleSubmit(values: WorkerFormValues): void {
    const payload = buildWorkerPayload(values);

    if (workerBeingEdited) {
      updateWorkerMutation.mutate({
        workerInternalId: workerBeingEdited.id,
        payload,
      });
      return;
    }

    createWorkerMutation.mutate(payload);
  }

  function openDeleteConfirmation(worker: Worker): void {
    modals.openConfirmModal({
      title: "Eliminar worker",
      children: (
        <Text size="sm">
          Se eliminará el worker administrativo {worker.name}.
        </Text>
      ),
      labels: {
        confirm: "Eliminar",
        cancel: "Cancelar",
      },
      confirmProps: {
        color: "red",
      },
      onConfirm: () => deleteWorkerMutation.mutate(worker.id),
    });
  }

  return (
    <Stack gap="lg">
      <AdministrativeViewHeader
        title="Workers"
        description="Gestiona los procesos que ejecutan sincronizaciones con una configuración estable."
        actionLabel="Crear worker"
        actionIcon={Plus}
        onAction={openCreateModal}
      />

      {renderWorkersContent({
        workers: workersQuery.data,
        isLoading: workersQuery.isPending,
        error: workersQuery.error,
        refetch: workersQuery.refetch,
        openEditModal,
        openDeleteConfirmation,
        isDeleting: deleteWorkerMutation.isPending,
      })}

      <Modal
        opened={isModalOpen}
        onClose={closeModal}
        title={workerBeingEdited ? "Editar worker" : "Crear worker"}
      >
        <WorkerForm
          key={workerBeingEdited?.id ?? "new-worker"}
          worker={workerBeingEdited}
          isSaving={createWorkerMutation.isPending || updateWorkerMutation.isPending}
          onCancel={closeModal}
          onSubmit={handleSubmit}
        />
      </Modal>
    </Stack>
  );
}

function WorkerForm({
  worker,
  isSaving,
  onCancel,
  onSubmit,
}: WorkerFormProps) {
  const form = useForm<WorkerFormValues>({
    initialValues: {
      workerId: worker?.worker_id ?? "",
      name: worker?.name ?? "",
      description: worker?.description ?? "",
      kafkaGroupId: worker?.kafka_group_id ?? "",
      enabled: worker?.enabled ?? true,
    },
    validate: {
      workerId: requiredText,
      name: requiredText,
    },
  });

  return (
    <form onSubmit={form.onSubmit(onSubmit)}>
      <Stack gap="md">
        <TextInput
          label="WORKER_ID"
          placeholder="local-worker"
          withAsterisk
          {...form.getInputProps("workerId")}
        />
        <TextInput
          label="Nombre"
          placeholder="Worker local"
          withAsterisk
          {...form.getInputProps("name")}
        />
        <Textarea
          label="Descripción"
          autosize
          minRows={2}
          {...form.getInputProps("description")}
        />
        <TextInput
          label="Grupo Kafka"
          placeholder="cdc-sync-worker-local-worker"
          {...form.getInputProps("kafkaGroupId")}
        />
        <Switch
          label="Activo"
          {...form.getInputProps("enabled", { type: "checkbox" })}
        />
        <Group justify="flex-end">
          <Button variant="default" onClick={onCancel}>
            Cancelar
          </Button>
          <Button type="submit" loading={isSaving}>
            Guardar
          </Button>
        </Group>
      </Stack>
    </form>
  );
}

type WorkersContentProps = {
  workers: Worker[] | undefined;
  isLoading: boolean;
  error: unknown;
  refetch: () => void;
  openEditModal: (worker: Worker) => void;
  openDeleteConfirmation: (worker: Worker) => void;
  isDeleting: boolean;
};

function renderWorkersContent({
  workers,
  isLoading,
  error,
  refetch,
  openEditModal,
  openDeleteConfirmation,
  isDeleting,
}: WorkersContentProps) {
  if (isLoading) {
    return <LoadingState message="Cargando workers" />;
  }

  if (error) {
    const apiError = normalizeApiError(error);

    return (
      <ErrorState
        title="No se pudieron cargar los workers"
        message={apiError.message}
        onRetry={refetch}
      />
    );
  }

  if (!workers || workers.length === 0) {
    return (
      <Text c="dimmed" size="sm">
        Todavía no hay workers registrados.
      </Text>
    );
  }

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
                      onClick={() => openEditModal(worker)}
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
                      onClick={() => openDeleteConfirmation(worker)}
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

function buildWorkerPayload(values: WorkerFormValues): WorkerRequest {
  return {
    worker_id: values.workerId.trim(),
    name: values.name.trim(),
    description: optionalText(values.description),
    kafka_group_id: optionalText(values.kafkaGroupId),
    enabled: values.enabled,
  };
}
