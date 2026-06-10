import { expect, test } from "@playwright/test";

import {
  createAdminApiMockState,
  setupAdminApiMocks,
  type DestinationResponse,
  type SourceConnectionResponse,
  type SyncConfigResponse,
  type WorkerResponse,
} from "./admin-api-mock";

const workerFixture: WorkerResponse = {
  id: "11111111-1111-4111-8111-111111111111",
  worker_id: "qa-worker",
  name: "Worker QA",
  description: "Worker para smoke frontend",
  kafka_group_id: "cdc-sync-worker-qa",
  enabled: true,
};

const sourceConnectionFixture: SourceConnectionResponse = {
  id: "22222222-2222-4222-8222-222222222222",
  name: "PostgreSQL QA",
  source_type: "postgresql",
  host: "postgres-qa",
  port: 15432,
  database_name: "cdc_sync_qa",
  credentials_configured: true,
};

const destinationFixture: DestinationResponse = {
  id: "33333333-3333-4333-8333-333333333333",
  name: "ClickHouse QA",
  destination_type: "clickhouse",
  host: "clickhouse-qa",
  port: 9440,
  secure: false,
  database_name: "cdc_sync_analytics_qa",
  credentials_configured: true,
};

const syncConfigFixture: SyncConfigResponse = {
  id: "44444444-4444-4444-8444-444444444444",
  name: "Configuración QA",
  source_connection_id: sourceConnectionFixture.id,
  destination_id: destinationFixture.id,
  sync_mode: "realtime",
  enabled: true,
  tables: [
    {
      logical_name: "customers",
      source_schema: "public",
      source_table: "customers",
      cdc_topic: "cdc_sync.public.customers",
      destination_table: "customers",
      primary_key_fields: ["id"],
      destination_columns: [
        {
          name: "id",
          destination_type: "UInt64",
          nullable: false,
        },
      ],
      enabled: true,
    },
  ],
};

test("carga suavemente la vista de configuraciones y sus paneles", async ({
  page,
}) => {
  const apiState = createAdminApiMockState({
    workers: [workerFixture],
    sourceConnections: [sourceConnectionFixture],
    destinations: [destinationFixture],
    syncConfigs: [syncConfigFixture],
  });

  await setupAdminApiMocks(page, apiState);

  await page.goto("/");
  await page.getByRole("tab", { name: "Configuraciones" }).click();

  await expect(
    page.getByRole("heading", { name: "Configuraciones" }),
  ).toBeVisible();
  await expect(page.getByText("Configuración QA")).toBeVisible();
  await expect(page.getByText("PostgreSQL QA")).toBeVisible();
  await expect(page.getByText("ClickHouse QA")).toBeVisible();
  await expect(page.getByText("realtime")).toBeVisible();
  await expect(page.getByText("Activa")).toBeVisible();

  await page.getByRole("tab", { name: "Asignación" }).click();
  await expect(
    page.getByText(
      "La configuración asignada se cargará cuando el worker arranque de nuevo manualmente.",
    ),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Asignar configuración" }),
  ).toBeVisible();

  await page.getByRole("tab", { name: "CDC" }).click();
  await expect(
    page.getByRole("button", { name: "Materializar CDC" }),
  ).toBeVisible();

  await page.getByRole("tab", { name: "Runtime" }).click();
  await expect(
    page.getByRole("button", { name: "Consultar runtime" }),
  ).toBeVisible();
});
