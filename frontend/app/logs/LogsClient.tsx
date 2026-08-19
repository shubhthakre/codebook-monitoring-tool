"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api, Monitor, SystemdLogs } from "@/lib/api";
import { copyTextToClipboard } from "@/lib/clipboard";
import { useAdminUnlock } from "@/lib/useAdminUnlock";

type LogPreset = "current" | "2min" | "5min" | "custom";

function toJournalTimestamp(localDatetime: string): string {
  // datetime-local is "YYYY-MM-DDTHH:mm" — journalctl accepts "YYYY-MM-DD HH:mm:ss"
  if (!localDatetime) return "";
  const normalized = localDatetime.replace("T", " ");
  return normalized.length === 16 ? `${normalized}:00` : normalized;
}

function presetSince(preset: LogPreset): string | undefined {
  switch (preset) {
    case "current":
      return undefined;
    case "2min":
      return "2 minutes ago";
    case "5min":
      return "5 minutes ago";
    default:
      return undefined;
  }
}

function safeFilenamePart(value: string): string {
  return value.replace(/[^\w.-]+/g, "_").replace(/^_+|_+$/g, "") || "service";
}

export default function SystemdLogsPage() {
  const { unlocked, handleTitleClick } = useAdminUnlock();
  const searchParams = useSearchParams();
  const initialId = searchParams.get("id");

  const [monitors, setMonitors] = useState<Monitor[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(
    initialId ? Number(initialId) : null
  );
  const [preset, setPreset] = useState<LogPreset>("current");
  const [customFrom, setCustomFrom] = useState("");
  const [customTo, setCustomTo] = useState("");
  const [lines, setLines] = useState(200);
  const [grep, setGrep] = useState("");
  const [loading, setLoading] = useState(false);
  const [listLoading, setListLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [logs, setLogs] = useState<SystemdLogs | null>(null);
  const [copyState, setCopyState] = useState<"idle" | "copied" | "failed">(
    "idle"
  );

  const systemdMonitors = useMemo(
    () => monitors.filter((m) => m.type === "systemd"),
    [monitors]
  );

  const selected = systemdMonitors.find((m) => m.id === selectedId) ?? null;

  const logText = useMemo(
    () => (logs?.lines?.length ? logs.lines.join("\n") : ""),
    [logs]
  );
  const hasLogText = logText.length > 0;

  const grepFromMonitor = (m: Monitor | null | undefined) =>
    typeof m?.config?.grep === "string" ? m.config.grep : "";

  useEffect(() => {
    api
      .getMonitors()
      .then((list) => {
        setMonitors(list);
        const systemd = list.filter((m) => m.type === "systemd");
        let next: Monitor | null = null;
        if (initialId) {
          const id = Number(initialId);
          next = systemd.find((m) => m.id === id) ?? systemd[0] ?? null;
        } else if (systemd.length > 0) {
          next = systemd[0];
        }
        if (next) {
          setSelectedId(next.id);
          setGrep(grepFromMonitor(next));
        }
      })
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Failed to load monitors")
      )
      .finally(() => setListLoading(false));
  }, [initialId]);

  const fetchLogs = useCallback(async () => {
    if (!selectedId) return;
    setLoading(true);
    setError(null);
    setCopyState("idle");

    try {
      let since: string | undefined;
      let until: string | undefined;

      if (preset === "custom") {
        if (!customFrom) {
          setError("Select a From timestamp for custom range");
          setLoading(false);
          return;
        }
        since = toJournalTimestamp(customFrom);
        if (customTo) until = toJournalTimestamp(customTo);
      } else {
        since = presetSince(preset);
      }

      const result = await api.getLogs(selectedId, {
        since,
        until,
        lines,
        grep: grep.trim(),
      });
      setLogs(result);
    } catch (err) {
      setLogs(null);
      setError(err instanceof Error ? err.message : "Failed to fetch logs");
    } finally {
      setLoading(false);
    }
  }, [selectedId, preset, customFrom, customTo, lines, grep]);

  useEffect(() => {
    if (listLoading || !selectedId || preset === "custom") return;
    void fetchLogs();
    // Auto-fetch when service or non-custom preset changes (after list load)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId, preset, listLoading]);

  useEffect(() => {
    const prevHtml = document.documentElement.style.overflow;
    const prevBody = document.body.style.overflow;
    document.documentElement.style.overflow = "hidden";
    document.body.style.overflow = "hidden";
    return () => {
      document.documentElement.style.overflow = prevHtml;
      document.body.style.overflow = prevBody;
    };
  }, []);

  const handleCopy = useCallback(async () => {
    if (!hasLogText) return;
    const ok = await copyTextToClipboard(logText);
    setCopyState(ok ? "copied" : "failed");
    window.setTimeout(() => setCopyState("idle"), ok ? 1800 : 2200);
  }, [hasLogText, logText]);

  const handleDownload = useCallback(() => {
    if (!hasLogText) return;
    const unit =
      typeof selected?.config?.unit === "string"
        ? selected.config.unit
        : selected?.name || "systemd";
    const stamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
    const filename = `${safeFilenamePart(unit)}-${stamp}.log`;
    const blob = new Blob([logText], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }, [hasLogText, logText, selected]);

  return (
    <div className="container logs-page">
      <header className="header logs-header">
        <div className="brand-block">
          <h1 className="brand" onClick={handleTitleClick}>
            Systemd <span>Logs</span>
          </h1>
          <p className="brand-sub">
            Journal output by service · current, recent, or custom range
          </p>
        </div>
        <nav className="nav-links">
          <Link href="/">Dashboard</Link>
          <Link href="/logs" className="nav-active">
            Systemd Logs
          </Link>
          {unlocked && <Link href="/settings">Settings</Link>}
        </nav>
      </header>

      {error && <div className="error-banner">{error}</div>}

      {listLoading ? (
        <p className="loading-state">Loading services…</p>
      ) : systemdMonitors.length === 0 ? (
        <div className="empty-state">
          <p>No systemd monitors configured yet.</p>
          <Link
            href="/"
            className="btn-primary"
            style={{ display: "inline-block", marginTop: "1rem" }}
          >
            Back to dashboard
          </Link>
        </div>
      ) : (
        <div className="logs-body">
          <div className="logs-toolbar">
            <div className="form-group" style={{ marginBottom: 0, minWidth: 220 }}>
              <label>Service</label>
              <select
                value={selectedId ?? ""}
                onChange={(e) => {
                  const id = Number(e.target.value);
                  setSelectedId(id);
                  const m = systemdMonitors.find((x) => x.id === id);
                  setGrep(grepFromMonitor(m));
                }}
              >
                {systemdMonitors.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                    {m.config?.unit ? ` (${String(m.config.unit)})` : ""}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group" style={{ marginBottom: 0 }}>
              <label>Time range</label>
              <div className="preset-row">
                {(
                  [
                    ["current", "Current"],
                    ["2min", "2 min"],
                    ["5min", "5 min"],
                    ["custom", "Custom"],
                  ] as const
                ).map(([value, label]) => (
                  <button
                    key={value}
                    type="button"
                    className={
                      preset === value
                        ? "btn-primary btn-sm"
                        : "btn-secondary btn-sm"
                    }
                    onClick={() => setPreset(value)}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>

            <div className="form-group" style={{ marginBottom: 0, width: 100 }}>
              <label>Lines</label>
              <input
                type="number"
                min={1}
                max={2000}
                value={lines}
                onChange={(e) => setLines(Number(e.target.value) || 200)}
              />
            </div>

            <div
              className="form-group"
              style={{ marginBottom: 0, minWidth: 220, flex: 1 }}
            >
              <label>Grep filter</label>
              <input
                type="text"
                value={grep}
                placeholder="error|warning (optional)"
                onChange={(e) => setGrep(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") void fetchLogs();
                }}
              />
            </div>

            <button
              type="button"
              className="btn-primary btn-sm"
              onClick={() => void fetchLogs()}
              disabled={loading || !selectedId}
              style={{ alignSelf: "flex-end" }}
            >
              {loading ? "Filtering..." : "Apply filter"}
            </button>
          </div>

          {preset === "custom" && (
            <div className="logs-custom-range">
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label>From</label>
                <input
                  type="datetime-local"
                  value={customFrom}
                  onChange={(e) => setCustomFrom(e.target.value)}
                  required
                />
              </div>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label>To (optional)</label>
                <input
                  type="datetime-local"
                  value={customTo}
                  onChange={(e) => setCustomTo(e.target.value)}
                />
              </div>
              <button
                type="button"
                className="btn-primary"
                onClick={() => void fetchLogs()}
                disabled={loading || !customFrom}
                style={{ alignSelf: "flex-end" }}
              >
                {loading ? "Fetching..." : "Fetch logs"}
              </button>
            </div>
          )}

          {selected && (
            <div className="logs-meta">
              <span className={`status-dot ${selected.last_status}`} />
              <span>
                {selected.name}
                {selected.config?.unit
                  ? ` · ${String(selected.config.unit)}`
                  : ""}
              </span>
              {logs && (
                <>
                  <span className="monitor-meta-sep">·</span>
                  <span>
                    {logs.active ? "active" : "inactive"} · {logs.count} lines
                  </span>
                  {logs.since && (
                    <>
                      <span className="monitor-meta-sep">·</span>
                      <span>since {logs.since}</span>
                    </>
                  )}
                  {logs.until && (
                    <>
                      <span className="monitor-meta-sep">·</span>
                      <span>until {logs.until}</span>
                    </>
                  )}
                  {logs.grep && (
                    <>
                      <span className="monitor-meta-sep">·</span>
                      <span>grep {logs.grep}</span>
                    </>
                  )}
                </>
              )}
              <div className="logs-actions">
                {preset !== "custom" && (
                  <button
                    type="button"
                    className="btn-secondary btn-sm"
                    onClick={() => void fetchLogs()}
                    disabled={loading}
                  >
                    {loading ? "Refreshing..." : "Refresh"}
                  </button>
                )}
                <button
                  type="button"
                  className="btn-secondary btn-sm"
                  onClick={() => void handleCopy()}
                  disabled={!hasLogText}
                >
                  {copyState === "copied"
                    ? "Copied"
                    : copyState === "failed"
                      ? "Copy failed"
                      : "Copy logs"}
                </button>
                <button
                  type="button"
                  className="btn-secondary btn-sm"
                  onClick={handleDownload}
                  disabled={!hasLogText}
                >
                  Download
                </button>
              </div>
            </div>
          )}

          <div className="log-viewer log-viewer-fill">
            {loading && !logs ? (
              <span style={{ color: "#8aa0ae" }}>Fetching logs...</span>
            ) : logs && logs.lines.length > 0 ? (
              logs.lines.join("\n")
            ) : (
              <span style={{ color: "#8aa0ae" }}>
                {logs
                  ? "No log lines for this range."
                  : "Select a service and time range."}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
