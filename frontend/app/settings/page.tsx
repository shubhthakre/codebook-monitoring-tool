"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { api, AppSettings } from "@/lib/api";
import { useAdminUnlock } from "@/lib/useAdminUnlock";

type FormState = {
  alert_enabled: boolean;
  alert_to: string;
  alert_from: string;
  alert_on_recovery: boolean;
  alert_cooldown_seconds: number;
  smtp_host: string;
  smtp_port: number;
  smtp_user: string;
  smtp_password: string;
  smtp_use_tls: boolean;
  smtp_use_ssl: boolean;
  oracle_client_lib_dir: string;
};

const emptyForm: FormState = {
  alert_enabled: false,
  alert_to: "",
  alert_from: "",
  alert_on_recovery: true,
  alert_cooldown_seconds: 300,
  smtp_host: "",
  smtp_port: 587,
  smtp_user: "",
  smtp_password: "",
  smtp_use_tls: true,
  smtp_use_ssl: false,
  oracle_client_lib_dir: "",
};

function toForm(data: AppSettings): FormState {
  return {
    alert_enabled: data.alert_enabled,
    alert_to: data.alert_to,
    alert_from: data.alert_from,
    alert_on_recovery: data.alert_on_recovery,
    alert_cooldown_seconds: data.alert_cooldown_seconds,
    smtp_host: data.smtp_host,
    smtp_port: data.smtp_port,
    smtp_user: data.smtp_user,
    smtp_password: "",
    smtp_use_tls: data.smtp_use_tls,
    smtp_use_ssl: data.smtp_use_ssl,
    oracle_client_lib_dir: data.oracle_client_lib_dir,
  };
}

