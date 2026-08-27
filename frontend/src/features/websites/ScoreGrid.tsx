"use client";

import { Box } from "@mui/material";

import { ScoreCard } from "@/components/common/ScoreCard";

const LABELS: Record<string, string> = {
  technical_seo: "Technical SEO",
  on_page_seo: "On-page SEO",
  content: "Content",
  aeo: "AEO",
  geo: "GEO",
  performance: "SIPulse Performance",
  technical_performance: "Technical Performance",
  ux_cwv: "UX / CWV",
  accessibility: "Accessibility",
  schema: "Schema",
  local_seo: "Local SEO",
  opportunity: "Opportunity",
};

const DEFAULT_KEYS = ["technical_seo", "on_page_seo", "content", "schema", "accessibility", "performance", "aeo", "geo", "local_seo", "opportunity"];

export function ScoreGrid({ scores, keys }: { scores: Record<string, number>; keys?: string[] }) {
  const extras = Object.keys(scores).filter((key) => !DEFAULT_KEYS.includes(key) && LABELS[key]);
  const order = keys ?? [...DEFAULT_KEYS, ...extras];
  return (
    <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr 1fr", sm: "repeat(3, 1fr)", md: "repeat(5, 1fr)" } }}>
      {order.map((key) => (
        <ScoreCard key={key} label={LABELS[key] ?? key} value={scores[key] ?? null} />
      ))}
    </Box>
  );
}
