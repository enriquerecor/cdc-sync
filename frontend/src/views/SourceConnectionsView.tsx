import { EmptyAdministrativeView } from "../components/FeedbackState";

export function SourceConnectionsView() {
  return (
    <EmptyAdministrativeView
      title="Orígenes PostgreSQL"
      description="Sección preparada para gestionar conexiones de origen y sus parámetros administrativos sin exponer secretos en lectura."
    />
  );
}
