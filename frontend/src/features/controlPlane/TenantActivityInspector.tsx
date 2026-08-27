"use client";

import { useEffect, useState } from "react";
import { Alert, Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, MenuItem, Stack, Tab, Tabs, TextField, Typography } from "@mui/material";

import { PageHeader } from "@/components/common/PageHeader";
import { ResponsiveDataList } from "@/components/common/ResponsiveDataList";
import { EmptyState } from "@/components/feedback/EmptyState";
import { ErrorState } from "@/components/feedback/ErrorState";
import { LoadingState } from "@/components/feedback/LoadingState";
import { platformAdminApi } from "@/services/platformAdminApi";
import type { PlatformActivityLog, PlatformAskLog, PlatformPageLog, PlatformPromptLog, PlatformTenant } from "@/types/api";

type TabKey = "prompts" | "asks" | "pages" | "activity";

function snippet(value: string, size = 80) {
  const text = (value || "").replace(/\s+/g, " ").trim();
  if (text.length <= size) return text || "—";
  return `${text.slice(0, size)}…`;
}

export function TenantActivityInspector() {
  const [tab, setTab] = useState<TabKey>("prompts");
  const [tenantId, setTenantId] = useState("");
  const [search, setSearch] = useState("");
  const [tenants, setTenants] = useState<PlatformTenant[]>([]);
  const [prompts, setPrompts] = useState<PlatformPromptLog[]>([]);
  const [asks, setAsks] = useState<PlatformAskLog[]>([]);
  const [pages, setPages] = useState<PlatformPageLog[]>([]);
  const [activity, setActivity] = useState<PlatformActivityLog[]>([]);
  const [error, setError] = useState("");
  const [ready, setReady] = useState(false);
  const [selected, setSelected] = useState<PlatformPromptLog | PlatformAskLog | PlatformPageLog | PlatformActivityLog | null>(null);

  const params = () => {
    const query: Record<string, string> = {};
    if (tenantId) query.tenant_id = tenantId;
    if (search) query.search = search;
    return query;
  };

  const load = () => {
    setReady(false);
    const query = params();
    Promise.all([
      platformAdminApi.tenants(),
      platformAdminApi.prompts(query),
      platformAdminApi.asks(query),
      platformAdminApi.pages(query),
      platformAdminApi.workspaceActivity({ ...query, page_size: "50" }),
    ])
      .then(([tenantPage, promptPage, askPage, pagePage, activityPage]) => {
        setTenants(tenantPage.results);
        setPrompts(promptPage.results);
        setAsks(askPage.results);
        setPages(pagePage.results);
        setActivity(activityPage.results);
        setError("");
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setReady(true));
  };

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const empty = tab === "prompts" ? !prompts.length : tab === "asks" ? !asks.length : tab === "pages" ? !pages.length : !activity.length;

  return (
    <Stack spacing={3}>
      <PageHeader
        eyebrow="Platform"
        title="Tenant activity"
        description="Prompts sent through the platform Claude/OpenAI key, Ask SIPulse questions, workspace page views, and audit events across every tenant."
      />
      <Stack direction={{ xs: "column", md: "row" }} spacing={1.5}>
        <TextField
          select
          label="Workspace"
          value={tenantId}
          onChange={(event) => setTenantId(event.target.value)}
          sx={{ minWidth: 220 }}
        >
          <MenuItem value="">All workspaces</MenuItem>
          {tenants.map((tenant) => (
            <MenuItem key={tenant.id} value={tenant.id}>
              {tenant.name}
            </MenuItem>
          ))}
        </TextField>
        <TextField label="Search" value={search} onChange={(event) => setSearch(event.target.value)} sx={{ flex: 1 }} />
        <Button variant="contained" onClick={() => void load()}>
          Refresh
        </Button>
      </Stack>
      <Tabs value={tab} onChange={(_, value: TabKey) => setTab(value)}>
        <Tab value="prompts" label={`Prompts (${prompts.length})`} />
        <Tab value="asks" label={`Ask (${asks.length})`} />
        <Tab value="pages" label={`Browsing (${pages.length})`} />
        <Tab value="activity" label={`Events (${activity.length})`} />
      </Tabs>
      {error ? <ErrorState message={error} onRetry={() => void load()} /> : null}
      {!ready && !error ? <LoadingState /> : null}
      {ready && empty && !error ? (
        <EmptyState title="Nothing recorded yet" description="Tenant prompts, Ask questions, and page views appear here after workspaces are used." />
      ) : null}
      {ready && tab === "prompts" && prompts.length ? (
        <ResponsiveDataList
          rows={prompts}
          cardTitle={(row) => row.tenant_name}
          onRowClick={setSelected}
          columns={[
            { key: "tenant", label: "Workspace", render: (row) => row.tenant_name },
            { key: "user", label: "User", render: (row) => row.user_email || "—" },
            { key: "task", label: "Task", render: (row) => row.task },
            { key: "provider", label: "Model", hideOnMobile: true, render: (row) => `${row.provider} ${row.model}`.trim() },
            { key: "prompt", label: "Prompt", render: (row) => snippet(row.untrusted_input || row.prompt) },
            { key: "tokens", label: "Tokens", hideOnMobile: true, render: (row) => row.prompt_tokens + row.completion_tokens },
            { key: "when", label: "When", hideOnMobile: true, render: (row) => new Date(row.created_at).toLocaleString() },
          ]}
        />
      ) : null}
      {ready && tab === "asks" && asks.length ? (
        <ResponsiveDataList
          rows={asks}
          cardTitle={(row) => row.question}
          onRowClick={setSelected}
          columns={[
            { key: "tenant", label: "Workspace", render: (row) => row.tenant_name },
            { key: "user", label: "User", render: (row) => row.user_email || "—" },
            { key: "question", label: "Question", render: (row) => snippet(row.question, 100) },
            { key: "intent", label: "Intent", hideOnMobile: true, render: (row) => row.intent || "none" },
            { key: "origin", label: "Origin", hideOnMobile: true, render: (row) => row.origin },
            { key: "when", label: "When", hideOnMobile: true, render: (row) => new Date(row.created_at).toLocaleString() },
          ]}
        />
      ) : null}
      {ready && tab === "pages" && pages.length ? (
        <ResponsiveDataList
          rows={pages}
          cardTitle={(row) => row.path}
          onRowClick={setSelected}
          columns={[
            { key: "tenant", label: "Workspace", render: (row) => row.tenant_name },
            { key: "user", label: "User", render: (row) => row.user_email || "—" },
            { key: "path", label: "Page", render: (row) => row.path },
            { key: "ip", label: "IP", hideOnMobile: true, render: (row) => row.ip_address || "—" },
            { key: "when", label: "When", hideOnMobile: true, render: (row) => new Date(row.created_at).toLocaleString() },
          ]}
        />
      ) : null}
      {ready && tab === "activity" && activity.length ? (
        <ResponsiveDataList
          rows={activity}
          cardTitle={(row) => row.title}
          onRowClick={setSelected}
          columns={[
            { key: "tenant", label: "Workspace", render: (row) => row.tenant_name || "—" },
            { key: "actor", label: "Actor", render: (row) => row.actor || "—" },
            { key: "title", label: "Event", render: (row) => row.title },
            { key: "scope", label: "Scope", hideOnMobile: true, render: (row) => row.scope || "—" },
            { key: "when", label: "When", hideOnMobile: true, render: (row) => new Date(row.created_at).toLocaleString() },
          ]}
        />
      ) : null}
      <Alert severity="info">Tenant workspaces never see this console. Prompt text is stored so SI Global can review platform-key usage. Page views are workspace routes only.</Alert>
      <Dialog open={Boolean(selected)} onClose={() => setSelected(null)} fullWidth maxWidth="md">
        <DialogTitle>Record detail</DialogTitle>
        <DialogContent>
          {selected && "prompt" in selected ? (
            <Stack spacing={1.5} sx={{ mt: 1 }}>
              <Typography variant="subtitle2">{selected.tenant_name} · {selected.task} · {selected.provider}</Typography>
              <Typography variant="h5">User input</Typography>
              <Box component="pre" sx={{ whiteSpace: "pre-wrap", fontSize: 13, m: 0 }}>
                {selected.untrusted_input || "—"}
              </Box>
              <Typography variant="h5">Prompt</Typography>
              <Box component="pre" sx={{ whiteSpace: "pre-wrap", fontSize: 13, m: 0 }}>
                {selected.prompt || "—"}
              </Box>
              <Typography variant="h5">Response</Typography>
              <Box component="pre" sx={{ whiteSpace: "pre-wrap", fontSize: 13, m: 0 }}>
                {selected.response_text || selected.error || "—"}
              </Box>
            </Stack>
          ) : null}
          {selected && "question" in selected ? (
            <Stack spacing={1.5} sx={{ mt: 1 }}>
              <Typography>{selected.tenant_name} · {selected.user_email}</Typography>
              <Typography variant="h5">{selected.question}</Typography>
              <Typography color="text.secondary">Intent {selected.intent || "none"} · {selected.origin}</Typography>
              {(selected.facts || []).map((fact) => (
                <Typography key={fact} color="text.secondary">
                  {fact}
                </Typography>
              ))}
            </Stack>
          ) : null}
          {selected && "path" in selected ? (
            <Stack spacing={1} sx={{ mt: 1 }}>
              <Typography>{selected.tenant_name}</Typography>
              <Typography>{selected.path}</Typography>
              <Typography color="text.secondary">{selected.user_email || "—"}</Typography>
              <Typography color="text.secondary">{selected.ip_address || "—"}</Typography>
              <Typography color="text.secondary">{selected.user_agent}</Typography>
            </Stack>
          ) : null}
          {selected && "action" in selected ? (
            <Stack spacing={1} sx={{ mt: 1 }}>
              <Typography>{selected.tenant_name || "Platform"}</Typography>
              <Typography>{selected.title}</Typography>
              <Typography color="text.secondary">{selected.actor || "—"}</Typography>
              <Box component="pre" sx={{ whiteSpace: "pre-wrap", fontSize: 13, m: 0 }}>
                {JSON.stringify(selected.metadata || {}, null, 2)}
              </Box>
            </Stack>
          ) : null}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSelected(null)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}
