import { expect, test } from "@playwright/test";

import {
  createAdminApiMockState,
  setupAdminApiMocks,
  type WorkerRequest,
} from "./admin-api-mock";

test("crea un worker desde el estado vacío", async ({ page }) => {
  const expectedWorkerPayload: WorkerRequest = {
    worker_id: "qa-worker",
    name: "Worker QA",
    description: "Worker para smoke frontend",
    kafka_group_id: "cdc-sync-worker-qa",
    enabled: true,
  };
  const apiState = createAdminApiMockState();

  await setupAdminApiMocks(page, apiState);

  await page.goto("/");

  await expect(page.getByRole("heading", { name: "cdc-sync" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Workers" })).toBeVisible();
  await expect(
    page.getByText("Todavía no hay workers registrados."),
  ).toBeVisible();

  await page.getByRole("button", { name: "Crear worker" }).click();

  const createWorkerDialog = page.getByRole("dialog", { name: "Crear worker" });
  await expect(createWorkerDialog).toBeVisible();

  await createWorkerDialog.getByLabel("WORKER_ID").fill(" qa-worker ");
  await createWorkerDialog.getByLabel("Nombre").fill(" Worker QA ");
  await createWorkerDialog
    .getByLabel("Descripción")
    .fill(" Worker para smoke frontend ");
  await createWorkerDialog
    .getByLabel("Grupo Kafka")
    .fill(" cdc-sync-worker-qa ");

  await createWorkerDialog.getByRole("button", { name: "Guardar" }).click();

  await expect(createWorkerDialog).toBeHidden();
  await expect(page.getByText("Worker QA")).toBeVisible();
  await expect(page.getByText("qa-worker")).toBeVisible();
  await expect(page.getByText("cdc-sync-worker-qa")).toBeVisible();
  await expect(page.getByText("Activo")).toBeVisible();
  expect(apiState.receivedWorkerPayload).toEqual(expectedWorkerPayload);
});
