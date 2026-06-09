import { Modal, Stack, Tabs, Text } from "@mantine/core";
import { Plus } from "lucide-react";

import { normalizeApiError } from "../api/errors";
import { AdministrativeViewHeader } from "../components/AdministrativeViewHeader";
import { ErrorState, LoadingState } from "../components/FeedbackState";
import { AssignmentPanel } from "./admin/components/configurations/AssignmentPanel";
import { CdcMaterializationPanel } from "./admin/components/configurations/CdcMaterializationPanel";
import { ConfigurationsTable } from "./admin/components/configurations/ConfigurationsTable";
import { RuntimeConfigPanel } from "./admin/components/configurations/RuntimeConfigPanel";
import { SyncConfigForm } from "./admin/components/configurations/SyncConfigForm";
import { useConfigPublication } from "./admin/hooks/useConfigPublication";
import { useSyncConfigsAdmin } from "./admin/hooks/useSyncConfigsAdmin";

export function ConfigurationsView() {
  const syncConfigsAdmin = useSyncConfigsAdmin();
  const configPublication = useConfigPublication();

  return (
    <Stack gap="lg">
      <AdministrativeViewHeader
        title="Configuraciones"
        description="Define tablas, claves primarias, publicación CDC y contrato runtime para cada worker."
        actionLabel="Crear configuración"
        actionIcon={Plus}
        onAction={syncConfigsAdmin.openCreateModal}
      />

      <Tabs defaultValue="configs" keepMounted={false}>
        <Tabs.List>
          <Tabs.Tab value="configs">Configuraciones</Tabs.Tab>
          <Tabs.Tab value="assignment">Asignación</Tabs.Tab>
          <Tabs.Tab value="cdc">CDC</Tabs.Tab>
          <Tabs.Tab value="runtime">Runtime</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="configs" pt="lg">
          {renderConfigurationsContent(syncConfigsAdmin)}
        </Tabs.Panel>

        <Tabs.Panel value="assignment" pt="lg">
          {renderAssignmentContent(configPublication)}
        </Tabs.Panel>

        <Tabs.Panel value="cdc" pt="lg">
          {renderMaterializationContent(configPublication)}
        </Tabs.Panel>

        <Tabs.Panel value="runtime" pt="lg">
          {renderRuntimeContent(configPublication)}
        </Tabs.Panel>
      </Tabs>

      <Modal
        opened={syncConfigsAdmin.isModalOpen}
        onClose={syncConfigsAdmin.closeModal}
        title={
          syncConfigsAdmin.configBeingEdited
            ? "Editar configuración"
            : "Crear configuración"
        }
        size="xl"
      >
        <SyncConfigForm
          key={syncConfigsAdmin.configBeingEdited?.id ?? "new-sync-config"}
          config={syncConfigsAdmin.configBeingEdited}
          sourceConnections={syncConfigsAdmin.sourceConnectionsQuery.data ?? []}
          destinations={syncConfigsAdmin.destinationsQuery.data ?? []}
          isSaving={syncConfigsAdmin.isSaving}
          onCancel={syncConfigsAdmin.closeModal}
          onSubmit={syncConfigsAdmin.handleSubmit}
        />
      </Modal>
    </Stack>
  );
}

type SyncConfigsAdminState = ReturnType<typeof useSyncConfigsAdmin>;
type ConfigPublicationState = ReturnType<typeof useConfigPublication>;

function renderConfigurationsContent(syncConfigsAdmin: SyncConfigsAdminState) {
  const {
    syncConfigsQuery,
    sourceConnectionsQuery,
    destinationsQuery,
    isDeleting,
    openEditModal,
    openDeleteConfirmation,
  } = syncConfigsAdmin;

  if (
    syncConfigsQuery.isPending ||
    sourceConnectionsQuery.isPending ||
    destinationsQuery.isPending
  ) {
    return <LoadingState message="Cargando configuraciones" />;
  }

  const error =
    syncConfigsQuery.error ??
    sourceConnectionsQuery.error ??
    destinationsQuery.error;
  if (error) {
    const apiError = normalizeApiError(error);

    return (
      <ErrorState
        title="No se pudieron cargar las configuraciones"
        message={apiError.message}
        onRetry={() => {
          void syncConfigsQuery.refetch();
          void sourceConnectionsQuery.refetch();
          void destinationsQuery.refetch();
        }}
      />
    );
  }

  if (!syncConfigsQuery.data || syncConfigsQuery.data.length === 0) {
    return (
      <Text c="dimmed" size="sm">
        Todavía no hay configuraciones registradas.
      </Text>
    );
  }

  return (
    <ConfigurationsTable
      configs={syncConfigsQuery.data}
      sourceConnections={sourceConnectionsQuery.data ?? []}
      destinations={destinationsQuery.data ?? []}
      isDeleting={isDeleting}
      onEdit={openEditModal}
      onDelete={openDeleteConfirmation}
    />
  );
}

function renderAssignmentContent(configPublication: ConfigPublicationState) {
  const { workersQuery, syncConfigsQuery } = configPublication;

  if (workersQuery.isPending || syncConfigsQuery.isPending) {
    return <LoadingState message="Cargando datos de publicación" />;
  }

  const error = workersQuery.error ?? syncConfigsQuery.error;
  if (error) {
    const apiError = normalizeApiError(error);

    return (
      <ErrorState
        title="No se pudieron cargar los datos de publicación"
        message={apiError.message}
        onRetry={() => {
          void workersQuery.refetch();
          void syncConfigsQuery.refetch();
        }}
      />
    );
  }

  return (
    <AssignmentPanel
      workers={workersQuery.data ?? []}
      configs={syncConfigsQuery.data ?? []}
      assignment={configPublication.assignment}
      isAssigning={configPublication.isAssigning}
      onSubmit={configPublication.assignConfig}
    />
  );
}

function renderMaterializationContent(configPublication: ConfigPublicationState) {
  const { sourceConnectionsQuery } = configPublication;

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

  return (
    <CdcMaterializationPanel
      sourceConnections={sourceConnectionsQuery.data ?? []}
      materializedConnector={configPublication.materializedConnector}
      isMaterializing={configPublication.isMaterializing}
      onSubmit={configPublication.materializeConnector}
    />
  );
}

function renderRuntimeContent(configPublication: ConfigPublicationState) {
  const { workersQuery } = configPublication;

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

  return (
    <RuntimeConfigPanel
      workers={workersQuery.data ?? []}
      runtimeConfig={configPublication.runtimeConfig}
      isLoadingRuntime={configPublication.isLoadingRuntime}
      onSubmit={configPublication.loadRuntimeConfig}
    />
  );
}
