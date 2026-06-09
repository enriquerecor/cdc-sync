import { apiClient } from "./client";
import type { components } from "./generated/openapi";
import { assertSuccessfulResponse, requireData } from "./response";

export type WorkerRuntimeConfigResponse =
  components["schemas"]["WorkerRuntimeConfigResponse"];

export async function getWorkerRuntimeConfig(
  workerId: string,
): Promise<WorkerRuntimeConfigResponse> {
  const { data, error, response } = await apiClient.GET(
    "/workers/{worker_id}/config",
    {
      params: {
        path: {
          worker_id: workerId,
        },
      },
    },
  );

  assertSuccessfulResponse(response, error, "No se pudo cargar el runtime");
  return requireData(data, "contrato runtime");
}
