"use client";

import { useEffect, useState } from "react";
import { Alert, Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, Stack, TextField, Typography } from "@mui/material";

import { useConfirm } from "@/components/common/ConfirmDialog";
import { ResponsiveDataList } from "@/components/common/ResponsiveDataList";
import { RowMenu } from "@/components/common/RowMenu";
import { StatusChip } from "@/components/common/StatusChip";
import { EmptyState } from "@/components/feedback/EmptyState";
import { ErrorState } from "@/components/feedback/ErrorState";
import { LoadingState } from "@/components/feedback/LoadingState";
import { platformAdminApi } from "@/services/platformAdminApi";
import { useAppSelector } from "@/store/hooks";
import type { PlatformAdmin } from "@/types/api";

type InviteDraft = { email: string; first_name: string; last_name: string };

function formatLastLogin(value: string | null): string {
  return value ? new Date(value).toLocaleString() : "Never";
}

export function PlatformAdminsManager() {
  const currentUserId = useAppSelector((state) => state.auth.user?.id);
  const confirm = useConfirm();
  const [admins, setAdmins] = useState<PlatformAdmin[]>([]);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [invite, setInvite] = useState<InviteDraft | null>(null);
  const [inviting, setInviting] = useState(false);

  const load = () =>
    platformAdminApi
      .platformAdmins()
      .then((page) => {
        setAdmins(page.results);
        setError("");
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setReady(true));

  useEffect(() => {
    void load();
  }, []);

  const openInvite = () => setInvite({ email: "", first_name: "", last_name: "" });

  return (
    <Stack spacing={2}>
      {error ? <ErrorState message={error} onRetry={() => void load()} /> : null}
      {notice ? (
        <Alert severity="success" onClose={() => setNotice("")}>
          {notice}
        </Alert>
      ) : null}
      <Box>
        <Button variant="contained" onClick={openInvite}>
          Add admin
        </Button>
      </Box>
      {!ready ? <LoadingState /> : null}
      {ready && admins.length === 0 ? (
        <EmptyState
          title="No platform admins yet"
          description="Invite people who need access to the Control Plane. They set their own password via a secure email link — nobody ever sees or stores it in plain text."
          actionLabel="Add admin"
          onAction={openInvite}
        />
      ) : null}
      {ready && admins.length > 0 ? (
        <ResponsiveDataList
          rows={admins}
          cardTitle={(row) => row.email}
          columns={[
            { key: "name", label: "Name", render: (row) => `${row.first_name} ${row.last_name}`.trim() || "—" },
            { key: "email", label: "Email", render: (row) => row.email },
            { key: "status", label: "Status", render: (row) => <StatusChip value={row.is_active ? "active" : "suspended"} /> },
            { key: "last_login", label: "Last login", hideOnMobile: true, render: (row) => formatLastLogin(row.last_login) },
            {
              key: "actions",
              label: "",
              render: (row) => {
                const isSelf = row.id === currentUserId;
                return (
                  <RowMenu
                    items={[
                      {
                        label: row.is_active ? "Suspend" : "Reactivate",
                        danger: row.is_active,
                        disabled: isSelf,
                        onClick: async () => {
                          try {
                            const next = await platformAdminApi.setPlatformAdminActive(row.id, !row.is_active);
                            setAdmins((current) => current.map((item) => (item.id === row.id ? next : item)));
                            setError("");
                          } catch (err) {
                            setError(err instanceof Error ? err.message : "Unable to update this admin.");
                          }
                        },
                      },
                      {
                        label: "Force password reset",
                        onClick: async () => {
                          try {
                            await platformAdminApi.resetPlatformAdminPassword(row.id);
                            setNotice(`Password reset link sent to ${row.email}.`);
                            setError("");
                          } catch (err) {
                            setError(err instanceof Error ? err.message : "Unable to send the reset link.");
                          }
                        },
                      },
                      {
                        label: "Remove",
                        danger: true,
                        disabled: isSelf,
                        onClick: async () => {
                          const ok = await confirm({
                            title: "Remove platform admin",
                            description: `${row.email} will lose Control Plane access immediately.`,
                            confirmLabel: "Remove",
                          });
                          if (!ok) {
                            return;
                          }
                          try {
                            await platformAdminApi.removePlatformAdmin(row.id);
                            setAdmins((current) => current.filter((item) => item.id !== row.id));
                            setError("");
                          } catch (err) {
                            setError(err instanceof Error ? err.message : "Unable to remove this admin.");
                          }
                        },
                      },
                    ]}
                  />
                );
              },
            },
          ]}
        />
      ) : null}
      <Dialog open={Boolean(invite)} onClose={() => setInvite(null)} fullWidth maxWidth="sm">
        {invite ? (
          <>
            <DialogTitle>Add platform admin</DialogTitle>
            <DialogContent>
              <Stack spacing={2} sx={{ mt: 1 }}>
                <Typography color="text.secondary">
                  They&apos;ll get an email with a secure link to set their own password.
                </Typography>
                <TextField
                  label="Email"
                  type="email"
                  value={invite.email}
                  onChange={(event) => setInvite({ ...invite, email: event.target.value })}
                  fullWidth
                />
                <TextField
                  label="First name"
                  value={invite.first_name}
                  onChange={(event) => setInvite({ ...invite, first_name: event.target.value })}
                  fullWidth
                />
                <TextField
                  label="Last name"
                  value={invite.last_name}
                  onChange={(event) => setInvite({ ...invite, last_name: event.target.value })}
                  fullWidth
                />
              </Stack>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setInvite(null)}>Cancel</Button>
              <Button
                variant="contained"
                disabled={inviting || !invite.email}
                onClick={async () => {
                  setInviting(true);
                  try {
                    const created = await platformAdminApi.invitePlatformAdmin(invite);
                    setAdmins((current) => [created, ...current]);
                    setInvite(null);
                    setNotice(`Invite sent to ${created.email}.`);
                    setError("");
                  } catch (err) {
                    setError(err instanceof Error ? err.message : "Unable to invite this admin.");
                  } finally {
                    setInviting(false);
                  }
                }}
              >
                Send invite
              </Button>
            </DialogActions>
          </>
        ) : null}
      </Dialog>
    </Stack>
  );
}
