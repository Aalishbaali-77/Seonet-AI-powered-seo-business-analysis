"use client";

import { Alert, Box, Button, Card, CardContent, Chip, Dialog, DialogActions, DialogContent, DialogTitle, Stack, Typography } from "@mui/material";
import { useEffect, useState } from "react";

import { PageHeader } from "@/components/common/PageHeader";
import { ResponsiveDataList } from "@/components/common/ResponsiveDataList";
import { StatusChip } from "@/components/common/StatusChip";
import { EmptyState } from "@/components/feedback/EmptyState";
import { ErrorState } from "@/components/feedback/ErrorState";
import { LoadingState } from "@/components/feedback/LoadingState";
import { billingApi } from "@/services/domainApi";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { bootstrapRequested } from "@/store/slices/authSlice";
import type { PlanPackage, PlatformInvoice } from "@/types/api";

type BillingPayload = {
  subscription?: {
    status: string;
    plan?: { id: string; name: string; code: string; price_amount?: string; currency?: string; interval?: string; max_users?: number };
    current_period_end?: string | null;
  };
  access?: { status: string; access: boolean; current_period_end: string | null; max_users: number; seats_used: number; plan_name: string | null };
  payment?: { method: string; gateway_name: string; card_available: boolean; instructions: string };
  modules?: string[];
  invoices?: PlatformInvoice[];
  plans?: PlanPackage[];
};

