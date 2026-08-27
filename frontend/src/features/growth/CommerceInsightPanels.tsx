"use client";

import { Alert, Button, Card, CardContent, Stack, Typography } from "@mui/material";
import { useRouter } from "next/navigation";

import { MiniBarChart } from "@/components/charts/MiniCharts";
import { ResponsiveDataList } from "@/components/common/ResponsiveDataList";
import type { CommerceAnalysis, CommerceExpert } from "@/types/domain";

export function CommerceInsightPanels({
  analysis,
  expert,
  sections = ["expert", "demand", "products", "actions"],
}: {
  analysis?: CommerceAnalysis | null;
  expert?: CommerceExpert | null;
  sections?: Array<"expert" | "demand" | "products" | "actions">;
}) {
  const router = useRouter();
  const show = (name: (typeof sections)[number]) => sections.includes(name);

  return (
    <>
      {show("expert") && (expert?.recommendation || expert?.inference) ? (
        <Card variant="outlined">
          <CardContent>
            <Stack spacing={1}>
              <Typography variant="h4">Business expert</Typography>
              <Typography variant="body2" color="text.secondary">
                Origin: {expert.origin || "heuristic"}. Inference is not stored as a KPI.
              </Typography>
              {expert.inference ? <Typography>INFERENCE: {expert.inference}</Typography> : null}
              {expert.recommendation ? <Typography>RECOMMENDATION: {expert.recommendation}</Typography> : null}
            </Stack>
          </CardContent>
        </Card>
      ) : null}
      {show("demand") && analysis?.available && analysis.demand?.served?.length ? (
        <Card variant="outlined">
          <CardContent>
            <Typography variant="h4" sx={{ mb: 1.5 }}>
              Where you are serving
            </Typography>
            <MiniBarChart items={analysis.demand.served.map((row) => ({ label: row.city, value: row.orders }))} />
            <ResponsiveDataList
              rows={analysis.demand.served.map((row) => ({ id: row.city, ...row }))}
              cardTitle={(row) => row.city}
              columns={[
                { key: "city", label: "City", render: (row) => row.city },
                { key: "orders", label: "Orders", render: (row) => row.orders },
                { key: "why", label: "Evidence", render: (row) => row.why },
              ]}
            />
          </CardContent>
        </Card>
      ) : null}
      {show("demand") && analysis?.demand?.thin?.length ? (
        <Card variant="outlined">
          <CardContent>
            <Typography variant="h4" sx={{ mb: 1.5 }}>
              Thin served books
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              Smaller than the busiest stored city. This is a count comparison, not a demand grade.
            </Typography>
            <ResponsiveDataList
              rows={analysis.demand.thin.map((row) => ({ id: row.city, ...row }))}
              cardTitle={(row) => row.city}
              columns={[
                { key: "city", label: "City", render: (row) => row.city },
                { key: "orders", label: "Orders", render: (row) => row.orders },
                { key: "why", label: "Evidence", render: (row) => row.why },
              ]}
            />
          </CardContent>
        </Card>
      ) : null}
      {show("demand") && analysis?.demand?.expansion?.length ? (
        <Card variant="outlined">
          <CardContent>
            <Typography variant="h4" sx={{ mb: 1.5 }}>
              Where to investigate serving
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              Only cities with stored evidence: profile market with no orders, customers without orders, product-city gaps, or ingested market signals.
            </Typography>
            <ResponsiveDataList
              rows={analysis.demand.expansion.map((row) => ({ id: `${row.kind}-${row.city}`, ...row }))}
              cardTitle={(row) => row.city}
              columns={[
                { key: "city", label: "City", render: (row) => row.city },
                { key: "kind", label: "Evidence type", render: (row) => row.kind.replaceAll("_", " ") },
                { key: "why", label: "Why", render: (row) => row.why },
              ]}
            />
          </CardContent>
        </Card>
      ) : null}
      {show("demand") && analysis?.available && !analysis.demand?.served?.length ? (
        <Alert severity="info">Placed orders exist, but city is blank, so served-market analysis cannot run.</Alert>
      ) : null}
      {show("products") && analysis?.products?.top?.length ? (
        <Card variant="outlined">
          <CardContent>
            <Typography variant="h4" sx={{ mb: 1.5 }}>
              Product research
            </Typography>
            <ResponsiveDataList
              rows={analysis.products.top.map((row, index) => ({ id: `${row.sku || row.name}-${index}`, ...row }))}
              cardTitle={(row) => row.name}
              columns={[
                { key: "name", label: "Product", render: (row) => row.name },
                { key: "units", label: "Units", render: (row) => row.units },
                { key: "revenue", label: "Line revenue", render: (row) => row.revenue },
              ]}
            />
          </CardContent>
        </Card>
      ) : null}
      {show("products") && analysis?.products?.gaps?.length ? (
        <ResponsiveDataList
          rows={analysis.products.gaps.map((row, index) => ({ id: `${row.name}-${row.city}-${index}`, ...row }))}
          cardTitle={(row) => `${row.name} in ${row.city}`}
          columns={[
            { key: "name", label: "Product gap", render: (row) => row.name },
            { key: "city", label: "Missing in", render: (row) => row.city },
            { key: "why", label: "Evidence", render: (row) => row.why },
          ]}
        />
      ) : null}
      {show("products") && analysis?.products?.unsold?.length ? (
        <ResponsiveDataList
          rows={analysis.products.unsold.map((row, index) => ({ id: `${row.sku || row.name}-unsold-${index}`, ...row }))}
          cardTitle={(row) => row.name}
          columns={[
            { key: "name", label: "Unsold catalog", render: (row) => row.name },
            { key: "sku", label: "SKU", render: (row) => row.sku || "—" },
            { key: "why", label: "Evidence", render: (row) => row.why },
          ]}
        />
      ) : null}
      {show("products") && analysis?.products?.weak_reviews?.length ? (
        <ResponsiveDataList
          rows={analysis.products.weak_reviews.map((row, index) => ({ id: `${row.sku || row.name}-weak-${index}`, ...row }))}
          cardTitle={(row) => row.name}
          columns={[
            { key: "name", label: "Weak reviews", render: (row) => row.name },
            { key: "negative", label: "1–2 star", render: (row) => row.negative },
            { key: "why", label: "Evidence", render: (row) => row.why },
          ]}
        />
      ) : null}
      {show("actions") && analysis?.next_actions?.length ? (
        <Card variant="outlined">
          <CardContent>
            <Stack spacing={1}>
              <Typography variant="h4">Next actions</Typography>
              {analysis.next_actions.map((item) => (
                <Typography key={item.action}>RECOMMENDATION: {item.action}</Typography>
              ))}
              <Button variant="outlined" onClick={() => router.push("/app/opportunities")}>
                Open opportunities
              </Button>
              <Button variant="text" onClick={() => router.push("/app/leads/discover")}>
                Find leads in existing Leads module
              </Button>
            </Stack>
          </CardContent>
        </Card>
      ) : null}
    </>
  );
}
