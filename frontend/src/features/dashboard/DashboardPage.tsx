"use client";

import { Box, Button, Card, CardContent, Chip, Stack, Typography } from "@mui/material";
import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { MiniBarChart, MiniLineChart } from "@/components/charts/MiniCharts";
import { EmptyState } from "@/components/feedback/EmptyState";
import { ErrorState } from "@/components/feedback/ErrorState";
import { LoadingState } from "@/components/feedback/LoadingState";
import { PageHeader } from "@/components/common/PageHeader";
import { ScoreCard } from "@/components/common/ScoreCard";
import { StatCard } from "@/components/common/StatCard";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { overviewRequested } from "@/store/slices/dashboardSlice";

export function DashboardPage() {
  const dispatch = useAppDispatch();
  const router = useRouter();
  const { status, data, error } = useAppSelector((state) => state.dashboard);
  const modules = useAppSelector((state) => state.auth.user?.modules ?? []);
  const tenant = useAppSelector((state) => state.tenant.items.find((item) => item.id === state.tenant.currentId));
  const subscription = useAppSelector((state) => state.auth.user?.subscription);
  const permissions = useAppSelector((state) => state.auth.user?.permissions ?? []);
  const canInvite = permissions.includes("member.manage");

  useEffect(() => {
    dispatch(overviewRequested());
  }, [dispatch]);

  return (
    <Stack spacing={3}>
      <PageHeader
        eyebrow={tenant?.name ?? "Overview"}
        title="Growth intelligence"
        description="Website health, lead quality, CRM progress, and usage for this workspace. Modules you see here are the ones assigned to your plan."
        actions={
          modules.includes("websites") ? (
            <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap" }}>
              <Button variant="outlined" onClick={() => router.push("/app/websites")}>
                View websites
              </Button>
              <Button variant="contained" onClick={() => router.push("/app/websites/new")}>
                Add website
              </Button>
            </Stack>
          ) : null
        }
      />
      {status === "loading" || status === "idle" ? <LoadingState rows={4} /> : null}
      {status === "error" ? <ErrorState message={error ?? "Unable to load dashboard."} onRetry={() => dispatch(overviewRequested())} /> : null}
      {status === "ready" && data ? (
        <>
          <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr", lg: "repeat(3, minmax(0, 1fr))", xl: "repeat(6, minmax(0, 1fr))" } }}>
            <StatCard label="Websites" value={data.overview.websites} hint="Connected properties" onClick={() => router.push("/app/websites")} />
            <StatCard label="Audits" value={data.overview.audits} hint="Completed analyses" onClick={() => router.push("/app/audits")} />
            <StatCard label="Total leads" value={data.overview.total_leads} onClick={() => router.push("/app/leads")} />
            <StatCard label="Qualified" value={data.overview.qualified_leads} />
            <StatCard label="CRM deals" value={data.overview.crm_deals ?? data.overview.opportunities} hint="Native CRM pipeline" onClick={() => router.push("/app/crm")} />
            <StatCard label="Growth opportunities" value={data.overview.growth_opportunities ?? 0} hint="Recorded evidence, not CRM deals" onClick={() => router.push("/app/opportunities")} />
            {typeof data.overview.campaigns === "number" ? (
              <StatCard label="Campaigns" value={data.overview.campaigns} hint="Recorded audience counts only" onClick={() => router.push("/app/marketing")} />
            ) : null}
            {typeof data.overview.commerce_orders === "number" ? (
              <StatCard
                label="Commerce orders"
                value={data.overview.commerce_orders}
                hint={data.overview.commerce_revenue ? `Stored revenue ${data.overview.commerce_revenue}` : "From CSV or store sync"}
                onClick={() => router.push("/app/business")}
              />
            ) : null}
            {typeof data.overview.served_cities === "number" ? (
              <StatCard
                label="Served cities"
                value={data.overview.served_cities}
                hint={`${data.overview.expansion_cities ?? 0} expansion cities with evidence`}
                onClick={() => router.push("/app/business/geography")}
              />
            ) : null}
          </Box>
          <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr", md: "repeat(3, minmax(0, 1fr))", lg: "repeat(6, minmax(0, 1fr))" } }}>
            <ScoreCard label="Website health" value={data.intelligence.website_health} onClick={() => router.push("/app/websites")} />
            <ScoreCard label="SEO score" value={data.intelligence.seo_score} onClick={() => router.push("/app/seo")} />
            <ScoreCard label="AEO score" value={data.intelligence.aeo_score} onClick={() => router.push("/app/aeo")} />
            <ScoreCard label="GEO score" value={data.intelligence.geo_score} onClick={() => router.push("/app/aeo")} />
            <ScoreCard
              label="SIPulse Performance"
              value={data.intelligence.performance_score}
              hint="Crawl TTFB and technical health"
              onClick={() => router.push("/app/performance")}
            />
            <ScoreCard label="Website opportunity" value={data.intelligence.opportunity_score} hint="From audit findings, not market scores" onClick={() => router.push("/app/audits")} />
          </Box>
          <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr", md: "repeat(3, minmax(0, 1fr))" } }}>
            <StatCard
              label="AI credits used"
              value={data.ai_usage.credits_used ?? data.ai_usage.credits}
              hint={`${data.ai_usage.credits_remaining ?? 0} remaining of ${data.ai_usage.credits_limit ?? 0}`}
              onClick={() => router.push("/app/usage")}
            />
            <StatCard label="AI tokens" value={data.ai_usage.tokens} hint="Prompt + completion this period" onClick={() => router.push("/app/usage")} />
          </Box>
          {data.lead_intelligence.data_quality ? (
            <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" } }}>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="h4" sx={{ mb: 1.5 }}>
                    Lead field completeness
                  </Typography>
                  <Typography color="text.secondary" sx={{ mb: 2 }}>
                    Counts of stored fields only. Missing email or phone is not invented. Average quality is completeness among scored leads.
                  </Typography>
                  <Box sx={{ display: "grid", gap: 1.5, gridTemplateColumns: { xs: "1fr 1fr", sm: "repeat(3, minmax(0, 1fr))" } }}>
                    <StatCard label="Website" value={`${data.lead_intelligence.data_quality.with_website}/${data.lead_intelligence.data_quality.leads}`} />
                    <StatCard label="Email" value={`${data.lead_intelligence.data_quality.with_email}/${data.lead_intelligence.data_quality.leads}`} />
                    <StatCard label="Phone" value={`${data.lead_intelligence.data_quality.with_phone}/${data.lead_intelligence.data_quality.leads}`} />
                    <StatCard label="Location" value={`${data.lead_intelligence.data_quality.with_location}/${data.lead_intelligence.data_quality.leads}`} />
                    <StatCard label="Industry" value={`${data.lead_intelligence.data_quality.with_industry}/${data.lead_intelligence.data_quality.leads}`} />
                    <StatCard
                      label="Avg quality"
                      value={data.lead_intelligence.data_quality.avg_quality_score ?? "—"}
                      hint="Field completeness, not predicted conversion"
                    />
                  </Box>
                </CardContent>
              </Card>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="h4" sx={{ mb: 1.5 }}>
                    New leads (14 days)
                  </Typography>
                  {data.lead_intelligence.new_leads_over_time.some((row) => row.count > 0) ? (
                    <MiniLineChart
                      series={[
                        {
                          label: "Leads created",
                          values: data.lead_intelligence.new_leads_over_time.map((row) => row.count),
                        },
                      ]}
                    />
                  ) : (
                    <Typography color="text.secondary">No leads were created in the last 14 days.</Typography>
                  )}
                </CardContent>
              </Card>
            </Box>
          ) : null}
          {data.lead_intelligence.by_industry.length || data.lead_intelligence.by_location.length || data.lead_intelligence.score_distribution.length ? (
            <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "1fr 1fr 1fr" } }}>
              {data.lead_intelligence.by_industry.length ? (
                <Card variant="outlined">
                  <CardContent>
                    <Typography variant="h4" sx={{ mb: 1.5 }}>
                      Leads by industry
                    </Typography>
                    <MiniBarChart items={data.lead_intelligence.by_industry.map((row) => ({ label: row.industry, value: row.count }))} />
                  </CardContent>
                </Card>
              ) : null}
              {data.lead_intelligence.by_location.length ? (
                <Card variant="outlined">
                  <CardContent>
                    <Typography variant="h4" sx={{ mb: 1.5 }}>
                      Leads by location
                    </Typography>
                    <MiniBarChart items={data.lead_intelligence.by_location.map((row) => ({ label: row.location, value: row.count }))} />
                  </CardContent>
                </Card>
              ) : null}
              {data.lead_intelligence.score_distribution.length ? (
                <Card variant="outlined">
                  <CardContent>
                    <Typography variant="h4" sx={{ mb: 1.5 }}>
                      Lead score buckets
                    </Typography>
                    <MiniBarChart items={data.lead_intelligence.score_distribution.map((row) => ({ label: row.label, value: row.count }))} />
                  </CardContent>
                </Card>
              ) : null}
            </Box>
          ) : null}
          <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" } }}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="h4" sx={{ mb: 1.5 }}>
                  Assigned modules
                </Typography>
                <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", gap: 1 }}>
                  {modules.length ? modules.map((code) => <Chip key={code} label={code} size="small" />) : <Typography color="text.secondary">No modules assigned yet.</Typography>}
                </Stack>
              </CardContent>
            </Card>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="h4" sx={{ mb: 1.5 }}>
                  Recent activity
                </Typography>
                {data.activity.length ? (
                  <Stack spacing={1}>
                    {data.activity.map((item) => (
                      <Box key={item.id} sx={{ display: "flex", justifyContent: "space-between", gap: 2 }}>
                        <Box sx={{ minWidth: 0 }}>
                          <Typography>{item.title}</Typography>
                          {item.actor ? (
                            <Typography variant="body2" color="text.secondary">
                              {item.actor}
                            </Typography>
                          ) : null}
                        </Box>
                        <Typography variant="body2" color="text.secondary" sx={{ flexShrink: 0 }}>
                          {new Date(item.created_at).toLocaleString()}
                        </Typography>
                      </Box>
                    ))}
                  </Stack>
                ) : (
                  <Typography color="text.secondary">Activity will appear as your team audits sites, discovers leads, and works CRM.</Typography>
                )}
              </CardContent>
            </Card>
          </Box>
          {subscription && subscription.seats_used <= 1 && canInvite ? (
            <EmptyState
              title="Invite your team"
              description="This workspace is ready. Add teammates from Settings so they can share websites, leads, and CRM."
              actionLabel="Invite teammates"
              onAction={() => router.push("/app/settings/team")}
            />
          ) : null}
          {data.overview.websites === 0 && modules.includes("websites") ? (
            <EmptyState
              title="No websites yet"
              description="Add your first website to start a real audit. Scores stay empty until an audit completes."
              actionLabel="Add website"
              onAction={() => router.push("/app/websites/new")}
            />
          ) : null}
          {data.overview.total_leads === 0 && modules.includes("leads") ? (
            <EmptyState
              title="No leads yet"
              description="Confirm an ICP and run discovery. Completeness scores stay empty until leads exist."
              actionLabel="Find leads"
              onAction={() => router.push("/app/leads/discover")}
            />
          ) : null}
          {(data.overview.growth_opportunities ?? 0) === 0 && modules.includes("opportunities") ? (
            <EmptyState
              title="No growth opportunities"
              description="Record evidence from imported orders or ingested market signals. SIPulse will not invent city grades."
              actionLabel="Open opportunities"
              onAction={() => router.push("/app/opportunities")}
            />
          ) : null}
        </>
      ) : null}
    </Stack>
  );
}
