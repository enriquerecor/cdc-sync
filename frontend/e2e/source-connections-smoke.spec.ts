import { expect, test } from "@playwright/test";

import {
  createAdminApiMockState,
  setupAdminApiMocks,
  type SourceConnectionCreateRequest,
} from "./admin-api-mock";

test("crea un origen PostgreSQL desde el estado vacío", async ({ page }) => {
  const expectedSourceConnectionPayload: SourceConnectionCreateRequest = {
    name: "PostgreSQL QA",
    source_type: "postgresql",
    host: "postgres-qa",
    port: 15432,
    database_name: "cdc_sync_qa",
    credentials: {
      user: "cdc_sync",
      password: "cdc_sync",
    },
  };
  const apiState = createAdminApiMockState();

  await setupAdminApiMocks(page, apiState);

  await page.goto("/");
  await page.getByRole("tab", { name: "Orígenes" }).click();

  await expect(
    page.getByRole("heading", { name: "Orígenes de datos" }),
  ).toBeVisible();
  await expect(
    page.getByText("Todavía no hay orígenes registrados."),
  ).toBeVisible();

  await page.getByRole("button", { name: "Crear origen" }).click();

  const createSourceDialog = page.getByRole("dialog", { name: "Crear origen" });
  await expect(createSourceDialog).toBeVisible();

  await createSourceDialog.getByLabel("Nombre").fill(" PostgreSQL QA ");
  await createSourceDialog.getByLabel("Host").fill(" postgres-qa ");
  await createSourceDialog.getByLabel("Puerto").fill("15432");
  await createSourceDialog.getByLabel("Base de datos").fill(" cdc_sync_qa ");
  await createSourceDialog.getByLabel("Usuario").fill(" cdc_sync ");
  await createSourceDialog.getByLabel("Contraseña").fill(" cdc_sync ");

  await createSourceDialog.getByRole("button", { name: "Guardar" }).click();

  await expect(createSourceDialog).toBeHidden();
  await expect(page.getByText("PostgreSQL QA")).toBeVisible();
  await expect(page.getByText("PostgreSQL", { exact: true })).toBeVisible();
  await expect(page.getByText("postgres-qa:15432")).toBeVisible();
  await expect(page.getByText("cdc_sync_qa")).toBeVisible();
  await expect(page.getByText("Configuradas")).toBeVisible();
  expect(apiState.receivedSourceConnectionPayload).toEqual(
    expectedSourceConnectionPayload,
  );
});
