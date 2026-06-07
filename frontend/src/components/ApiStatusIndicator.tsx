import { Badge, Group, Loader, Text, Tooltip } from "@mantine/core";
import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, CircleAlert } from "lucide-react";

import { normalizeApiError } from "../api/errors";
import { getHealthStatus } from "../api/health";

export function ApiStatusIndicator() {
  const healthQuery = useQuery({
    queryKey: ["api-health"],
    queryFn: getHealthStatus,
  });

  if (healthQuery.isPending) {
    return (
      <Group gap="xs" wrap="nowrap">
        <Loader size="xs" color="teal" />
        <Text size="sm" c="dimmed">
          Comprobando API
        </Text>
      </Group>
    );
  }

  if (healthQuery.isError) {
    const apiError = normalizeApiError(healthQuery.error);

    return (
      <Tooltip label={apiError.message}>
        <Badge
          color="red"
          variant="light"
          leftSection={<CircleAlert size={14} strokeWidth={1.8} />}
        >
          API no disponible
        </Badge>
      </Tooltip>
    );
  }

  return (
    <Badge
      color="teal"
      variant="light"
      leftSection={<CheckCircle2 size={14} strokeWidth={1.8} />}
    >
      API conectada
    </Badge>
  );
}
