"use client";

import { Box, Button, Chip, Paper, Stack, Typography } from "@mui/material";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { PageHeader } from "@/components/common/PageHeader";
import { ScoreRing } from "@/components/common/ScoreRing";
import { StatCard } from "@/components/common/StatCard";
import { StatusChip } from "@/components/common/StatusChip";
import { ErrorState } from "@/components/feedback/ErrorState";
import { LoadingState } from "@/components/feedback/LoadingState";
import { auditApi, websiteApi } from "@/services/domainApi";
import type { PerformancePageDetail } from "@/types/domain";

export function PerformancePageDetailView() {
  const params = useParams<{ id: string; pageId: string }>();
  const router = useRouter();
  const [detail, setDetail] = useState<PerformancePageDetail | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    websiteApi
      .get(params.id)
      .then((site) => {
        const auditId = site.last_audit?.id;
        if (!auditId) throw new Error("No completed audit.");
        return auditApi.page(auditId, params.pageId);
      })
      .then(setDetail)
      .catch((err: Error) => setError(err.message));
  }, [params.id, params.pageId]);

  if (error) return <ErrorState message={error} />;
  if (!detail) return <LoadingState />;

  const hops = detail.redirect_hops || [];
  const timing = detail.timing || {};
  const response = detail.response || {};

  return (
    <Stack spacing={3}>
      <PageHeader
        eyebrow="URL detail"
        title={detail.url}
        description="All timings below are Seonet crawl measurements unless a lab source is labeled."
        actions={
          <Button onClick={() => router.push(`/app/websites/${params.id}/performance`)}>Back to performance</Button>
        }
      />
      <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)", md: "repeat(5, 1fr)" } }}>
        <Paper variant="outlined" sx={{ p: 2, display: "flex", justifyContent: "center" }}>
          <ScoreRing value={detail.page_score} size={96} />
        </Paper>
        <StatCard label="TTFB" value={`${detail.ttfb_ms} ms`} hint="Seonet Crawl" />
        <StatCard label="Status" value={detail.status_code ?? "—"} />
        <StatCard label="HTML size" value={`${Math.round(detail.html_size_bytes / 1024)} KB`} />
        <StatCard label="Transfer" value={`${Math.round(detail.transfer_bytes / 1024)} KB`} />
      </Box>
      <Typography variant="h4">Network</Typography>
      <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr 1fr", md: "repeat(6, 1fr)" } }}>
        <StatCard label="DNS" value={timing.dns_ms == null ? "—" : `${timing.dns_ms} ms`} hint="When exposed" />
        <StatCard label="TCP" value={timing.tcp_ms == null ? "—" : `${timing.tcp_ms} ms`} hint="When exposed" />
        <StatCard label="TLS" value={timing.tls_ms == null ? "—" : `${timing.tls_ms} ms`} hint="When exposed" />
        <StatCard label="TTFB" value={`${timing.ttfb_ms ?? detail.ttfb_ms} ms`} hint="Crawl" />
        <StatCard label="Download" value={`${timing.download_ms ?? "—"} ms`} hint="Crawl" />
        <StatCard label="Total" value={`${timing.total_ms ?? "—"} ms`} hint="Crawl" />
      </Box>
      <Typography variant="h4">Response</Typography>
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Stack spacing={0.75}>
          {Object.entries({
            Status: response.status,
            Protocol: response.protocol,
            Compression: response.compression,
            "Cache-Control": response.cache_control,
            ETag: response.etag,
            "Last-Modified": response.last_modified,
            Server: response.server,
            CDN: response.cdn,
            "Final URL": response.final_url,
          }).map(([label, value]) => (
            <Typography key={label}>
              <strong>{label}:</strong> {String(value || "—")}
            </Typography>
          ))}
        </Stack>
      </Paper>
      <Typography variant="h4">Redirect chain</Typography>
      <Paper variant="outlined" sx={{ p: 2 }}>
        {hops.length ? (
          <Stack spacing={1}>
            {hops.map((hop, index) => (
              <Typography key={`${hop.url}-${index}`}>
                {String(hop.url)} → {String(hop.status || hop.type || "")}
              </Typography>
            ))}
            <Typography>{detail.url} → {detail.status_code}</Typography>
          </Stack>
        ) : (
          <Typography color="text.secondary">No redirect hops. Final status {detail.status_code}.</Typography>
        )}
      </Paper>
      <Typography variant="h4">Resources</Typography>
      <Stack spacing={1}>
        {(detail.resources || []).slice(0, 40).map((resource, index) => (
          <Paper key={`${resource.url}-${index}`} variant="outlined" sx={{ p: 1.5 }}>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1} sx={{ justifyContent: "space-between" }}>
              <Typography sx={{ wordBreak: "break-all" }}>{String(resource.url)}</Typography>
              <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap" }}>
                <Chip size="small" label={String(resource.type)} />
                <Chip size="small" variant="outlined" label={resource.first_party ? "first-party" : "third-party"} />
                {resource.blocking ? <Chip size="small" color="warning" label="blocking" /> : null}
              </Stack>
            </Stack>
          </Paper>
        ))}
      </Stack>
      <Typography variant="h4">Recommendations</Typography>
      {(detail.issues || []).map((issue) => (
        <Paper key={issue.id} variant="outlined" sx={{ p: 2 }}>
          <Stack direction="row" spacing={1} sx={{ mb: 0.5, alignItems: "center" }}>
            <StatusChip value={issue.severity} />
            <Typography variant="h5">{issue.title}</Typography>
          </Stack>
          <Typography color="text.secondary">{issue.evidence}</Typography>
          <Typography sx={{ mt: 1 }}>{issue.recommendation}</Typography>
        </Paper>
      ))}
    </Stack>
  );
}
