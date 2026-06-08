import { modals } from "@mantine/modals";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import {
  createDestination,
  deleteDestination,
  listDestinations,
  updateDestination,
  type Destination,
  type DestinationUpdateRequest,
} from "../../../api/controlPlaneAdmin";
import type { DestinationFormValues } from "../types/forms";
import {
  showApiErrorNotification,
  showFormErrorNotification,
  showSuccessNotification,
} from "../utils/notifications";
import {
  buildDestinationCreatePayload,
  buildDestinationUpdatePayload,
} from "../utils/payloadMappers";
import { CONTROL_PLANE_QUERY_KEYS } from "../utils/queryKeys";

export function useDestinationsAdmin() {
  const queryClient = useQueryClient();
  const [destinationBeingEdited, setDestinationBeingEdited] =
    useState<Destination | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const destinationsQuery = useQuery({
    queryKey: CONTROL_PLANE_QUERY_KEYS.destinations,
    queryFn: listDestinations,
  });

  const createDestinationMutation = useMutation({
    mutationFn: createDestination,
    onSuccess: () => {
      closeModal();
      void queryClient.invalidateQueries({
        queryKey: CONTROL_PLANE_QUERY_KEYS.destinations,
      });
      showSuccessNotification(
        "Destino creado",
        "El destino se guardó correctamente",
      );
    },
    onError: showApiErrorNotification,
  });

  const updateDestinationMutation = useMutation({
    mutationFn: ({
      destinationId,
      payload,
    }: {
      destinationId: string;
      payload: DestinationUpdateRequest;
    }) => updateDestination(destinationId, payload),
    onSuccess: () => {
      closeModal();
      void queryClient.invalidateQueries({
        queryKey: CONTROL_PLANE_QUERY_KEYS.destinations,
      });
      showSuccessNotification(
        "Destino actualizado",
        "Los cambios se guardaron correctamente",
      );
    },
    onError: showApiErrorNotification,
  });

  const deleteDestinationMutation = useMutation({
    mutationFn: deleteDestination,
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: CONTROL_PLANE_QUERY_KEYS.destinations,
      });
      showSuccessNotification("Destino eliminado", "El destino se eliminó");
    },
    onError: showApiErrorNotification,
  });

  function openCreateModal(): void {
    setDestinationBeingEdited(null);
    setIsModalOpen(true);
  }

  function openEditModal(destination: Destination): void {
    setDestinationBeingEdited(destination);
    setIsModalOpen(true);
  }

  function closeModal(): void {
    setIsModalOpen(false);
    setDestinationBeingEdited(null);
  }

  function handleSubmit(values: DestinationFormValues): void {
    try {
      if (destinationBeingEdited) {
        updateDestinationMutation.mutate({
          destinationId: destinationBeingEdited.id,
          payload: buildDestinationUpdatePayload(values),
        });
        return;
      }

      createDestinationMutation.mutate(buildDestinationCreatePayload(values));
    } catch (error) {
      showFormErrorNotification(error);
    }
  }

  function openDeleteConfirmation(destination: Destination): void {
    modals.openConfirmModal({
      title: "Eliminar destino",
      children: `Se eliminará el destino administrativo ${destination.name}.`,
      labels: {
        confirm: "Eliminar",
        cancel: "Cancelar",
      },
      confirmProps: {
        color: "red",
      },
      onConfirm: () => deleteDestinationMutation.mutate(destination.id),
    });
  }

  return {
    destinationsQuery,
    destinationBeingEdited,
    isModalOpen,
    isSaving:
      createDestinationMutation.isPending ||
      updateDestinationMutation.isPending,
    isDeleting: deleteDestinationMutation.isPending,
    openCreateModal,
    openEditModal,
    closeModal,
    handleSubmit,
    openDeleteConfirmation,
  };
}
