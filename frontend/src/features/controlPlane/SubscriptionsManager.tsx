"use client";

import { useEffect, useState } from "react";
import { Button, Dialog, DialogActions, DialogContent, DialogTitle, MenuItem, Stack, TextField } from "@mui/material";

import { useConfirm } from "@/components/common/ConfirmDialog";
import { PageHeader } from "@/components/common/PageHeader";
import { ResponsiveDataList } from "@/components/common/ResponsiveDataList";
import { RowMenu } from "@/components/common/RowMenu";
import { StatusChip } from "@/components/common/StatusChip";
import { EmptyState } from "@/components/feedback/EmptyState";
import { ErrorState } from "@/components/feedback/ErrorState";
import { LoadingState } from "@/components/feedback/LoadingState";
import { platformAdminApi } from "@/services/platformAdminApi";
import type { PlanPackage, PlatformSubscription, PlatformTenant } from "@/types/api";

export function SubscriptionsManager() {
  const confirm = useConfirm();
  const [items, setItems] = useState<PlatformSubscription[]>([]);
  const [tenants, setTenants] = useState<PlatformTenant[]>([]);
  const [packages, setPackages] = useState<PlanPackage[]>([]);
  const [error, setError] = useState("");
  const [ready, setReady] = useState(false);
  const [editing, setEditing] = useState<{ id?: string; tenant_id: string; plan_id: string; status: string; seats: number } | null>(null);

  const load = () =>
    Promise.all([platformAdminApi.subscriptions(), platformAdminApi.tenants(), platformAdminApi.packages()])
      .then(([subs, tenantPage, packagePage]) => {
        setItems(subs.results);
        setTenants(tenantPage.results);
        setPackages(packagePage.results);
        setError("");
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setReady(true));

  useEffect(() => {
    void load();
  }, []);

  return (
    <Stack spacing={3}>
      <PageHeader
        eyebrow="Commercial"
        title="Tenant subscriptions"
        description="Create or change a workspace subscription, adjust seats, or cancel. Cancel keeps the record in a canceled state."
        actions={
          <Button variant="contained" onClick={() => setEditing({ tenant_id: "", plan_id: "", status: "trialing", seats: 1 })}>
            New subscription
          </Button>
        }
      />
      {error ? <ErrorState message={error} onRetry={() => void load()} /> : null}
      {!ready && !error ? <LoadingState /> : null}
      {ready && !items.length && !error ? <EmptyState title="No subscriptions" description="Assign a package to a tenant to start a subscription." /> : null}
      {items.length ? (
        <ResponsiveDataList
          rows={items}
          cardTitle={(row) => row.tenant_name}
          columns={[
            { key: "tenant", label: "Tenant", render: (row) => row.tenant_name },
            { key: "plan", label: "Package", render: (row) => row.plan.name },
            { key: "status", label: "Status", render: (row) => <StatusChip value={row.status} /> },
            { key: "seats", label: "Seats", hideOnMobile: true, render: (row) => row.seats },
            { key: "gateway", label: "Gateway", hideOnMobile: true, render: (row) => row.gateway_name ?? "—" },
            {
              key: "actions",
              label: "",
              render: (row) => (
                <RowMenu
                  items={[
                    {
                      label: "Edit",
                      onClick: () => setEditing({ id: row.id, tenant_id: row.tenant_id, plan_id: row.plan.id, status: row.status, seats: row.seats }),
                    },
                    {
                      label: "Cancel",
                      danger: true,
                      disabled: row.status === "canceled",
                      onClick: async () => {
                        const ok = await confirm({
                          title: "Cancel subscription",
                          description: `The subscription for ${row.tenant_name} will be canceled.`,
                          confirmLabel: "Cancel subscription",
                        });
                        if (!ok) {
                          return;
                        }
                        await platformAdminApi.cancelSubscription(row.id);
                        await load();
                      },
                    },
                  ]}
                />
              ),
            },
          ]}
        />
      ) : null}
      <Dialog open={Boolean(editing)} onClose={() => setEditing(null)} fullWidth maxWidth="sm">
        {editing ? (
          <>
            <DialogTitle>{editing.id ? "Edit subscription" : "New subscription"}</DialogTitle>
            <DialogContent>
              <Stack spacing={2} sx={{ mt: 1 }}>
                <TextField select label="Tenant" value={editing.tenant_id} disabled={Boolean(editing.id)} onChange={(event) => setEditing({ ...editing, tenant_id: event.target.value })}>
                  {tenants.map((tenant) => (
                    <MenuItem key={tenant.id} value={tenant.id}>
                      {tenant.name}
                    </MenuItem>
                  ))}
                </TextField>
                <TextField select label="Package" value={editing.plan_id} onChange={(event) => setEditing({ ...editing, plan_id: event.target.value })}>
                  {packages.map((item) => (
                    <MenuItem key={item.id} value={item.id}>
                      {item.name}
                    </MenuItem>
                  ))}
                </TextField>
                <TextField select label="Status" value={editing.status} onChange={(event) => setEditing({ ...editing, status: event.target.value })}>
                  <MenuItem value="trialing">Trialing</MenuItem>
                  <MenuItem value="active">Active</MenuItem>
                  <MenuItem value="past_due">Past due</MenuItem>
                  <MenuItem value="canceled">Canceled</MenuItem>
                </TextField>
                <TextField label="Seats" type="number" value={editing.seats} onChange={(event) => setEditing({ ...editing, seats: Number(event.target.value) })} />
              </Stack>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setEditing(null)}>Cancel</Button>
              <Button
                variant="contained"
                onClick={async () => {
                  if (editing.id) {
                    await platformAdminApi.updateSubscription(editing.id, { plan_id: editing.plan_id, status: editing.status, seats: editing.seats });
                  } else {
                    await platformAdminApi.createSubscription(editing);
                  }
                  setEditing(null);
                  await load();
                }}
              >
                Save
              </Button>
            </DialogActions>
          </>
        ) : null}
      </Dialog>
    </Stack>
  );
}
