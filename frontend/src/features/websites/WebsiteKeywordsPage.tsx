"use client";

import { Alert, Button, Chip, Stack, TextField, Typography } from "@mui/material";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { PageHeader } from "@/components/common/PageHeader";
import { ResponsiveDataList } from "@/components/common/ResponsiveDataList";
import { EmptyState } from "@/components/feedback/EmptyState";
import { ErrorState } from "@/components/feedback/ErrorState";
import { LoadingState } from "@/components/feedback/LoadingState";
import { useAuditSession } from "@/features/websites/auditSession";
import { websiteApi } from "@/services/domainApi";
import type { KeywordRankRun, Website } from "@/types/domain";

function toCsv(values: string[] | undefined) {
  return (values ?? []).join(", ");
}

function fromCsv(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function WebsiteKeywordsPage() {
  const params = useParams<{ id: string }>();
  const { start, job } = useAuditSession();
  const seen = useRef("");
  const [site, setSite] = useState<Website | null>(null);
  const [keywordDraft, setKeywordDraft] = useState("");
  const [saving, setSaving] = useState(false);
  const [run, setRun] = useState<KeywordRankRun | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const checking = Boolean(job && job.job_type === "check_keyword_ranks" && job.status !== "COMPLETED" && job.status !== "FAILED");

  const load = () =>
    Promise.all([websiteApi.get(params.id), websiteApi.keywords(params.id)])
      .then(([website, data]) => {
        setSite(website);
        setKeywordDraft(toCsv(website.keywords));
        setRun(data.run);
        setError("");
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));

  useEffect(() => {
    void load();
  }, [params.id]);

  useEffect(() => {
    if (job?.job_type !== "check_keyword_ranks") return;
    const key = `${job.id}:${job.status}`;
    if (seen.current === key) return;
    if (job.status === "COMPLETED" || job.status === "FAILED") {
      seen.current = key;
      void load();
      if (job.status === "FAILED") setError(job.error || "Keyword check failed.");
    }
  }, [job]);

  if (loading) return <LoadingState />;

  return (
    <Stack spacing={3}>
      <PageHeader
        title="Keyword ranks and suggestions"
        description="Save SEO keywords on this website, then check them in the background. Claude or another package AI drafts extra queries when the subscription includes the AI module."
        actions={
          <Button
            variant="contained"
            disabled={checking}
            onClick={async () => {
              try {
                if (fromCsv(keywordDraft).join(",") !== (site?.keywords ?? []).join(",")) {
                  const updated = await websiteApi.update(params.id, { keywords: fromCsv(keywordDraft) });
                  setSite(updated);
                }
                const created = await websiteApi.checkKeywords(params.id);
                start({
                  jobId: created.id,
                  kind: "check_keyword_ranks",
                  title: "Checking keyword ranks",
                  href: `/app/websites/${params.id}/keywords`,
                  websiteId: params.id,
                });
                setError("");
              } catch (err) {
                setError(err instanceof Error ? err.message : "Unable to start keyword check.");
              }
            }}
          >
            Check keywords in the background
          </Button>
        }
      />
      {error ? <ErrorState message={error} onRetry={() => void load()} /> : null}
      <Stack direction={{ xs: "column", sm: "row" }} spacing={1} sx={{ alignItems: { sm: "flex-start" } }}>
        <TextField
          label="SEO keywords"
          helperText="Comma-separated. Saved on this website before the check runs."
          value={keywordDraft}
          onChange={(event) => setKeywordDraft(event.target.value)}
          fullWidth
          multiline
          minRows={2}
        />
        <Button
          disabled={saving}
          onClick={async () => {
            setSaving(true);
            try {
              const updated = await websiteApi.update(params.id, { keywords: fromCsv(keywordDraft) });
              setSite(updated);
              setError("");
            } catch (err) {
              setError(err instanceof Error ? err.message : "Unable to save keywords.");
            } finally {
              setSaving(false);
            }
          }}
        >
          {saving ? "Saving…" : "Save keywords"}
        </Button>
      </Stack>
      {run?.why ? <Alert severity="info">{run.why}</Alert> : null}
      {run?.status === "failed" && run.error ? <Alert severity="error">{run.error}</Alert> : null}
      {!run ? (
        <EmptyState title="No keyword check yet" description="Save keywords on this page, then start the background check. Enable Google Custom Search or SerpAPI in the platform console for positions." />
      ) : (
        <>
          <Typography color="text.secondary">
            Source: {run.source || "none"} · {run.keywords.length} stored queries
            {run.status !== "completed" ? ` · ${run.status}` : ""}
          </Typography>
          {run.results.length ? (
            <ResponsiveDataList
              rows={run.results.map((row) => ({ id: row.keyword, ...row }))}
              cardTitle={(row) => row.keyword}
              columns={[
                { key: "keyword", label: "Keyword", render: (row) => row.keyword },
                { key: "position", label: "First-page position", render: (row) => row.position ?? "Not in sample" },
                { key: "page", label: "Page 1", render: (row) => (row.in_first_page ? "Yes" : "No") },
                { key: "url", label: "Matched URL", render: (row) => row.matched_url || "—" },
              ]}
            />
          ) : null}
          {run.ai?.reason ? <Alert severity={run.ai.used ? "success" : "info"}>{run.ai.reason}</Alert> : null}
          <Typography variant="h4">Suggested queries</Typography>
          {run.suggestions.length ? (
            run.suggestions.map((item) => (
              <Stack key={`${item.origin}-${item.keyword}`} spacing={0.5}>
                <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap" }}>
                  <Typography>{item.keyword}</Typography>
                  <Chip size="small" label={item.origin} variant="outlined" />
                  <Chip size="small" label={item.intent} variant="outlined" />
                </Stack>
                <Typography color="text.secondary">{item.why}</Typography>
              </Stack>
            ))
          ) : (
            <EmptyState title="No suggestions" description="Suggestions are built from stored keywords and optional AI inference. They are not a ranking forecast." />
          )}
        </>
      )}
    </Stack>
  );
}
