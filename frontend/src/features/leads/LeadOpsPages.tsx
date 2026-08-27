"use client";

import { Alert, Button, MenuItem, Stack, TextField } from "@mui/material";
import { useEffect, useState } from "react";

import { PageHeader } from "@/components/common/PageHeader";
import { ResponsiveDataList } from "@/components/common/ResponsiveDataList";
import { EmptyState } from "@/components/feedback/EmptyState";
import { useJobSession } from "@/features/websites/auditSession";
import { leadApi } from "@/services/domainApi";
import type { Lead, LeadSavedList } from "@/types/domain";

export function LeadListsPage() {
  const [lists, setLists] = useState<LeadSavedList[]>([]);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [name, setName] = useState("");
  const [active, setActive] = useState<LeadSavedList | null>(null);
  const [leadId, setLeadId] = useState("");
  const [note, setNote] = useState("");

  const load = async () => {
    const [listPage, leadPage] = await Promise.all([leadApi.lists(), leadApi.list({ page_size: "100" })]);
    setLists(listPage.results);
    setLeads(leadPage.results);
    if (active) {
      setActive(await leadApi.getList(active.id));
    }
  };

  useEffect(() => {
    void load();
  }, []);

  return (
    <Stack spacing={3}>
      <PageHeader
        title="Lead lists"
        description="Saved groups of existing SIPulse leads. Lists do not invent new companies."
        actions={
          <Stack direction="row" spacing={1}>
            <TextField size="small" label="List name" value={name} onChange={(event) => setName(event.target.value)} />
            <Button
              variant="contained"
              onClick={async () => {
                if (!name.trim()) return;
                await leadApi.createList({ name: name.trim() });
                setName("");
                await load();
              }}
            >
              Create list
            </Button>
          </Stack>
        }
      />
      {note ? <Alert severity="success">{note}</Alert> : null}
      {lists.length ? (
        <ResponsiveDataList
          rows={lists}
          cardTitle={(row) => row.name}
          onRowClick={(row) => void leadApi.getList(row.id).then(setActive)}
          columns={[
            { key: "name", label: "List", render: (row) => row.name },
            { key: "count", label: "Leads", render: (row) => row.lead_count },
          ]}
        />
      ) : (
        <EmptyState title="No lists" description="Create a list, then add leads you already discovered." />
      )}
      {active ? (
        <Stack spacing={2}>
          <PageHeader title={active.name} description={`${active.leads?.length ?? 0} leads in this list.`} />
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
            <TextField select size="small" label="Add lead" value={leadId} onChange={(event) => setLeadId(event.target.value)} sx={{ minWidth: 220 }}>
              {leads.map((item) => (
                <MenuItem key={item.id} value={item.id}>
                  {item.company_name}
                </MenuItem>
              ))}
            </TextField>
            <Button
              variant="contained"
              onClick={async () => {
                if (!leadId) return;
                await leadApi.addToList(active.id, [leadId]);
                setNote("Lead added to list.");
                setLeadId("");
                await load();
              }}
            >
              Add
            </Button>
          </Stack>
          {(active.leads ?? []).length ? (
            <ResponsiveDataList
              rows={active.leads ?? []}
              cardTitle={(row) => row.company_name}
              columns={[
                { key: "name", label: "Company", render: (row) => row.company_name },
                { key: "location", label: "Location", render: (row) => row.location || "—" },
                { key: "score", label: "Score", render: (row) => row.lead_score ?? "—" },
              ]}
            />
          ) : (
            <EmptyState title="Empty list" description="Add a discovered lead." />
          )}
        </Stack>
      ) : null}
    </Stack>
  );
}

export function LeadScoringPage() {
  const [rows, setRows] = useState<Lead[]>([]);
  const [note, setNote] = useState("");
  const load = () => void leadApi.list({ ordering: "-lead_score", page_size: "100" }).then((data) => setRows(data.results));
  useEffect(() => {
    load();
  }, []);
  return (
    <Stack spacing={3}>
      <PageHeader
        title="Lead scoring"
        description="Completeness plus ICP fit. Missing emails and phones stay missing. This is not a market opportunity grade."
        actions={
          <Button
            variant="contained"
            onClick={async () => {
              const result = await leadApi.score();
              setNote(`Scored ${result.scored} leads from known fields.`);
              load();
            }}
          >
            Score leads
          </Button>
        }
      />
      {note ? <Alert severity="info">{note}</Alert> : null}
      {rows.length ? (
        <ResponsiveDataList
          rows={rows}
          cardTitle={(row) => row.company_name}
          columns={[
            { key: "name", label: "Company", render: (row) => row.company_name },
            { key: "lead", label: "Lead score", render: (row) => row.lead_score ?? "—" },
            { key: "quality", label: "Quality", render: (row) => row.quality_score ?? "—" },
            { key: "icp", label: "ICP fit", render: (row) => row.icp_fit ?? "—" },
            { key: "origin", label: "Origin", render: (row) => row.origin },
          ]}
        />
      ) : (
        <EmptyState title="No leads" description="Discover or add leads first." />
      )}
    </Stack>
  );
}

export function LeadEnrichmentPage() {
  const { start } = useJobSession();
  const [rows, setRows] = useState<Lead[]>([]);
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const load = () => void leadApi.list({ page_size: "100" }).then((data) => setRows(data.results));
  useEffect(() => {
    load();
  }, []);
  return (
    <Stack spacing={3}>
      <PageHeader
        title="Enrichment"
        description="Fills missing website, email, phone, location, and industry from the company site, Wikidata, enabled discovery APIs, and licensed Hunter / Clearbit / Apollo / search keys. Empty stays empty."
        actions={
          <Button
            variant="contained"
            onClick={async () => {
              try {
                const started = await leadApi.enrichMany();
                start({ jobId: started.job.id, kind: "enrich_leads", title: "Lead enrichment", href: "/app/leads/enrichment" });
              } catch (err) {
                setError(err instanceof Error ? err.message : "Unable to start enrichment.");
              }
            }}
          >
            Enrich incomplete
          </Button>
        }
      />
      {error ? <Alert severity="error">{error}</Alert> : null}
      {note ? <Alert severity="info">{note}</Alert> : null}
      {rows.length ? (
        <ResponsiveDataList
          rows={rows}
          cardTitle={(row) => row.company_name}
          columns={[
            { key: "name", label: "Company", render: (row) => row.company_name },
            { key: "email", label: "Email", render: (row) => row.email || "—" },
            { key: "phone", label: "Phone", render: (row) => row.phone || "—" },
            { key: "website", label: "Website", render: (row) => row.website || "—" },
            { key: "industry", label: "Industry", render: (row) => row.industry || "—" },
            { key: "location", label: "Location", render: (row) => row.location || "—" },
            {
              key: "action",
              label: "",
              render: (row) => (
                <Button
                  size="small"
                  onClick={async () => {
                    try {
                      const result = await leadApi.enrich(row.id);
                      const filled = result.filled.map((item) => item.field).join(", ") || "nothing new";
                      setNote(`${row.company_name}: filled ${filled}. Still missing ${result.missing_fields.join(", ") || "nothing"}. ${result.why}`);
                      setError("");
                      load();
                    } catch (err) {
                      setError(err instanceof Error ? err.message : "Unable to enrich this lead.");
                    }
                  }}
                >
                  Enrich
                </Button>
              ),
            },
          ]}
        />
      ) : (
        <EmptyState title="No leads" description="Enrichment runs on leads you already have." />
      )}
    </Stack>
  );
}
