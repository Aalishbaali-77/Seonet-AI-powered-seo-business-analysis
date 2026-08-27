"use client";

import { Alert, Button, Stack, Typography } from "@mui/material";
import { useEffect, useState } from "react";

import { PageHeader } from "@/components/common/PageHeader";
import { PrintReportChrome } from "@/components/common/PrintReportChrome";
import { CommerceInsightPanels } from "@/features/growth/CommerceInsightPanels";
import { advisorApi, businessApi } from "@/services/domainApi";
import type { AdvisorResult, CommerceAnalysis, CommerceExpert } from "@/types/domain";

export function AdvisorPanel({
  domain,
  title,
  description,
}: {
  domain: "business" | "market" | "opportunity" | "lead" | "marketing";
  title: string;
  description: string;
}) {
  const [result, setResult] = useState<AdvisorResult | null>(null);
  const [analysis, setAnalysis] = useState<CommerceAnalysis | null>(null);
  const [expert, setExpert] = useState<CommerceExpert | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (domain !== "business") return;
    void businessApi.overview().then((data) => {
      setAnalysis(data.analysis);
      setExpert(data.expert);
    });
  }, [domain]);

  return (
    <PrintReportChrome title={title}>
    <Stack spacing={3}>
      <PageHeader
        title={title}
        description={description}
        actions={
          <Button
            variant="contained"
            disabled={busy}
            onClick={async () => {
              setBusy(true);
              setError("");
              try {
                setResult(await advisorApi.ask(domain));
                if (domain === "business") {
                  const overview = await businessApi.overview();
                  setAnalysis(overview.analysis);
                  setExpert(overview.expert);
                }
              } catch (err) {
                setError(err instanceof Error ? err.message : "Unable to load advisor.");
              } finally {
                setBusy(false);
              }
            }}
          >
            Analyze facts
          </Button>
        }
      />
      {error ? <Alert severity="error">{error}</Alert> : null}
      {domain === "business" ? <CommerceInsightPanels analysis={analysis} expert={expert} /> : null}
      {result ? (
        <Stack spacing={2}>
          <Alert severity="info">Origin: {result.origin}. Facts are stored workspace data. Inference is not stored as fact.</Alert>
          {result.facts.map((line) => (
            <Typography key={line}>FACT: {line}</Typography>
          ))}
          {result.inference ? <Typography>INFERENCE: {result.inference}</Typography> : null}
          {result.recommendation ? <Typography>RECOMMENDATION: {result.recommendation}</Typography> : null}
        </Stack>
      ) : domain !== "business" ? (
        <Alert severity="info">Run analysis to load facts from this workspace. No sample revenue or city grades are shown.</Alert>
      ) : null}
    </Stack>
    </PrintReportChrome>
  );
}
