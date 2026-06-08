import {
  Badge,
  Button,
  Group,
  Select,
  Stack,
  Table,
  Text,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { Cable } from "lucide-react";

import type {
  CdcConnectorMaterializationResponse,
  SourceConnection,
} from "../../../../api/controlPlaneAdmin";
import type { MaterializationFormValues } from "../../types/forms";
import { requiredText } from "../../utils/formValidation";

type CdcMaterializationPanelProps = {
  sourceConnections: SourceConnection[];
  materializedConnector: CdcConnectorMaterializationResponse | null;
  isMaterializing: boolean;
  onSubmit: (values: MaterializationFormValues) => void;
};

export function CdcMaterializationPanel({
  sourceConnections,
  materializedConnector,
  isMaterializing,
  onSubmit,
}: CdcMaterializationPanelProps) {
  const form = useForm<MaterializationFormValues>({
    initialValues: {
      sourceConnectionId: "",
    },
    validate: {
      sourceConnectionId: requiredText,
    },
  });

  return (
    <Stack gap="md">
      <form onSubmit={form.onSubmit(onSubmit)}>
        <Stack gap="md">
          <Select
            label="Origen"
            data={sourceConnections.map((sourceConnection) => ({
              value: sourceConnection.id,
              label: sourceConnection.name,
            }))}
            placeholder="Selecciona un origen"
            withAsterisk
            {...form.getInputProps("sourceConnectionId")}
          />

          <Group justify="flex-end">
            <Button
              type="submit"
              loading={isMaterializing}
              leftSection={<Cable size={16} strokeWidth={1.8} />}
            >
              Materializar CDC
            </Button>
          </Group>
        </Stack>
      </form>

      {materializedConnector ? (
        <MaterializationResult connector={materializedConnector} />
      ) : null}
    </Stack>
  );
}

type MaterializationResultProps = {
  connector: CdcConnectorMaterializationResponse;
};

function MaterializationResult({ connector }: MaterializationResultProps) {
  return (
    <Stack gap="sm">
      <Text fw={600}>Resultado</Text>
      <Table withTableBorder verticalSpacing="sm">
        <Table.Tbody>
          <Table.Tr>
            <Table.Th>Conector</Table.Th>
            <Table.Td>{connector.connector_name}</Table.Td>
          </Table.Tr>
          <Table.Tr>
            <Table.Th>Clase</Table.Th>
            <Table.Td>{connector.connector_class}</Table.Td>
          </Table.Tr>
          <Table.Tr>
            <Table.Th>Topic prefix</Table.Th>
            <Table.Td>{connector.topic_prefix}</Table.Td>
          </Table.Tr>
        </Table.Tbody>
      </Table>
      <Group gap="xs">
        {connector.captured_tables.map((table) => (
          <Badge key={table} variant="light">
            {table}
          </Badge>
        ))}
      </Group>
    </Stack>
  );
}
