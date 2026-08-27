"use client";

import { Alert, Box, Button, Chip, Paper, Stack, TextField, Typography } from "@mui/material";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { MiniBarChart, MiniLineChart } from "@/components/charts/MiniCharts";
import { PageHeader } from "@/components/common/PageHeader";
import { ResponsiveDataList } from "@/components/common/ResponsiveDataList";
import { ScoreRing } from "@/components/common/ScoreRing";
import { StatCard } from "@/components/common/StatCard";
import { StatusChip } from "@/components/common/StatusChip";
import { ErrorState } from "@/components/feedback/ErrorState";
import { LoadingState } from "@/components/feedback/LoadingState";
import { apiClient } from "@/services/apiClient";
import { auditApi, websiteApi } from "@/services/domainApi";
import type { AuditPerformance, PerformanceCompare, PerformancePageRow, PerformanceTrends, Website } from "@/types/domain";

function formatBytes(value?: number | null) {
  if (!value) return "—";
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${Math.round(value / 1024)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

export function WebsitePerformancePage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [site, setSite] = useState<Website | null>(null);
  const [perf, setPerf] = useState<AuditPerformance | null>(null);
  const [pages, setPages] = useState<PerformancePageRow[]>([]);
  const [pageCount, setPageCount] = useState(0);
  const [page, setPage] = useState(1);
  const [ordering, setOrdering] = useState("-ttfb_ms");
  const [trends, setTrends] = useState<PerformanceTrends | null>(null);
  const [compare, setCompare] = useState<PerformanceCompare | null>(null);
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const auditId = site?.last_audit?.id;
  const pageSize = 25;

  useEffect(() => {
    websiteApi
      .get(params.id)
      .then(async (item) => {
        setSite(item);
        const latest = item.last_audit?.id;
        if (!latest) {
          setLoading(false);
          return;
        }
        const [performance, trend, compared] = await Promise.all([
          auditApi.performance(latest),
          websiteApi.performanceTrends(item.id),
          auditApi.compare(latest),
        ]);
        setPerf(performance);
        setTrends(trend);
        setCompare(compared);
        setLoading(false);
      })
      .catch((err: Error) => {
        setError(err.message);
        setLoading(false);
      });
  }, [params.id]);

  useEffect(() => {
    if (!auditId) return;
    auditApi
      .pages(auditId, {
        ordering,
        page: String(page),
        page_size: String(pageSize),
        ...(search.trim() ? { search: search.trim() } : {}),
      })
      .then((pageList) => {
        setPages(pageList.results);
        setPageCount(pageList.count ?? pageList.results.length);
      })
      .catch((err: Error) => setError(err.message));
  }, [auditId, page, ordering, search]);

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;
  if (!site) return <ErrorState message="Website not found." />;
  if (!auditId || !perf) {
    return (
      <Stack spacing={3}>
        <PageHeader title="Website Performance Intelligence" description={site.domain} />
        <Alert severity="info">Run an audit to capture crawl TTFB, HTML size, redirects, and compression.</Alert>
        <Button variant="contained" onClick={() => router.push(`/app/websites/${site.id}`)}>
          Back to website
        </Button>
      </Stack>
    );
  }

  const snap = perf.snapshot || {};
  const kpis = snap.kpis || {};
  const dist = snap.distributions || {};
  const delta = typeof site.last_audit?.summary?.delta === "number" ? site.last_audit.summary.delta : null;

  const exportCsv = async () => {
    const response = await apiClient.get(`/audits/${auditId}/pages/export/`, { responseType: "blob" });
    const blob = new Blob([response.data], { type: "text/csv" });
    const href = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = href;
    link.download = `performance-${site.domain}.csv`;
    link.click();
    URL.revokeObjectURL(href);
  };

  return (
    <Stack spacing={3}>
      <PageHeader
        eyebrow={site.domain}
        title="Website Performance Intelligence"
        description="Technical Performance is crawl data. UX / CWV is lab or field overlay when a PageSpeed key is configured."
        actions={
          <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap" }}>
            <Button onClick={() => router.push(`/app/websites/${site.id}`)}>Website</Button>
            <Button onClick={() => void exportCsv()}>Export CSV</Button>
          </Stack>
        }
      />
      <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", sm: "repeat(3, 1fr)" } }}>
        <Paper variant="outlined" sx={{ p: 2, display: "flex", justifyContent: "center" }}>
          <Stack spacing={0.5} sx={{ alignItems: "center" }}>
            <ScoreRing value={perf.scores.overall} size={128} />
            <Typography>SIPulse Performance</Typography>
            <Typography variant="body2" color="text.secondary">
              {snap.band || "—"}
              {delta !== null ? ` · ${delta > 0 ? "↑ +" : "↓ "}${delta}` : ""}
            </Typography>
          </Stack>
        </Paper>
        <Paper variant="outlined" sx={{ p: 2, display: "flex", justifyContent: "center" }}>
          <Stack spacing={0.5} sx={{ alignItems: "center" }}>
            <ScoreRing value={perf.scores.technical} size={128} />
            <Typography>Technical Performance</Typography>
            <Typography variant="body2" color="text.secondary">
              SIPulse Crawl
            </Typography>
          </Stack>
        </Paper>
        <Paper variant="outlined" sx={{ p: 2, display: "flex", justifyContent: "center" }}>
          <Stack spacing={0.5} sx={{ alignItems: "center" }}>
            <ScoreRing value={perf.scores.ux} size={128} />
            <Typography>UX / CWV</Typography>
            <Typography variant="body2" color="text.secondary">
              {snap.ux_available ? snap.ux_band : "Unavailable — crawl score still stands"}
            </Typography>
          </Stack>
        </Paper>
      </Box>
      {snap.explain?.overall ? <Alert severity="info">{snap.explain.overall}</Alert> : null}
      {snap.regression?.detected ? <Alert severity="warning">{snap.regression.message || "Performance regression detected."}</Alert> : null}
      <Typography variant="h4">Technical health</Typography>
      <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr 1fr", md: "repeat(4, 1fr)" } }}>
        <StatCard label="Median TTFB" value={`${kpis.median_ttfb_ms ?? "—"} ms`} hint="SIPulse Crawl" onClick={() => document.getElementById("url-table")?.scrollIntoView()} />
        <StatCard label="Average TTFB" value={`${kpis.avg_ttfb_ms ?? "—"} ms`} hint="SIPulse Crawl" />
        <StatCard label="HTML size" value={formatBytes(kpis.median_html_bytes)} hint="Median document" />
        <StatCard label="Transfer size" value={formatBytes(kpis.transfer_bytes)} />
        <StatCard label="Compression" value={`${kpis.compression_rate ?? 0}%`} />
        <StatCard label="Redirect pages" value={kpis.redirect_pages ?? 0} />
        <StatCard label="Slow pages" value={kpis.slow_pages ?? 0} />
        <StatCard label="Critical issues" value={perf.issue_counts.critical ?? 0} />
      </Box>
      <Typography variant="h4">Core Web Vitals</Typography>
      <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", sm: "repeat(3, 1fr)" } }}>
        {["lcp_ms", "inp_ms", "cls"].map((key) => (
          <Paper key={key} variant="outlined" sx={{ p: 2 }}>
            <Typography variant="subtitle2" color="text.secondary">
              {key.replace("_ms", "").toUpperCase()}
            </Typography>
            <Typography variant="h4">{String((snap.ux_metrics as Record<string, unknown> | undefined)?.[key] ?? "—")}</Typography>
            <Typography variant="caption" color="text.secondary">
              {snap.ux_available ? "Browser Lab" : "No lab/field data"}
            </Typography>
          </Paper>
        ))}
      </Box>
      {trends?.points?.length ? (
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="h5" sx={{ mb: 2 }}>
            Performance trend
          </Typography>
          <MiniLineChart
            series={[
              { label: "Overall", values: trends.points.map((point) => point.overall) },
              { label: "Technical", values: trends.points.map((point) => point.technical) },
              { label: "UX / CWV", values: trends.points.map((point) => point.ux) },
            ]}
          />
        </Paper>
      ) : null}
      <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" } }}>
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="h5" sx={{ mb: 2 }}>
            Compression
          </Typography>
          <MiniBarChart
            items={Object.entries(dist.compression || {}).map(([label, value]) => ({ label, value }))}
          />
        </Paper>
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="h5" sx={{ mb: 2 }}>
            HTTP protocol
          </Typography>
          <MiniBarChart items={Object.entries(dist.protocol || {}).map(([label, value]) => ({ label, value }))} />
        </Paper>
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="h5" sx={{ mb: 2 }}>
            Resource weight
          </Typography>
          <MiniBarChart items={Object.entries(dist.resources || {}).map(([label, value]) => ({ label, value }))} />
        </Paper>
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="h5" sx={{ mb: 2 }}>
            Status distribution
          </Typography>
          <MiniBarChart items={Object.entries(dist.status || {}).map(([label, value]) => ({ label, value }))} />
        </Paper>
      </Box>
      <Typography variant="h4">Top performance issues</Typography>
      <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap" }}>
        {Object.entries(perf.issue_counts).map(([key, value]) => (
          <Chip key={key} label={`${key} ${value}`} variant="outlined" />
        ))}
      </Stack>
      {(perf.recommendations || []).map((item) => (
        <Paper key={item.code + item.title} variant="outlined" sx={{ p: 2 }}>
          <Stack direction="row" spacing={1} sx={{ mb: 0.5, alignItems: "center" }}>
            <StatusChip value={item.severity} />
            <Typography variant="h5">{item.title}</Typography>
          </Stack>
          <Typography color="text.secondary">{item.evidence}</Typography>
          <Typography sx={{ mt: 1 }}>{item.recommendation}</Typography>
          {item.ai_interpretation ? (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              {item.ai_interpretation}
            </Typography>
          ) : null}
        </Paper>
      ))}
      {compare?.comparison?.available ? (
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="h5" sx={{ mb: 2 }}>
            Crawl comparison
          </Typography>
          <Box sx={{ overflowX: "auto" }}>
            <Box component="table" sx={{ width: "100%", borderCollapse: "collapse", minWidth: 480 }}>
              <Box component="thead">
                <Box component="tr">
                  {["Metric", "Previous", "Current", "Change"].map((label) => (
                    <Box component="th" key={label} sx={{ textAlign: "left", p: 1, borderBottom: 1, borderColor: "divider" }}>
                      {label}
                    </Box>
                  ))}
                </Box>
              </Box>
              <Box component="tbody">
                {compare.comparison.rows.map((row) => (
                  <Box component="tr" key={row.metric}>
                    <Box component="td" sx={{ p: 1, borderBottom: 1, borderColor: "divider" }}>
                      {row.metric}
                    </Box>
                    <Box component="td" sx={{ p: 1, borderBottom: 1, borderColor: "divider" }}>
                      {row.previous ?? "—"}
                    </Box>
                    <Box component="td" sx={{ p: 1, borderBottom: 1, borderColor: "divider" }}>
                      {row.current ?? "—"}
                    </Box>
                    <Box component="td" sx={{ p: 1, borderBottom: 1, borderColor: "divider" }}>
                      {row.change === null || row.change === undefined ? "—" : `${row.change > 0 ? "+" : ""}${row.change}`}
                    </Box>
                  </Box>
                ))}
              </Box>
            </Box>
          </Box>
        </Paper>
      ) : null}
      <Box id="url-table">
        <Typography variant="h4" sx={{ mb: 2 }}>
          URL performance
        </Typography>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1} sx={{ mb: 2, alignItems: { sm: "center" }, flexWrap: "wrap" }}>
          <TextField
            label="Search URL"
            value={search}
            onChange={(event) => {
              setSearch(event.target.value);
              setPage(1);
            }}
            sx={{ maxWidth: 360 }}
          />
          {[
            { key: "-ttfb_ms", label: "Slowest TTFB" },
            { key: "ttfb_ms", label: "Fastest TTFB" },
            { key: "-html_size_bytes", label: "Largest HTML" },
            { key: "page_score", label: "Lowest score" },
          ].map((item) => (
            <Button key={item.key} variant={ordering === item.key ? "contained" : "outlined"} onClick={() => { setOrdering(item.key); setPage(1); }}>
              {item.label}
            </Button>
          ))}
        </Stack>
        <ResponsiveDataList
          rows={pages}
          cardTitle={(row) => row.url}
          onRowClick={(row) => router.push(`/app/websites/${site.id}/performance/pages/${row.id}`)}
          columns={[
            { key: "url", label: "URL", render: (row) => row.url },
            { key: "status", label: "Status", hideOnMobile: true, render: (row) => row.status_code ?? "—" },
            { key: "score", label: "Performance", render: (row) => row.page_score ?? "—" },
            { key: "ttfb", label: "TTFB", render: (row) => `${row.ttfb_ms} ms` },
            { key: "html", label: "HTML", hideOnMobile: true, render: (row) => formatBytes(row.html_size_bytes) },
            { key: "transfer", label: "Transfer", hideOnMobile: true, render: (row) => formatBytes(row.transfer_bytes) },
            { key: "redirects", label: "Redirects", hideOnMobile: true, render: (row) => row.redirect_count },
            { key: "compression", label: "Compression", render: (row) => row.compression || "none" },
            { key: "protocol", label: "Protocol", hideOnMobile: true, render: (row) => row.http_protocol || "—" },
            { key: "lcp", label: "LCP", hideOnMobile: true, render: (row) => (row.lcp_ms ? `${row.lcp_ms} ms` : "—") },
          ]}
        />
        <Stack direction="row" spacing={1} sx={{ mt: 2, alignItems: "center" }}>
          <Button disabled={page <= 1} onClick={() => setPage((current) => Math.max(1, current - 1))}>
            Previous
          </Button>
          <Typography variant="body2" color="text.secondary">
            Page {page} of {Math.max(1, Math.ceil(pageCount / pageSize))} · {pageCount} URLs
          </Typography>
          <Button disabled={page * pageSize >= pageCount} onClick={() => setPage((current) => current + 1)}>
            Next
          </Button>
        </Stack>
      </Box>
    </Stack>
  );
}
