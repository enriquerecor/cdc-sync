import {
  ActionIcon,
  Button,
  Divider,
  Group,
  Paper,
  Select,
  SimpleGrid,
  Stack,
  Switch,
  Text,
  TextInput,
  Tooltip,
} from "@mantine/core";
import {
  useForm,
  type FormErrors,
  type UseFormReturnType,
} from "@mantine/form";
import { Plus, Trash2 } from "lucide-react";
import { useState, type KeyboardEvent } from "react";

import type {
  Destination,
  SourceConnection,
  SyncConfig,
} from "../../../../api/controlPlaneAdmin";
import type {
  ConfiguredTableFormValues,
  SyncConfigFormValues,
} from "../../types/forms";
import { buildSyncConfigFormValues } from "../../utils/payloadMappers";
import { requiredText } from "../../utils/formValidation";
import {
  createConfiguredTableFromName,
  createEmptyDestinationColumn,
} from "../../utils/syncConfigFormDefaults";

type SyncConfigFormValidation = (
  values: SyncConfigFormValues,
) => FormErrors;
type SyncConfigFormReturn = UseFormReturnType<
  SyncConfigFormValues,
  SyncConfigFormValues,
  SyncConfigFormValidation
>;

type SyncConfigFormProps = {
  config: SyncConfig | null;
  sourceConnections: SourceConnection[];
  destinations: Destination[];
  isSaving: boolean;
  onCancel: () => void;
  onSubmit: (values: SyncConfigFormValues) => void;
};

