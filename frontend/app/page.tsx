"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  api,
  CheckResult,
  Monitor,
  MONITOR_TYPES,
  MonitorType,
} from "@/lib/api";

function StatusDot({ status }: { status: string }) {
  return <span className={`status-dot ${status}`} title={status} />;
}

function formatTime(iso: string | null) {
  if (!iso) return "Never";
  return new Date(iso).toLocaleString();
}

interface MonitorFormProps {
  onClose: () => void;
  onSaved: () => void;
  editMonitor?: Monitor | null;
}

function MonitorForm({ onClose, onSaved, editMonitor }: MonitorFormProps) {
  const [name, setName] = useState(editMonitor?.name ?? "");
  const [type, setType] = useState<MonitorType>(editMonitor?.type ?? "http");
  const [interval, setInterval] = useState(editMonitor?.interval_seconds ?? 60);
  const [enabled, setEnabled] = useState(editMonitor?.enabled ?? true);
  const [config, setConfig] = useState<Record<string, string>>(
    Object.fromEntries(
      Object.entries(editMonitor?.config ?? {}).map(([k, v]) => [k, String(v)])
    )
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const typeDef = MONITOR_TYPES.find((t) => t.value === type)!;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);

    const parsedConfig: Record<string, unknown> = {};
    for (const [key, val] of Object.entries(config)) {
      if (val === "") continue;
      if (["port", "expected_status", "timeout", "lines"].includes(key)) {
        parsedConfig[key] = Number(val);
      } else {
        parsedConfig[key] = val;
      }
    }

    try {
      if (editMonitor) {
        await api.updateMonitor(editMonitor.id, {
          name,
          config: parsedConfig,
          interval_seconds: interval,
          enabled,
        });
      } else {
        await api.createMonitor({
          name,
          type,
          config: parsedConfig,
          interval_seconds: interval,
          enabled,
        });
      }
      onSaved();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>{editMonitor ? "Edit Monitor" : "Add Monitor"}</h2>
        {error && <div className="error-banner">{error}</div>}
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Production API"
              required
            />
          </div>

          {!editMonitor && (
            <div className="form-group">
              <label>Type</label>
              <select
                value={type}
                onChange={(e) => {
                  setType(e.target.value as MonitorType);
                  setConfig({});
                }}
              >
                {MONITOR_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
              <small style={{ color: "var(--text-muted)" }}>
                {typeDef.description}
              </small>
            </div>
          )}

          {typeDef.fields.map((field) => (
            <div className="form-group" key={field.key}>
              <label>
                {field.label}
                {field.required && " *"}
              </label>
              <input
                type={field.type ?? "text"}
                value={config[field.key] ?? ""}
                onChange={(e) =>
                  setConfig({ ...config, [field.key]: e.target.value })
                }
                placeholder={field.placeholder}
                required={field.required}
              />
            </div>
          ))}

          <div className="form-row">
            <div className="form-group">
              <label>Check Interval (seconds)</label>
              <input
                type="number"
                min={10}
                max={86400}
                value={interval}
                onChange={(e) => setInterval(Number(e.target.value))}
              />
            </div>
            <div className="form-group">
              <label>Enabled</label>
              <select
                value={enabled ? "yes" : "no"}
                onChange={(e) => setEnabled(e.target.value === "yes")}
              >
                <option value="yes">Yes</option>
                <option value="no">No</option>
              </select>
            </div>
          </div>

          <div className="form-actions">
            <button type="button" className="btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? "Saving..." : editMonitor ? "Update" : "Create"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

interface DetailPanelProps {
  monitor: Monitor;
  onClose: () => void;
  onRefresh: () => void;
}

function DetailPanel({ monitor, onClose, onRefresh }: DetailPanelProps) {
  const [history, setHistory] = useState<CheckResult[]>([]);
  const [logs, setLogs] = useState<string[]>([]);
  const [checking, setChecking] = useState(false);

  const load = useCallback(async () => {
    const h = await api.getHistory(monitor.id);
    setHistory(h);
    const latest = h[0];
    if (
      monitor.type === "systemd" &&
      latest?.details &&
      Array.isArray(latest.details.lines)
    ) {
      setLogs(latest.details.lines as string[]);
    }
  }, [monitor.id, monitor.type]);

  useEffect(() => {
    load();
  }, [load]);

  const handleCheck = async () => {
    setChecking(true);
    try {
      const result = await api.checkNow(monitor.id);
      if (
        monitor.type === "systemd" &&
        result.details &&
        Array.isArray(result.details.lines)
      ) {
        setLogs(result.details.lines as string[]);
      }
      await load();
      onRefresh();
    } finally {
      setChecking(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal"
        style={{ maxWidth: 720 }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "1rem" }}>
          <StatusDot status={monitor.last_status} />
          <h2 style={{ margin: 0 }}>{monitor.name}</h2>
          <span className="badge">{monitor.type}</span>
        </div>

        <p className="monitor-meta" style={{ marginBottom: "1rem" }}>
          {monitor.last_message ?? "No message"} · Last checked:{" "}
          {formatTime(monitor.last_checked_at)}
          {monitor.last_response_ms != null &&
            ` · ${monitor.last_response_ms.toFixed(0)}ms`}
        </p>

        <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1.5rem" }}>
          <button
            className="btn-primary btn-sm"
            onClick={handleCheck}
            disabled={checking}
          >
            {checking ? "Checking..." : "Check Now"}
          </button>
          <button className="btn-secondary btn-sm" onClick={onClose}>
            Close
          </button>
        </div>

        {monitor.type === "systemd" && (
          <>
            {logs.length > 0 && (
              <>
                <h3 style={{ fontSize: "0.9375rem", marginBottom: "0.5rem" }}>
                  Systemd Logs
                </h3>
                <div className="log-viewer">{logs.join("\n")}</div>
              </>
            )}
            <Link
              href={`/logs?id=${monitor.id}`}
              className="btn-secondary btn-sm"
              style={{ display: "inline-block", marginTop: "0.75rem" }}
            >
              Open full logs viewer →
            </Link>
          </>
        )}

        <h3 style={{ fontSize: "0.9375rem", margin: "1.5rem 0 0.5rem" }}>
          Check History
        </h3>
        <table className="history-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Status</th>
              <th>Message</th>
              <th>Response</th>
            </tr>
          </thead>
          <tbody>
            {history.map((row) => (
              <tr key={row.id}>
                <td>{formatTime(row.checked_at)}</td>
                <td>
                  <StatusDot status={row.status} />
                </td>
                <td>{row.message}</td>
                <td>
                  {row.response_ms != null
                    ? `${row.response_ms.toFixed(0)}ms`
                    : "—"}
                </td>
              </tr>
            ))}
            {history.length === 0 && (
              <tr>
                <td colSpan={4} style={{ color: "var(--text-muted)" }}>
                  No history yet
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [monitors, setMonitors] = useState<Monitor[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editMonitor, setEditMonitor] = useState<Monitor | null>(null);
  const [detailMonitor, setDetailMonitor] = useState<Monitor | null>(null);
  const [checkingId, setCheckingId] = useState<number | null>(null);
  const [actionsOpenId, setActionsOpenId] = useState<number | null>(null);

  const refresh = useCallback(async () => {
    try {
      const m = await api.getMonitors();
      setMonitors(m);
      setError(null);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to connect to backend. Is it running on port 8000?"
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 15000);
    return () => clearInterval(interval);
  }, [refresh]);

  useEffect(() => {
    if (actionsOpenId == null) return;
    const close = () => setActionsOpenId(null);
    document.addEventListener("click", close);
    return () => document.removeEventListener("click", close);
  }, [actionsOpenId]);

  const handleCheck = async (id: number) => {
    setCheckingId(id);
    try {
      await api.checkNow(id);
      await refresh();
    } finally {
      setCheckingId(null);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this monitor?")) return;
    await api.deleteMonitor(id);
    await refresh();
  };

  const handleToggle = async (monitor: Monitor) => {
    await api.updateMonitor(monitor.id, { enabled: !monitor.enabled });
    await refresh();
  };

  const dashboardMonitors = monitors.filter((m) => m.type !== "systemd");
  const summary = {
    total: dashboardMonitors.length,
    up: dashboardMonitors.filter((m) => m.last_status === "up").length,
    down: dashboardMonitors.filter((m) => m.last_status === "down").length,
  };

  return (
    <div className="container">
      <header className="header">
        <div>
          <h1>Codebook Monitoring</h1>
          <p style={{ color: "var(--text-muted)", fontSize: "0.875rem" }}>
            Servers · Databases · Systemd logs
          </p>
        </div>
        <div className="header-actions">
          <nav className="nav-links">
            <Link href="/" className="nav-active">
              Dashboard
            </Link>
            <Link href="/logs">Systemd Logs</Link>
          </nav>
          <button className="btn-primary" onClick={() => setShowForm(true)}>
            + Add Monitor
          </button>
        </div>
      </header>

      {error && <div className="error-banner">{error}</div>}

      {!loading && (
        <div className="summary-grid">
          <div className="summary-card">
            <div className="value">{summary.total}</div>
            <div className="label">Total</div>
          </div>
          <div className="summary-card up">
            <div className="value">{summary.up}</div>
            <div className="label">Up</div>
          </div>
          <div className="summary-card down">
            <div className="value">{summary.down}</div>
            <div className="label">Down</div>
          </div>
        </div>
      )}

      {loading ? (
        <p style={{ color: "var(--text-muted)" }}>Loading...</p>
      ) : dashboardMonitors.length === 0 ? (
        <div className="empty-state">
          <p>No monitors configured yet.</p>
          <button
            className="btn-primary"
            style={{ marginTop: "1rem" }}
            onClick={() => setShowForm(true)}
          >
            Add your first monitor
          </button>
        </div>
      ) : (
        <div className="monitor-list">
          {dashboardMonitors.map((m) => (
            <div className="monitor-card" key={m.id}>
              <div
                className="monitor-card-header"
                style={{ cursor: "pointer" }}
                onClick={() => setDetailMonitor(m)}
              >
                <StatusDot status={m.last_status} />
                <div className="monitor-info">
                  <h3>{m.name}</h3>
                  <div className="monitor-meta">
                    <span className="badge">{m.type}</span>
                    <span className="monitor-meta-sep">·</span>
                    <span>{m.last_message ?? "Not checked yet"}</span>
                    <span className="monitor-meta-sep">·</span>
                    <span>{formatTime(m.last_checked_at)}</span>
                    {m.last_response_ms != null && (
                      <>
                        <span className="monitor-meta-sep">·</span>
                        <span>{m.last_response_ms.toFixed(0)}ms</span>
                      </>
                    )}
                    {!m.enabled && (
                      <>
                        <span className="monitor-meta-sep">·</span>
                        <span>Disabled</span>
                      </>
                    )}
                  </div>
                </div>
              </div>
              <div className="monitor-actions">
                <button
                  className="btn-secondary btn-sm"
                  onClick={() => handleCheck(m.id)}
                  disabled={checkingId === m.id}
                >
                  {checkingId === m.id ? "..." : "Check"}
                </button>
                <div className="monitor-actions-menu">
                  <button
                    className="btn-secondary btn-sm"
                    aria-expanded={actionsOpenId === m.id}
                    aria-label="More actions"
                    onClick={(e) => {
                      e.stopPropagation();
                      setActionsOpenId(actionsOpenId === m.id ? null : m.id);
                    }}
                  >
                    ⋯
                  </button>
                  {actionsOpenId === m.id && (
                    <div className="monitor-actions-dropdown">
                      <button
                        className="btn-secondary btn-sm"
                        onClick={() => {
                          setEditMonitor(m);
                          setShowForm(true);
                          setActionsOpenId(null);
                        }}
                      >
                        Edit
                      </button>
                      <button
                        className="btn-secondary btn-sm"
                        onClick={() => {
                          handleToggle(m);
                          setActionsOpenId(null);
                        }}
                      >
                        {m.enabled ? "Disable" : "Enable"}
                      </button>
                      <button
                        className="btn-danger btn-sm"
                        onClick={() => {
                          handleDelete(m.id);
                          setActionsOpenId(null);
                        }}
                      >
                        Delete
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {showForm && (
        <MonitorForm
          editMonitor={editMonitor}
          onClose={() => {
            setShowForm(false);
            setEditMonitor(null);
          }}
          onSaved={refresh}
        />
      )}

      {detailMonitor && (
        <DetailPanel
          monitor={detailMonitor}
          onClose={() => setDetailMonitor(null)}
          onRefresh={refresh}
        />
      )}
    </div>
  );
}
