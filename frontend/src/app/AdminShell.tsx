import {
  AppShell,
  Box,
  Group,
  Stack,
  Tabs,
  Text,
  Title,
} from "@mantine/core";
import {
  Database,
  HardDrive,
  LayoutDashboard,
  ServerCog,
  Settings2,
} from "lucide-react";
import { useState } from "react";

import { ApiStatusIndicator } from "../components/ApiStatusIndicator";
import { ColorSchemeToggle } from "../components/ColorSchemeToggle";
import { ConfigurationsView } from "../views/ConfigurationsView";
import { DestinationsView } from "../views/DestinationsView";
import { SourceConnectionsView } from "../views/SourceConnectionsView";
import { WorkersView } from "../views/WorkersView";

const ADMIN_SECTIONS = [
  {
    value: "workers",
    label: "Workers",
    icon: ServerCog,
    component: <WorkersView />,
  },
  {
    value: "sources",
    label: "Orígenes",
    icon: Database,
    component: <SourceConnectionsView />,
  },
  {
    value: "destinations",
    label: "Destinos",
    icon: HardDrive,
    component: <DestinationsView />,
  },
  {
    value: "configs",
    label: "Configuraciones",
    icon: Settings2,
    component: <ConfigurationsView />,
  },
] as const;

type AdminSectionValue = (typeof ADMIN_SECTIONS)[number]["value"];

export function AdminShell() {
  const [activeSection, setActiveSection] =
    useState<AdminSectionValue>("workers");

  return (
    <AppShell
      header={{ height: 72 }}
      footer={{ height: 28 }}
      padding={{ base: "md", md: "lg" }}
    >
      <AppShell.Header>
        <Group h="100%" px={{ base: "md", md: "lg" }} justify="space-between">
          <Group gap="sm" wrap="nowrap">
            <Box c="teal.7" lh={0}>
              <LayoutDashboard size={28} strokeWidth={1.8} />
            </Box>
            <Stack gap={0}>
              <Group gap="xs">
                <Title order={1} size="h3">
                  cdc-sync
                </Title>
              </Group>
              <Text size="sm" c="dimmed">
                Consola de sincronización CDC
              </Text>
            </Stack>
          </Group>
          <Group gap="sm" wrap="nowrap">
            <ColorSchemeToggle />
            <ApiStatusIndicator />
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Main>
        <Stack gap="lg">
          <Text size="sm" c="dimmed">
            Gestiona sincronizaciones entre sistemas operacionales y analíticos.
          </Text>

          <Tabs
            value={activeSection}
            onChange={(value) => {
              if (!value) {
                return;
              }

              setActiveSection(value as AdminSectionValue);
            }}
            keepMounted={false}
          >
            <Tabs.List>
              {ADMIN_SECTIONS.map((section) => (
                <Tabs.Tab
                  key={section.value}
                  value={section.value}
                  leftSection={<section.icon size={16} strokeWidth={1.8} />}
                >
                  {section.label}
                </Tabs.Tab>
              ))}
            </Tabs.List>

            {ADMIN_SECTIONS.map((section) => (
              <Tabs.Panel key={section.value} value={section.value} pt="lg">
                {section.component}
              </Tabs.Panel>
            ))}
          </Tabs>
        </Stack>
      </AppShell.Main>

      <AppShell.Footer className="app-footer">
        <Group h="100%" justify="center" px="md">
          <Text className="app-footer-text" size="xs">
            Enrique Redondo Cortés
          </Text>
        </Group>
      </AppShell.Footer>
    </AppShell>
  );
}
