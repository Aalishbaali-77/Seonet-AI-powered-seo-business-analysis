"use client";

import { Button, Paper, Stack, Typography } from "@mui/material";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { PageHeader } from "@/components/common/PageHeader";
import { PrintReportChrome } from "@/components/common/PrintReportChrome";
import { EmptyState } from "@/components/feedback/EmptyState";
import { LoadingState } from "@/components/feedback/LoadingState";
import { auditApi, reportsApi } from "@/services/domainApi";
import { useAppSelector } from "@/store/hooks";
import type { Audit, WorkspaceReport } from "@/types/domain";

export function IntelligenceReportsPage() {
  const router = useRouter();
  const canExport = useAppSelector((state) => state.auth.user?.permissions ?? []).includes("report.export");
  const [items, setItems] = useState<Audit[]>([]);
  const [catalog, setCatalog] = useState<WorkspaceReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    void Promise.all([auditApi.listAll({ status: "completed" }), reportsApi.catalog().catch(() => ({ results: [] }))])
      .then(([audits, reports]) => {
        setItems(audits);
        setCatalog(reports.results);
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingState />;

  return (
    <PrintReportChrome
      title="Intelligence reports"
      actions={
        canExport ? (
          <Button
            onClick={() =>
              void reportsApi
                .exportJson()
                .then((payload) => {
                  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
                  const url = URL.createObjectURL(blob);
                  const link = document.createElement("a");
                  link.href = url;
                  link.download = "seonet-reports.json";
                  link.click();
                  URL.revokeObjectURL(url);
                })
                .catch((err: Error) => setError(err.message))
            }
          >
            Export JSON catalog
          </Button>
        ) : undefined
      }
    >
    <Stack spacing={2}>
      <PageHeader
        title="Intelligence reports"
        description="Print branded workspace reports from real rows. Empty modules stay empty."
      />
      {error ? <Typography color="error">{error}</Typography> : null}
      {catalog.map((report) => (
        <Paper key={report.code} variant="outlined" sx={{ p: 2 }}>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ justifyContent: "space-between", alignItems: { sm: "center" } }}>
            <Stack spacing={0.5}>
              <Typography variant="h5">{report.title}</Typography>
              <Typography color="text.secondary">
                {report.count} records · {report.available ? "Ready to open" : "No data yet"} · {report.why}
              </Typography>
              {report.stages?.length ? (
                <Typography variant="body2" color="text.secondary">
                  {report.stages.map((row) => `${row.name}: ${row.deals} · ${row.amount}`).join(" · ")}
                </Typography>
              ) : null}
            </Stack>
            <Button variant={report.available ? "contained" : "outlined"} onClick={() => router.push(report.href)}>
              Open
            </Button>
          </Stack>
        </Paper>
      ))}
      {items.map((audit) => (
        <Paper key={audit.id} variant="outlined" sx={{ p: 2 }}>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ justifyContent: "space-between", alignItems: { sm: "center" } }}>
            <Stack spacing={0.5}>
              <Typography variant="h5">{audit.website_name || audit.website_domain}</Typography>
              <Typography color="text.secondary">
                Score {audit.overall_score ?? "—"} · {audit.issue_count} issues ·{" "}
                {audit.completed_at ? new Date(audit.completed_at).toLocaleString() : ""}
              </Typography>
            </Stack>
            <Button variant="contained" onClick={() => router.push(`/app/audits/${audit.id}/report`)}>
              Print audit
            </Button>
          </Stack>
        </Paper>
      ))}
      {catalog.length === 0 && items.length === 0 ? (
        <EmptyState title="No reports yet" description="Complete a website audit or import commerce data to produce a report." actionLabel="Websites" onAction={() => router.push("/app/websites")} />
      ) : null}
    </Stack>
    </PrintReportChrome>
  );
}
