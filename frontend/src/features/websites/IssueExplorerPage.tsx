"use client";

import { Button, Chip, FormControl, InputLabel, MenuItem, Paper, Select, Stack, Typography } from "@mui/material";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState } from "@/components/feedback/EmptyState";
import { ErrorState } from "@/components/feedback/ErrorState";
import { LoadingState } from "@/components/feedback/LoadingState";
import { auditApi, websiteApi } from "@/services/domainApi";
import type { AuditIssue } from "@/types/domain";

export function IssueExplorerPage() {
  const params = useParams<{ id: string }>();
  const [auditId, setAuditId] = useState("");
  const [issues, setIssues] = useState<AuditIssue[]>([]);
  const [severity, setSeverity] = useState("all");
  const [category, setCategory] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    websiteApi
      .get(params.id)
      .then((site) => {
        if (!site.last_audit) {
          setIssues([]);
          return;
        }
        setAuditId(site.last_audit.id);
        return auditApi.issues(site.last_audit.id).then((rows) => setIssues(rows));
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [params.id]);

  const categories = useMemo(() => Array.from(new Set(issues.map((issue) => issue.category))), [issues]);
  const filtered = useMemo(
    () =>
      issues.filter(
        (issue) =>
          (severity === "all" || issue.severity === severity) && (category === "all" || issue.category === category),
      ),
    [issues, severity, category],
  );

  const setStatus = async (issue: AuditIssue, status: string) => {
    if (!auditId) return;
    try {
      const updated = await auditApi.updateIssue(auditId, issue.id, { status });
      setIssues((current) => current.map((row) => (row.id === updated.id ? { ...row, ...updated } : row)));
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update issue status.");
    }
  };

  if (loading) return <LoadingState />;
  if (error && !issues.length) return <ErrorState message={error} />;

  return (
    <Stack spacing={2}>
      <PageHeader title="Issues" description="Verified findings from the latest live crawl. Status changes stay in this workspace." />
      {error ? <ErrorState message={error} /> : null}
      {issues.length === 0 && !error ? <EmptyState title="No issues" description="Run an audit to generate findings from crawled HTML." /> : null}
      <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
        <FormControl sx={{ minWidth: 180 }} size="small">
          <InputLabel>Severity</InputLabel>
          <Select value={severity} label="Severity" onChange={(event) => setSeverity(event.target.value)}>
            <MenuItem value="all">All</MenuItem>
            <MenuItem value="critical">Critical</MenuItem>
            <MenuItem value="high">High</MenuItem>
            <MenuItem value="medium">Medium</MenuItem>
            <MenuItem value="low">Low</MenuItem>
          </Select>
        </FormControl>
        <FormControl sx={{ minWidth: 180 }} size="small">
          <InputLabel>Category</InputLabel>
          <Select value={category} label="Category" onChange={(event) => setCategory(event.target.value)}>
            <MenuItem value="all">All</MenuItem>
            {categories.map((item) => (
              <MenuItem key={item} value={item}>
                {item}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Stack>
      {filtered.map((issue) => (
        <Paper key={issue.id} variant="outlined" sx={{ p: 2 }}>
          <Stack direction="row" spacing={1} sx={{ mb: 1, flexWrap: "wrap", gap: 1 }}>
            <Chip size="small" color={issue.severity === "high" || issue.severity === "critical" ? "error" : "warning"} label={issue.severity} />
            <Chip size="small" label={issue.category} variant="outlined" />
            <Chip size="small" label={issue.origin} variant="outlined" />
            <Chip size="small" label={issue.status} />
          </Stack>
          <Typography variant="h5">{issue.title}</Typography>
          <Typography variant="subtitle2" sx={{ mt: 1 }}>
            Why it matters
          </Typography>
          <Typography color="text.secondary">{issue.why_it_matters}</Typography>
          <Typography variant="subtitle2" sx={{ mt: 1 }}>
            Evidence
          </Typography>
          <Typography>{issue.evidence}</Typography>
          <Typography variant="subtitle2" sx={{ mt: 1 }}>
            How to fix
          </Typography>
          <Typography>{issue.recommendation}</Typography>
          <Typography variant="body2" sx={{ mt: 1 }} color="text.secondary">
            Effort: {issue.estimated_effort || "n/a"} · URLs: {issue.affected_urls.join(", ") || "—"}
          </Typography>
          <Stack direction="row" spacing={1} sx={{ mt: 1.5 }}>
            <Button size="small" disabled={issue.status === "resolved"} onClick={() => void setStatus(issue, "resolved")}>
              Mark resolved
            </Button>
            <Button size="small" disabled={issue.status === "ignored"} onClick={() => void setStatus(issue, "ignored")}>
              Ignore
            </Button>
            <Button size="small" disabled={issue.status === "open"} onClick={() => void setStatus(issue, "open")}>
              Reopen
            </Button>
          </Stack>
        </Paper>
      ))}
    </Stack>
  );
}
