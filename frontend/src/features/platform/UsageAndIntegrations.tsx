"use client";

import { Alert, Box, Stack, Typography } from "@mui/material";
import { useEffect, useState } from "react";

import { PageHeader } from "@/components/common/PageHeader";
import { StatCard } from "@/components/common/StatCard";
import { LoadingState } from "@/components/feedback/LoadingState";
import { billingApi } from "@/services/domainApi";

type UsagePayload = { events?: Array<{ event_type: string; total: number }>; count?: number };
type AiUsagePayload = {
  requests?: number;
  failed?: number;
  prompt_tokens?: number;
  completion_tokens?: number;
  tokens?: number;
  credits_used?: number;
  credits_limit?: number;
  credits_remaining?: number;
  period_start?: string;
  by_provider?: Array<{ provider: string; tokens: number; requests: number }>;
};

export function UsageBillingPage() {
  const [usage, setUsage] = useState<UsagePayload | null>(null);
  const [ai, setAi] = useState<AiUsagePayload | null>(null);
  const [error, setError] = useState("");
  const [ready, setReady] = useState(false);

  useEffect(() => {
    Promise.all([billingApi.usage(), billingApi.aiUsage()])
      .then(([u, a]) => {
        setUsage(u as UsagePayload);
        setAi(a as AiUsagePayload);
        setError("");
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setReady(true));
  }, []);

  const otherEvents = (usage?.events ?? []).filter((event) => event.event_type !== "ai_request" && event.event_type !== "ai_tokens");

  return (
    <Stack spacing={3}>
      <PageHeader
        title="Usage"
        description="Metered workspace events and AI tokens billed against this package. Platform API keys are shared; credits are counted per workspace."
      />
      {error ? <Alert severity="error">{error}</Alert> : null}
      {!ready && !error ? <LoadingState /> : null}
      {ready ? (
        <>
          <Typography variant="h4">AI credits this period</Typography>
          <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr", md: "repeat(4, minmax(0, 1fr))" } }}>
            <StatCard label="Credits used" value={ai?.credits_used ?? 0} hint="Prompt + completion tokens" />
            <StatCard label="Package credits" value={ai?.credits_limit ?? 0} hint="From the assigned package" />
            <StatCard label="Remaining" value={ai?.credits_remaining ?? 0} />
            <StatCard label="AI requests" value={ai?.requests ?? 0} hint={`${ai?.failed ?? 0} failed`} />
          </Box>
          <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr", md: "repeat(3, minmax(0, 1fr))" } }}>
            <StatCard label="Prompt tokens" value={ai?.prompt_tokens ?? 0} />
            <StatCard label="Completion tokens" value={ai?.completion_tokens ?? 0} />
            <StatCard label="Total tokens" value={ai?.tokens ?? 0} />
          </Box>
          {(ai?.by_provider ?? []).length ? (
            <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" } }}>
              {(ai?.by_provider ?? []).map((row) => (
                <StatCard key={row.provider} label={row.provider} value={row.tokens} hint={`${row.requests} requests`} />
              ))}
            </Box>
          ) : null}
          <Alert severity="info">
            Claude and other models are configured once by SI Global. This workspace is billed for tokens it actually consumed. Inferences are never stored as facts.
          </Alert>
          <Typography variant="h4">Other metered events</Typography>
          <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr", md: "repeat(3, minmax(0, 1fr))" } }}>
            <StatCard label="Events" value={usage?.count ?? 0} />
            {otherEvents.map((event) => (
              <StatCard key={event.event_type} label={event.event_type} value={event.total} />
            ))}
          </Box>
        </>
      ) : null}
    </Stack>
  );
}
