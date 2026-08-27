"use client";

import { Alert, Button, Chip, Dialog, DialogActions, DialogContent, DialogTitle, MenuItem, Stack, TextField, Typography } from "@mui/material";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { PageHeader } from "@/components/common/PageHeader";
import { PrintReportChrome } from "@/components/common/PrintReportChrome";
import { ResponsiveDataList } from "@/components/common/ResponsiveDataList";
import { StatusChip } from "@/components/common/StatusChip";
import { EmptyState } from "@/components/feedback/EmptyState";
import { ErrorState } from "@/components/feedback/ErrorState";
import { LoadingState } from "@/components/feedback/LoadingState";
import { leadApi, opportunityApi } from "@/services/domainApi";
import type { GrowthOpportunity, Lead } from "@/types/domain";

const TYPES = ["business", "market", "product", "geographic", "customer", "cross_sell", "upsell"];

export function OpportunityListPage() {
  const router = useRouter();
  const [rows, setRows] = useState<GrowthOpportunity[]>([]);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ title: "", type: "geographic", evidence: "", recommended_action: "", potential_impact: "" });

  const load = () =>
    opportunityApi
      .list()
      .then((data) => {
        setRows(data.results);
        setError("");
      })
      .catch((err: Error) => setError(err.message));

  useEffect(() => {
    void load();
  }, []);

  return (
    <PrintReportChrome title="Opportunities">
    <Stack spacing={3}>
      <PageHeader
        title="Opportunities"
        description="Growth opportunities recorded with evidence. This is not the CRM deal pipeline and not a generated list of fake city scores."
        actions={
          <Stack direction="row" spacing={1} className="no-print">
            <Button
              variant="outlined"
              onClick={async () => {
                const result = await opportunityApi.generate();
                setNote(result.created ? `${result.created} recorded from evidence.` : result.note);
                await load();
              }}
            >
              Generate from evidence
            </Button>
            <Button variant="contained" onClick={() => setOpen(true)}>
              Record opportunity
            </Button>
          </Stack>
        }
      />
      {note ? <Alert severity="info">{note}</Alert> : null}
      {error ? <ErrorState message={error} onRetry={() => void load()} /> : null}
      {rows.length ? (
        <ResponsiveDataList
          rows={rows}
          cardTitle={(row) => row.title}
          onRowClick={(row) => router.push(`/app/opportunities/${row.id}`)}
          columns={[
            { key: "title", label: "Opportunity", render: (row) => row.title },
            { key: "type", label: "Type", render: (row) => row.type },
            { key: "score", label: "Score", render: (row) => (row.score == null ? "—" : row.score) },
            { key: "status", label: "Status", render: (row) => <StatusChip value={row.status} /> },
            { key: "origin", label: "Origin", render: (row) => row.origin },
            { key: "leads", label: "Linked leads", render: (row) => row.related_leads?.length ?? 0 },
          ]}
        />
      ) : (
        <EmptyState title="No opportunities yet" description="Record one from business or market evidence. SIPulse will not auto-create Lahore=92 style rows without signals." />
      )}
      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Record opportunity</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField label="Title" value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} />
            <TextField select label="Type" value={form.type} onChange={(event) => setForm({ ...form, type: event.target.value })}>
              {TYPES.map((item) => (
                <MenuItem key={item} value={item}>
                  {item}
                </MenuItem>
              ))}
            </TextField>
            <TextField label="Evidence" multiline minRows={3} value={form.evidence} onChange={(event) => setForm({ ...form, evidence: event.target.value })} />
            <TextField label="Recommended action" multiline minRows={2} value={form.recommended_action} onChange={(event) => setForm({ ...form, recommended_action: event.target.value })} />
            <TextField label="Potential impact" value={form.potential_impact} onChange={(event) => setForm({ ...form, potential_impact: event.target.value })} />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={async () => {
              await opportunityApi.create(form);
              setOpen(false);
              await load();
            }}
          >
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
    </PrintReportChrome>
  );
}

