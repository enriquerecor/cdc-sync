import {
  Button,
  Group,
  Stack,
  Switch,
  TextInput,
  Textarea,
} from "@mantine/core";
import { useForm } from "@mantine/form";

import type { Worker } from "../../../api/controlPlaneAdmin";
import type { WorkerFormValues } from "../types/forms";
import { requiredText } from "../utils/formValidation";

type WorkerFormProps = {
  worker: Worker | null;
  isSaving: boolean;
  onCancel: () => void;
  onSubmit: (values: WorkerFormValues) => void;
};

export function WorkerForm({
  worker,
  isSaving,
  onCancel,
  onSubmit,
}: WorkerFormProps) {
  const form = useForm<WorkerFormValues>({
    initialValues: {
      workerId: worker?.worker_id ?? "",
      name: worker?.name ?? "",
      description: worker?.description ?? "",
      kafkaGroupId: worker?.kafka_group_id ?? "",
      enabled: worker?.enabled ?? true,
    },
    validate: {
      workerId: requiredText,
      name: requiredText,
    },
  });

  return (
    <form onSubmit={form.onSubmit(onSubmit)}>
      <Stack gap="md">
        <TextInput
          label="WORKER_ID"
          placeholder="local-worker"
          withAsterisk
          {...form.getInputProps("workerId")}
        />
        <TextInput
          label="Nombre"
          placeholder="Worker local"
          withAsterisk
          {...form.getInputProps("name")}
        />
        <Textarea
          label="Descripción"
          autosize
          minRows={2}
          {...form.getInputProps("description")}
        />
        <TextInput
          label="Grupo Kafka"
          placeholder="cdc-sync-worker-local-worker"
          {...form.getInputProps("kafkaGroupId")}
        />
        <Switch
          label="Activo"
          {...form.getInputProps("enabled", { type: "checkbox" })}
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
