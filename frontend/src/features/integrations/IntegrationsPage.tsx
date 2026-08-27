"use client";

import { Alert, Box, Button, Card, CardContent, Checkbox, Dialog, DialogActions, DialogContent, DialogTitle, FormControlLabel, MenuItem, Stack, Switch, TextField, Typography } from "@mui/material";
import { useEffect, useMemo, useRef, useState } from "react";

import { useConfirm } from "@/components/common/ConfirmDialog";
import { PageHeader } from "@/components/common/PageHeader";
import { StatusChip } from "@/components/common/StatusChip";
import { EmptyState } from "@/components/feedback/EmptyState";
import { ErrorState } from "@/components/feedback/ErrorState";
import { LoadingState } from "@/components/feedback/LoadingState";
import { integrationApi, type IntegrationItem, type IntegrationField } from "@/services/domainApi";
import { useJobSession } from "@/features/websites/auditSession";
import { useAppSelector } from "@/store/hooks";

type DraftValue = string | string[] | boolean;
type Draft = Record<string, DraftValue>;

const GROUP_LABELS: Record<string, string> = {
  commerce: "E-commerce stores",
  crm: "CRM",
  erp: "ERP",
  sheets: "Spreadsheets",
  webhook: "Webhooks",
};

function emptyDraft(item: IntegrationItem): Draft {
  const draft: Draft = {};
  item.fields.forEach((field) => {
    if (field.input === "events") {
      draft[field.key] = (item.config.events as string[]) ?? [];
    } else if (field.input === "toggle") {
      draft[field.key] = item.config[field.key] !== false && item.config[field.key] !== "false";
    } else if (!field.secret) {
      draft[field.key] = String(item.config[field.key] ?? "");
    } else {
      draft[field.key] = "";
    }
  });
  return draft;
}

