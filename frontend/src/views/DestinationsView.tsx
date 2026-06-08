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
  Switch,
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
  createDestination,
  deleteDestination,
  listDestinations,
  updateDestination,
  type Destination,
  type DestinationCreateRequest,
  type DestinationUpdateRequest,
} from "../api/controlPlaneAdmin";
import { AdministrativeViewHeader } from "../components/AdministrativeViewHeader";
import { ErrorState, LoadingState } from "../components/FeedbackState";
import {
  DESTINATION_ENGINE_DEFINITIONS,
  findEngineDefinition,
  getEngineOptions,
  requireEnabledEngineDefinition,
} from "./engineDefinitions";
import {
  buildDestinationCredentials,
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

const DESTINATIONS_QUERY_KEY = ["control-plane-admin", "destinations"] as const;
const DEFAULT_DESTINATION_TYPE = "clickhouse";
const DESTINATION_ENGINE_OPTIONS = getEngineOptions(DESTINATION_ENGINE_DEFINITIONS);

type DestinationFormValues = CredentialsFormValues & {
  name: string;
  destinationType: string;
  host: string;
  port: number | "";
  secure: boolean;
  databaseName: string;
};

type DestinationFormProps = {
  destination: Destination | null;
  isSaving: boolean;
  onCancel: () => void;
  onSubmit: (values: DestinationFormValues) => void;
};

export function DestinationsView() {
  const queryClient = useQueryClient();
  const [destinationBeingEdited, setDestinationBeingEdited] =
    useState<Destination | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const destinationsQuery = useQuery({
    queryKey: DESTINATIONS_QUERY_KEY,
    queryFn: listDestinations,
  });

  const createDestinationMutation = useMutation({
    mutationFn: createDestination,
    onSuccess: () => {
      closeModal();
      void queryClient.invalidateQueries({ queryKey: DESTINATIONS_QUERY_KEY });
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
      void queryClient.invalidateQueries({ queryKey: DESTINATIONS_QUERY_KEY });
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
      void queryClient.invalidateQueries({ queryKey: DESTINATIONS_QUERY_KEY });
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
      return;
    }
  }

  function openDeleteConfirmation(destination: Destination): void {
    modals.openConfirmModal({
      title: "Eliminar destino",
      children: (
        <Text size="sm">
          Se eliminará el destino administrativo {destination.name}.
        </Text>
      ),
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
        destinations: destinationsQuery.data,
        isLoading: destinationsQuery.isPending,
        error: destinationsQuery.error,
        refetch: destinationsQuery.refetch,
        openEditModal,
        openDeleteConfirmation,
        isDeleting: deleteDestinationMutation.isPending,
      })}

      <Modal
        opened={isModalOpen}
        onClose={closeModal}
        title={destinationBeingEdited ? "Editar destino" : "Crear destino"}
      >
        <DestinationForm
          key={destinationBeingEdited?.id ?? "new-destination"}
          destination={destinationBeingEdited}
          isSaving={
            createDestinationMutation.isPending ||
            updateDestinationMutation.isPending
          }
          onCancel={closeModal}
          onSubmit={handleSubmit}
        />
      </Modal>
    </Stack>
  );
}

function DestinationForm({
  destination,
  isSaving,
  onCancel,
  onSubmit,
}: DestinationFormProps) {
  const mode: EntityFormMode = destination ? "edit" : "create";
  const form = useForm<DestinationFormValues>({
    initialValues: {
      name: destination?.name ?? "",
      destinationType: destination?.destination_type ?? DEFAULT_DESTINATION_TYPE,
      host: destination?.host ?? "",
      port: destination?.port ?? getDefaultDestinationPort(),
      secure: destination?.secure ?? false,
      databaseName: destination?.database_name ?? "",
      credentialsUser: "",
      credentialsPassword: "",
    },
    validate: {
      name: requiredText,
      destinationType: requiredText,
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
    DESTINATION_ENGINE_DEFINITIONS,
    form.values.destinationType,
  );

  function handleDestinationTypeChange(value: string | null): void {
    if (!value) {
      return;
    }

    const definition = findEngineDefinition(
      DESTINATION_ENGINE_DEFINITIONS,
      value,
    );

    if (!definition) {
      form.setFieldError("destinationType", "Motor desconocido");
      return;
    }

    if (!definition.enabled) {
      form.setFieldError("destinationType", "Motor no soportado todavía");
      return;
    }

    form.setFieldValue("destinationType", definition.value);
    form.setFieldValue("port", definition.defaultPort);
  }

  return (
    <form onSubmit={form.onSubmit(onSubmit)}>
      <Stack gap="md">
        <TextInput
          label="Nombre"
          placeholder="Destino analítico"
          withAsterisk
          {...form.getInputProps("name")}
        />
        <Select
          label="Motor"
          data={DESTINATION_ENGINE_OPTIONS}
          value={form.values.destinationType}
          onChange={handleDestinationTypeChange}
          withAsterisk
          error={form.errors.destinationType}
        />
        <TextInput
          label="Host"
          placeholder="analytics.internal"
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
          placeholder="cdc_sync_analytics"
          withAsterisk
          {...form.getInputProps("databaseName")}
        />
        <Switch
          label="Conexión segura"
          {...form.getInputProps("secure", { type: "checkbox" })}
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

type DestinationsContentProps = {
  destinations: Destination[] | undefined;
  isLoading: boolean;
  error: unknown;
  refetch: () => void;
  openEditModal: (destination: Destination) => void;
  openDeleteConfirmation: (destination: Destination) => void;
  isDeleting: boolean;
};

function renderDestinationsContent({
  destinations,
  isLoading,
  error,
  refetch,
  openEditModal,
  openDeleteConfirmation,
  isDeleting,
}: DestinationsContentProps) {
  if (isLoading) {
    return <LoadingState message="Cargando destinos" />;
  }

  if (error) {
    const apiError = normalizeApiError(error);

    return (
      <ErrorState
        title="No se pudieron cargar los destinos"
        message={apiError.message}
        onRetry={refetch}
      />
    );
  }

  if (!destinations || destinations.length === 0) {
    return (
      <Text c="dimmed" size="sm">
        Todavía no hay destinos registrados.
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
            <Table.Th>Seguridad</Table.Th>
            <Table.Th>Credenciales</Table.Th>
            <Table.Th ta="right">Acciones</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {destinations.map((destination) => (
            <Table.Tr key={destination.id}>
              <Table.Td>
                <Text fw={500}>{destination.name}</Text>
              </Table.Td>
              <Table.Td>
                <Badge variant="light">
                  {getDestinationEngineLabel(destination.destination_type)}
                </Badge>
              </Table.Td>
              <Table.Td>
                {destination.host}:{destination.port}
              </Table.Td>
              <Table.Td>{destination.database_name}</Table.Td>
              <Table.Td>
                <Badge color={destination.secure ? "teal" : "gray"} variant="light">
                  {destination.secure ? "Segura" : "Sin TLS"}
                </Badge>
              </Table.Td>
              <Table.Td>
                <Badge
                  color={destination.credentials_configured ? "teal" : "red"}
                  variant="light"
                >
                  {destination.credentials_configured
                    ? "Configuradas"
                    : "Pendientes"}
                </Badge>
              </Table.Td>
              <Table.Td>
                <Group justify="flex-end" gap="xs" wrap="nowrap">
                  <Tooltip label="Editar destino">
                    <ActionIcon
                      variant="subtle"
                      aria-label="Editar destino"
                      onClick={() => openEditModal(destination)}
                    >
                      <Pencil size={16} strokeWidth={1.8} />
                    </ActionIcon>
                  </Tooltip>
                  <Tooltip label="Eliminar destino">
                    <ActionIcon
                      color="red"
                      variant="subtle"
                      aria-label="Eliminar destino"
                      loading={isDeleting}
                      onClick={() => openDeleteConfirmation(destination)}
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

function buildDestinationCreatePayload(
  values: DestinationFormValues,
): DestinationCreateRequest {
  const basePayload = buildDestinationBasePayload(values);
  const credentials = buildDestinationCredentials(values, "create");

  if (!credentials) {
    throw new Error("Las credenciales del destino son obligatorias");
  }

  return {
    ...basePayload,
    credentials,
  };
}

function buildDestinationUpdatePayload(
  values: DestinationFormValues,
): DestinationUpdateRequest {
  const basePayload = buildDestinationBasePayload(values);
  const credentials = buildDestinationCredentials(values, "edit");

  if (!credentials) {
    return basePayload;
  }

  return {
    ...basePayload,
    credentials,
  };
}

function buildDestinationBasePayload(
  values: DestinationFormValues,
): Omit<DestinationUpdateRequest, "credentials"> {
  const engine = requireEnabledEngineDefinition(
    DESTINATION_ENGINE_DEFINITIONS,
    values.destinationType,
  );
  const port = getValidatedPort(values.port);

  return {
    name: values.name.trim(),
    destination_type: engine.value,
    host: values.host.trim(),
    port,
    secure: values.secure,
    database_name: values.databaseName.trim(),
  };
}

function getDestinationEngineLabel(destinationType: string): string {
  return (
    findEngineDefinition(DESTINATION_ENGINE_DEFINITIONS, destinationType)
      ?.label ?? destinationType
  );
}

function getDefaultDestinationPort(): number {
  return requireEnabledEngineDefinition(
    DESTINATION_ENGINE_DEFINITIONS,
    DEFAULT_DESTINATION_TYPE,
  ).defaultPort;
}
