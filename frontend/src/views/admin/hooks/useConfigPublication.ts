import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";

import {
  assignConfigToWorker,
  listSourceConnections,
  listSyncConfigs,
  listWorkers,
  materializeSourceCdcConnector,
  type AssignmentResponse,
  type CdcConnectorMaterializationResponse,
} from "../../../api/controlPlaneAdmin";
import {
  getWorkerRuntimeConfig,
  type WorkerRuntimeConfigResponse,
} from "../../../api/workerRuntime";
import type {
  AssignmentFormValues,
  MaterializationFormValues,
  RuntimeLookupFormValues,
} from "../types/forms";
import {
  showApiErrorNotification,
  showSuccessNotification,
} from "../utils/notifications";
import { CONTROL_PLANE_QUERY_KEYS } from "../utils/queryKeys";

export function useConfigPublication() {
  const [assignment, setAssignment] = useState<AssignmentResponse | null>(null);
  const [materializedConnector, setMaterializedConnector] =
    useState<CdcConnectorMaterializationResponse | null>(null);
  const [runtimeConfig, setRuntimeConfig] =
    useState<WorkerRuntimeConfigResponse | null>(null);

  const workersQuery = useQuery({
    queryKey: CONTROL_PLANE_QUERY_KEYS.workers,
    queryFn: listWorkers,
  });
  const syncConfigsQuery = useQuery({
    queryKey: CONTROL_PLANE_QUERY_KEYS.syncConfigs,
    queryFn: listSyncConfigs,
  });
  const sourceConnectionsQuery = useQuery({
    queryKey: CONTROL_PLANE_QUERY_KEYS.sourceConnections,
    queryFn: listSourceConnections,
  });

  const assignmentMutation = useMutation({
    mutationFn: (values: AssignmentFormValues) =>
      assignConfigToWorker(values.workerInternalId, values.configId),
    onMutate: () => {
      setAssignment(null);
    },
    onSuccess: (response) => {
      setAssignment(response);
      showSuccessNotification(
        "Configuración asignada",
        "El worker cargará esta configuración en el próximo arranque manual",
      );
    },
    onError: (error) => {
      setAssignment(null);
      showApiErrorNotification(error);
    },
  });

  const materializationMutation = useMutation({
    mutationFn: (values: MaterializationFormValues) =>
      materializeSourceCdcConnector(values.sourceConnectionId),
    onMutate: () => {
      setMaterializedConnector(null);
    },
    onSuccess: (response) => {
      setMaterializedConnector(response);
      showSuccessNotification(
        "Conector materializado",
        "Kafka Connect recibió la configuración CDC",
      );
    },
    onError: (error) => {
      setMaterializedConnector(null);
      showApiErrorNotification(error);
    },
  });

  const runtimeLookupMutation = useMutation({
    mutationFn: (values: RuntimeLookupFormValues) =>
      getWorkerRuntimeConfig(values.workerId.trim()),
    onMutate: () => {
      setRuntimeConfig(null);
    },
    onSuccess: (response) => {
      setRuntimeConfig(response);
      showSuccessNotification(
        "Runtime cargado",
        "Se recibió el contrato publicado para el worker",
      );
    },
    onError: (error) => {
      setRuntimeConfig(null);
      showApiErrorNotification(error);
    },
  });

  return {
    workersQuery,
    syncConfigsQuery,
    sourceConnectionsQuery,
    assignment,
    materializedConnector,
    runtimeConfig,
    isAssigning: assignmentMutation.isPending,
    isMaterializing: materializationMutation.isPending,
    isLoadingRuntime: runtimeLookupMutation.isPending,
    assignConfig: assignmentMutation.mutate,
    materializeConnector: materializationMutation.mutate,
    loadRuntimeConfig: runtimeLookupMutation.mutate,
  };
}
