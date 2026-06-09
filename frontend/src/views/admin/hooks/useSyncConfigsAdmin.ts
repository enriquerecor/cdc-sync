import { modals } from "@mantine/modals";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import {
  createSyncConfig,
  deleteSyncConfig,
  listDestinations,
  listSourceConnections,
  listSyncConfigs,
  updateSyncConfig,
  type SyncConfig,
  type SyncConfigRequest,
} from "../../../api/controlPlaneAdmin";
import type { SyncConfigFormValues } from "../types/forms";
import {
  showApiErrorNotification,
  showFormErrorNotification,
  showSuccessNotification,
} from "../utils/notifications";
import { buildSyncConfigPayload } from "../utils/payloadMappers";
import { CONTROL_PLANE_QUERY_KEYS } from "../utils/queryKeys";

export function useSyncConfigsAdmin() {
  const queryClient = useQueryClient();
  const [configBeingEdited, setConfigBeingEdited] = useState<SyncConfig | null>(
    null,
  );
  const [isModalOpen, setIsModalOpen] = useState(false);

  const syncConfigsQuery = useQuery({
    queryKey: CONTROL_PLANE_QUERY_KEYS.syncConfigs,
    queryFn: listSyncConfigs,
  });
  const sourceConnectionsQuery = useQuery({
    queryKey: CONTROL_PLANE_QUERY_KEYS.sourceConnections,
    queryFn: listSourceConnections,
  });
  const destinationsQuery = useQuery({
    queryKey: CONTROL_PLANE_QUERY_KEYS.destinations,
    queryFn: listDestinations,
  });

  const createSyncConfigMutation = useMutation({
    mutationFn: createSyncConfig,
    onSuccess: () => {
      closeModal();
      void queryClient.invalidateQueries({
        queryKey: CONTROL_PLANE_QUERY_KEYS.syncConfigs,
      });
      showSuccessNotification(
        "Configuración creada",
        "La configuración se guardó correctamente",
      );
    },
    onError: showApiErrorNotification,
  });

  const updateSyncConfigMutation = useMutation({
    mutationFn: ({
      configId,
      payload,
    }: {
      configId: string;
      payload: SyncConfigRequest;
    }) => updateSyncConfig(configId, payload),
    onSuccess: () => {
      closeModal();
      void queryClient.invalidateQueries({
        queryKey: CONTROL_PLANE_QUERY_KEYS.syncConfigs,
      });
      showSuccessNotification(
        "Configuración actualizada",
        "El agregado se reemplazó correctamente",
      );
    },
    onError: showApiErrorNotification,
  });

  const deleteSyncConfigMutation = useMutation({
    mutationFn: deleteSyncConfig,
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: CONTROL_PLANE_QUERY_KEYS.syncConfigs,
      });
      showSuccessNotification(
        "Configuración eliminada",
        "La configuración se eliminó",
      );
    },
    onError: showApiErrorNotification,
  });

  function openCreateModal(): void {
    setConfigBeingEdited(null);
    setIsModalOpen(true);
  }

  function openEditModal(config: SyncConfig): void {
    setConfigBeingEdited(config);
    setIsModalOpen(true);
  }

  function closeModal(): void {
    setIsModalOpen(false);
    setConfigBeingEdited(null);
  }

  function handleSubmit(values: SyncConfigFormValues): void {
    try {
      const payload = buildSyncConfigPayload(values);

      if (configBeingEdited) {
        updateSyncConfigMutation.mutate({
          configId: configBeingEdited.id,
          payload,
        });
        return;
      }

      createSyncConfigMutation.mutate(payload);
    } catch (error) {
      showFormErrorNotification(error);
    }
  }

  function openDeleteConfirmation(config: SyncConfig): void {
    modals.openConfirmModal({
      title: "Eliminar configuración",
      children: `Se eliminará la configuración administrativa ${config.name}.`,
      labels: {
        confirm: "Eliminar",
        cancel: "Cancelar",
      },
      confirmProps: {
        color: "red",
      },
      onConfirm: () => deleteSyncConfigMutation.mutate(config.id),
    });
  }

  return {
    syncConfigsQuery,
    sourceConnectionsQuery,
    destinationsQuery,
    configBeingEdited,
    isModalOpen,
    isSaving:
      createSyncConfigMutation.isPending ||
      updateSyncConfigMutation.isPending,
    isDeleting: deleteSyncConfigMutation.isPending,
    openCreateModal,
    openEditModal,
    closeModal,
    handleSubmit,
    openDeleteConfirmation,
  };
}
