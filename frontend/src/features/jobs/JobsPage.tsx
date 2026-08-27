"use client";

import { Alert, Button, MenuItem, Stack, TextField } from "@mui/material";
import { useEffect, useState } from "react";

import { PageHeader } from "@/components/common/PageHeader";
import { ResponsiveDataList } from "@/components/common/ResponsiveDataList";
import { StatusChip } from "@/components/common/StatusChip";
import { EmptyState } from "@/components/feedback/EmptyState";
import { ErrorState } from "@/components/feedback/ErrorState";
import { LoadingState } from "@/components/feedback/LoadingState";
import { jobApi } from "@/services/domainApi";
import type { Job } from "@/types/domain";

export function JobsPage() {
  const [rows, setRows] = useState<Job[]>([]);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = async (next = status) => {
    const params: Record<string, string> = {};
    if (next) params.status = next;
    const page = await jobApi.list(params);
    setRows(page.results);
  };

  useEffect(() => {
    void load()
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingState />;
  if (error && !rows.length) return <ErrorState message={error} onRetry={() => void load().catch((err: Error) => setError(err.message))} />;

  return (
    <Stack spacing={3}>
      <PageHeader
        title="Jobs"
        description="Background work for this workspace: audits, enrichment, keyword ranks, and store syncs. Progress is stored on the job record."
      />
      {error ? <Alert severity="error">{error}</Alert> : null}
      <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
        <TextField select size="small" label="Status" value={status} onChange={(event) => setStatus(event.target.value)} sx={{ minWidth: 180 }}>
          <MenuItem value="">All</MenuItem>
          {["QUEUED", "RUNNING", "COMPLETED", "FAILED", "CANCELLED"].map((item) => (
            <MenuItem key={item} value={item}>
              {item}
            </MenuItem>
          ))}
        </TextField>
        <Button onClick={() => void load().catch((err: Error) => setError(err.message))}>Apply</Button>
      </Stack>
      {rows.length ? (
        <ResponsiveDataList
          rows={rows}
          cardTitle={(row) => row.job_type.replace(/_/g, " ")}
          columns={[
            { key: "type", label: "Job", render: (row) => row.job_type.replace(/_/g, " ") },
            { key: "status", label: "Status", render: (row) => <StatusChip value={row.status} /> },
            { key: "progress", label: "Progress", render: (row) => `${row.progress}%` },
            { key: "created", label: "Created", render: (row) => (row.created_at ? new Date(row.created_at).toLocaleString() : "—") },
            { key: "error", label: "Error", render: (row) => row.error || "—" },
            {
              key: "cancel",
              label: "",
              render: (row) =>
                row.status === "QUEUED" || row.status === "RUNNING" || row.status === "PENDING" ? (
                  <Button
                    size="small"
                    onClick={() =>
                      void jobApi
                        .cancel(row.id)
                        .then(() => load())
                        .catch((err: Error) => setError(err.message))
                    }
                  >
                    Cancel
                  </Button>
                ) : null,
            },
          ]}
        />
      ) : (
        <EmptyState title="No jobs" description="Run an audit, enrich leads, or sync a store to create a job." />
      )}
    </Stack>
  );
}
