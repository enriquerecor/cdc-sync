import {
  Button,
  Code,
  Group,
  Select,
  Stack,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { Search } from "lucide-react";

import type { Worker } from "../../../../api/controlPlaneAdmin";
import type { WorkerRuntimeConfigResponse } from "../../../../api/workerRuntime";
import type { RuntimeLookupFormValues } from "../../types/forms";
import { requiredText } from "../../utils/formValidation";

type RuntimeConfigPanelProps = {
  workers: Worker[];
  runtimeConfig: WorkerRuntimeConfigResponse | null;
  isLoadingRuntime: boolean;
  onSubmit: (values: RuntimeLookupFormValues) => void;
};

export function RuntimeConfigPanel({
  workers,
  runtimeConfig,
  isLoadingRuntime,
  onSubmit,
}: RuntimeConfigPanelProps) {
  const form = useForm<RuntimeLookupFormValues>({
    initialValues: {
      workerId: "",
    },
    validate: {
      workerId: requiredText,
    },
  });

  return (
    <Stack gap="md">
      <form onSubmit={form.onSubmit(onSubmit)}>
        <Stack gap="md">
          <Select
            label="WORKER_ID"
            data={workers.map((worker) => ({
              value: worker.worker_id,
              label: `${worker.worker_id} (${worker.name})`,
            }))}
            placeholder="Selecciona un worker"
            searchable
            withAsterisk
            {...form.getInputProps("workerId")}
          />

          <Group justify="flex-end">
            <Button
              type="submit"
              loading={isLoadingRuntime}
              leftSection={<Search size={16} strokeWidth={1.8} />}
            >
              Consultar runtime
            </Button>
          </Group>
        </Stack>
      </form>

      {runtimeConfig ? (
        <Code block>{JSON.stringify(runtimeConfig, null, 2)}</Code>
      ) : null}
    </Stack>
  );
}
