"use client";

import { Alert, Box, Button, Chip, Paper, Stack, Typography } from "@mui/material";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { PageHeader } from "@/components/common/PageHeader";
import { PrintReportChrome } from "@/components/common/PrintReportChrome";
import { ErrorState } from "@/components/feedback/ErrorState";
import { LoadingState } from "@/components/feedback/LoadingState";
import { ScoreGrid } from "@/features/websites/ScoreGrid";
import { auditApi } from "@/services/domainApi";
import type { AuditReport } from "@/types/domain";

function downloadJson(report: AuditReport) {
  const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${report.website.domain}-sipulse-audit.json`;
  link.click();
  URL.revokeObjectURL(url);
}

function downloadCsv(report: AuditReport) {
  const rows = [["severity", "category", "title", "evidence", "recommendation", "status", "urls"]];
  Object.values(report.issues_by_category)
    .flat()
    .forEach((issue) => {
      rows.push([
        issue.severity,
        issue.category,
        issue.title,
        issue.evidence.replaceAll("\n", " "),
        issue.recommendation.replaceAll("\n", " "),
        issue.status,
        issue.affected_urls.join(" "),
      ]);
    });
  const csv = rows.map((row) => row.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${report.website.domain}-sipulse-issues.csv`;
  link.click();
  URL.revokeObjectURL(url);
}

export function AuditReportPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [report, setReport] = useState<AuditReport | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    auditApi
      .report(params.id)
      .then(setReport)
      .catch((err: Error) => setError(err.message));
  }, [params.id]);

  if (error) return <ErrorState message={error} />;
  if (!report) return <LoadingState />;

  const summary = report.audit.summary ?? {};

  return (
    <PrintReportChrome
      title={`${report.website.name || report.website.domain} — intelligence report`}
      actions={
        <Stack direction="row" spacing={1}>
          <Button onClick={() => downloadCsv(report)}>CSV issues</Button>
          <Button onClick={() => downloadJson(report)}>JSON</Button>
          <Button onClick={() => router.push(`/app/websites/${report.website.id}/keywords`)}>Keyword ranks</Button>
          <Button variant="contained" onClick={() => router.push(`/app/websites/${report.website.id}/fix?audit=${report.audit.id}`)}>
            Connect access and apply fixes
          </Button>
        </Stack>
      }
    >
    <Stack spacing={3} className="audit-report">
      <PageHeader
        title={`${report.website.name || report.website.domain} — intelligence report`}
        description={report.website.url}
      />
      <Typography color="text.secondary">
        Generated {report.audit.completed_at ? new Date(report.audit.completed_at).toLocaleString() : ""} · {report.audit.pages_crawled} pages crawled ·{" "}
        {report.audit.issue_count} findings · origin: fact
      </Typography>
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography variant="h4">Overall {report.audit.overall_score ?? "—"}</Typography>
        {typeof summary.delta === "number" ? (
          <Typography color="text.secondary">
            {summary.delta > 0 ? "+" : ""}
            {String(summary.delta)} vs previous audit
          </Typography>
        ) : null}
        {typeof summary.performance_note === "string" ? (
          <Alert severity="info" sx={{ mt: 1 }}>
            {summary.performance_note}
          </Alert>
        ) : null}
      </Paper>
      <ScoreGrid scores={report.audit.scores ?? {}} />
      <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", gap: 1 }}>
        <Chip label={summary.https ? "HTTPS" : "Not HTTPS"} color={summary.https ? "success" : "error"} />
        <Chip label={summary.robots_txt ? "robots.txt" : "No robots.txt"} variant="outlined" />
        <Chip label={summary.sitemap ? "Sitemap" : "No sitemap"} variant="outlined" />
        <Chip label={summary.faq_schema ? "FAQ schema" : "No FAQ schema"} variant="outlined" />
        <Chip label={`TTFB ${String(summary.avg_ttfb_ms ?? "—")} ms`} variant="outlined" />
      </Stack>
      {report.website.competitors?.length ? (
        <Typography color="text.secondary">Competitors on file: {report.website.competitors.join(", ")}. Audit each as its own website for a like-for-like crawl.</Typography>
      ) : null}
      {Object.entries(report.issues_by_category).map(([category, issues]) => (
        <Box key={category}>
          <Typography variant="h4" sx={{ mb: 1, textTransform: "capitalize" }}>
            {category.replaceAll("_", " ")}
          </Typography>
          <Stack spacing={1.5}>
            {issues.map((issue) => (
              <Paper key={issue.id} variant="outlined" sx={{ p: 2 }}>
                <Stack direction="row" spacing={1} sx={{ mb: 1, flexWrap: "wrap", gap: 1 }}>
                  <Chip size="small" label={issue.severity} color={issue.severity === "critical" || issue.severity === "high" ? "error" : "warning"} />
                  <Chip size="small" label={issue.status} variant="outlined" />
                </Stack>
                <Typography variant="h5">{issue.title}</Typography>
                <Typography sx={{ mt: 1 }}>{issue.evidence}</Typography>
                <Typography color="text.secondary" sx={{ mt: 1 }}>
                  {issue.recommendation}
                </Typography>
              </Paper>
            ))}
          </Stack>
        </Box>
      ))}
      <Button className="no-print" onClick={() => router.push(`/app/websites/${report.website.id}`)}>Back to website</Button>
    </Stack>
    </PrintReportChrome>
  );
}
