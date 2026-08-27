"use client";

import { Button, Chip, Paper, Stack, Typography } from "@mui/material";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState } from "@/components/feedback/EmptyState";
import { ErrorState } from "@/components/feedback/ErrorState";
import { LoadingState } from "@/components/feedback/LoadingState";
import { auditApi, websiteApi } from "@/services/domainApi";
import type { AuditRecommendation } from "@/types/domain";

export function RecommendationsPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [items, setItems] = useState<AuditRecommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    websiteApi
      .get(params.id)
      .then((site) => {
        if (!site.last_audit) {
          setItems([]);
          return;
        }
        return auditApi.recommendations(site.last_audit.id).then((rows) => {
          setItems(rows.sort((a, b) => (b.priority ?? 0) - (a.priority ?? 0)));
        });
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [params.id]);

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;

  return (
    <Stack spacing={2}>
      <PageHeader
        title="Fix roadmap"
        description="Prioritized actions from verified crawl findings. AI interpretation appears only when an AI provider is configured."
        actions={
          <Stack direction="row" spacing={1}>
            <Button onClick={() => router.push(`/app/websites/${params.id}/keywords`)}>Keyword ranks</Button>
            <Button variant="contained" onClick={() => router.push(`/app/websites/${params.id}/fix`)}>
              Connect access and apply fixes
            </Button>
          </Stack>
        }
      />
      {items.length === 0 ? (
        <EmptyState title="No recommendations yet" description="Complete an audit to build a fact-based fix list." />
      ) : null}
      {items.map((item) => (
        <Paper key={item.id} variant="outlined" sx={{ p: 2 }}>
          <Stack direction="row" spacing={1} sx={{ mb: 1, flexWrap: "wrap", gap: 1 }}>
            {item.severity ? <Chip size="small" label={item.severity} color={item.severity === "critical" || item.severity === "high" ? "error" : "warning"} /> : null}
            {item.category ? <Chip size="small" label={item.category} variant="outlined" /> : null}
            <Chip size="small" label={item.effort || "effort n/a"} variant="outlined" />
            <Chip size="small" label={`Priority ${item.priority ?? "—"}`} variant="outlined" />
          </Stack>
          <Typography variant="h5">{item.title}</Typography>
          <Typography variant="subtitle2" sx={{ mt: 1 }}>
            Verified finding
          </Typography>
          <Typography color="text.secondary">{item.verified_finding}</Typography>
          {item.ai_interpretation ? (
            <>
              <Typography variant="subtitle2" sx={{ mt: 1 }}>
                AI interpretation
              </Typography>
              <Typography>{item.ai_interpretation}</Typography>
            </>
          ) : (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              Fact-based recommendation. AI interpretation is empty until an AI provider is connected.
            </Typography>
          )}
          <Typography variant="subtitle2" sx={{ mt: 1 }}>
            Action
          </Typography>
          <Typography>{item.recommendation}</Typography>
        </Paper>
      ))}
    </Stack>
  );
}