export function OpportunityDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [item, setItem] = useState<GrowthOpportunity | null>(null);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [matches, setMatches] = useState<Lead[]>([]);

  const load = () =>
    opportunityApi
      .get(params.id)
      .then(setItem)
      .catch((err: Error) => setError(err.message));

  useEffect(() => {
    void load();
  }, [params.id]);

  useEffect(() => {
    if (!query.trim()) {
      setMatches([]);
      return;
    }
    const handle = window.setTimeout(() => {
      void leadApi.list({ search: query.trim(), page_size: "8" }).then((data) => setMatches(data.results)).catch(() => setMatches([]));
    }, 250);
    return () => window.clearTimeout(handle);
  }, [query]);

  if (error) return <ErrorState message={error} />;
  if (!item) return <LoadingState />;

  const linked = item.related_leads ?? [];
  const linkedIds = new Set(linked.map((row) => row.id));

  const setLinked = async (ids: string[]) => {
    const next = await opportunityApi.update(item.id, { related_lead_ids: ids });
    setItem(next);
  };

  return (
    <PrintReportChrome title={item.title}>
    <Stack spacing={2}>
      <PageHeader
        title={item.title}
        description={`${item.type} · origin ${item.origin}`}
        actions={
          <Stack direction="row" spacing={1} className="no-print">
            <Button variant="outlined" onClick={() => router.push(`/app/marketing?opportunity=${item.id}`)}>
              Record campaign
            </Button>
            <Button variant="contained" onClick={() => router.push(item.geo_place ? `/app/leads/discover?geo_place=${item.geo_place}` : "/app/leads/discover")}>
              Find leads
            </Button>
          </Stack>
        }
      />
      <StatusChip value={item.status} />
      <TextField
        select
        label="Status"
        value={item.status}
        onChange={async (event) => {
          const next = await opportunityApi.update(item.id, { status: event.target.value });
          setItem(next);
        }}
        sx={{ maxWidth: 240 }}
        className="no-print"
      >
        {["open", "reviewing", "accepted", "dismissed"].map((status) => (
          <MenuItem key={status} value={status}>
            {status}
          </MenuItem>
        ))}
      </TextField>
      <Typography>Score: {item.score ?? "—"} · Confidence: {item.confidence ?? "—"}</Typography>
      {item.geo_place_name ? <Typography>Market: {item.geo_place_name}</Typography> : null}
      <Typography>Evidence: {item.evidence}</Typography>
      <Typography>Recommended action: {item.recommended_action}</Typography>
      {item.potential_impact ? <Typography>Impact: {item.potential_impact}</Typography> : null}
      <Typography variant="h4">Linked leads</Typography>
      <Typography color="text.secondary">Link existing SIPulse leads. Discovery stays in Leads. Empty here means no members for an opportunity campaign.</Typography>
      {linked.length ? (
        <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", gap: 1 }}>
          {linked.map((lead) => (
            <Chip
              key={lead.id}
              label={`${lead.company_name}${lead.location ? ` · ${lead.location}` : ""}`}
              onDelete={() => void setLinked(linked.filter((row) => row.id !== lead.id).map((row) => row.id))}
              onClick={() => router.push(`/app/leads/${lead.id}`)}
            />
          ))}
        </Stack>
      ) : (
        <Typography color="text.secondary">No leads linked yet.</Typography>
      )}
      <TextField
        className="no-print"
        label="Search existing leads"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
      />
      {matches.map((lead) => (
        <Stack key={lead.id} direction="row" spacing={1} sx={{ alignItems: "center" }} className="no-print">
          <Typography sx={{ flex: 1 }}>
            {lead.company_name} {lead.location ? `· ${lead.location}` : ""}
          </Typography>
          <Button
            size="small"
            disabled={linkedIds.has(lead.id)}
            onClick={() => void setLinked([...linkedIds, lead.id])}
          >
            Link
          </Button>
        </Stack>
      ))}
    </Stack>
    </PrintReportChrome>
  );
}
