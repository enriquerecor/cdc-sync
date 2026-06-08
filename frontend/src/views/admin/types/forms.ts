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
