"use client";

import { Box, Button, Chip, Stack, TextField, Typography } from "@mui/material";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { useConfirm } from "@/components/common/ConfirmDialog";
import { PageHeader } from "@/components/common/PageHeader";
import { ResponsiveDataList } from "@/components/common/ResponsiveDataList";
import { RowMenu } from "@/components/common/RowMenu";
import { StatusChip } from "@/components/common/StatusChip";
import { EmptyState } from "@/components/feedback/EmptyState";
import { ErrorState } from "@/components/feedback/ErrorState";
import { LoadingState } from "@/components/feedback/LoadingState";
import { promoteLeadToCrm } from "@/features/leads/promoteLead";
import { useJobSession } from "@/features/websites/auditSession";
import { leadApi } from "@/services/domainApi";
import { useAppSelector } from "@/store/hooks";
import type { Lead } from "@/types/domain";

const STATUS_FILTERS = [
  { key: "", label: "All" },
  { key: "new", label: "New" },
  { key: "qualified", label: "Qualified" },
  { key: "contacted", label: "Contacted" },
  { key: "unqualified", label: "Unqualified" },
];

const PAGE_SIZE = 25;

function websiteHost(website: string) {
  if (!website) return "";
  try {
    return new URL(website.startsWith("http") ? website : `https://${website}`).hostname.replace(/^www\./, "");
  } catch {
    return website;
  }
}

function copyText(value: string) {
  return navigator.clipboard.writeText(value);
}

