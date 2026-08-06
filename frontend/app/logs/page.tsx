import { Suspense } from "react";
import SystemdLogsPage from "./LogsClient";

export default function LogsRoute() {
  return (
    <Suspense
      fallback={
        <div className="container">
          <p style={{ color: "var(--text-muted)" }}>Loading logs...</p>
        </div>
      }
    >
      <SystemdLogsPage />
    </Suspense>
  );
}
