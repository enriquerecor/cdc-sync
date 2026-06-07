import { AdminShell } from "./app/AdminShell";
import { AppProviders } from "./app/AppProviders";

export function App() {
  return (
    <AppProviders>
      <AdminShell />
    </AppProviders>
  );
}
