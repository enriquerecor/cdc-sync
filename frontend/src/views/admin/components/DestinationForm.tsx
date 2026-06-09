import {
  Button,
  Group,
  NumberInput,
  PasswordInput,
  Select,
  Stack,
  Switch,
  Text,
  TextInput,
} from "@mantine/core";
import { useForm } from "@mantine/form";

import type { Destination } from "../../../api/controlPlaneAdmin";
import type {
  DestinationFormValues,
  EntityFormMode,
} from "../types/forms";
import {
  DESTINATION_ENGINE_DEFINITIONS,
  findEngineDefinition,
  getEngineOptions,
} from "../utils/engineDefinitions";
import {
  DEFAULT_DESTINATION_TYPE,
  getDefaultDestinationPort,
} from "../utils/engineLabels";
import {
  requiredText,
  validateCredentialsPassword,
  validateCredentialsUser,
  validatePort,
} from "../utils/formValidation";

const DESTINATION_ENGINE_OPTIONS = getEngineOptions(DESTINATION_ENGINE_DEFINITIONS);

type DestinationFormProps = {
  destination: Destination | null;
  isSaving: boolean;
  onCancel: () => void;
  onSubmit: (values: DestinationFormValues) => void;
};

export function DestinationForm({
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
