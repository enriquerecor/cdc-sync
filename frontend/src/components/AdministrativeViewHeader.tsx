import { Button, Group, Stack, Text, Title } from "@mantine/core";
import type { LucideIcon } from "lucide-react";

type AdministrativeViewHeaderProps = {
  title: string;
  description: string;
  actionLabel?: string;
  actionIcon?: LucideIcon;
  onAction?: () => void;
};

export function AdministrativeViewHeader({
  title,
  description,
  actionLabel,
  actionIcon: ActionIcon,
  onAction,
}: AdministrativeViewHeaderProps) {
  return (
    <Group align="flex-start" justify="space-between" gap="md">
      <Stack gap="xs">
        <Title order={2} size="h3">
          {title}
        </Title>
        <Text c="dimmed" maw={720}>
          {description}
        </Text>
      </Stack>
      {actionLabel && onAction ? (
        <Button
          leftSection={
            ActionIcon ? <ActionIcon size={16} strokeWidth={1.8} /> : null
          }
          onClick={onAction}
        >
          {actionLabel}
        </Button>
      ) : null}
    </Group>
  );
}
