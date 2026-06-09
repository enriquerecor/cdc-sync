export type CredentialsFormValues = {
  credentialsUser: string;
  credentialsPassword: string;
};

export type EntityFormMode = "create" | "edit";

export type WorkerFormValues = {
  workerId: string;
  name: string;
  description: string;
  kafkaGroupId: string;
  enabled: boolean;
};

export type SourceConnectionFormValues = CredentialsFormValues & {
  name: string;
  sourceType: string;
  host: string;
  port: number | "";
  databaseName: string;
};

export type DestinationFormValues = CredentialsFormValues & {
  name: string;
  destinationType: string;
  host: string;
  port: number | "";
  secure: boolean;
  databaseName: string;
};

export type DestinationColumnFormValues = {
  name: string;
  destinationType: string;
  nullable: boolean;
};

export type ConfiguredTableFormValues = {
  logicalName: string;
  sourceSchema: string;
  sourceTable: string;
  cdcTopic: string;
  destinationTable: string;
  primaryKeyFields: string;
  destinationColumns: DestinationColumnFormValues[];
  enabled: boolean;
};

export type SyncConfigFormValues = {
  name: string;
  sourceConnectionId: string;
  destinationId: string;
  syncMode: string;
  tables: ConfiguredTableFormValues[];
  enabled: boolean;
};

export type AssignmentFormValues = {
  workerInternalId: string;
  configId: string;
};

export type MaterializationFormValues = {
  sourceConnectionId: string;
};

export type RuntimeLookupFormValues = {
  workerId: string;
};
