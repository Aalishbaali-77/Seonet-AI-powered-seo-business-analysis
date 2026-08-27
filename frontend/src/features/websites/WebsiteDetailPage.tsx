"use client";

import { Alert, Box, Button, Chip, Paper, Stack, Typography } from "@mui/material";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { PageHeader } from "@/components/common/PageHeader";
import { ScoreRing, scoreRating } from "@/components/common/ScoreRing";
import { ErrorState } from "@/components/feedback/ErrorState";
import { LoadingState } from "@/components/feedback/LoadingState";
import { useAuditSession } from "@/features/websites/auditSession";
import { ScoreGrid } from "@/features/websites/ScoreGrid";
import { websiteApi } from "@/services/domainApi";
import type { Website } from "@/types/domain";

export function WebsiteDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [site, setSite] = useState<Website | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const { start, job, session } = useAuditSession();

  useEffect(() => {
    websiteApi
      .get(params.id)
      .then(setSite)
      .catch((err: Error) => setError(err.message));
  }, [params.id]);

  useEffect(() => {
    if (job?.status === "COMPLETED" && session?.websiteId === params.id) {
      websiteApi.get(params.id).then(setSite).catch((err: Error) => setError(err.message));
    }
  }, [job?.status, session?.websiteId, params.id]);

  if (!site && error) return <ErrorState message={error} />;
  if (!site) return <LoadingState />;

  const scores = site.last_audit?.scores ?? {};
  const summary = site.last_audit?.summary ?? {};
  const delta = typeof summary.delta === "number" ? summary.delta : null;

  return (
    <Stack spacing={3}>
      <PageHeader
        title={site.name || site.domain}
        description={site.url}
        actions={
          <Button
            variant="contained"
            disabled={busy}
            onClick={async () => {
              setBusy(true);
              setError("");
              try {
                const created = await websiteApi.startAudit(site.id);
                start({ jobId: created.id, websiteId: site.id, websiteLabel: site.name || site.domain });
              } catch (err) {
                setError(err instanceof Error ? err.message : "Unable to start audit.");
              } finally {
                setBusy(false);
              }
            }}
          >
            {busy ? "Starting…" : "Run audit"}
          </Button>
        }
      />
      {error ? <Alert severity="error">{error}</Alert> : null}
      <Stack direction="row" sx={{ gap: 1, flexWrap: "wrap" }}>
        <Chip label={site.status} />
        <Chip label={site.industry || "No industry"} variant="outlined" />
        {site.keywords?.length ? <Chip label={`${site.keywords.length} keywords`} variant="outlined" /> : null}
        {site.target_markets?.length ? <Chip label={site.target_markets.join(", ")} variant="outlined" /> : null}
      </Stack>
      {site.last_audit ? (
        <>
          <Paper
            variant="outlined"
            sx={{
              p: { xs: 2.5, md: 3.5 },
              background: (theme) =>
                theme.palette.mode === "dark"
                  ? "linear-gradient(135deg, rgba(46,196,182,0.08), rgba(11,79,108,0.18))"
                  : "linear-gradient(135deg, rgba(46,196,182,0.08), rgba(11,79,108,0.06))",
            }}
          >
            <Stack direction={{ xs: "column", sm: "row" }} spacing={3} sx={{ alignItems: { xs: "center", sm: "center" } }}>
              <Stack spacing={1} sx={{ alignItems: "center" }}>
                <ScoreRing value={site.last_audit.overall_score} size={168} stroke={12} label="Overall" />
                <Typography variant="subtitle2" color="text.secondary">
                  Overall
                </Typography>
              </Stack>
              <Box sx={{ flex: 1 }}>
                <Typography variant="h3" sx={{ mb: 0.5 }}>
                  {scoreRating(site.last_audit.overall_score)}
                </Typography>
                <Typography color="text.secondary">
                  {site.last_audit.issue_count} issues · {site.last_audit.pages_crawled ?? "—"} pages crawled ·{" "}
                  {site.last_audit.completed_at ? new Date(site.last_audit.completed_at).toLocaleString() : ""}
                  {delta !== null ? ` · ${delta > 0 ? "+" : ""}${delta} vs previous audit` : ""}
                </Typography>
                {typeof summary.performance_note === "string" ? (
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1.25 }}>
                    {summary.performance_note}
                  </Typography>
                ) : null}
              </Box>
            </Stack>
          </Paper>
          <ScoreGrid scores={scores} />
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1} sx={{ flexWrap: "wrap", gap: 1 }}>
            <Button onClick={() => router.push(`/app/websites/${site.id}/issues`)}>Issues</Button>
            <Button onClick={() => router.push(`/app/websites/${site.id}/performance`)}>Performance</Button>
            <Button onClick={() => router.push(`/app/websites/${site.id}/recommendations`)}>Recommendations</Button>
            <Button onClick={() => router.push(`/app/websites/${site.id}/keywords`)}>Keyword ranks</Button>
            <Button onClick={() => router.push(`/app/websites/${site.id}/fix`)}>Apply recommended fixes</Button>
            <Button onClick={() => router.push(`/app/websites/${site.id}/history`)}>History</Button>
            <Button variant="contained" onClick={() => router.push(`/app/audits/${site.last_audit?.id}/report`)}>
              Open report
            </Button>
          </Stack>
        </>
      ) : (
        <>
          <Alert severity="info">No completed audit yet. Run an audit to generate verified findings from a live crawl. Keyword ranks can still use stored keywords.</Alert>
          <Button onClick={() => router.push(`/app/websites/${site.id}/keywords`)}>Keyword ranks</Button>
        </>
      )}
      {site.competitors?.length ? (
        <Box>
          <Typography variant="subtitle2">Competitors saved for this property</Typography>
          <Typography color="text.secondary">{site.competitors.join(", ")}. Each competitor can be added as its own website for a like-for-like audit.</Typography>
        </Box>
      ) : null}
    </Stack>
  );
}
