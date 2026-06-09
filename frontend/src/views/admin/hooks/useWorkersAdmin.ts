import { modals } from "@mantine/modals";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import {
  createWorker,
  deleteWorker,
  listWorkers,
  updateWorker,
  type Worker,
  type WorkerRequest,
} from "../../../api/controlPlaneAdmin";
import type { WorkerFormValues } from "../types/forms";
import { buildWorkerPayload } from "../utils/payloadMappers";
import {
  showApiErrorNotification,
  showSuccessNotification,
} from "../utils/notifications";

const WORKERS_QUERY_KEY = ["control-plane-admin", "workers"] as const;

export function useWorkersAdmin() {
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
      children: `Se eliminará el worker administrativo ${worker.name}.`,
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

  return {
    workersQuery,
    workerBeingEdited,
    isModalOpen,
    isSaving: createWorkerMutation.isPending || updateWorkerMutation.isPending,
    isDeleting: deleteWorkerMutation.isPending,
    openCreateModal,
    openEditModal,
    closeModal,
    handleSubmit,
    openDeleteConfirmation,
  };
}
