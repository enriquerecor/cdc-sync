import { Modal, Stack, Text } from "@mantine/core";
import { Plus } from "lucide-react";

import { normalizeApiError } from "../api/errors";
import { AdministrativeViewHeader } from "../components/AdministrativeViewHeader";
import { ErrorState, LoadingState } from "../components/FeedbackState";
import { SourceConnectionForm } from "./admin/components/SourceConnectionForm";
import { SourceConnectionsTable } from "./admin/components/SourceConnectionsTable";
import { useSourceConnectionsAdmin } from "./admin/hooks/useSourceConnectionsAdmin";

export function SourceConnectionsView() {
  const {
    sourceConnectionsQuery,
    sourceConnectionBeingEdited,
    isModalOpen,
    isSaving,
    isDeleting,
    openCreateModal,
    openEditModal,
    closeModal,
    handleSubmit,
    openDeleteConfirmation,
  } = useSourceConnectionsAdmin();

  return (
    <Stack gap="lg">
      <AdministrativeViewHeader
        title="Orígenes de datos"
        description="Gestiona conexiones transaccionales desde las que se capturan cambios."
        actionLabel="Crear origen"
        actionIcon={Plus}
        onAction={openCreateModal}
      />

      {renderSourceConnectionsContent({
        sourceConnectionsQuery,
        isDeleting,
        openEditModal,
        openDeleteConfirmation,
      })}

      <Modal
        opened={isModalOpen}
        onClose={closeModal}
        title={
          sourceConnectionBeingEdited ? "Editar origen" : "Crear origen"
        }
      >
        <SourceConnectionForm
          key={sourceConnectionBeingEdited?.id ?? "new-source-connection"}
          sourceConnection={sourceConnectionBeingEdited}
          isSaving={isSaving}
          onCancel={closeModal}
          onSubmit={handleSubmit}
        />
      </Modal>
    </Stack>
  );
}

type SourceConnectionsContentProps = {
  sourceConnectionsQuery: ReturnType<
    typeof useSourceConnectionsAdmin
  >["sourceConnectionsQuery"];
  isDeleting: boolean;
  openEditModal: ReturnType<typeof useSourceConnectionsAdmin>["openEditModal"];
  openDeleteConfirmation: ReturnType<
    typeof useSourceConnectionsAdmin
  >["openDeleteConfirmation"];
};

function renderSourceConnectionsContent({
  sourceConnectionsQuery,
  isDeleting,
  openEditModal,
  openDeleteConfirmation,
}: SourceConnectionsContentProps) {
  if (sourceConnectionsQuery.isPending) {
    return <LoadingState message="Cargando orígenes" />;
  }

  if (sourceConnectionsQuery.error) {
    const apiError = normalizeApiError(sourceConnectionsQuery.error);

    return (
      <ErrorState
        title="No se pudieron cargar los orígenes"
        message={apiError.message}
        onRetry={() => void sourceConnectionsQuery.refetch()}
      />
    );
  }

  if (!sourceConnectionsQuery.data || sourceConnectionsQuery.data.length === 0) {
    return (
      <Text c="dimmed" size="sm">
        Todavía no hay orígenes registrados.
      </Text>
    );
  }

  return (
    <SourceConnectionsTable
      sourceConnections={sourceConnectionsQuery.data}
      isDeleting={isDeleting}
      onEdit={openEditModal}
      onDelete={openDeleteConfirmation}
    />
  );
}