export function SyncConfigForm({
  config,
  sourceConnections,
  destinations,
  isSaving,
  onCancel,
  onSubmit,
}: SyncConfigFormProps) {
  const [newTableName, setNewTableName] = useState("");
  const [newTableNamespace, setNewTableNamespace] = useState("public");
  const form = useForm<SyncConfigFormValues>({
    initialValues: buildSyncConfigFormValues(config),
    validate: validateSyncConfigForm,
  });
  const sourceConnectionOptions = sourceConnections.map((sourceConnection) => ({
    value: sourceConnection.id,
    label: sourceConnection.name,
  }));
  const destinationOptions = destinations.map((destination) => ({
    value: destination.id,
    label: destination.name,
  }));

  function addTableFromName(): void {
    const trimmedTableName = newTableName.trim();
    const trimmedTableNamespace = newTableNamespace.trim();

    if (!trimmedTableName || !trimmedTableNamespace) {
      return;
    }

    const table = createConfiguredTableFromName(
      trimmedTableName,
      trimmedTableNamespace,
      form.values.tables,
    );

    form.insertListItem("tables", table);
    form.clearFieldError("tables");
    setNewTableName("");
  }

  function handleAddTableInputKeyDown(
    event: KeyboardEvent<HTMLInputElement>,
  ): void {
    if (event.key !== "Enter") {
      return;
    }

    event.preventDefault();
    addTableFromName();
  }

  function addDestinationColumn(tableIndex: number): void {
    form.insertListItem(
      `tables.${tableIndex}.destinationColumns`,
      createEmptyDestinationColumn(),
    );
  }

  return (
    <form onSubmit={form.onSubmit(onSubmit)}>
      <Stack gap="md">
        <SimpleGrid cols={{ base: 1, md: 2 }}>
          <TextInput
            label="Nombre"
            placeholder="Configuración local"
            withAsterisk
            {...form.getInputProps("name")}
          />
          <Select
            label="Modo"
            data={[{ value: "realtime", label: "Realtime" }]}
            withAsterisk
            {...form.getInputProps("syncMode")}
          />
          <Select
            label="Origen"
            data={sourceConnectionOptions}
            placeholder="Selecciona un origen"
            withAsterisk
            {...form.getInputProps("sourceConnectionId")}
          />
          <Select
            label="Destino"
            data={destinationOptions}
            placeholder="Selecciona un destino"
            withAsterisk
            {...form.getInputProps("destinationId")}
          />
        </SimpleGrid>

        <Switch
          label="Configuración activa"
          {...form.getInputProps("enabled", { type: "checkbox" })}
        />

        <Divider />

        <Group justify="space-between" align="flex-end">
          <Text fw={600}>Tablas</Text>
          <Group gap="xs" align="flex-end">
            <TextInput
              label="Nombre de tabla"
              placeholder="customers"
              value={newTableName}
              onChange={(event) => setNewTableName(event.currentTarget.value)}
              onKeyDown={handleAddTableInputKeyDown}
            />
            <TextInput
              label="Namespace"
              placeholder="public"
              value={newTableNamespace}
              onChange={(event) =>
                setNewTableNamespace(event.currentTarget.value)
              }
              onKeyDown={handleAddTableInputKeyDown}
            />
            <Button
              type="button"
              size="sm"
              variant="light"
              disabled={!newTableName.trim() || !newTableNamespace.trim()}
              leftSection={<Plus size={14} strokeWidth={1.8} />}
              onClick={addTableFromName}
            >
              Añadir tabla
            </Button>
          </Group>
        </Group>

        {form.errors.tables ? (
          <Text c="red" size="sm">
            {form.errors.tables}
          </Text>
        ) : null}

        {form.values.tables.length === 0 ? (
          <Text c="dimmed" size="sm">
            Todavía no hay tablas configuradas.
          </Text>
        ) : null}

        {form.values.tables.map((table, tableIndex) => (
          <Paper key={tableIndex} withBorder p="md" radius="sm">
            <Stack gap="md">
              <Group justify="space-between" align="center">
                <Text fw={600}>Tabla {tableIndex + 1}</Text>
                <Group gap="xs" wrap="nowrap">
                  <Switch
                    label="Activa"
                    {...form.getInputProps(`tables.${tableIndex}.enabled`, {
                      type: "checkbox",
                    })}
                  />
                  <Tooltip label="Eliminar tabla">
                    <ActionIcon
                      type="button"
                      color="red"
                      variant="subtle"
                      aria-label="Eliminar tabla"
                      onClick={() => form.removeListItem("tables", tableIndex)}
                    >
                      <Trash2 size={16} strokeWidth={1.8} />
                    </ActionIcon>
                  </Tooltip>
                </Group>
              </Group>

              <SimpleGrid cols={{ base: 1, md: 2 }}>
                <TextInput
                  label="Nombre lógico"
                  placeholder="customers"
                  withAsterisk
                  {...form.getInputProps(`tables.${tableIndex}.logicalName`)}
                />
                <TextInput
                  label="Namespace origen"
                  placeholder="default"
                  withAsterisk
                  {...form.getInputProps(`tables.${tableIndex}.sourceSchema`)}
                />
                <TextInput
                  label="Tabla origen"
                  placeholder="customers"
                  withAsterisk
                  {...form.getInputProps(`tables.${tableIndex}.sourceTable`)}
                />
                <TextInput
                  label="Topic CDC"
                  placeholder="cdc_sync.public.customers"
                  withAsterisk
                  {...form.getInputProps(`tables.${tableIndex}.cdcTopic`)}
                />
                <TextInput
                  label="Tabla destino"
                  placeholder="customers"
                  withAsterisk
                  {...form.getInputProps(
                    `tables.${tableIndex}.destinationTable`,
                  )}
                />
                <TextInput
                  label="Claves primarias"
                  placeholder="id, tenant_id"
                  withAsterisk
                  {...form.getInputProps(
                    `tables.${tableIndex}.primaryKeyFields`,
                  )}
                />
              </SimpleGrid>

              <DestinationColumnsEditor
                table={table}
                tableIndex={tableIndex}
                form={form}
                onAddColumn={() => addDestinationColumn(tableIndex)}
              />
            </Stack>
          </Paper>
        ))}

        <Group justify="flex-end">
          <Button type="button" variant="default" onClick={onCancel}>
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

type DestinationColumnsEditorProps = {
  table: ConfiguredTableFormValues;
  tableIndex: number;
  form: SyncConfigFormReturn;
  onAddColumn: () => void;
};

function DestinationColumnsEditor({
  table,
  tableIndex,
  form,
  onAddColumn,
}: DestinationColumnsEditorProps) {
  return (
    <Stack gap="sm">
      <Group justify="space-between" align="center">
        <Text fw={500} size="sm">
          Columnas destino
        </Text>
        <Button
          type="button"
          size="xs"
          variant="light"
          leftSection={<Plus size={14} strokeWidth={1.8} />}
          onClick={onAddColumn}
        >
          Añadir columna
        </Button>
      </Group>

      {table.destinationColumns.map((_, columnIndex) => (
        <SimpleGrid
          key={columnIndex}
          cols={{ base: 1, md: 4 }}
          spacing="sm"
          verticalSpacing="sm"
        >
          <TextInput
            label="Nombre"
            placeholder="email"
            withAsterisk
            {...form.getInputProps(
              `tables.${tableIndex}.destinationColumns.${columnIndex}.name`,
            )}
          />
          <TextInput
            label="Tipo destino"
            placeholder="String"
            withAsterisk
            {...form.getInputProps(
              `tables.${tableIndex}.destinationColumns.${columnIndex}.destinationType`,
            )}
          />
          <Switch
            label="Nullable"
            mt={{ base: 0, md: 28 }}
            {...form.getInputProps(
              `tables.${tableIndex}.destinationColumns.${columnIndex}.nullable`,
              { type: "checkbox" },
            )}
          />
          <Group align="flex-end" justify="flex-end">
            <Tooltip label="Eliminar columna">
              <ActionIcon
                type="button"
                color="red"
                variant="subtle"
                aria-label="Eliminar columna"
                mt={{ base: 0, md: 28 }}
                disabled={table.destinationColumns.length === 1}
                onClick={() =>
                  form.removeListItem(
                    `tables.${tableIndex}.destinationColumns`,
                    columnIndex,
                  )
                }
              >
                <Trash2 size={16} strokeWidth={1.8} />
              </ActionIcon>
            </Tooltip>
          </Group>
        </SimpleGrid>
      ))}
    </Stack>
  );
}

function validateSyncConfigForm(values: SyncConfigFormValues): FormErrors {
  const errors: Record<string, string> = {};

  setRequiredError(errors, "name", values.name);
  setRequiredError(errors, "sourceConnectionId", values.sourceConnectionId);
  setRequiredError(errors, "destinationId", values.destinationId);
  setRequiredError(errors, "syncMode", values.syncMode);

  if (values.tables.length === 0) {
    errors.tables = "Añade al menos una tabla";
  }

  values.tables.forEach((table, tableIndex) => {
    setRequiredError(
      errors,
      `tables.${tableIndex}.logicalName`,
      table.logicalName,
    );
    setRequiredError(
      errors,
      `tables.${tableIndex}.sourceSchema`,
      table.sourceSchema,
    );
    setRequiredError(
      errors,
      `tables.${tableIndex}.sourceTable`,
      table.sourceTable,
    );
    setRequiredError(errors, `tables.${tableIndex}.cdcTopic`, table.cdcTopic);
    setRequiredError(
      errors,
      `tables.${tableIndex}.destinationTable`,
      table.destinationTable,
    );

    if (splitCommaSeparatedText(table.primaryKeyFields).length === 0) {
      errors[`tables.${tableIndex}.primaryKeyFields`] =
        "Indica al menos una clave primaria";
    }

    if (table.destinationColumns.length === 0) {
      errors[`tables.${tableIndex}.destinationColumns`] =
        "Añade al menos una columna destino";
    }

    table.destinationColumns.forEach((column, columnIndex) => {
      setRequiredError(
        errors,
        `tables.${tableIndex}.destinationColumns.${columnIndex}.name`,
        column.name,
      );
      setRequiredError(
        errors,
        `tables.${tableIndex}.destinationColumns.${columnIndex}.destinationType`,
        column.destinationType,
      );
    });
  });

  return errors;
}

function setRequiredError(
  errors: Record<string, string>,
  path: string,
  value: string,
): void {
  const error = requiredText(value);
  if (!error) {
    return;
  }

  errors[path] = error;
}

function splitCommaSeparatedText(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}
