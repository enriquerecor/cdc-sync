import {
  ActionIcon,
  Badge,
  Button,
  Group,
  Modal,
  NumberInput,
  PasswordInput,
  ScrollArea,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Tooltip,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { modals } from "@mantine/modals";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { useState } from "react";

import { normalizeApiError } from "../api/errors";
import {
  createSourceConnection,
  deleteSourceConnection,
  listSourceConnections,
  updateSourceConnection,
  type SourceConnection,
  type SourceConnectionCreateRequest,
  type SourceConnectionUpdateRequest,
} from "../api/controlPlaneAdmin";
import { AdministrativeViewHeader } from "../components/AdministrativeViewHeader";
import { ErrorState, LoadingState } from "../components/FeedbackState";
import {
  SOURCE_ENGINE_DEFINITIONS,
  findEngineDefinition,
  getEngineOptions,
  requireEnabledEngineDefinition,
} from "./engineDefinitions";
import {
  buildSourceCredentials,
  getValidatedPort,
  requiredText,
  validateCredentialsPassword,
  validateCredentialsUser,
  validatePort,
  type CredentialsFormValues,
  type EntityFormMode,
} from "./formHelpers";
import {
  showApiErrorNotification,
  showFormErrorNotification,
  showSuccessNotification,
} from "./notificationHelpers";

const SOURCE_CONNECTIONS_QUERY_KEY = [
  "control-plane-admin",
  "source-connections",
] as const;
const DEFAULT_SOURCE_TYPE = "postgresql";
const SOURCE_ENGINE_OPTIONS = getEngineOptions(SOURCE_ENGINE_DEFINITIONS);

type SourceConnectionFormValues = CredentialsFormValues & {
  name: string;
  sourceType: string;
  host: string;
  port: number | "";
  databaseName: string;
};

type SourceConnectionFormProps = {
  sourceConnection: SourceConnection | null;
  isSaving: boolean;
  onCancel: () => void;
  onSubmit: (values: SourceConnectionFormValues) => void;
};

export function SourceConnectionsView() {
  const queryClient = useQueryClient();
  const [sourceConnectionBeingEdited, setSourceConnectionBeingEdited] =
    useState<SourceConnection | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const sourceConnectionsQuery = useQuery({
    queryKey: SOURCE_CONNECTIONS_QUERY_KEY,
    queryFn: listSourceConnections,
  });

  const createSourceConnectionMutation = useMutation({
    mutationFn: createSourceConnection,
    onSuccess: () => {
      closeModal();
      void queryClient.invalidateQueries({
        queryKey: SOURCE_CONNECTIONS_QUERY_KEY,
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
        queryKey: SOURCE_CONNECTIONS_QUERY_KEY,
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
        queryKey: SOURCE_CONNECTIONS_QUERY_KEY,
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
      return;
    }
  }

  function openDeleteConfirmation(sourceConnection: SourceConnection): void {
    modals.openConfirmModal({
      title: "Eliminar origen",
      children: (
        <Text size="sm">
          Se eliminará el origen administrativo {sourceConnection.name}.
        </Text>
      ),
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
        sourceConnections: sourceConnectionsQuery.data,
        isLoading: sourceConnectionsQuery.isPending,
        error: sourceConnectionsQuery.error,
        refetch: sourceConnectionsQuery.refetch,
        openEditModal,
        openDeleteConfirmation,
        isDeleting: deleteSourceConnectionMutation.isPending,
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
          isSaving={
            createSourceConnectionMutation.isPending ||
            updateSourceConnectionMutation.isPending
          }
          onCancel={closeModal}
          onSubmit={handleSubmit}
        />
      </Modal>
    </Stack>
  );
}

function SourceConnectionForm({
  sourceConnection,
  isSaving,
  onCancel,
  onSubmit,
}: SourceConnectionFormProps) {
  const mode: EntityFormMode = sourceConnection ? "edit" : "create";
  const form = useForm<SourceConnectionFormValues>({
    initialValues: {
      name: sourceConnection?.name ?? "",
      sourceType: sourceConnection?.source_type ?? DEFAULT_SOURCE_TYPE,
      host: sourceConnection?.host ?? "",
      port: sourceConnection?.port ?? getDefaultSourcePort(),
      databaseName: sourceConnection?.database_name ?? "",
      credentialsUser: "",
      credentialsPassword: "",
    },
    validate: {
      name: requiredText,
      sourceType: requiredText,
      host: requiredText,
      port: validatePort,
      databaseName: requiredText,
      credentialsUser: (value, values) =>
        validateCredentialsUser(value, values, mode),
      credentialsPassword: (value, values) =>
        validateCredentialsPassword(value, values, mode),
    },
  });
  const selectedEngine = findEngineDefinition(
    SOURCE_ENGINE_DEFINITIONS,
    form.values.sourceType,
  );

  function handleSourceTypeChange(value: string | null): void {
    if (!value) {
      return;
    }

    const definition = findEngineDefinition(SOURCE_ENGINE_DEFINITIONS, value);

    if (!definition) {
      form.setFieldError("sourceType", "Motor desconocido");
      return;
    }

    if (!definition.enabled) {
      form.setFieldError("sourceType", "Motor no soportado todavía");
      return;
    }

    form.setFieldValue("sourceType", definition.value);
    form.setFieldValue("port", definition.defaultPort);
  }

  return (
    <form onSubmit={form.onSubmit(onSubmit)}>
      <Stack gap="md">
        <TextInput
          label="Nombre"
          placeholder="Origen operacional"
          withAsterisk
          {...form.getInputProps("name")}
        />
        <Select
          label="Motor"
          data={SOURCE_ENGINE_OPTIONS}
          value={form.values.sourceType}
          onChange={handleSourceTypeChange}
          withAsterisk
          error={form.errors.sourceType}
        />
        <TextInput
          label="Host"
          placeholder="db.internal"
          withAsterisk
          {...form.getInputProps("host")}
        />
        <NumberInput
          label="Puerto"
          min={1}
          max={65535}
          withAsterisk
          {...form.getInputProps("port")}
        />
        <TextInput
          label={selectedEngine?.databaseLabel ?? "Base de datos"}
          placeholder="cdc_sync"
          withAsterisk
          {...form.getInputProps("databaseName")}
        />
        <Text fw={500} size="sm">
          {selectedEngine?.credentialsLabel ?? "Credenciales"}
        </Text>
        <TextInput
          label="Usuario"
          autoComplete="off"
          withAsterisk={mode === "create"}
          {...form.getInputProps("credentialsUser")}
        />
        <PasswordInput
          label={mode === "create" ? "Contraseña" : "Nueva contraseña"}
          autoComplete="new-password"
          withAsterisk={mode === "create"}
          {...form.getInputProps("credentialsPassword")}
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

type SourceConnectionsContentProps = {
  sourceConnections: SourceConnection[] | undefined;
  isLoading: boolean;
  error: unknown;
  refetch: () => void;
  openEditModal: (sourceConnection: SourceConnection) => void;
  openDeleteConfirmation: (sourceConnection: SourceConnection) => void;
  isDeleting: boolean;
};

function renderSourceConnectionsContent({
  sourceConnections,
  isLoading,
  error,
  refetch,
  openEditModal,
  openDeleteConfirmation,
  isDeleting,
}: SourceConnectionsContentProps) {
  if (isLoading) {
    return <LoadingState message="Cargando orígenes" />;
  }

  if (error) {
    const apiError = normalizeApiError(error);

    return (
      <ErrorState
        title="No se pudieron cargar los orígenes"
        message={apiError.message}
        onRetry={refetch}
      />
    );
  }

  if (!sourceConnections || sourceConnections.length === 0) {
    return (
      <Text c="dimmed" size="sm">
        Todavía no hay orígenes registrados.
      </Text>
    );
  }

  return (
    <ScrollArea>
      <Table striped highlightOnHover withTableBorder verticalSpacing="sm">
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Nombre</Table.Th>
            <Table.Th>Motor</Table.Th>
            <Table.Th>Host</Table.Th>
            <Table.Th>Base</Table.Th>
            <Table.Th>Credenciales</Table.Th>
            <Table.Th ta="right">Acciones</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {sourceConnections.map((sourceConnection) => (
            <Table.Tr key={sourceConnection.id}>
              <Table.Td>
                <Text fw={500}>{sourceConnection.name}</Text>
              </Table.Td>
              <Table.Td>
                <Badge variant="light">
                  {getSourceEngineLabel(sourceConnection.source_type)}
                </Badge>
              </Table.Td>
              <Table.Td>
                {sourceConnection.host}:{sourceConnection.port}
              </Table.Td>
              <Table.Td>{sourceConnection.database_name}</Table.Td>
              <Table.Td>
                <Badge
                  color={sourceConnection.credentials_configured ? "teal" : "red"}
                  variant="light"
                >
                  {sourceConnection.credentials_configured
                    ? "Configuradas"
                    : "Pendientes"}
                </Badge>
              </Table.Td>
              <Table.Td>
                <Group justify="flex-end" gap="xs" wrap="nowrap">
                  <Tooltip label="Editar origen">
                    <ActionIcon
                      variant="subtle"
                      aria-label="Editar origen"
                      onClick={() => openEditModal(sourceConnection)}
                    >
                      <Pencil size={16} strokeWidth={1.8} />
                    </ActionIcon>
                  </Tooltip>
                  <Tooltip label="Eliminar origen">
                    <ActionIcon
                      color="red"
                      variant="subtle"
                      aria-label="Eliminar origen"
                      loading={isDeleting}
                      onClick={() => openDeleteConfirmation(sourceConnection)}
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

function buildSourceConnectionCreatePayload(
  values: SourceConnectionFormValues,
): SourceConnectionCreateRequest {
  const basePayload = buildSourceConnectionBasePayload(values);
  const credentials = buildSourceCredentials(values, "create");

  if (!credentials) {
    throw new Error("Las credenciales del origen son obligatorias");
  }

  return {
    ...basePayload,
    credentials,
  };
}

function buildSourceConnectionUpdatePayload(
  values: SourceConnectionFormValues,
): SourceConnectionUpdateRequest {
  const basePayload = buildSourceConnectionBasePayload(values);
  const credentials = buildSourceCredentials(values, "edit");

  if (!credentials) {
    return basePayload;
  }

  return {
    ...basePayload,
    credentials,
  };
}

function buildSourceConnectionBasePayload(
  values: SourceConnectionFormValues,
): Omit<SourceConnectionUpdateRequest, "credentials"> {
  const engine = requireEnabledEngineDefinition(
    SOURCE_ENGINE_DEFINITIONS,
    values.sourceType,
  );
  const port = getValidatedPort(values.port);

  return {
    name: values.name.trim(),
    source_type: engine.value,
    host: values.host.trim(),
    port,
    database_name: values.databaseName.trim(),
  };
}

function getSourceEngineLabel(sourceType: string): string {
  return (
    findEngineDefinition(SOURCE_ENGINE_DEFINITIONS, sourceType)?.label ??
    sourceType
  );
}

function getDefaultSourcePort(): number {
  return requireEnabledEngineDefinition(
    SOURCE_ENGINE_DEFINITIONS,
    DEFAULT_SOURCE_TYPE,
  ).defaultPort;
}
