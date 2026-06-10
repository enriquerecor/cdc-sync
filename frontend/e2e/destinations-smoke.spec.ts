import { expect, test } from "@playwright/test";

import {
  createAdminApiMockState,
  setupAdminApiMocks,
  type DestinationCreateRequest,
} from "./admin-api-mock";

test("crea un destino ClickHouse desde el estado vacío", async ({ page }) => {
  const expectedDestinationPayload: DestinationCreateRequest = {
    name: "ClickHouse QA",
    destination_type: "clickhouse",
    host: "clickhouse-qa",
    port: 9440,
    secure: false,
    database_name: "cdc_sync_analytics_qa",
    credentials: {
      user: "cdc_sync",
      password: "cdc_sync",
    },
  };
  const apiState = createAdminApiMockState();

  await setupAdminApiMocks(page, apiState);

  await page.goto("/");
  await page.getByRole("tab", { name: "Destinos" }).click();

  await expect(
    page.getByRole("heading", { name: "Destinos analíticos" }),
  ).toBeVisible();
  await expect(
    page.getByText("Todavía no hay destinos registrados."),
  ).toBeVisible();

  await page.getByRole("button", { name: "Crear destino" }).click();

  const createDestinationDialog = page.getByRole("dialog", {
    name: "Crear destino",
  });
  await expect(createDestinationDialog).toBeVisible();

  await createDestinationDialog.getByLabel("Nombre").fill(" ClickHouse QA ");
  await createDestinationDialog.getByLabel("Host").fill(" clickhouse-qa ");
  await createDestinationDialog.getByLabel("Puerto").fill("9440");
  await createDestinationDialog
    .getByLabel("Base de datos")
    .fill(" cdc_sync_analytics_qa ");
  await createDestinationDialog.getByLabel("Usuario").fill(" cdc_sync ");
  await createDestinationDialog.getByLabel("Contraseña").fill(" cdc_sync ");

  await createDestinationDialog
    .getByRole("button", { name: "Guardar" })
    .click();

  await expect(createDestinationDialog).toBeHidden();
  await expect(page.getByText("ClickHouse QA")).toBeVisible();
  await expect(page.getByText("ClickHouse", { exact: true })).toBeVisible();
  await expect(page.getByText("clickhouse-qa:9440")).toBeVisible();
  await expect(page.getByText("cdc_sync_analytics_qa")).toBeVisible();
  await expect(page.getByText("Sin TLS")).toBeVisible();
  await expect(page.getByText("Configuradas")).toBeVisible();
  expect(apiState.receivedDestinationPayload).toEqual(
    expectedDestinationPayload,
  );
});
