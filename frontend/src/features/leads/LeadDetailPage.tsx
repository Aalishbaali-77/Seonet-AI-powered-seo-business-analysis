"use client";

import { Button, Paper, Stack, Typography } from "@mui/material";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { PageHeader } from "@/components/common/PageHeader";
import { StatusChip } from "@/components/common/StatusChip";
import { ErrorState } from "@/components/feedback/ErrorState";
import { LoadingState } from "@/components/feedback/LoadingState";
import { promoteLeadToCrm } from "@/features/leads/promoteLead";
import { leadApi } from "@/services/domainApi";
import { useAppSelector } from "@/store/hooks";
import type { Lead } from "@/types/domain";

export function LeadDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const canCrm = useAppSelector((state) => state.auth.user?.modules ?? []).includes("crm");
  const [lead, setLead] = useState<Lead | null>(null);
  const [error, setError] = useState("");

  const load = () =>
    leadApi
      .get(params.id)
      .then((item) => {
        setLead(item);
        setError("");
      })
      .catch((err: Error) => setError(err.message));

  useEffect(() => {
    void load();
  }, [params.id]);

  const patchStatus = async (next: Lead["status"]) => {
    if (!lead) return;
    try {
      setLead(await leadApi.update(lead.id, { status: next }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update lead.");
    }
  };

  if (!lead && !error) return <LoadingState />;
  if (error && !lead) return <ErrorState message={error} onRetry={() => void load()} />;
  if (!lead) return <ErrorState message="Lead not found." />;

  return (
    <Stack spacing={3}>
      <PageHeader
        title={lead.company_name}
        description={`${lead.industry || "Industry unknown"} · ${lead.location || "Location unknown"}`}
        actions={
          <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap" }}>
            <Button onClick={() => router.push("/app/leads")}>Back to leads</Button>
            <Button disabled={lead.status === "qualified"} onClick={() => void patchStatus("qualified")}>
              Qualify
            </Button>
            <Button disabled={lead.status === "contacted"} onClick={() => void patchStatus("contacted")}>
              Mark contacted
            </Button>
            <Button
              disabled={!lead.website}
              onClick={() =>
                window.open(lead.website.startsWith("http") ? lead.website : `https://${lead.website}`, "_blank", "noopener")
              }
            >
              Open website
            </Button>
            <Button
              onClick={async () => {
                try {
                  const result = await leadApi.enrich(lead.id);
                  setLead(result.lead);
                  setError(result.missing_fields.length ? `Still missing ${result.missing_fields.join(", ")}.` : "");
                } catch (err) {
                  setError(err instanceof Error ? err.message : "Unable to enrich this lead.");
                }
              }}
            >
              Enrich
            </Button>
            <Button
              variant="contained"
              disabled={!canCrm || lead.crm_synced}
              onClick={async () => {
                try {
                  await promoteLeadToCrm(lead);
                  setLead({ ...lead, crm_synced: true });
                  router.push("/app/crm");
                } catch (err) {
                  setError(err instanceof Error ? err.message : "Unable to add this lead to CRM.");
                }
              }}
            >
              {lead.crm_synced ? "In CRM" : "Add to CRM"}
            </Button>
          </Stack>
        }
      />
      {error ? <ErrorState message={error} onRetry={() => void load()} /> : null}
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Stack spacing={1}>
          <StatusChip value={lead.status} />
          <Typography>Lead score: {lead.lead_score ?? "—"}</Typography>
          <Typography>Stored opportunity score: {lead.opportunity_score ?? "—"}</Typography>
          <Typography>Quality: {lead.quality_score ?? "—"}</Typography>
          <Typography>Website: {lead.website || "—"}</Typography>
          <Typography>Email: {lead.email || "—"}</Typography>
          <Typography>Phone: {lead.phone || "—"}</Typography>
          <Typography>LinkedIn: {lead.linkedin_url || "—"}</Typography>
          <Typography>Employees: {lead.employee_count || "—"}</Typography>
          {lead.description ? <Typography>About: {lead.description}</Typography> : null}
          <Typography>
            Source: {lead.source} ({lead.origin})
          </Typography>
          <Typography>CRM synced: {lead.crm_synced ? "Yes" : "No"}</Typography>
          {lead.notes ? <Typography>Notes: {lead.notes}</Typography> : null}
          {lead.ai_summary ? <Typography>Summary: {lead.ai_summary}</Typography> : null}
          {lead.enriched_at ? <Typography>Last enriched: {new Date(lead.enriched_at).toLocaleString()}</Typography> : null}
          {lead.enrichment?.length ? (
            <Typography color="text.secondary">
              Last fill: {(lead.enrichment[lead.enrichment.length - 1].filled || [])
                .map((item) => `${item.field} (${item.source})`)
                .join(", ") || "nothing new"}
            </Typography>
          ) : null}
        </Stack>
      </Paper>
    </Stack>
  );
}
