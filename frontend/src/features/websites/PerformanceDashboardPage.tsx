"use client";

import { Alert, Box, Button, Paper, Stack, Typography } from "@mui/material";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { PrintReportChrome } from "@/components/common/PrintReportChrome";
import { PageHeader } from "@/components/common/PageHeader";
import { ScoreRing } from "@/components/common/ScoreRing";
import { StatCard } from "@/components/common/StatCard";
import { EmptyState } from "@/components/feedback/EmptyState";
import { LoadingState } from "@/components/feedback/LoadingState";
import { websiteApi } from "@/services/domainApi";
import type { Website } from "@/types/domain";

function snapshotOf(site: Website) {
  const summary = site.last_audit?.summary ?? {};
  return (summary.performance as Record<string, unknown> | undefined) ?? {};
}

function kpisOf(site: Website) {
  const snap = snapshotOf(site);
  return (snap.kpis as Record<string, number> | undefined) ?? {};
}

export function PerformanceDashboardPage() {
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
    if (!audited.length) return { overall: 0, technical: 0, ux: null as number | null, ttfb: 0 };
    const overall = Math.round(audited.reduce((sum, site) => sum + (site.last_audit?.scores.performance ?? 0), 0) / audited.length);
    const technical = Math.round(
      audited.reduce((sum, site) => sum + (site.last_audit?.scores.technical_performance ?? site.last_audit?.scores.performance ?? 0), 0) / audited.length,
    );
    const uxValues = audited.map((site) => site.last_audit?.scores.ux_cwv).filter((value): value is number => typeof value === "number");
    const ttfb = Math.round(audited.reduce((sum, site) => sum + (kpisOf(site).median_ttfb_ms || Number(site.last_audit?.summary?.avg_ttfb_ms) || 0), 0) / audited.length);
    return { overall, technical, ux: uxValues.length ? Math.round(uxValues.reduce((a, b) => a + b, 0) / uxValues.length) : null, ttfb };
  }, [audited]);

  if (loading) return <LoadingState />;

  return (
    <PrintReportChrome title="Website Performance Intelligence">
    <Stack spacing={3}>
      <PageHeader
        eyebrow="Website intelligence"
        title="Website Performance Intelligence"
        description="Seonet scores come from the crawler: TTFB, HTML weight, redirects, compression, caching, and protocol. Browser lab / Core Web Vitals are an optional overlay, never the sole score."
      />
      {audited.length === 0 ? (
        <EmptyState title="No performance crawls yet" description="Add a website and run an audit. Technical Performance is measured from live HTTP, not a Lighthouse placeholder." actionLabel="Add website" onAction={() => router.push("/app/websites/new")} />
      ) : (
        <>
          <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", sm: "repeat(3, 1fr)" } }}>
            <Paper variant="outlined" sx={{ p: 2, display: "flex", justifyContent: "center" }}>
              <Stack spacing={1} sx={{ alignItems: "center" }}>
                <ScoreRing value={averages.overall} size={120} label="Overall" />
                <Typography>Seonet Performance</Typography>
              </Stack>
            </Paper>
            <Paper variant="outlined" sx={{ p: 2, display: "flex", justifyContent: "center" }}>
              <Stack spacing={1} sx={{ alignItems: "center" }}>
                <ScoreRing value={averages.technical} size={120} label="Technical" />
                <Typography>Technical Performance</Typography>
              </Stack>
            </Paper>
            <Paper variant="outlined" sx={{ p: 2, display: "flex", justifyContent: "center" }}>
              <Stack spacing={1} sx={{ alignItems: "center" }}>
                <ScoreRing value={averages.ux} size={120} label="UX" />
                <Typography>UX / CWV</Typography>
                <Typography variant="caption" color="text.secondary">
                  {averages.ux === null ? "Lab data unavailable" : "Browser lab / field overlay"}
                </Typography>
              </Stack>
            </Paper>
          </Box>
          <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr 1fr", md: "repeat(4, 1fr)" } }}>
            <StatCard label="Median TTFB" value={`${averages.ttfb} ms`} hint="Seonet Crawl" />
            <StatCard label="Properties audited" value={audited.length} />
            <StatCard label="Data source" value="Crawl" hint="Lighthouse is optional" />
            <StatCard label="UX coverage" value={averages.ux === null ? "Off" : "On"} />
          </Box>
          <Alert severity="info">Click a property to open URL-level TTFB, redirect chains, compression, and crawl comparison.</Alert>
          {audited.map((site) => {
            const kpis = kpisOf(site);
            const delta = typeof site.last_audit?.summary?.delta === "number" ? site.last_audit.summary.delta : null;
            return (
              <Paper key={site.id} variant="outlined" sx={{ p: 2 }}>
                <Stack direction={{ xs: "column", md: "row" }} spacing={2} sx={{ justifyContent: "space-between", alignItems: { md: "center" } }}>
                  <Box>
                    <Typography variant="h5">{site.domain}</Typography>
                    <Typography color="text.secondary">
                      Seonet {site.last_audit?.scores.performance ?? "—"} · Technical {site.last_audit?.scores.technical_performance ?? site.last_audit?.scores.performance ?? "—"} · TTFB{" "}
                      {kpis.median_ttfb_ms ?? site.last_audit?.summary?.avg_ttfb_ms ?? "—"} ms
                      {delta !== null ? ` · ${delta > 0 ? "↑ +" : "↓ "}${delta} vs previous crawl` : ""}
                    </Typography>
                  </Box>
                  <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap" }}>
                    <Button onClick={() => router.push(`/app/websites/${site.id}`)}>Website</Button>
                    <Button variant="contained" onClick={() => router.push(`/app/websites/${site.id}/performance`)}>
                      Open performance
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
