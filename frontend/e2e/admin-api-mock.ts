import type { Page, Route } from "@playwright/test";

import type { components } from "../src/api/generated/openapi";

export type WorkerRequest = components["schemas"]["WorkerRequest"];
export type WorkerResponse = components["schemas"]["WorkerResponse"];
export type SourceConnectionCreateRequest =
  components["schemas"]["SourceConnectionCreateRequest"];
export type SourceConnectionResponse =
  components["schemas"]["SourceConnectionResponse"];
export type DestinationCreateRequest =
  components["schemas"]["DestinationCreateRequest"];
export type DestinationResponse =
  components["schemas"]["DestinationResponse"];
export type SyncConfigResponse = components["schemas"]["SyncConfigResponse"];

const API_BASE_URL = "http://127.0.0.1:8000";

const corsHeaders = {
  "access-control-allow-headers": "content-type",
  "access-control-allow-methods": "GET,POST,PUT,DELETE,OPTIONS",
  "access-control-allow-origin": "*",
};

export type AdminApiMockState = {
  workers: WorkerResponse[];
  sourceConnections: SourceConnectionResponse[];
  destinations: DestinationResponse[];
  syncConfigs: SyncConfigResponse[];
  receivedWorkerPayload: unknown;
  receivedSourceConnectionPayload: unknown;
  receivedDestinationPayload: unknown;
};

export function createAdminApiMockState(
  overrides: Partial<AdminApiMockState> = {},
): AdminApiMockState {
  return {
    workers: [],
    sourceConnections: [],
    destinations: [],
    syncConfigs: [],
    receivedWorkerPayload: null,
    receivedSourceConnectionPayload: null,
    receivedDestinationPayload: null,
    ...overrides,
  };
}

export async function setupAdminApiMocks(
  page: Page,
  state: AdminApiMockState,
): Promise<void> {
  await page.route(`${API_BASE_URL}/**`, async (route) => {
    const request = route.request();
    const requestUrl = new URL(request.url());
    const routeKey = `${request.method()} ${requestUrl.pathname}`;

    switch (routeKey) {
      case "GET /health":
        await fulfillJson(route, 200, {
          status: "ok",
          checks: {
            database: "ok",
          },
        });
        return;

      case "GET /api/v1/workers":
        await fulfillJson(route, 200, state.workers);
        return;

      case "OPTIONS /api/v1/workers":
        await fulfillNoContent(route);
        return;

      case "POST /api/v1/workers":
        state.receivedWorkerPayload = request.postDataJSON();
        state.workers = [
          buildCreatedWorker(state.receivedWorkerPayload as WorkerRequest),
        ];
        await fulfillJson(route, 201, state.workers[0]);
        return;

      case "GET /api/v1/source-connections":
        await fulfillJson(route, 200, state.sourceConnections);
        return;

      case "OPTIONS /api/v1/source-connections":
        await fulfillNoContent(route);
        return;

      case "POST /api/v1/source-connections":
        state.receivedSourceConnectionPayload = request.postDataJSON();
        state.sourceConnections = [
          buildCreatedSourceConnection(
            state.receivedSourceConnectionPayload as SourceConnectionCreateRequest,
          ),
        ];
        await fulfillJson(route, 201, state.sourceConnections[0]);
        return;

      case "GET /api/v1/destinations":
        await fulfillJson(route, 200, state.destinations);
        return;

      case "OPTIONS /api/v1/destinations":
        await fulfillNoContent(route);
        return;

      case "POST /api/v1/destinations":
        state.receivedDestinationPayload = request.postDataJSON();
        state.destinations = [
          buildCreatedDestination(
            state.receivedDestinationPayload as DestinationCreateRequest,
          ),
        ];
        await fulfillJson(route, 201, state.destinations[0]);
        return;

      case "GET /api/v1/configs":
        await fulfillJson(route, 200, state.syncConfigs);
        return;

      default:
        throw new Error(`Petición API no mockeada: ${routeKey}`);
    }
  });
}

function buildCreatedWorker(payload: WorkerRequest): WorkerResponse {
  return {
    id: "11111111-1111-4111-8111-111111111111",
    worker_id: payload.worker_id,
    name: payload.name,
    description: payload.description ?? null,
    kafka_group_id: payload.kafka_group_id ?? null,
    enabled: payload.enabled,
  };
}

function buildCreatedSourceConnection(
  payload: SourceConnectionCreateRequest,
): SourceConnectionResponse {
  return {
    id: "22222222-2222-4222-8222-222222222222",
    name: payload.name,
    source_type: payload.source_type,
    host: payload.host,
    port: payload.port,
    database_name: payload.database_name,
    credentials_configured: true,
  };
}

function buildCreatedDestination(
  payload: DestinationCreateRequest,
): DestinationResponse {
  return {
    id: "33333333-3333-4333-8333-333333333333",
    name: payload.name,
    destination_type: payload.destination_type,
    host: payload.host,
    port: payload.port,
    secure: payload.secure,
    database_name: payload.database_name,
    credentials_configured: true,
  };
}

async function fulfillNoContent(route: Route): Promise<void> {
  await route.fulfill({
    status: 204,
    headers: corsHeaders,
  });
}

async function fulfillJson(
  route: Route,
  status: number,
  body: unknown,
): Promise<void> {
  await route.fulfill({
    status,
    headers: corsHeaders,
    contentType: "application/json",
    json: body,
  });
}
