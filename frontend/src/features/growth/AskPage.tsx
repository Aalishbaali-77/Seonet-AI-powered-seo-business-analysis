"use client";

import { Alert, Button, Stack, TextField, Typography } from "@mui/material";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { PageHeader } from "@/components/common/PageHeader";
import { useAuditSession } from "@/features/websites/auditSession";
import { advisorApi } from "@/services/domainApi";

export function AskPage() {
  const router = useRouter();
  const { start, job } = useAuditSession();
  const seen = useRef("");
  const [question, setQuestion] = useState("Analyze the market for my business");
  const [facts, setFacts] = useState<string[]>([]);
  const [why, setWhy] = useState("");
  const [origin, setOrigin] = useState("");
  const [inference, setInference] = useState("");
  const [recommendation, setRecommendation] = useState("");
  const [href, setHref] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const analyzing = Boolean(job && job.job_type === "analyze_market" && job.status !== "COMPLETED" && job.status !== "FAILED" && job.status !== "CANCELLED");

  const applyJob = () => {
    if (!job || job.job_type !== "analyze_market") return;
    const findings = Array.isArray(job.result.findings) ? (job.result.findings as string[]) : [];
    const citations = Array.isArray(job.result.citations) ? (job.result.citations as Array<{ text?: string }>) : [];
    const nextFacts = [...findings];
    citations.forEach((item) => {
      if (item.text && !nextFacts.includes(item.text)) nextFacts.push(item.text);
    });
    setFacts(nextFacts);
    setInference(String(job.result.inference ?? ""));
    setRecommendation(String(job.result.recommendation ?? ""));
    setOrigin(String(job.result.origin ?? "facts_only"));
    setWhy("Market analysis for this workspace business from the saved profile, placed orders, and ingested signals. City grades are not invented.");
    setHref("/app/markets");
  };

  useEffect(() => {
    if (job?.job_type !== "analyze_market") return;
    const key = `${job.id}:${job.status}`;
    if (seen.current === key) return;
    if (job.status === "COMPLETED") {
      seen.current = key;
      applyJob();
      setBusy(false);
    }
    if (job.status === "FAILED") {
      seen.current = key;
      setError(job.error || "Market analysis failed.");
      setBusy(false);
    }
  }, [job]);

  return (
    <Stack spacing={3}>
      <PageHeader
        title="Ask SIPulse"
        description="Counts stay allowlisted. Market and business questions run analysis on this tenant's saved profile, orders, and ingested signals — they do not invent city grades or next-year revenue."
      />
      <TextField
        label="Question"
        value={question}
        onChange={(event) => setQuestion(event.target.value)}
        multiline
        minRows={2}
      />
      <Button
        variant="contained"
        disabled={busy || analyzing || !question.trim()}
        onClick={async () => {
          setBusy(true);
          setError("");
          try {
            const result = await advisorApi.query(question.trim());
            if (result.job_id) {
              start({
                jobId: result.job_id,
                kind: "analyze_market",
                title: question.trim() || "Market analysis",
                href: result.href || "/app/markets",
              });
            }
            setFacts(result.facts);
            setWhy(result.why);
            setOrigin(result.origin);
            setInference(result.inference || "");
            setRecommendation(result.recommendation || "");
            setHref(result.href || "");
            if (!result.job_id) {
              setBusy(false);
            }
          } catch (err) {
            setError(err instanceof Error ? err.message : "Unable to answer.");
            setBusy(false);
          }
        }}
      >
        Ask
      </Button>
      {error ? <Alert severity="error">{error}</Alert> : null}
      {why ? <Alert severity="info">Origin: {origin}. {why}</Alert> : null}
      {facts.map((line) => (
        <Typography key={line}>FACT: {line}</Typography>
      ))}
      {inference ? <Typography>INFERENCE: {inference}</Typography> : null}
      {recommendation ? <Typography>RECOMMENDATION: {recommendation}</Typography> : null}
      {href ? (
        <Button variant="outlined" onClick={() => router.push(href)}>
          Open market brief
        </Button>
      ) : null}
    </Stack>
  );
}
