import {
  Button,
  Group,
  NumberInput,
  PasswordInput,
  Select,
  Stack,
  Text,
  TextInput,
} from "@mantine/core";
import { useForm } from "@mantine/form";

import type { SourceConnection } from "../../../api/controlPlaneAdmin";
import type {
  EntityFormMode,
  SourceConnectionFormValues,
} from "../types/forms";
import {
  SOURCE_ENGINE_DEFINITIONS,
  findEngineDefinition,
  getEngineOptions,
} from "../utils/engineDefinitions";
import {
  DEFAULT_SOURCE_TYPE,
  getDefaultSourcePort,
} from "../utils/engineLabels";
import {
  requiredText,
  validateCredentialsPassword,
  validateCredentialsUser,
  validatePort,
} from "../utils/formValidation";

const SOURCE_ENGINE_OPTIONS = getEngineOptions(SOURCE_ENGINE_DEFINITIONS);

type SourceConnectionFormProps = {
  sourceConnection: SourceConnection | null;
  isSaving: boolean;
  onCancel: () => void;
  onSubmit: (values: SourceConnectionFormValues) => void;
};

export function SourceConnectionForm({
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
