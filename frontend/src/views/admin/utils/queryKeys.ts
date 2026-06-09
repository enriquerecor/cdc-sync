export const CONTROL_PLANE_QUERY_KEYS = {
  workers: ["control-plane-admin", "workers"],
  sourceConnections: ["control-plane-admin", "source-connections"],
  destinations: ["control-plane-admin", "destinations"],
  syncConfigs: ["control-plane-admin", "configs"],
} as const;