export function LeadListPage() {
  const router = useRouter();
  const confirm = useConfirm();
  const { job } = useJobSession();
  const modules = useAppSelector((state) => state.auth.user?.modules ?? []);
  const permissions = useAppSelector((state) => state.auth.user?.permissions ?? []);
  const canCrm = modules.includes("crm");
  const canExport = permissions.includes("lead.export");
  const [leads, setLeads] = useState<Lead[]>([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState("");

  const load = useCallback(() => {
    return leadApi
      .list({
        page: String(page),
        page_size: String(PAGE_SIZE),
        ordering: "-updated_at",
        ...(search.trim() ? { search: search.trim() } : {}),
        ...(statusFilter ? { status: statusFilter } : {}),
      })
      .then((data) => {
        setLeads(data.results);
        setCount(data.count ?? data.results.length);
        setStatus("ready");
        setError("");
      })
      .catch((err: Error) => {
        setError(err.message);
        setStatus("error");
      });
  }, [page, search, statusFilter]);

  useEffect(() => {
    const delay = search.trim() ? 300 : 0;
    const handle = window.setTimeout(() => void load(), delay);
    return () => window.clearTimeout(handle);
  }, [load, search]);

  useEffect(() => {
    if (job?.job_type === "discover_leads" && job.status === "COMPLETED") {
      void load();
    }
  }, [job?.id, job?.status, job?.job_type, load]);

  const patchStatus = async (lead: Lead, next: Lead["status"]) => {
    try {
      await leadApi.update(lead.id, { status: next });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update lead.");
    }
  };

  const addToCrm = async (lead: Lead) => {
    try {
      await promoteLeadToCrm(lead);
      await load();
      router.push("/app/crm");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to add this lead to CRM.");
    }
  };

  const removeLead = async (lead: Lead) => {
    const ok = await confirm({
      title: "Remove lead",
      description: `${lead.company_name} will be permanently removed. This cannot be undone.`,
      confirmLabel: "Remove",
    });
    if (!ok) {
      return;
    }
    try {
      await leadApi.delete(lead.id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to remove lead.");
    }
  };

  return (
    <Stack spacing={3}>
      <PageHeader
        title="Leads"
        description="Prospects from confirmed ICPs. Qualify, contact, or send a company into CRM from the row actions."
        actions={
          <Stack direction="row" spacing={1}>
            {canExport && count > 0 ? (
              <Button
                variant="outlined"
                onClick={() =>
                  void leadApi
                    .exportCsv({
                      ...(search.trim() ? { search: search.trim() } : {}),
                      ...(statusFilter ? { status: statusFilter } : {}),
                    })
                    .catch((err: Error) => setError(err.message))
                }
              >
                Export CSV
              </Button>
            ) : null}
            <Button variant="contained" onClick={() => router.push("/app/leads/discover")}>
              Find leads
            </Button>
          </Stack>
        }
      />
      {status === "loading" ? <LoadingState /> : null}
      {error ? <ErrorState message={error} onRetry={() => void load()} /> : null}
      {status === "ready" ? (
        <Stack direction={{ xs: "column", md: "row" }} spacing={1.5} sx={{ alignItems: { md: "center" } }}>
          <TextField
            size="small"
            label="Search company, industry, location, or email"
            value={search}
            onChange={(event) => {
              setSearch(event.target.value);
              setPage(1);
            }}
            sx={{ flex: 1, maxWidth: 420 }}
          />
          <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap" }}>
            {STATUS_FILTERS.map((item) => (
              <Chip
                key={item.label}
                label={item.label}
                color={statusFilter === item.key ? "primary" : "default"}
                variant={statusFilter === item.key ? "filled" : "outlined"}
                onClick={() => {
                  setStatusFilter(item.key);
                  setPage(1);
                }}
              />
            ))}
          </Stack>
        </Stack>
      ) : null}
      {status === "ready" && leads.length === 0 && !error ? (
        <EmptyState
          title={search || statusFilter ? "No matching leads" : "No leads found"}
          description={
            search || statusFilter
              ? "Clear search or status filters to see the rest of the workspace."
              : "Define your ideal customer profile and target locations to discover prospects."
          }
          actionLabel={search || statusFilter ? undefined : "Create lead search"}
          onAction={search || statusFilter ? undefined : () => router.push("/app/leads/discover")}
        />
      ) : null}
      {status === "ready" && leads.length > 0 ? (
        <>
          <ResponsiveDataList
            rows={leads}
            cardTitle={(lead) => lead.company_name}
            onRowClick={(lead) => router.push(`/app/leads/${lead.id}`)}
            columns={[
              { key: "company", label: "Company", render: (lead) => lead.company_name },
              { key: "industry", label: "Industry", hideOnMobile: true, render: (lead) => lead.industry || "—" },
              { key: "location", label: "Location", render: (lead) => lead.location || "—" },
              {
                key: "website",
                label: "Website",
                hideOnMobile: true,
                render: (lead) =>
                  lead.website ? (
                    <Box
                      component="a"
                      href={lead.website.startsWith("http") ? lead.website : `https://${lead.website}`}
                      target="_blank"
                      rel="noreferrer"
                      onClick={(event) => event.stopPropagation()}
                    >
                      {websiteHost(lead.website)}
                    </Box>
                  ) : (
                    "—"
                  ),
              },
              { key: "score", label: "Score", render: (lead) => lead.lead_score ?? "—" },
              { key: "opportunity", label: "Opportunity", hideOnMobile: true, render: (lead) => lead.opportunity_score ?? "—" },
              { key: "source", label: "Source", hideOnMobile: true, render: (lead) => lead.source || "—" },
              { key: "status", label: "Status", render: (lead) => <StatusChip value={lead.status} /> },
              {
                key: "actions",
                label: "Actions",
                render: (lead) => (
                  <RowMenu
                    label={`Actions for ${lead.company_name}`}
                    items={[
                      { label: "Open", onClick: () => router.push(`/app/leads/${lead.id}`) },
                      {
                        label: "Qualify",
                        disabled: lead.status === "qualified",
                        onClick: () => void patchStatus(lead, "qualified"),
                      },
                      {
                        label: "Mark contacted",
                        disabled: lead.status === "contacted",
                        onClick: () => void patchStatus(lead, "contacted"),
                      },
                      {
                        label: "Unqualify",
                        disabled: lead.status === "unqualified",
                        onClick: () => void patchStatus(lead, "unqualified"),
                      },
                      {
                        label: "Open website",
                        disabled: !lead.website,
                        onClick: () =>
                          window.open(lead.website.startsWith("http") ? lead.website : `https://${lead.website}`, "_blank", "noopener"),
                      },
                      {
                        label: "Copy email",
                        disabled: !lead.email,
                        onClick: () => void copyText(lead.email).catch(() => setError("Unable to copy email.")),
                      },
                      {
                        label: "Copy phone",
                        disabled: !lead.phone,
                        onClick: () => void copyText(lead.phone).catch(() => setError("Unable to copy phone.")),
                      },
                      {
                        label: "Enrich",
                        onClick: () =>
                          void leadApi
                            .enrich(lead.id)
                            .then(() => load())
                            .catch((err: Error) => setError(err.message)),
                      },
                      {
                        label: lead.crm_synced ? "In CRM" : "Add to CRM",
                        disabled: !canCrm || lead.crm_synced,
                        onClick: () => void addToCrm(lead),
                      },
                      { label: "Remove", danger: true, onClick: () => void removeLead(lead) },
                    ]}
                  />
                ),
              },
            ]}
          />
          <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
            <Button disabled={page <= 1} onClick={() => setPage((current) => Math.max(1, current - 1))}>
              Previous
            </Button>
            <Typography variant="body2" color="text.secondary">
              Page {page} of {Math.max(1, Math.ceil(count / PAGE_SIZE))} · {count} leads
            </Typography>
            <Button disabled={page * PAGE_SIZE >= count} onClick={() => setPage((current) => current + 1)}>
              Next
            </Button>
          </Stack>
        </>
      ) : null}
    </Stack>
  );
}