export default function SettingsPage() {
  const router = useRouter();
  const { unlocked, ready, handleTitleClick } = useAdminUnlock();
  const [form, setForm] = useState<FormState>(emptyForm);
  const [meta, setMeta] = useState<Pick<
    AppSettings,
    "configured" | "source" | "smtp_password_set" | "oracle_restart_required"
  > | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getSettings();
      setForm(toForm(data));
      setMeta({
        configured: data.configured,
        source: data.source,
        smtp_password_set: data.smtp_password_set,
        oracle_restart_required: data.oracle_restart_required,
      });
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to load settings. Is the backend running?"
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!ready) return;
    if (!unlocked) {
      router.replace("/");
      return;
    }
    load();
  }, [ready, unlocked, router]);

  const patch = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const payload = {
        alert_enabled: form.alert_enabled,
        alert_to: form.alert_to,
        alert_from: form.alert_from,
        alert_on_recovery: form.alert_on_recovery,
        alert_cooldown_seconds: Number(form.alert_cooldown_seconds),
        smtp_host: form.smtp_host,
        smtp_port: Number(form.smtp_port),
        smtp_user: form.smtp_user,
        smtp_use_tls: form.smtp_use_tls,
        smtp_use_ssl: form.smtp_use_ssl,
        oracle_client_lib_dir: form.oracle_client_lib_dir,
        ...(form.smtp_password ? { smtp_password: form.smtp_password } : {}),
      };
      const data = await api.updateSettings(payload);
      setForm(toForm(data));
      setMeta({
        configured: data.configured,
        source: data.source,
        smtp_password_set: data.smtp_password_set,
        oracle_restart_required: data.oracle_restart_required,
      });
      setSuccess(
        data.oracle_restart_required
          ? "Settings saved. Restart the backend so the Oracle Instant Client path takes effect."
          : "Settings saved. Alerts will use these values immediately."
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    setError(null);
    setSuccess(null);
    try {
      const result = await api.testEmail();
      setSuccess(result.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Test email failed");
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="container">
      <header className="header">
        <div className="brand-block">
          <h1 className="brand" onClick={handleTitleClick}>
            Alert <span>Settings</span>
          </h1>
          <p className="brand-sub">
            Email alerts, SMTP, and Oracle Instant Client — no .env edit needed
          </p>
        </div>
        <nav className="nav-links">
          <Link href="/">Dashboard</Link>
          <Link href="/logs">Systemd Logs</Link>
          {unlocked && (
            <Link href="/settings" className="nav-active">
              Settings
            </Link>
          )}
        </nav>
      </header>

      {error && <div className="error-banner">{error}</div>}
      {success && <div className="success-banner">{success}</div>}

      {!ready || !unlocked || loading ? (
        <p className="loading-state">Loading settings…</p>
      ) : (
        <form className="settings-card" onSubmit={handleSave}>
          <div className="settings-status">
            <span className={`badge ${meta?.configured ? "" : "badge-disabled"}`}>
              {meta?.configured ? "Alerts ready" : "Not fully configured"}
            </span>
            <span className="settings-source">
              Source: {meta?.source === "ui" ? "saved in UI" : "backend/.env"}
            </span>
          </div>

          <section className="settings-section">
            <h2>Email alerts</h2>
            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={form.alert_enabled}
                onChange={(e) => patch("alert_enabled", e.target.checked)}
              />
              Enable email alerts when a monitor goes down
            </label>
            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={form.alert_on_recovery}
                onChange={(e) => patch("alert_on_recovery", e.target.checked)}
              />
              Also email when a service recovers
            </label>
            <div className="form-group">
              <label>Recipients</label>
              <input
                value={form.alert_to}
                onChange={(e) => patch("alert_to", e.target.value)}
                placeholder="ops@example.com, oncall@example.com"
              />
              <small>Comma-separated email addresses</small>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>From address</label>
                <input
                  value={form.alert_from}
                  onChange={(e) => patch("alert_from", e.target.value)}
                  placeholder="monitoring@example.com"
                />
              </div>
              <div className="form-group">
                <label>Cooldown (seconds)</label>
                <input
                  type="number"
                  min={0}
                  value={form.alert_cooldown_seconds}
                  onChange={(e) =>
                    patch("alert_cooldown_seconds", Number(e.target.value))
                  }
                />
                <small>Minimum time between repeat down alerts</small>
              </div>
            </div>
          </section>

          <section className="settings-section">
            <h2>SMTP</h2>
            <div className="form-row">
              <div className="form-group">
                <label>Host</label>
                <input
                  value={form.smtp_host}
                  onChange={(e) => patch("smtp_host", e.target.value)}
                  placeholder="smtp.example.com"
                />
              </div>
              <div className="form-group">
                <label>Port</label>
                <input
                  type="number"
                  min={1}
                  max={65535}
                  value={form.smtp_port}
                  onChange={(e) => patch("smtp_port", Number(e.target.value))}
                />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Username</label>
                <input
                  value={form.smtp_user}
                  onChange={(e) => patch("smtp_user", e.target.value)}
                  placeholder="smtp user"
                  autoComplete="off"
                />
              </div>
              <div className="form-group">
                <label>Password</label>
                <input
                  type="password"
                  value={form.smtp_password}
                  onChange={(e) => patch("smtp_password", e.target.value)}
                  placeholder={
                    meta?.smtp_password_set
                      ? "Leave blank to keep current password"
                      : "SMTP password"
                  }
                  autoComplete="new-password"
                />
              </div>
            </div>
            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={form.smtp_use_tls}
                onChange={(e) => patch("smtp_use_tls", e.target.checked)}
              />
              STARTTLS (typical for port 587)
            </label>
            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={form.smtp_use_ssl}
                onChange={(e) => patch("smtp_use_ssl", e.target.checked)}
              />
              Implicit SSL (typical for port 465)
            </label>
          </section>

          <section className="settings-section">
            <h2>Oracle Instant Client</h2>
            <div className="form-group">
              <label>Library directory</label>
              <input
                value={form.oracle_client_lib_dir}
                onChange={(e) =>
                  patch("oracle_client_lib_dir", e.target.value)
                }
                placeholder="D:\\oracle\\instantclient_23_26"
              />
              <small>
                Folder containing oci.dll (Windows) or libclntsh. Required for
                Oracle 11g. Changing this usually needs a backend restart.
              </small>
            </div>
          </section>

          <div className="form-actions settings-actions">
            <button
              type="button"
              className="btn-secondary"
              onClick={handleTest}
              disabled={testing || saving}
            >
              {testing ? "Sending…" : "Send test email"}
            </button>
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? "Saving…" : "Save settings"}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
