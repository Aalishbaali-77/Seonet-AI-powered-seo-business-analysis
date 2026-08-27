"use client";

import { Alert, Box, Button, Card, CardContent, Stack, Typography } from "@mui/material";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { PageHeader } from "@/components/common/PageHeader";
import { StatCard } from "@/components/common/StatCard";
import { StatusChip } from "@/components/common/StatusChip";
import { RowMenu } from "@/components/common/RowMenu";
import { ErrorState } from "@/components/feedback/ErrorState";
import { LoadingState } from "@/components/feedback/LoadingState";
import { platformAdminApi } from "@/services/platformAdminApi";
import { useAppSelector } from "@/store/hooks";
import type { PlatformOverview } from "@/types/api";

export function PlatformDashboard() {
  const router = useRouter();
  const owner = useAppSelector((state) => state.ui.branding.legal_name);
  const [data, setData] = useState<PlatformOverview | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    platformAdminApi
      .overview()
      .then(setData)
      .catch((err: Error) => setError(err.message));
  }, []);

  return (
    <Stack spacing={3}>
      <PageHeader
        eyebrow={owner}
        title="Platform control plane"
        description="Manage every tenant workspace, commercial package, module entitlement, payment gateway, and invoice from one operator console."
      />
      {error ? <ErrorState message={error} onRetry={() => window.location.reload()} /> : null}
      {!data && !error ? <LoadingState rows={4} /> : null}
      {data ? (
        <>
          <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr", lg: "repeat(4, minmax(0, 1fr))" } }}>
            <StatCard label="Tenants" value={data.tenants.total} hint={`${data.tenants.active} active`} />
            <StatCard label="Active subscriptions" value={data.subscriptions.active} hint={`${data.subscriptions.trialing} on trial`} />
            <StatCard label="Collected" value={`$${data.invoices.collected}`} hint={`${data.invoices.paid} paid invoices`} />
            <StatCard label="Outstanding" value={`$${data.invoices.outstanding}`} hint={`${data.invoices.issued} issued · ${data.invoices.overdue} overdue`} />
            <StatCard label="AI requests" value={data.ai?.requests ?? 0} hint="Completed this calendar month" />
            <StatCard label="AI tokens" value={data.ai?.tokens ?? 0} hint="All tenants, platform keys" onClick={() => router.push("/platform/activity")} />
            <StatCard label="Page views" value={data.telemetry?.page_views ?? 0} hint="Workspace browsing" onClick={() => router.push("/platform/activity")} />
          </Box>
          <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "2fr 1fr" } }}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="h4" sx={{ mb: 2 }}>
                  Recent workspaces
                </Typography>
                <Stack spacing={1.5}>
                  {data.recent_tenants.map((tenant) => (
                    <Box key={tenant.id} sx={{ display: "flex", justifyContent: "space-between", gap: 2, alignItems: "center" }}>
                      <Box sx={{ minWidth: 0 }}>
                        <Typography sx={{ fontWeight: 600 }}>{tenant.name}</Typography>
                        <Typography variant="body2" color="text.secondary">
                          {new Date(tenant.created_at).toLocaleDateString()}
                        </Typography>
                      </Box>
                      <Stack direction="row" spacing={1} sx={{ alignItems: "center", flexShrink: 0 }}>
                        <StatusChip value={tenant.status} />
                        <RowMenu
                          items={[
                            { label: "Manage", onClick: () => router.push("/platform/tenants") },
                            { label: "Invoices", onClick: () => router.push("/platform/invoices") },
                            { label: "Subscriptions", onClick: () => router.push("/platform/subscriptions") },
                          ]}
                        />
                      </Stack>
                    </Box>
                  ))}
                </Stack>
              </CardContent>
            </Card>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="h4" sx={{ mb: 2 }}>
                  Catalog
                </Typography>
                <Stack spacing={1.25}>
                  <Typography>{data.packages} commercial packages</Typography>
                  <Typography>{data.modules} product modules</Typography>
                  <Typography>{data.gateways} payment gateways enabled</Typography>
                  <Typography>{data.lead_sources ?? 0} API sources enabled</Typography>
                  <Typography>{data.users} active users</Typography>
                </Stack>
              </CardContent>
            </Card>
          </Box>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="h4" sx={{ mb: 2 }}>
                Platform activity
              </Typography>
              {data.activity?.length ? (
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
                <Typography color="text.secondary">Operator actions on tenants, packages, and invoices appear here.</Typography>
              )}
            </CardContent>
          </Card>
          <Alert severity="info">
            Stripe and PayPal stay disabled until credentials are stored. Manual invoicing is the live collection path until a gateway is configured.
          </Alert>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
            <Button variant="contained" onClick={() => router.push("/platform/tenants")}>
              Assign modules
            </Button>
            <Button variant="outlined" onClick={() => router.push("/platform/packages")}>
              Edit packages
            </Button>
            <Button variant="outlined" onClick={() => router.push("/platform/landing")}>
              Edit landing page
            </Button>
            <Button variant="outlined" onClick={() => router.push("/platform/activity")}>
              Tenant activity
            </Button>
          </Stack>
        </>
      ) : null}
    </Stack>
  );
}
