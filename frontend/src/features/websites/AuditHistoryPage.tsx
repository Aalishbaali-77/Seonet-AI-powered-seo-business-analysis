"use client";

import { Box, Button, Paper, Stack, Typography } from "@mui/material";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState } from "@/components/feedback/EmptyState";
import { LoadingState } from "@/components/feedback/LoadingState";
import { auditApi } from "@/services/domainApi";
import type { Audit } from "@/types/domain";

export function AuditHistoryPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [items, setItems] = useState<Audit[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    auditApi
      .listAll({ website: params.id })
      .then((rows) => setItems(rows))
      .finally(() => setLoading(false));
  }, [params.id]);

  if (loading) return <LoadingState />;

  return (
    <Stack spacing={2}>
      <PageHeader title="Audit history" description="Every crawl for this website, with score movement between completed audits." />
      {items.length === 0 ? <EmptyState title="No audits yet" description="Run the first audit to start a history." /> : null}
      {items.map((audit, index) => {
        const older = items[index + 1];
        const delta =
          audit.overall_score != null && older?.overall_score != null ? audit.overall_score - older.overall_score : audit.summary?.delta;
        return (
          <Paper key={audit.id} variant="outlined" sx={{ p: 2 }}>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ justifyContent: "space-between", alignItems: { sm: "center" } }}>
              <Box>
                <Typography variant="h5">
                  Score {audit.overall_score ?? "—"}{" "}
                  {typeof delta === "number" && index > 0 ? (
                    <Typography component="span" color={delta > 0 ? "success.main" : delta < 0 ? "error.main" : "text.secondary"}>
                      {delta > 0 ? "+" : ""}
                      {delta}
                    </Typography>
                  ) : null}
                </Typography>
                <Typography color="text.secondary">
                  {audit.status} · {audit.pages_crawled} pages · {audit.issue_count} issues ·{" "}
                  {audit.completed_at ? new Date(audit.completed_at).toLocaleString() : new Date(audit.created_at).toLocaleString()}
                </Typography>
              </Box>
              <Button disabled={audit.status !== "completed"} onClick={() => router.push(`/app/audits/${audit.id}/report`)}>
                Report
              </Button>
            </Stack>
          </Paper>
        );
      })}
    </Stack>
  );
}
