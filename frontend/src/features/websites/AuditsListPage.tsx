"use client";

import { Button, Chip, Paper, Stack, Typography } from "@mui/material";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState } from "@/components/feedback/EmptyState";
import { ErrorState } from "@/components/feedback/ErrorState";
import { LoadingState } from "@/components/feedback/LoadingState";
import { useJobSession } from "@/features/websites/auditSession";
import { auditApi } from "@/services/domainApi";
import type { Audit } from "@/types/domain";

export function AuditsListPage() {
  const router = useRouter();
  const { start } = useJobSession();
  const [items, setItems] = useState<Audit[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    auditApi
      .listAll()
      .then((rows) => {
        setItems(rows);
        setError("");
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;

  return (
    <Stack spacing={2}>
      <PageHeader title="Audits" description="Completed and in-progress website intelligence runs for this workspace." />
      {items.length === 0 ? (
        <EmptyState title="No audits yet" description="Add a website and start an audit to see scores and issues here." actionLabel="Add website" onAction={() => router.push("/app/websites/new")} />
      ) : null}
      {items.map((audit) => (
        <Paper key={audit.id} variant="outlined" sx={{ p: 2 }}>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ justifyContent: "space-between" }}>
            <Stack spacing={0.5}>
              <Typography variant="h5">{audit.website_name || audit.website_domain || "Website"}</Typography>
              <Typography color="text.secondary">
                Score {audit.overall_score ?? "—"} · {audit.status} · {audit.pages_crawled} pages · {audit.issue_count} issues
              </Typography>
              <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", gap: 1 }}>
                <Chip size="small" label={audit.website_domain || "domain"} variant="outlined" />
                {audit.scores?.aeo != null ? <Chip size="small" label={`AEO ${audit.scores.aeo}`} variant="outlined" /> : null}
                {audit.scores?.geo != null ? <Chip size="small" label={`GEO ${audit.scores.geo}`} variant="outlined" /> : null}
              </Stack>
            </Stack>
            <Stack direction="row" spacing={1} sx={{ alignItems: "flex-start" }}>
              {audit.job && audit.status !== "completed" ? (
                <Button
                  onClick={() =>
                    start({
                      jobId: audit.job as string,
                      kind: "run_audit",
                      title: audit.website_name || audit.website_domain || "Website",
                      href: audit.website_id ? `/app/websites/${audit.website_id}` : "/app/audits",
                      websiteId: audit.website_id,
                    })
                  }
                >
                  Show progress
                </Button>
              ) : null}
              {audit.website_id ? (
                <Button onClick={() => router.push(`/app/websites/${audit.website_id}`)}>Website</Button>
              ) : null}
              <Button variant="contained" disabled={audit.status !== "completed"} onClick={() => router.push(`/app/audits/${audit.id}/report`)}>
                Report
              </Button>
            </Stack>
          </Stack>
        </Paper>
      ))}
    </Stack>
  );
}
