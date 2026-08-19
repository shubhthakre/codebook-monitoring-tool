export type MonitorType =
  | "http"
  | "tcp"
  | "postgres"
  | "mysql"
  | "sqlite"
  | "oracle"
  | "systemd"
  | "smtp"
  | "graph";

export interface Monitor {
  id: number;
  name: string;
  type: MonitorType;
  config: Record<string, unknown>;
  interval_seconds: number;
  enabled: boolean;
  last_status: "up" | "down" | "unknown";
  last_message: string | null;
  last_checked_at: string | null;
  last_response_ms: number | null;
  created_at: string;
  updated_at: string;
}

export interface HealthSummary {
  total: number;
  up: number;
  down: number;
  unknown: number;
}

export interface CheckResult {
  id: number;
  monitor_id: number;
  status: string;
  message: string | null;
  response_ms: number | null;
  details: Record<string, unknown> | null;
  checked_at: string;
}

export interface SystemdLogs {
  monitor_id: number;
  unit: string;
  active: boolean;
  since: string | null;
  until: string | null;
  grep: string | null;
  count: number;
  lines: string[];
}

export interface AppSettings {
  alert_enabled: boolean;
  alert_to: string;
  alert_from: string;
  alert_on_recovery: boolean;
  alert_cooldown_seconds: number;
  smtp_host: string;
  smtp_port: number;
  smtp_user: string;
  smtp_password_set: boolean;
  smtp_use_tls: boolean;
  smtp_use_ssl: boolean;
  oracle_client_lib_dir: string;
  oracle_client_resolved: string;
  oracle_client_platform: string;
  configured: boolean;
  source: "ui" | "env" | string;
  oracle_restart_required: boolean;
}

export type AppSettingsUpdate = Omit<
  AppSettings,
  | "smtp_password_set"
  | "configured"
  | "source"
  | "oracle_restart_required"
  | "oracle_client_resolved"
  | "oracle_client_platform"
> & {
  smtp_password?: string;
};