export function SubscriptionPage() {
  const dispatch = useAppDispatch();
  const permissions = useAppSelector((state) => state.auth.user?.permissions ?? []);
  const canManage = permissions.includes("billing.manage");
  const [billing, setBilling] = useState<BillingPayload | null>(null);
  const [error, setError] = useState("");
  const [ready, setReady] = useState(false);
  const [busy, setBusy] = useState(false);
  const [payInfo, setPayInfo] = useState<{ instructions: string; gateway_name: string; number?: string; checkout_url?: string } | null>(null);

  const load = () =>
    billingApi
      .get()
      .then((value) => {
        setBilling(value as BillingPayload);
        setError("");
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setReady(true));

  useEffect(() => {
    void load();
  }, []);

  const plan = billing?.subscription?.plan;
  const access = billing?.access;
  const locked = access ? !access.access : false;
  const period = access?.current_period_end ? new Date(access.current_period_end).toLocaleDateString() : null;

  const choosePlan = async (planId: string) => {
    setBusy(true);
    try {
      const invoice = (await billingApi.subscribe(planId)) as PlatformInvoice;
      await load();
      const paid = await billingApi.payInvoice(invoice.id);
      if (paid.checkout_url) {
        window.location.assign(paid.checkout_url);
        return;
      }
      setPayInfo({
        instructions: paid.instructions,
        gateway_name: paid.gateway_name,
        number: invoice.number,
      });
      dispatch(bootstrapRequested());
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to start checkout.");
    } finally {
      setBusy(false);
    }
  };

  const payInvoice = async (invoice: PlatformInvoice) => {
    setBusy(true);
    try {
      const paid = await billingApi.payInvoice(invoice.id);
      if (paid.checkout_url) {
        window.location.assign(paid.checkout_url);
        return;
      }
      setPayInfo({
        instructions: paid.instructions,
        gateway_name: paid.gateway_name,
        number: invoice.number,
        checkout_url: paid.checkout_url,
      });
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to start payment.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Stack spacing={3}>
      <PageHeader
        title="Subscription"
        description="Your package, invoices, and payment for this workspace. Dashboard access stays off until the current period is active."
      />
      {error ? <ErrorState message={error} onRetry={() => void load()} /> : null}
      {!ready && !error ? <LoadingState rows={4} /> : null}
      {ready ? (
        <>
          {locked ? (
            <Alert severity="warning">
              Workspace access is paused. Choose a package and pay the invoice. Access returns after SI Global confirms payment.
            </Alert>
          ) : null}
          <Card variant="outlined">
            <CardContent>
              <Typography variant="h4" sx={{ mb: 1 }}>
                Current package
              </Typography>
              {plan ? (
                <Stack spacing={0.75}>
                  <Typography variant="h3">{plan.name}</Typography>
                  <StatusChip value={access?.status ?? billing?.subscription?.status ?? "trialing"} />
                  {plan.price_amount ? (
                    <Typography color="text.secondary">
                      {plan.currency} {plan.price_amount} / {plan.interval}
                    </Typography>
                  ) : null}
                  {period ? (
                    <Typography color="text.secondary">Current period ends {period}</Typography>
                  ) : null}
                  {access ? (
                    <Typography color="text.secondary">
                      Seats {access.seats_used} of {access.max_users}
                    </Typography>
                  ) : null}
                  <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", gap: 1, pt: 1 }}>
                    {(billing?.modules ?? []).map((code) => (
                      <Chip key={code} size="small" label={code} />
                    ))}
                  </Stack>
                </Stack>
              ) : (
                <Typography color="text.secondary">No subscription is attached yet. Choose a public package below.</Typography>
              )}
            </CardContent>
          </Card>
          <Alert severity="info">{billing?.payment?.instructions ?? "Pay issued invoices. Access restores after payment is confirmed."}</Alert>
          <Typography variant="h4">Packages</Typography>
          <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))", lg: "repeat(4, minmax(0, 1fr))" } }}>
            {(billing?.plans ?? []).map((item) => {
              const current = plan?.id === item.id;
              const custom = Number(item.price_amount) <= 0;
              return (
                <Card key={item.id} variant="outlined">
                  <CardContent>
                    <Stack spacing={1}>
                      <Typography variant="h4">{item.name}</Typography>
                      <Typography color="text.secondary">{custom ? "Custom" : `${item.currency} ${item.price_amount} / ${item.interval}`}</Typography>
                      <Typography variant="body2" color="text.secondary">
                        {item.description}
                      </Typography>
                      {canManage && !custom ? (
                        <Button variant={current && !locked ? "outlined" : "contained"} disabled={busy || (current && !locked && access?.status === "active")} onClick={() => void choosePlan(item.id)}>
                          {current && !locked && access?.status === "active" ? "Current package" : item.cta_label || "Choose package"}
                        </Button>
                      ) : (
                        <Typography variant="body2" color="text.secondary">
                          {custom ? "Contact SI Global for this package." : current ? "Current package" : "Owners and admins can change the package."}
                        </Typography>
                      )}
                    </Stack>
                  </CardContent>
                </Card>
              );
            })}
          </Box>
          <Stack spacing={1}>
            <Typography variant="h4">Invoices</Typography>
            {billing?.invoices?.length ? (
              <ResponsiveDataList
                rows={billing.invoices}
                cardTitle={(row) => row.number}
                columns={[
                  { key: "number", label: "Invoice", render: (row) => row.number },
                  { key: "plan", label: "Package", hideOnMobile: true, render: (row) => row.plan_name ?? "—" },
                  { key: "total", label: "Total", render: (row) => `${row.currency} ${row.total}` },
                  { key: "status", label: "Status", render: (row) => <StatusChip value={row.status} /> },
                  { key: "due", label: "Due", hideOnMobile: true, render: (row) => (row.due_at ? new Date(row.due_at).toLocaleDateString() : "—") },
                  {
                    key: "pay",
                    label: "",
                    render: (row) =>
                      canManage && (row.status === "issued" || row.status === "overdue") ? (
                        <Button size="small" variant="contained" disabled={busy} onClick={() => void payInvoice(row)}>
                          Pay
                        </Button>
                      ) : null,
                  },
                ]}
              />
            ) : (
              <EmptyState title="No invoices yet" description="Choose a package to issue an invoice. Card checkout opens when SI Global enables Stripe or PayPal in the control plane." />
            )}
          </Stack>
        </>
      ) : null}
      <Dialog open={Boolean(payInfo)} onClose={() => setPayInfo(null)} fullWidth maxWidth="sm">
        {payInfo ? (
          <>
            <DialogTitle>Pay {payInfo.number ?? "invoice"}</DialogTitle>
            <DialogContent>
              <Stack spacing={1.5} sx={{ mt: 1 }}>
                <Typography>{payInfo.instructions}</Typography>
                <Typography variant="body2" color="text.secondary">
                  Payment method: {payInfo.gateway_name}. Card checkout marks the invoice paid after the gateway confirms collection. Manual invoices wait for SI Global to confirm payment.
                </Typography>
              </Stack>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setPayInfo(null)}>Close</Button>
            </DialogActions>
          </>
        ) : null}
      </Dialog>
    </Stack>
  );
}
