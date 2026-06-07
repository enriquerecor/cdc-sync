import { Alert, Button, Group, Loader, Stack, Text, Title } from "@mantine/core";
import { CircleAlert, CircleCheck, RotateCcw } from "lucide-react";
import type { ReactNode } from "react";

type LoadingStateProps = {
  message: string;
};

export function LoadingState({ message }: LoadingStateProps) {
  return (
    <Group gap="sm">
      <Loader size="sm" color="teal" />
      <Text size="sm" c="dimmed">
        {message}
      </Text>
    </Group>
  );
}

type ErrorStateProps = {
  title: string;
  message: string;
  retryLabel?: string;
  onRetry?: () => void;
};

export function ErrorState({
  title,
  message,
  retryLabel = "Reintentar",
  onRetry,
}: ErrorStateProps) {
  return (
    <Alert
      color="red"
      variant="light"
      title={title}
      icon={<CircleAlert size={18} strokeWidth={1.8} />}
    >
      <Stack gap="sm">
        <Text size="sm">{message}</Text>
        {onRetry ? (
          <Group>
            <Button
              size="xs"
              color="red"
              variant="light"
              leftSection={<RotateCcw size={14} strokeWidth={1.8} />}
              onClick={onRetry}
            >
              {retryLabel}
            </Button>
          </Group>
        ) : null}
      </Stack>
    </Alert>
  );
}

type SuccessStateProps = {
  title: string;
  children?: ReactNode;
};

export function SuccessState({ title, children }: SuccessStateProps) {
  return (
    <Alert
      color="teal"
      variant="light"
      title={title}
      icon={<CircleCheck size={18} strokeWidth={1.8} />}
    >
      {children}
    </Alert>
  );
}

type EmptyAdministrativeViewProps = {
  title: string;
  description: string;
};

export function EmptyAdministrativeView({
  title,
  description,
}: EmptyAdministrativeViewProps) {
  return (
    <Stack gap="xs">
      <Title order={2} size="h3">
        {title}
      </Title>
      <Text c="dimmed" maw={720}>
        {description}
      </Text>
    </Stack>
  );
}
