import {
  Alert,
  Button,
  Group,
  Select,
  SimpleGrid,
  Stack,
  Text,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { CircleAlert, Send } from "lucide-react";

import type {
  AssignmentResponse,
  SyncConfig,
  Worker,
} from "../../../../api/controlPlaneAdmin";
import type { AssignmentFormValues } from "../../types/forms";
import { requiredText } from "../../utils/formValidation";

type AssignmentPanelProps = {
  workers: Worker[];
  configs: SyncConfig[];
  assignment: AssignmentResponse | null;
  isAssigning: boolean;
  onSubmit: (values: AssignmentFormValues) => void;
};

export function AssignmentPanel({
  workers,
  configs,
  assignment,
  isAssigning,
  onSubmit,
}: AssignmentPanelProps) {
  const form = useForm<AssignmentFormValues>({
    initialValues: {
      workerInternalId: "",
      configId: "",
    },
    validate: {
      workerInternalId: requiredText,
      configId: requiredText,
    },
  });

  return (
    <Stack gap="md">
      <Alert
        color="yellow"
        variant="light"
        icon={<CircleAlert size={18} strokeWidth={1.8} />}
      >
        La configuración asignada se cargará cuando el worker arranque de nuevo
        manualmente.
      </Alert>

      <form onSubmit={form.onSubmit(onSubmit)}>
        <Stack gap="md">
          <SimpleGrid cols={{ base: 1, md: 2 }}>
            <Select
              label="Worker"
              data={workers.map((worker) => ({
                value: worker.id,
                label: `${worker.name} (${worker.worker_id})`,
              }))}
              placeholder="Selecciona un worker"
              withAsterisk
              {...form.getInputProps("workerInternalId")}
            />
            <Select
              label="Configuración"
              data={configs.map((config) => ({
                value: config.id,
                label: config.name,
              }))}
              placeholder="Selecciona una configuración"
              withAsterisk
              {...form.getInputProps("configId")}
            />
          </SimpleGrid>

          <Group justify="flex-end">
            <Button
              type="submit"
              loading={isAssigning}
              leftSection={<Send size={16} strokeWidth={1.8} />}
            >
              Asignar configuración
            </Button>
          </Group>
        </Stack>
      </form>

      {assignment ? (
        <Text size="sm" c="dimmed">
          Última asignación: {assignment.worker_id} recibió{" "}
          {assignment.config_id}.
        </Text>
      ) : null}
    </Stack>
  );
}
