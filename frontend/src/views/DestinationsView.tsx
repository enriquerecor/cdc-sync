import { Modal, Stack, Text } from "@mantine/core";
import { Plus } from "lucide-react";

import { normalizeApiError } from "../api/errors";
import { AdministrativeViewHeader } from "../components/AdministrativeViewHeader";
import { ErrorState, LoadingState } from "../components/FeedbackState";
import { DestinationForm } from "./admin/components/DestinationForm";
import { DestinationsTable } from "./admin/components/DestinationsTable";
import { useDestinationsAdmin } from "./admin/hooks/useDestinationsAdmin";

export function DestinationsView() {
  const {
    destinationsQuery,
    destinationBeingEdited,
    isModalOpen,
    isSaving,
    isDeleting,
    openCreateModal,
    openEditModal,
    closeModal,
    handleSubmit,
    openDeleteConfirmation,
  } = useDestinationsAdmin();

  return (
    <Stack gap="lg">
      <AdministrativeViewHeader
        title="Destinos analíticos"
        description="Gestiona almacenes analíticos donde se publican los cambios sincronizados."
        actionLabel="Crear destino"
        actionIcon={Plus}
        onAction={openCreateModal}
      />

      {renderDestinationsContent({
        destinationsQuery,
        isDeleting,
        openEditModal,
        openDeleteConfirmation,
      })}

      <Modal
        opened={isModalOpen}
        onClose={closeModal}
        title={destinationBeingEdited ? "Editar destino" : "Crear destino"}
      >
        <DestinationForm
          key={destinationBeingEdited?.id ?? "new-destination"}
          destination={destinationBeingEdited}
          isSaving={isSaving}
          onCancel={closeModal}
          onSubmit={handleSubmit}
        />
      </Modal>
    </Stack>
  );
}

type DestinationsContentProps = {
  destinationsQuery: ReturnType<
    typeof useDestinationsAdmin
  >["destinationsQuery"];
  isDeleting: boolean;
  openEditModal: ReturnType<typeof useDestinationsAdmin>["openEditModal"];
  openDeleteConfirmation: ReturnType<
    typeof useDestinationsAdmin
  >["openDeleteConfirmation"];
};

function renderDestinationsContent({
  destinationsQuery,
  isDeleting,
  openEditModal,
  openDeleteConfirmation,
}: DestinationsContentProps) {
  if (destinationsQuery.isPending) {
    return <LoadingState message="Cargando destinos" />;
  }

  if (destinationsQuery.error) {
    const apiError = normalizeApiError(destinationsQuery.error);

    return (
      <ErrorState
        title="No se pudieron cargar los destinos"
        message={apiError.message}
        onRetry={() => void destinationsQuery.refetch()}
      />
    );
  }

  if (!destinationsQuery.data || destinationsQuery.data.length === 0) {
    return (
      <Text c="dimmed" size="sm">
        Todavía no hay destinos registrados.
      </Text>
    );
  }

  return (
    <DestinationsTable
      destinations={destinationsQuery.data}
      isDeleting={isDeleting}
      onEdit={openEditModal}
      onDelete={openDeleteConfirmation}
    />
  );
}
