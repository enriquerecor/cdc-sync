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
export type SyncConfig = components["schemas"]["SyncConfigResponse"];
export type SyncConfigRequest = components["schemas"]["SyncConfigRequest"];
export type ConfiguredTableRequest =
  components["schemas"]["ConfiguredTableRequest"];
export type DestinationColumnRequest =
  components["schemas"]["DestinationColumnRequest"];
export type AssignmentResponse = components["schemas"]["AssignmentResponse"];
export type CdcConnectorMaterializationResponse =
  components["schemas"]["CdcConnectorMaterializationResponse"];

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

export async function listSyncConfigs(): Promise<SyncConfig[]> {
  const { data, error, response } = await apiClient.GET("/api/v1/configs");

  assertSuccessfulResponse(
    response,
    error,
    "No se pudieron cargar las configuraciones",
  );
  return requireData(data, "configuraciones");
}

export async function createSyncConfig(
  payload: SyncConfigRequest,
): Promise<SyncConfig> {
  const { data, error, response } = await apiClient.POST("/api/v1/configs", {
    body: payload,
  });

  assertSuccessfulResponse(response, error, "No se pudo crear la configuración");
  return requireData(data, "configuración creada");
}

export async function updateSyncConfig(
  configId: string,
  payload: SyncConfigRequest,
): Promise<SyncConfig> {
  const { data, error, response } = await apiClient.PUT(
    "/api/v1/configs/{config_id}",
    {
      params: {
        path: {
          config_id: configId,
        },
      },
      body: payload,
    },
  );

  assertSuccessfulResponse(
    response,
    error,
    "No se pudo actualizar la configuración",
  );
  return requireData(data, "configuración actualizada");
}

export async function deleteSyncConfig(configId: string): Promise<void> {
  const { error, response } = await apiClient.DELETE(
    "/api/v1/configs/{config_id}",
    {
      params: {
        path: {
          config_id: configId,
        },
      },
    },
  );

  assertSuccessfulResponse(
    response,
    error,
    "No se pudo eliminar la configuración",
  );
}

export async function assignConfigToWorker(
  workerInternalId: string,
  configId: string,
): Promise<AssignmentResponse> {
  const { data, error, response } = await apiClient.PUT(
    "/api/v1/workers/{worker_internal_id}/config-assignment",
    {
      params: {
        path: {
          worker_internal_id: workerInternalId,
        },
      },
      body: {
        config_id: configId,
      },
    },
  );

  assertSuccessfulResponse(response, error, "No se pudo asignar la configuración");
  return requireData(data, "asignación publicada");
}

export async function materializeSourceCdcConnector(
  sourceConnectionId: string,
): Promise<CdcConnectorMaterializationResponse> {
  const { data, error, response } = await apiClient.PUT(
    "/api/v1/source-connections/{source_connection_id}/cdc-connector",
    {
      params: {
        path: {
          source_connection_id: sourceConnectionId,
        },
      },
    },
  );

  assertSuccessfulResponse(response, error, "No se pudo materializar CDC");
  return requireData(data, "conector CDC materializado");
}
