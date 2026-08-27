"use client";

import { Box, Button, Paper, Stack, Typography } from "@mui/material";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { PrintReportChrome } from "@/components/common/PrintReportChrome";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState } from "@/components/feedback/EmptyState";
import { LoadingState } from "@/components/feedback/LoadingState";
import { ScoreGrid } from "@/features/websites/ScoreGrid";
import { websiteApi } from "@/services/domainApi";
import type { Website } from "@/types/domain";

export function SeoDashboardPage() {
  const router = useRouter();
  const [items, setItems] = useState<Website[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    websiteApi
      .listAll()
      .then((rows) => setItems(rows))
      .finally(() => setLoading(false));
  }, []);

  const audited = useMemo(() => items.filter((item) => item.last_audit), [items]);
  const averages = useMemo(() => {
    if (!audited.length) return {};
    const keys = ["technical_seo", "on_page_seo", "content", "schema", "accessibility", "performance"];
    const totals: Record<string, number> = {};
    audited.forEach((site) => {
      keys.forEach((key) => {
        totals[key] = (totals[key] ?? 0) + (site.last_audit?.scores[key] ?? 0);
      });
    });
    return Object.fromEntries(keys.map((key) => [key, Math.round(totals[key] / audited.length)]));
  }, [audited]);

  if (loading) return <LoadingState />;

  return (
    <PrintReportChrome title="SEO intelligence">
    <Stack spacing={3}>
      <PageHeader
        title="SEO intelligence"
        description="Technical, on-page, content, schema, accessibility, and crawl-measured performance from the latest live audits."
      />
      {audited.length === 0 ? (
        <EmptyState title="No SEO scores yet" description="Add a website and run an audit. Scores are computed from crawled HTML, not estimates." actionLabel="Add website" onAction={() => router.push("/app/websites/new")} />
      ) : (
        <>
          <Typography variant="h4">Workspace average</Typography>
          <ScoreGrid scores={averages} keys={["technical_seo", "on_page_seo", "content", "schema", "accessibility", "performance"]} />
          {audited.map((site) => (
            <Paper key={site.id} variant="outlined" sx={{ p: 2 }}>
              <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ justifyContent: "space-between" }}>
                <Box>
                  <Typography variant="h5">{site.domain}</Typography>
                  <Typography color="text.secondary">
                    Overall {site.last_audit?.overall_score ?? "—"} · Technical {site.last_audit?.scores.technical_seo ?? "—"} · On-page{" "}
                    {site.last_audit?.scores.on_page_seo ?? "—"} · {site.last_audit?.issue_count} issues
                  </Typography>
                </Box>
                <Stack direction="row" spacing={1}>
                  <Button onClick={() => router.push(`/app/websites/${site.id}`)}>Website</Button>
                  <Button onClick={() => router.push(`/app/websites/${site.id}/keywords`)}>Keywords</Button>
                  <Button variant="contained" onClick={() => router.push(`/app/websites/${site.id}/issues`)}>
                    Issues
                  </Button>
                </Stack>
              </Stack>
            </Paper>
          ))}
        </>
      )}
    </Stack>
    </PrintReportChrome>
  );
}
