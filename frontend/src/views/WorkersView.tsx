import { Modal, Stack, Text } from "@mantine/core";
import { Plus } from "lucide-react";

import { normalizeApiError } from "../api/errors";
import { AdministrativeViewHeader } from "../components/AdministrativeViewHeader";
import { ErrorState, LoadingState } from "../components/FeedbackState";
import { WorkerForm } from "./admin/components/WorkerForm";
import { WorkersTable } from "./admin/components/WorkersTable";
import { useWorkersAdmin } from "./admin/hooks/useWorkersAdmin";

export function WorkersView() {
  const {
    workersQuery,
    workerBeingEdited,
    isModalOpen,
    isSaving,
    isDeleting,
    openCreateModal,
    openEditModal,
    closeModal,
    handleSubmit,
    openDeleteConfirmation,
  } = useWorkersAdmin();

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
        workersQuery,
        isDeleting,
        openEditModal,
        openDeleteConfirmation,
      })}

      <Modal
        opened={isModalOpen}
        onClose={closeModal}
        title={workerBeingEdited ? "Editar worker" : "Crear worker"}
      >
        <WorkerForm
          key={workerBeingEdited?.id ?? "new-worker"}
          worker={workerBeingEdited}
          isSaving={isSaving}
          onCancel={closeModal}
          onSubmit={handleSubmit}
        />
      </Modal>
    </Stack>
  );
}

type WorkersContentProps = {
  workersQuery: ReturnType<typeof useWorkersAdmin>["workersQuery"];
  isDeleting: boolean;
  openEditModal: ReturnType<typeof useWorkersAdmin>["openEditModal"];
  openDeleteConfirmation: ReturnType<
    typeof useWorkersAdmin
  >["openDeleteConfirmation"];
};

function renderWorkersContent({
  workersQuery,
  isDeleting,
  openEditModal,
  openDeleteConfirmation,
}: WorkersContentProps) {
  if (workersQuery.isPending) {
    return <LoadingState message="Cargando workers" />;
  }

  if (workersQuery.error) {
    const apiError = normalizeApiError(workersQuery.error);

    return (
      <ErrorState
        title="No se pudieron cargar los workers"
        message={apiError.message}
        onRetry={() => void workersQuery.refetch()}
      />
    );
  }

  if (!workersQuery.data || workersQuery.data.length === 0) {
    return (
      <Text c="dimmed" size="sm">
        Todavía no hay workers registrados.
      </Text>
    );
  }

  return (
    <WorkersTable
      workers={workersQuery.data}
      isDeleting={isDeleting}
      onEdit={openEditModal}
      onDelete={openDeleteConfirmation}
    />
  );
}
