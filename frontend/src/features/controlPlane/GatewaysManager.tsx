"use client";

import { useEffect, useState } from "react";
import { Alert, Button, Card, CardContent, Dialog, DialogActions, DialogContent, DialogTitle, MenuItem, Stack, TextField, Typography } from "@mui/material";

import { useConfirm } from "@/components/common/ConfirmDialog";
import { PageHeader } from "@/components/common/PageHeader";
import { RowMenu } from "@/components/common/RowMenu";
import { StatusChip } from "@/components/common/StatusChip";
import { EmptyState } from "@/components/feedback/EmptyState";
import { ErrorState } from "@/components/feedback/ErrorState";
import { LoadingState } from "@/components/feedback/LoadingState";
import { platformAdminApi } from "@/services/platformAdminApi";
import type { PaymentGateway } from "@/types/api";

const emptyGateway = {
  code: "",
  provider: "manual",
  display_name: "",
  is_enabled: false,
  test_mode: true,
};

export function GatewaysManager() {
  const confirm = useConfirm();
  const [gateways, setGateways] = useState<PaymentGateway[]>([]);
  const [error, setError] = useState("");
  const [ready, setReady] = useState(false);
  const [editing, setEditing] = useState<(typeof emptyGateway & { id?: string; publishable_key?: string; secret_key?: string }) | null>(null);

  const load = () =>
    platformAdminApi
      .gateways()
      .then((page) => {
        setGateways(page.results);
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
        eyebrow="Collections"
        title="Payment gateways"
        description="Add collection methods, store credentials, set the default, or remove unused gateways. Secrets never return to the browser."
        actions={
          <Button variant="contained" onClick={() => setEditing(emptyGateway)}>
            New gateway
          </Button>
        }
      />
      <Alert severity="info">Manual / bank transfer is the default live path. Enable Stripe or PayPal only after storing credentials.</Alert>
      {error ? <ErrorState message={error} onRetry={() => void load()} /> : null}
      {!ready && !error ? <LoadingState /> : null}
      {ready && !gateways.length && !error ? <EmptyState title="No gateways" description="Create a collection method." /> : null}
      <Stack spacing={2}>
        {gateways.map((gateway) => (
          <Card key={gateway.id} variant="outlined">
            <CardContent>
              <Stack direction="row" spacing={1} sx={{ justifyContent: "space-between", alignItems: "flex-start" }}>
                <Stack spacing={0.5}>
                  <Typography variant="h4">{gateway.display_name}</Typography>
                  <Typography color="text.secondary">{gateway.provider}</Typography>
                  <StatusChip value={gateway.is_enabled ? "active" : "disconnected"} />
                  {gateway.is_default ? <Typography variant="body2">Default collection method</Typography> : null}
                  {gateway.provider !== "manual" ? (
                    <Typography variant="body2" color="text.secondary">
                      Credentials {gateway.credentials_configured ? "are stored on the server" : "are not configured"}
                    </Typography>
                  ) : null}
                </Stack>
                <RowMenu
                  items={[
                    {
                      label: "Edit",
                      onClick: () =>
                        setEditing({
                          id: gateway.id,
                          code: gateway.code,
                          provider: gateway.provider,
                          display_name: gateway.display_name,
                          is_enabled: gateway.is_enabled,
                          test_mode: gateway.test_mode,
                          publishable_key: "",
                          secret_key: "",
                        }),
                    },
                    {
                      label: gateway.is_enabled ? "Disable" : "Enable",
                      onClick: async () => {
                        await platformAdminApi.updateGateway(gateway.id, { is_enabled: !gateway.is_enabled });
                        await load();
                      },
                    },
                    {
                      label: "Set as default",
                      disabled: gateway.is_default,
                      onClick: async () => {
                        await platformAdminApi.updateGateway(gateway.id, { is_default: true });
                        await load();
                      },
                    },
                    {
                      label: "Delete",
                      danger: true,
                      onClick: async () => {
                        const ok = await confirm({
                          title: "Delete payment gateway",
                          description: `${gateway.display_name} will be removed. Stored credentials are deleted.`,
                          confirmLabel: "Delete",
                        });
                        if (!ok) {
                          return;
                        }
                        try {
                          await platformAdminApi.deleteGateway(gateway.id);
                          await load();
                        } catch (err) {
                          setError(err instanceof Error ? err.message : "Unable to delete gateway.");
                        }
                      },
                    },
                  ]}
                />
              </Stack>
            </CardContent>
          </Card>
        ))}
      </Stack>
      <Dialog open={Boolean(editing)} onClose={() => setEditing(null)} fullWidth maxWidth="sm">
        {editing ? (
          <>
            <DialogTitle>{editing.id ? "Edit gateway" : "New gateway"}</DialogTitle>
            <DialogContent>
              <Stack spacing={2} sx={{ mt: 1 }}>
                <TextField label="Code" value={editing.code} disabled={Boolean(editing.id)} onChange={(event) => setEditing({ ...editing, code: event.target.value })} />
                <TextField select label="Provider" value={editing.provider} disabled={Boolean(editing.id)} onChange={(event) => setEditing({ ...editing, provider: event.target.value })}>
                  <MenuItem value="manual">Manual</MenuItem>
                  <MenuItem value="stripe">Stripe</MenuItem>
                  <MenuItem value="paypal">PayPal</MenuItem>
                </TextField>
                <TextField label="Display name" value={editing.display_name} onChange={(event) => setEditing({ ...editing, display_name: event.target.value })} />
                {editing.provider !== "manual" ? (
                  <>
                    <TextField label="Publishable key" value={editing.publishable_key ?? ""} onChange={(event) => setEditing({ ...editing, publishable_key: event.target.value })} />
                    <TextField label="Secret key" type="password" value={editing.secret_key ?? ""} onChange={(event) => setEditing({ ...editing, secret_key: event.target.value })} />
                  </>
                ) : null}
              </Stack>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setEditing(null)}>Cancel</Button>
              <Button
                variant="contained"
                onClick={async () => {
                  const payload = {
                    code: editing.code,
                    provider: editing.provider,
                    display_name: editing.display_name,
                    is_enabled: editing.is_enabled,
                    test_mode: editing.test_mode,
                    publishable_key: editing.publishable_key,
                    secret_key: editing.secret_key,
                  };
                  if (editing.id) {
                    await platformAdminApi.updateGateway(editing.id, payload);
                  } else {
                    await platformAdminApi.createGateway(payload);
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
