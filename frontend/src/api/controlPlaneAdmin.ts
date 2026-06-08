import { apiClient } from "./client";
import type { components } from "./generated/openapi";
import { assertSuccessfulResponse, requireData } from "./response";

export type Worker = components["schemas"]["WorkerResponse"];
export type WorkerRequest = components["schemas"]["WorkerRequest"];
export type SourceConnection =
  components["schemas"]["SourceConnectionResponse"];
export type SourceConnectionCreateRequest =
  components["schemas"]["SourceConnectionCreateRequest"];
export type SourceConnectionUpdateRequest =
  components["schemas"]["SourceConnectionUpdateRequest"];
export type Destination = components["schemas"]["DestinationResponse"];
export type DestinationCreateRequest =
  components["schemas"]["DestinationCreateRequest"];
export type DestinationUpdateRequest =
  components["schemas"]["DestinationUpdateRequest"];

export async function listWorkers(): Promise<Worker[]> {
  const { data, error, response } = await apiClient.GET("/api/v1/workers");

  assertSuccessfulResponse(response, error, "No se pudieron cargar los workers");
  return requireData(data, "workers");
}

export async function createWorker(payload: WorkerRequest): Promise<Worker> {
  const { data, error, response } = await apiClient.POST("/api/v1/workers", {
    body: payload,
  });

  assertSuccessfulResponse(response, error, "No se pudo crear el worker");
  return requireData(data, "worker creado");
}

export async function updateWorker(
  workerInternalId: string,
  payload: WorkerRequest,
): Promise<Worker> {
  const { data, error, response } = await apiClient.PUT(
    "/api/v1/workers/{worker_internal_id}",
    {
      params: {
        path: {
          worker_internal_id: workerInternalId,
        },
      },
      body: payload,
    },
  );

  assertSuccessfulResponse(response, error, "No se pudo actualizar el worker");
  return requireData(data, "worker actualizado");
}

export async function deleteWorker(workerInternalId: string): Promise<void> {
  const { error, response } = await apiClient.DELETE(
    "/api/v1/workers/{worker_internal_id}",
    {
      params: {
        path: {
          worker_internal_id: workerInternalId,
        },
      },
    },
  );

  assertSuccessfulResponse(response, error, "No se pudo eliminar el worker");
}

export async function listSourceConnections(): Promise<SourceConnection[]> {
  const { data, error, response } = await apiClient.GET(
    "/api/v1/source-connections",
  );

  assertSuccessfulResponse(
    response,
    error,
    "No se pudieron cargar los orígenes",
  );
  return requireData(data, "orígenes");
}

export async function createSourceConnection(
  payload: SourceConnectionCreateRequest,
): Promise<SourceConnection> {
  const { data, error, response } = await apiClient.POST(
    "/api/v1/source-connections",
    {
      body: payload,
    },
  );

  assertSuccessfulResponse(response, error, "No se pudo crear el origen");
  return requireData(data, "origen creado");
}

export async function updateSourceConnection(
  sourceConnectionId: string,
  payload: SourceConnectionUpdateRequest,
): Promise<SourceConnection> {
  const { data, error, response } = await apiClient.PUT(
    "/api/v1/source-connections/{source_connection_id}",
    {
      params: {
        path: {
          source_connection_id: sourceConnectionId,
        },
      },
      body: payload,
    },
  );

  assertSuccessfulResponse(response, error, "No se pudo actualizar el origen");
  return requireData(data, "origen actualizado");
}

export async function deleteSourceConnection(
  sourceConnectionId: string,
): Promise<void> {
  const { error, response } = await apiClient.DELETE(
    "/api/v1/source-connections/{source_connection_id}",
    {
      params: {
        path: {
          source_connection_id: sourceConnectionId,
        },
      },
    },
  );

  assertSuccessfulResponse(response, error, "No se pudo eliminar el origen");
}

export async function listDestinations(): Promise<Destination[]> {
  const { data, error, response } = await apiClient.GET("/api/v1/destinations");

  assertSuccessfulResponse(
    response,
    error,
    "No se pudieron cargar los destinos",
  );
  return requireData(data, "destinos");
}

export async function createDestination(
  payload: DestinationCreateRequest,
): Promise<Destination> {
  const { data, error, response } = await apiClient.POST(
    "/api/v1/destinations",
    {
      body: payload,
    },
  );

  assertSuccessfulResponse(response, error, "No se pudo crear el destino");
  return requireData(data, "destino creado");
}

export async function updateDestination(
  destinationId: string,
  payload: DestinationUpdateRequest,
): Promise<Destination> {
  const { data, error, response } = await apiClient.PUT(
    "/api/v1/destinations/{destination_id}",
    {
      params: {
        path: {
          destination_id: destinationId,
        },
      },
      body: payload,
    },
  );

  assertSuccessfulResponse(response, error, "No se pudo actualizar el destino");
  return requireData(data, "destino actualizado");
}

export async function deleteDestination(destinationId: string): Promise<void> {
  const { error, response } = await apiClient.DELETE(
    "/api/v1/destinations/{destination_id}",
    {
      params: {
        path: {
          destination_id: destinationId,
        },
      },
    },
  );

  assertSuccessfulResponse(response, error, "No se pudo eliminar el destino");
}
