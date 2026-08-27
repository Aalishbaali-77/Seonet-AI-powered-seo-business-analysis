"use client";

import { Alert, Box, Button, Chip, Paper, Stack, Typography } from "@mui/material";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { PrintReportChrome } from "@/components/common/PrintReportChrome";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState } from "@/components/feedback/EmptyState";
import { LoadingState } from "@/components/feedback/LoadingState";
import { ScoreGrid } from "@/features/websites/ScoreGrid";
import { websiteApi } from "@/services/domainApi";
import type { Website } from "@/types/domain";

export function AeoDashboardPage() {
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
    const keys = ["aeo", "geo", "schema", "local_seo", "content"];
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
    <PrintReportChrome title="AEO / GEO intelligence">
    <Stack spacing={3}>
      <PageHeader
        title="AEO / GEO intelligence"
        description="Answer-engine and geographic readiness from JSON-LD types, FAQ/HowTo markup, language, hreflang, and local NAP — measured on the live crawl."
      />
      <Alert severity="info">
        These scores do not invent AI rankings. They measure whether the site publishes the facts answer engines and local/geo crawlers actually read.
      </Alert>
      {audited.length === 0 ? (
        <EmptyState title="No AEO scores yet" description="Run a website audit to measure FAQ, HowTo, Organization, language, and local signals." actionLabel="Add website" onAction={() => router.push("/app/websites/new")} />
      ) : (
        <>
          <ScoreGrid scores={averages} keys={["aeo", "geo", "schema", "local_seo", "content"]} />
          {audited.map((site) => {
            const summary = site.last_audit?.summary ?? {};
            const types = Array.isArray(summary.schema_types) ? (summary.schema_types as string[]) : [];
            return (
              <Paper key={site.id} variant="outlined" sx={{ p: 2 }}>
                <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ justifyContent: "space-between" }}>
                  <Box>
                    <Typography variant="h5">{site.domain}</Typography>
                    <Typography color="text.secondary">
                      AEO {site.last_audit?.scores.aeo ?? "—"} · GEO {site.last_audit?.scores.geo ?? "—"} · Local {site.last_audit?.scores.local_seo ?? "—"}
                    </Typography>
                    <Stack direction="row" spacing={1} sx={{ mt: 1, flexWrap: "wrap", gap: 1 }}>
                      {summary.faq_schema ? <Chip size="small" label="FAQ schema" color="success" /> : <Chip size="small" label="No FAQ schema" variant="outlined" />}
                      {summary.local_business ? <Chip size="small" label="LocalBusiness" color="success" /> : null}
                      {types.slice(0, 6).map((type) => (
                        <Chip key={type} size="small" label={type} variant="outlined" />
                      ))}
                    </Stack>
                  </Box>
                  <Stack direction="row" spacing={1}>
                    <Button onClick={() => router.push(`/app/websites/${site.id}/keywords`)}>Keywords</Button>
                    <Button variant="contained" onClick={() => router.push(`/app/websites/${site.id}`)}>
                      Open
                    </Button>
                  </Stack>
                </Stack>
              </Paper>
            );
          })}
        </>
      )}
    </Stack>
    </PrintReportChrome>
  );
}