const API = "/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const detail = err.detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((d: { msg?: string }) => d.msg ?? JSON.stringify(d)).join(", ")
          : "Request failed";
    throw new Error(message);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  getSummary: () => request<HealthSummary>("/summary"),
  getMonitors: () => request<Monitor[]>("/monitors"),
  getMonitor: (id: number) => request<Monitor>(`/monitors/${id}`),
  createMonitor: (data: {
    name: string;
    type: MonitorType;
    config: Record<string, unknown>;
    interval_seconds: number;
    enabled: boolean;
  }) =>
    request<Monitor>("/monitors", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateMonitor: (
    id: number,
    data: Partial<{
      name: string;
      config: Record<string, unknown>;
      interval_seconds: number;
      enabled: boolean;
    }>
  ) =>
    request<Monitor>(`/monitors/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  deleteMonitor: (id: number) =>
    request<void>(`/monitors/${id}`, { method: "DELETE" }),
  checkNow: (id: number) =>
    request<{
      monitor_id: number;
      status: string;
      message: string | null;
      response_ms: number | null;
      details: Record<string, unknown> | null;
    }>(`/monitors/${id}/check`, { method: "POST" }),
  getHistory: (id: number, limit = 50) =>
    request<CheckResult[]>(`/monitors/${id}/history?limit=${limit}`),
  getLogs: (
    id: number,
    opts?: { since?: string; until?: string; lines?: number; grep?: string }
  ) => {
    const params = new URLSearchParams();
    if (opts?.since) params.set("since", opts.since);
    if (opts?.until) params.set("until", opts.until);
    if (opts?.lines != null) params.set("lines", String(opts.lines));
    if (opts?.grep != null) params.set("grep", opts.grep);
    const qs = params.toString();
    return request<SystemdLogs>(
      `/monitors/${id}/logs${qs ? `?${qs}` : ""}`
    );
  },
  getSettings: () => request<AppSettings>("/settings"),
  updateSettings: (data: AppSettingsUpdate) =>
    request<AppSettings>("/settings", {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  testEmail: () =>
    request<{ ok: boolean; message: string }>("/settings/test-email", {
      method: "POST",
    }),
};

export const MONITOR_TYPES: {
  value: MonitorType;
  label: string;
  description: string;
  fields: { key: string; label: string; type?: string; placeholder?: string; required?: boolean }[];
}[] = [
  {
    value: "http",
    label: "HTTP / Server",
    description: "Check a URL or web endpoint",
    fields: [
      { key: "url", label: "URL", placeholder: "https://example.com/health", required: true },
      { key: "method", label: "Method", placeholder: "GET" },
      { key: "expected_status", label: "Expected Status", placeholder: "200" },
      { key: "timeout", label: "Timeout (sec)", placeholder: "10" },
      { key: "verify_ssl", label: "Verify SSL (true/false)", placeholder: "true" },
    ],
  },
  {
    value: "tcp",
    label: "TCP / Port",
    description: "Check if a host:port is reachable",
    fields: [
      { key: "host", label: "Host", placeholder: "192.168.1.1", required: true },
      { key: "port", label: "Port", placeholder: "443", required: true },
      { key: "timeout", label: "Timeout (sec)", placeholder: "5" },
    ],
  },
  {
    value: "postgres",
    label: "PostgreSQL",
    description: "Test PostgreSQL database connection",
    fields: [
      { key: "host", label: "Host", placeholder: "localhost", required: true },
      { key: "port", label: "Port", placeholder: "5432" },
      { key: "database", label: "Database", placeholder: "postgres", required: true },
      { key: "user", label: "User", placeholder: "postgres", required: true },
      { key: "password", label: "Password", type: "password" },
      { key: "query", label: "Test Query", placeholder: "SELECT 1" },
    ],
  },
  {
    value: "mysql",
    label: "MySQL",
    description: "Test MySQL database connection",
    fields: [
      { key: "host", label: "Host", placeholder: "localhost", required: true },
      { key: "port", label: "Port", placeholder: "3306" },
      { key: "database", label: "Database", placeholder: "mydb" },
      { key: "user", label: "User", placeholder: "root", required: true },
      { key: "password", label: "Password", type: "password" },
      { key: "query", label: "Test Query", placeholder: "SELECT 1" },
    ],
  },
  {
    value: "sqlite",
    label: "SQLite",
    description: "Test a local SQLite database file",
    fields: [
      { key: "path", label: "File Path", placeholder: "/path/to/db.sqlite", required: true },
      { key: "query", label: "Test Query", placeholder: "SELECT 1" },
    ],
  },
  {
    value: "oracle",
    label: "Oracle",
    description: "Test Oracle database connection",
    fields: [
      { key: "host", label: "Host", placeholder: "localhost", required: true },
      { key: "port", label: "Port", placeholder: "1521" },
      { key: "service_name", label: "Service Name", placeholder: "ORCL (not 'oracle')" },
      { key: "dsn", label: "DSN (optional)", placeholder: "10.210.9.25:1521/ORCL" },
      { key: "user", label: "User", required: true },
      { key: "password", label: "Password", type: "password" },
      { key: "query", label: "Test Query", placeholder: "SELECT 1 FROM DUAL" },
    ],
  },
  {
    value: "systemd",
    label: "Systemd Logs",
    description: "Fetch journal logs for a Linux service (requires Linux + journalctl)",
    fields: [
      { key: "unit", label: "Unit Name", placeholder: "nginx.service", required: true },
      { key: "lines", label: "Lines", placeholder: "50" },
      { key: "since", label: "Since", placeholder: "1 hour ago" },
      {
        key: "grep",
        label: "Grep filter",
        placeholder: "error|warning (optional PCRE)",
      },
    ],
  },
  {
    value: "smtp",
    label: "SMTP",
    description: "Test SMTP server connection (and optional login) without sending mail",
    fields: [
      { key: "host", label: "Host", placeholder: "smtp.example.com", required: true },
      { key: "port", label: "Port", placeholder: "587" },
      { key: "user", label: "User (optional)" },
      { key: "password", label: "Password (optional)", type: "password" },
      {
        key: "use_tls",
        label: "STARTTLS (true/false)",
        placeholder: "true (typical for 587)",
      },
      {
        key: "use_ssl",
        label: "SSL (true/false)",
        placeholder: "false (true for port 465)",
      },
      { key: "timeout", label: "Timeout (sec)", placeholder: "10" },
    ],
  },
  {
    value: "graph",
    label: "Microsoft Graph",
    description: "OAuth client-credentials token + Graph API call",
    fields: [
      {
        key: "tenant_id",
        label: "Tenant ID",
        placeholder: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        required: true,
      },
      {
        key: "client_id",
        label: "Client ID (App ID)",
        placeholder: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        required: true,
      },
      {
        key: "client_secret",
        label: "Client Secret",
        type: "password",
        required: true,
      },
      {
        key: "scope",
        label: "Scope",
        placeholder: "https://graph.microsoft.com/.default",
      },
      {
        key: "endpoint",
        label: "Graph endpoint",
        placeholder: "https://graph.microsoft.com/v1.0/",
      },
      { key: "timeout", label: "Timeout (sec)", placeholder: "15" },
    ],
  },
];
