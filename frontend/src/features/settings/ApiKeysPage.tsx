"use client";

import { Alert, Button, Dialog, DialogActions, DialogContent, DialogTitle, Stack, TextField, Typography } from "@mui/material";
import { useEffect, useState } from "react";

import { useConfirm } from "@/components/common/ConfirmDialog";
import { PageHeader } from "@/components/common/PageHeader";
import { ResponsiveDataList } from "@/components/common/ResponsiveDataList";
import { RowMenu } from "@/components/common/RowMenu";
import { EmptyState } from "@/components/feedback/EmptyState";
import { LoadingState } from "@/components/feedback/LoadingState";
import { tenantApi, type WorkspaceApiToken } from "@/services/domainApi";
import { useAppSelector } from "@/store/hooks";

export function ApiKeysPage({ embedded = false }: { embedded?: boolean }) {
  const tenantId = useAppSelector((state) => state.tenant.currentId);
  const permissions = useAppSelector((state) => state.auth.user?.permissions ?? []);
  const canManage = permissions.includes("settings.manage");
  const confirm = useConfirm();
  const [tokens, setTokens] = useState<WorkspaceApiToken[]>([]);
  const [name, setName] = useState("Workspace API");
  const [error, setError] = useState("");
  const [ready, setReady] = useState(false);
  const [secret, setSecret] = useState<string | null>(null);

  const load = () => {
    if (!tenantId) {
      return;
    }
    tenantApi
      .apiTokens(tenantId)
      .then((rows) => {
        setTokens(rows);
        setError("");
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setReady(true));
  };

  useEffect(() => {
    load();
  }, [tenantId]);

  return (
    <Stack spacing={3}>
      {embedded ? null : (
        <PageHeader
          title="API keys"
          description="Issue a workspace token so your CRM, ERP, or automation can call the Seonet API. The full token is shown once."
          actions={
            canManage ? (
              <Button
                variant="contained"
                onClick={async () => {
                  if (!tenantId) {
                    return;
                  }
                  try {
                    const created = await tenantApi.createApiToken(tenantId, name);
                    setTokens((current) => [created, ...current]);
                    setSecret(created.token ?? null);
                    setError("");
                  } catch (err) {
                    setError(err instanceof Error ? err.message : "Unable to create API token.");
                  }
                }}
              >
                Create token
              </Button>
            ) : null
          }
        />
      )}
      {error ? <Alert severity="error">{error}</Alert> : null}
      {canManage ? (
        <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ alignItems: { sm: "flex-end" } }}>
          <TextField label="Token name" value={name} onChange={(event) => setName(event.target.value)} sx={{ maxWidth: 360, flex: 1 }} />
          {embedded ? (
            <Button
              variant="contained"
              onClick={async () => {
                if (!tenantId) {
                  return;
                }
                try {
                  const created = await tenantApi.createApiToken(tenantId, name);
                  setTokens((current) => [created, ...current]);
                  setSecret(created.token ?? null);
                  setError("");
                } catch (err) {
                  setError(err instanceof Error ? err.message : "Unable to create API token.");
                }
              }}
            >
              Create token
            </Button>
          ) : null}
        </Stack>
      ) : null}
      {!ready ? <LoadingState /> : null}
      {ready && !tokens.length ? (
        <EmptyState title="No API tokens" description="Create a token to let an external system read and write this workspace over HTTPS." />
      ) : null}
      {tokens.length ? (
        <ResponsiveDataList
          rows={tokens}
          cardTitle={(row) => row.name}
          columns={[
            { key: "name", label: "Name", render: (row) => row.name },
            { key: "prefix", label: "Prefix", render: (row) => row.prefix },
            { key: "used", label: "Last used", hideOnMobile: true, render: (row) => (row.last_used_at ? new Date(row.last_used_at).toLocaleString() : "Never") },
            {
              key: "actions",
              label: "",
              render: (row) =>
                canManage ? (
                  <RowMenu
                    items={[
                      {
                        label: "Revoke",
                        danger: true,
                        onClick: async () => {
                          if (!tenantId) {
                            return;
                          }
                          const ok = await confirm({
                            title: "Revoke API token",
                            description: `${row.name} will stop working immediately. This cannot be undone.`,
                            confirmLabel: "Revoke",
                          });
                          if (!ok) {
                            return;
                          }
                          try {
                            await tenantApi.revokeApiToken(tenantId, row.id);
                            setTokens((current) => current.filter((item) => item.id !== row.id));
                          } catch (err) {
                            setError(err instanceof Error ? err.message : "Unable to revoke token.");
                          }
                        },
                      },
                    ]}
                  />
                ) : null,
            },
          ]}
        />
      ) : null}
      <Dialog open={Boolean(secret)} onClose={() => setSecret(null)} fullWidth maxWidth="sm">
        {secret ? (
          <>
            <DialogTitle>Copy this API token now</DialogTitle>
            <DialogContent>
              <Stack spacing={1.5} sx={{ mt: 1 }}>
                <Alert severity="warning">Seonet will not show the full token again.</Alert>
                <TextField label="API token" value={secret} slotProps={{ input: { readOnly: true } }} />
                <Typography variant="body2" color="text.secondary">
                  Send it as Authorization: Bearer &lt;token&gt;. Do not put it in frontend apps.
                </Typography>
              </Stack>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setSecret(null)}>Done</Button>
            </DialogActions>
          </>
        ) : null}
      </Dialog>
    </Stack>
  );
}
