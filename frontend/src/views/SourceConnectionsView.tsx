import { Select, Stack } from "@mantine/core";
import { useState } from "react";

import { EmptyAdministrativeView } from "../components/FeedbackState";

const SOURCE_ENGINE_OPTIONS = [
  { value: "postgresql", label: "PostgreSQL" },
  { value: "mysql", label: "MySQL", disabled: true },
  { value: "sql-server", label: "SQL Server", disabled: true },
  { value: "oracle", label: "Oracle", disabled: true },
];

export function SourceConnectionsView() {
  const [sourceEngine, setSourceEngine] = useState("postgresql");

  return (
    <Stack gap="md">
      <EmptyAdministrativeView
        title="Orígenes de datos"
        description="Define las conexiones transaccionales desde las que se capturan los cambios."
      />
      <Select
        label="Motor de origen"
        description="Selecciona la tecnología transaccional disponible para capturar cambios."
        data={SOURCE_ENGINE_OPTIONS}
        value={sourceEngine}
        onChange={(value) => {
          if (!value) {
            return;
          }

          setSourceEngine(value);
        }}
        maw={420}
      />
    </Stack>
  );
}
