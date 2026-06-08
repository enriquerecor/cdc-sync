import { modals } from "@mantine/modals";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import {
  createSourceConnection,
  deleteSourceConnection,
  listSourceConnections,
  updateSourceConnection,
  type SourceConnection,
  type SourceConnectionUpdateRequest,
} from "../../../api/controlPlaneAdmin";
import type { SourceConnectionFormValues } from "../types/forms";
import {
  showApiErrorNotification,
  showFormErrorNotification,
  showSuccessNotification,
} from "../utils/notifications";
import {
  buildSourceConnectionCreatePayload,
  buildSourceConnectionUpdatePayload,
} from "../utils/payloadMappers";
import { CONTROL_PLANE_QUERY_KEYS } from "../utils/queryKeys";

export function useSourceConnectionsAdmin() {
  const queryClient = useQueryClient();
  const [sourceConnectionBeingEdited, setSourceConnectionBeingEdited] =
    useState<SourceConnection | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const sourceConnectionsQuery = useQuery({
    queryKey: CONTROL_PLANE_QUERY_KEYS.sourceConnections,
    queryFn: listSourceConnections,
  });

  const createSourceConnectionMutation = useMutation({
    mutationFn: createSourceConnection,
    onSuccess: () => {
      closeModal();
      void queryClient.invalidateQueries({
        queryKey: CONTROL_PLANE_QUERY_KEYS.sourceConnections,
      });
      showSuccessNotification("Origen creado", "El origen se guardó correctamente");
    },
    onError: showApiErrorNotification,
  });

  const updateSourceConnectionMutation = useMutation({
    mutationFn: ({
      sourceConnectionId,
      payload,
    }: {
      sourceConnectionId: string;
      payload: SourceConnectionUpdateRequest;
    }) => updateSourceConnection(sourceConnectionId, payload),
    onSuccess: () => {
      closeModal();
      void queryClient.invalidateQueries({
        queryKey: CONTROL_PLANE_QUERY_KEYS.sourceConnections,
      });
      showSuccessNotification(
        "Origen actualizado",
        "Los cambios se guardaron correctamente",
      );
    },
    onError: showApiErrorNotification,
  });

  const deleteSourceConnectionMutation = useMutation({
    mutationFn: deleteSourceConnection,
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: CONTROL_PLANE_QUERY_KEYS.sourceConnections,
      });
      showSuccessNotification("Origen eliminado", "El origen se eliminó");
    },
    onError: showApiErrorNotification,
  });

  function openCreateModal(): void {
    setSourceConnectionBeingEdited(null);
    setIsModalOpen(true);
  }

  function openEditModal(sourceConnection: SourceConnection): void {
    setSourceConnectionBeingEdited(sourceConnection);
    setIsModalOpen(true);
  }

  function closeModal(): void {
    setIsModalOpen(false);
    setSourceConnectionBeingEdited(null);
  }

  function handleSubmit(values: SourceConnectionFormValues): void {
    try {
      if (sourceConnectionBeingEdited) {
        updateSourceConnectionMutation.mutate({
          sourceConnectionId: sourceConnectionBeingEdited.id,
          payload: buildSourceConnectionUpdatePayload(values),
        });
        return;
      }

      createSourceConnectionMutation.mutate(
        buildSourceConnectionCreatePayload(values),
      );
    } catch (error) {
      showFormErrorNotification(error);
    }
  }

  function openDeleteConfirmation(sourceConnection: SourceConnection): void {
    modals.openConfirmModal({
      title: "Eliminar origen",
      children: `Se eliminará el origen administrativo ${sourceConnection.name}.`,
      labels: {
        confirm: "Eliminar",
        cancel: "Cancelar",
      },
      confirmProps: {
        color: "red",
      },
      onConfirm: () => deleteSourceConnectionMutation.mutate(sourceConnection.id),
    });
  }

  return {
    sourceConnectionsQuery,
    sourceConnectionBeingEdited,
    isModalOpen,
    isSaving:
      createSourceConnectionMutation.isPending ||
      updateSourceConnectionMutation.isPending,
    isDeleting: deleteSourceConnectionMutation.isPending,
    openCreateModal,
    openEditModal,
    closeModal,
    handleSubmit,
    openDeleteConfirmation,
  };
}
