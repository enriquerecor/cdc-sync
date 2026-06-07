import { Select, Stack } from "@mantine/core";
import { useState } from "react";

import { EmptyAdministrativeView } from "../components/FeedbackState";

const DESTINATION_ENGINE_OPTIONS = [
  { value: "clickhouse", label: "ClickHouse" },
  { value: "bigquery", label: "BigQuery", disabled: true },
  { value: "snowflake", label: "Snowflake", disabled: true },
  { value: "redshift", label: "Redshift", disabled: true },
];

export function DestinationsView() {
  const [destinationEngine, setDestinationEngine] = useState("clickhouse");

  return (
    <Stack gap="md">
      <EmptyAdministrativeView
        title="Destinos analíticos"
        description="Configura los almacenes analíticos donde se publican los cambios sincronizados."
      />
      <Select
        label="Motor de destino"
        description="Selecciona la tecnología analítica disponible para persistir los cambios."
        data={DESTINATION_ENGINE_OPTIONS}
        value={destinationEngine}
        onChange={(value) => {
          if (!value) {
            return;
          }

          setDestinationEngine(value);
        }}
        maw={420}
      />
    </Stack>
  );
}