export function IntegrationsPage() {
  const permissions = useAppSelector((state) => state.auth.user?.permissions ?? []);
  const canConfigure = permissions.includes("integration.configure");
  const { start, job } = useJobSession();
  const seenSync = useRef("");
  const [items, setItems] = useState<IntegrationItem[]>([]);
  const [events, setEvents] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [ready, setReady] = useState(false);
  const [busy, setBusy] = useState(false);
  const confirm = useConfirm();
  const [editing, setEditing] = useState<IntegrationItem | null>(null);
  const [draft, setDraft] = useState<Draft>({});
  const [revealed, setRevealed] = useState<Record<string, string> | null>(null);

  const load = () =>
    integrationApi
      .list()
      .then((payload) => {
        setItems(payload.items);
        setEvents(payload.webhook_events);
        setError("");
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setReady(true));

  useEffect(() => {
    void load();
  }, []);

  useEffect(() => {
    if (job?.job_type !== "sync_commerce" || job.status !== "COMPLETED") {
      return;
    }
    if (seenSync.current === job.id) {
      return;
    }
    seenSync.current = job.id;
    void load();
  }, [job]);

  const grouped = useMemo(() => {
    const order = ["commerce", "crm", "erp", "sheets", "webhook"];
    return order
      .map((category) => ({ category, items: items.filter((item) => item.category === category) }))
      .filter((group) => group.items.length);
  }, [items]);

  const openEditor = (item: IntegrationItem) => {
    setEditing(item);
    setDraft(emptyDraft(item));
    setRevealed(null);
  };

  const save = async () => {
    if (!editing) {
      return;
    }
    setBusy(true);
    try {
      const payload: Record<string, unknown> = {};
      editing.fields.forEach((field) => {
        const value = draft[field.key];
        if (field.secret && !value) {
          return;
        }
        payload[field.key] = value;
      });
      const next = await integrationApi.save(editing.code, payload);
      setItems((current) => current.map((item) => (item.code === next.code ? { ...item, ...next } : item)));
      setRevealed(next.revealed ?? null);
      setError("");
      if (!next.revealed) {
        setEditing(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save integration.");
    } finally {
      setBusy(false);
    }
  };

  const run = async (item: IntegrationItem, action: "test" | "disconnect" | "rotate" | "sync") => {
    if (action === "disconnect") {
      const ok = await confirm({
        title: `Disconnect ${item.name}`,
        description: `Stored credentials for ${item.name} will be removed from this workspace.`,
        confirmLabel: "Disconnect",
      });
      if (!ok) {
        return;
      }
    }
    if (action === "rotate") {
      const ok = await confirm({
        title: "Rotate webhook secret",
        description: "The current secret will stop working. Copy the new secret immediately.",
        confirmLabel: "Rotate",
      });
      if (!ok) {
        return;
      }
    }
    setBusy(true);
    try {
      if (action === "sync") {
        const created = await integrationApi.sync(item.code);
        start({ jobId: created.id, kind: "sync_commerce", title: `${item.name} sync`, href: "/app/business/ecommerce" });
        setError("");
        return;
      }
      const next =
        action === "test"
          ? await integrationApi.test(item.code)
          : action === "rotate"
            ? await integrationApi.rotateWebhook()
            : await integrationApi.disconnect(item.code);
      setItems((current) => current.map((row) => (row.code === next.code ? { ...row, ...next } : row)));
      if (next.revealed) {
        setRevealed(next.revealed);
      }
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update integration.");
      await load();
    } finally {
      setBusy(false);
    }
  };

  return (
    <Stack spacing={3}>
      <PageHeader
        title="Integrations"
        description="Connect Shopify, WooCommerce, Etsy, or eBay to pull store data into Business Analysis. HubSpot, Odoo, Sheets, and webhooks push leads and audit results. Secrets stay on the server."
      />
      {error ? <ErrorState message={error} onRetry={() => void load()} /> : null}
      {!ready && !error ? <LoadingState /> : null}
      {ready && !items.length ? <EmptyState title="No integrations" description="Integrations will appear here for this workspace." /> : null}
      {grouped.map((group) => (
        <Stack key={group.category} spacing={2}>
          <Typography variant="h4">{GROUP_LABELS[group.category] ?? group.category}</Typography>
          <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" } }}>
            {group.items.map((item) => (
              <Card key={item.code} variant="outlined">
                <CardContent>
                  <Stack spacing={1.25}>
                    <Stack direction="row" spacing={1} sx={{ justifyContent: "space-between", alignItems: "flex-start" }}>
                      <Typography variant="h4">{item.name}</Typography>
                      <StatusChip value={item.locked ? "locked" : item.status} />
                    </Stack>
                    <Typography color="text.secondary">{item.description}</Typography>
                    {item.credentials_configured ? (
                      <Typography variant="body2" color="text.secondary">
                        Credentials are stored on the server.
                        {item.records_synced ? ` ${item.records_synced} records stored.` : ""}
                      </Typography>
                    ) : null}
                    {item.code === "google_sheets" && typeof item.config.client_email === "string" && item.config.client_email ? (
                      <Typography variant="body2" color="text.secondary">
                        Share the Sheet with {item.config.client_email} as Editor.
                      </Typography>
                    ) : null}
                    {item.last_error ? (
                      <Alert severity="error">{item.last_error}</Alert>
                    ) : null}
                    {item.locked ? (
                      <Typography variant="body2" color="text.secondary">
                        {item.lock_reason}
                      </Typography>
                    ) : null}
                    {canConfigure && item.connectable && !item.locked ? (
                      <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", gap: 1 }}>
                        <Button variant="contained" disabled={busy} onClick={() => openEditor(item)}>
                          {item.credentials_configured ? "Update" : "Connect"}
                        </Button>
                        {item.credentials_configured ? (
                          <Button disabled={busy} onClick={() => void run(item, "test")}>
                            Test connection
                          </Button>
                        ) : null}
                        {item.category === "commerce" && item.credentials_configured ? (
                          <Button disabled={busy} onClick={() => void run(item, "sync")}>
                            Sync store
                          </Button>
                        ) : null}
                        {item.code === "webhook" && item.credentials_configured ? (
                          <Button disabled={busy} onClick={() => void run(item, "rotate")}>
                            Rotate secret
                          </Button>
                        ) : null}
                        {item.credentials_configured || item.status !== "disconnected" ? (
                          <Button color="error" disabled={busy} onClick={() => void run(item, "disconnect")}>
                            Disconnect
                          </Button>
                        ) : null}
                      </Stack>
                    ) : null}
                  </Stack>
                </CardContent>
              </Card>
            ))}
          </Box>
        </Stack>
      ))}
      <Dialog open={Boolean(editing)} onClose={() => setEditing(null)} fullWidth maxWidth="md">
        {editing ? (
          <>
            <DialogTitle>Connect {editing.name}</DialogTitle>
            <DialogContent>
              <Stack spacing={2} sx={{ mt: 1 }}>
                {editing.setup_steps?.length ? (
                  <Box>
                    <Typography variant="subtitle2" sx={{ mb: 1 }}>
                      How to connect — follow these steps even if you are not technical
                    </Typography>
                    <Box component="ol" sx={{ pl: 2.5, m: 0 }}>
                      {editing.setup_steps.map((step) => (
                        <Typography key={step} component="li" variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                          {step}
                        </Typography>
                      ))}
                    </Box>
                  </Box>
                ) : null}
                {editing.fields.map((field) => (
                  <FieldInput
                    key={field.key}
                    field={field}
                    value={draft[field.key]}
                    events={events}
                    onChange={(value) => setDraft({ ...draft, [field.key]: value })}
                  />
                ))}
                {editing.fields.some((field) => field.secret) ? (
                  <Typography variant="body2" color="text.secondary">
                    Leave secret fields empty to keep the stored value.
                  </Typography>
                ) : null}
              </Stack>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setEditing(null)}>Cancel</Button>
              <Button variant="contained" disabled={busy} onClick={() => void save()}>
                Save
              </Button>
            </DialogActions>
          </>
        ) : null}
      </Dialog>
      <Dialog open={Boolean(revealed)} onClose={() => setRevealed(null)} fullWidth maxWidth="sm">
        {revealed ? (
          <>
            <DialogTitle>Copy this secret now</DialogTitle>
            <DialogContent>
              <Stack spacing={1.5} sx={{ mt: 1 }}>
                <Alert severity="warning">It will not be shown again.</Alert>
                {Object.entries(revealed).map(([key, value]) => (
                  <TextField key={key} label={key.replaceAll("_", " ")} value={value} slotProps={{ input: { readOnly: true } }} />
                ))}
              </Stack>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setRevealed(null)}>Done</Button>
            </DialogActions>
          </>
        ) : null}
      </Dialog>
    </Stack>
  );
}

function FieldInput({
  field,
  value,
  events,
  onChange,
}: {
  field: IntegrationField;
  value: DraftValue | undefined;
  events: string[];
  onChange: (value: DraftValue) => void;
}) {
  if (field.input === "events") {
    const selected = Array.isArray(value) ? value : [];
    return (
      <Box>
        <Typography variant="subtitle2" sx={{ mb: 0.5 }}>
          {field.label}
        </Typography>
        <Stack>
          {events.map((event) => (
            <FormControlLabel
              key={event}
              control={
                <Checkbox
                  checked={selected.includes(event)}
                  onChange={(_event, checked) => {
                    const next = new Set(selected);
                    if (checked) {
                      next.add(event);
                    } else {
                      next.delete(event);
                    }
                    onChange([...next]);
                  }}
                />
              }
              label={event}
            />
          ))}
        </Stack>
      </Box>
    );
  }
  if (field.input === "toggle") {
    return (
      <FormControlLabel
        control={<Switch checked={value !== false} onChange={(_event, checked) => onChange(checked)} />}
        label={field.help ? `${field.label}. ${field.help}` : field.label}
      />
    );
  }
  if (field.key === "auth_header") {
    return (
      <TextField
        select
        label={field.label}
        value={typeof value === "string" && value ? value : "Authorization"}
        onChange={(event) => onChange(event.target.value)}
        helperText={field.help}
      >
        <MenuItem value="Authorization">Authorization (Bearer)</MenuItem>
        <MenuItem value="X-API-Key">X-API-Key</MenuItem>
      </TextField>
    );
  }
  const helper = field.secret ? [field.help, "Write-only. Never returned to the browser."].filter(Boolean).join(" ") : field.help;
  return (
    <TextField
      label={field.label}
      type={field.input === "password" ? "password" : "text"}
      required={field.required && !field.secret}
      value={typeof value === "string" ? value : ""}
      onChange={(event) => onChange(event.target.value)}
      helperText={helper}
      multiline={field.input === "textarea"}
      minRows={field.input === "textarea" ? 8 : undefined}
    />
  );
}
