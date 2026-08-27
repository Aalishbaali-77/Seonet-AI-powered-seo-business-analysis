"use client";

import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  MenuItem,
  Stack,
  Tab,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { useConfirm } from "@/components/common/ConfirmDialog";
import { PageHeader } from "@/components/common/PageHeader";
import { ResponsiveDataList } from "@/components/common/ResponsiveDataList";
import { RowMenu } from "@/components/common/RowMenu";
import { StatusChip } from "@/components/common/StatusChip";
import { EmptyState } from "@/components/feedback/EmptyState";
import { LoadingState } from "@/components/feedback/LoadingState";
import { accessApi, tenantApi, type AccessPermission, type WorkspaceMember, type WorkspaceProfile, type WorkspaceRole } from "@/services/domainApi";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { bootstrapRequested } from "@/store/slices/authSlice";
import { ApiKeysPage } from "@/features/settings/ApiKeysPage";

const SECTION_HREF = {
  workspace: "/app/settings",
  team: "/app/settings/team",
  roles: "/app/settings/roles",
  api: "/app/settings/api",
} as const;

export function WorkspaceSettingsPage({ section }: { section: "workspace" | "team" | "roles" | "api" }) {
  const router = useRouter();
  const dispatch = useAppDispatch();
  const tenantId = useAppSelector((state) => state.tenant.currentId);
  const permissions = useAppSelector((state) => state.auth.user?.permissions ?? []);
  const subscription = useAppSelector((state) => state.auth.user?.subscription);
  const canManageWorkspace = permissions.includes("settings.manage");
  const canViewMembers = permissions.includes("member.view") || permissions.includes("member.manage");
  const canManageMembers = permissions.includes("member.manage");
  const canManageRoles = permissions.includes("role.manage");
  const confirm = useConfirm();
  const [name, setName] = useState("");
  const [status, setStatus] = useState("");
  const [profile, setProfile] = useState({
    timezone: "UTC",
    locale: "en-US",
    currency: "USD",
    company_legal_name: "",
    company_website: "",
    industry: "",
    support_email: "",
    reply_to_email: "",
    notification_digest: "daily",
    primary_crm: "native",
  });
  const [saved, setSaved] = useState("");
  const [error, setError] = useState("");
  const [ready, setReady] = useState(false);
  const [members, setMembers] = useState<WorkspaceMember[]>([]);
  const [roles, setRoles] = useState<WorkspaceRole[]>([]);
  const [catalog, setCatalog] = useState<AccessPermission[]>([]);
  const [invite, setInvite] = useState<{ email: string; first_name: string; role_code: string; password: string } | null>(null);
  const [roleDraft, setRoleDraft] = useState<{ id?: string; name: string; permission_codes: string[] } | null>(null);

  const load = () => {
    if (!tenantId) {
      return;
    }
    const tasks: Array<Promise<unknown>> = [
      tenantApi.get(tenantId).then((tenant: WorkspaceProfile) => {
        setName(tenant.name);
        setStatus(tenant.status);
        setProfile({
          timezone: tenant.timezone || "UTC",
          locale: tenant.locale || "en-US",
          currency: tenant.currency || "USD",
          company_legal_name: tenant.company_legal_name || "",
          company_website: tenant.company_website || "",
          industry: tenant.industry || "",
          support_email: tenant.support_email || "",
          reply_to_email: tenant.reply_to_email || "",
          notification_digest: tenant.notification_digest || "daily",
          primary_crm: tenant.primary_crm || "native",
        });
      }),
      accessApi.roles().then(setRoles),
    ];
    if (canViewMembers) {
      tasks.push(tenantApi.members(tenantId).then(setMembers));
    }
    if (canManageRoles) {
      tasks.push(accessApi.permissions().then(setCatalog));
    }
    Promise.all(tasks)
      .then(() => setError(""))
      .catch((err: Error) => setError(err.message))
      .finally(() => setReady(true));
  };

  useEffect(() => {
    load();
  }, [tenantId, canViewMembers, canManageRoles]);

  const groupedPermissions = useMemo(() => {
    const groups = new Map<string, AccessPermission[]>();
    catalog.forEach((item) => {
      const current = groups.get(item.module) ?? [];
      current.push(item);
      groups.set(item.module, current);
    });
    return [...groups.entries()];
  }, [catalog]);

  return (
    <Stack spacing={3}>
      <PageHeader
        title="Workspace settings"
        description="You own this tenant. Invite your team, assign roles, and decide what each role can do — without leaving the workspace."
      />
      {error ? <Alert severity="error">{error}</Alert> : null}
      {saved ? <Alert severity="success">{saved}</Alert> : null}
      {subscription ? (
        <Typography color="text.secondary">
          Seats {subscription.seats_used} of {subscription.max_users}
        </Typography>
      ) : null}
      <Tabs value={section} onChange={(_event, value: keyof typeof SECTION_HREF) => router.push(SECTION_HREF[value])}>
        <Tab label="Workspace" value="workspace" />
        <Tab label="Team" value="team" />
        <Tab label="Roles & permissions" value="roles" />
        <Tab label="API keys" value="api" />
      </Tabs>
      {!ready ? <LoadingState /> : null}
      {ready && section === "workspace" ? (
        <Card variant="outlined">
          <CardContent>
            <Stack spacing={2}>
              <TextField label="Workspace name" value={name} onChange={(event) => setName(event.target.value)} disabled={!canManageWorkspace} />
              <TextField label="Legal name" value={profile.company_legal_name} onChange={(event) => setProfile({ ...profile, company_legal_name: event.target.value })} disabled={!canManageWorkspace} />
              <TextField label="Website" value={profile.company_website} onChange={(event) => setProfile({ ...profile, company_website: event.target.value })} disabled={!canManageWorkspace} />
              <TextField label="Industry" value={profile.industry} onChange={(event) => setProfile({ ...profile, industry: event.target.value })} disabled={!canManageWorkspace} />
              <TextField select label="Timezone" value={profile.timezone} onChange={(event) => setProfile({ ...profile, timezone: event.target.value })} disabled={!canManageWorkspace}>
                {["UTC", "America/New_York", "America/Chicago", "America/Los_Angeles", "Europe/London", "Europe/Berlin", "Asia/Dubai", "Asia/Karachi", "Asia/Kolkata", "Australia/Sydney"].map((zone) => (
                  <MenuItem key={zone} value={zone}>
                    {zone}
                  </MenuItem>
                ))}
              </TextField>
              <TextField select label="Currency" value={profile.currency} onChange={(event) => setProfile({ ...profile, currency: event.target.value })} disabled={!canManageWorkspace}>
                {["USD", "EUR", "GBP", "AED", "SAR", "PKR", "INR", "CAD", "AUD"].map((code) => (
                  <MenuItem key={code} value={code}>
                    {code}
                  </MenuItem>
                ))}
              </TextField>
              <TextField select label="Notification digest" value={profile.notification_digest} onChange={(event) => setProfile({ ...profile, notification_digest: event.target.value })} disabled={!canManageWorkspace}>
                <MenuItem value="off">Off</MenuItem>
                <MenuItem value="daily">Daily</MenuItem>
                <MenuItem value="weekly">Weekly</MenuItem>
              </TextField>
              <TextField select label="Primary CRM" value={profile.primary_crm} onChange={(event) => setProfile({ ...profile, primary_crm: event.target.value })} disabled={!canManageWorkspace}>
                <MenuItem value="native">Seonet CRM</MenuItem>
                <MenuItem value="hubspot">HubSpot</MenuItem>
                <MenuItem value="odoo">Odoo</MenuItem>
                <MenuItem value="custom_api">Custom REST / ERP</MenuItem>
              </TextField>
              <TextField label="Support email" value={profile.support_email} onChange={(event) => setProfile({ ...profile, support_email: event.target.value })} disabled={!canManageWorkspace} />
              <TextField label="Reply-to email" value={profile.reply_to_email} onChange={(event) => setProfile({ ...profile, reply_to_email: event.target.value })} disabled={!canManageWorkspace} />
              <Typography variant="body2" color="text.secondary">
                Status: {status || "—"}
              </Typography>
              {canManageWorkspace ? (
                <Button
                  variant="contained"
                  onClick={async () => {
                    if (!tenantId) {
                      return;
                    }
                    try {
                      await tenantApi.update(tenantId, { name, ...profile });
                      setSaved("Workspace saved.");
                      setError("");
                    } catch (err) {
                      setError(err instanceof Error ? err.message : "Unable to save workspace.");
                    }
                  }}
                >
                  Save
                </Button>
              ) : null}
            </Stack>
          </CardContent>
        </Card>
      ) : null}
      {ready && section === "team" ? (
        <Stack spacing={2}>
          {canManageMembers ? (
            <Box>
              <Button variant="contained" onClick={() => setInvite({ email: "", first_name: "", role_code: "viewer", password: "" })}>
                Add teammate
              </Button>
            </Box>
          ) : (
            <Typography color="text.secondary">You can view the team. Only owners and admins can add people.</Typography>
          )}
          {members.length <= 1 && canManageMembers ? (
            <EmptyState
              title="Invite your team"
              description="You are the only person in this workspace. Add teammates and assign roles when you are ready."
              actionLabel="Add teammate"
              onAction={() => setInvite({ email: "", first_name: "", role_code: "viewer", password: "" })}
            />
          ) : null}
          {members.length ? (
            <ResponsiveDataList
              rows={members}
              cardTitle={(row) => row.email}
              columns={[
                { key: "email", label: "Email", render: (row) => row.email },
                { key: "name", label: "Name", hideOnMobile: true, render: (row) => `${row.first_name} ${row.last_name}`.trim() || "—" },
                {
                  key: "roles",
                  label: "Role",
                  render: (row) =>
                    canManageMembers ? (
                      <TextField
                        select
                        size="small"
                        value={row.roles[0] ?? "viewer"}
                        onChange={async (event) => {
                          if (!tenantId) {
                            return;
                          }
                          try {
                            const next = await tenantApi.updateMember(tenantId, row.id, { role_code: event.target.value });
                            setMembers((current) => current.map((item) => (item.id === row.id ? next : item)));
                            setSaved("Role updated.");
                            setError("");
                          } catch (err) {
                            setError(err instanceof Error ? err.message : "Unable to update role.");
                          }
                        }}
                        sx={{ minWidth: 180 }}
                      >
                        {roles.map((role) => (
                          <MenuItem key={role.code} value={role.code}>
                            {role.name}
                          </MenuItem>
                        ))}
                      </TextField>
                    ) : (
                      row.roles.join(", ") || "—"
                    ),
                },
                { key: "status", label: "Status", render: (row) => <StatusChip value={row.status} /> },
                {
                  key: "actions",
                  label: "",
                  render: (row) =>
                    canManageMembers ? (
                      <RowMenu
                        items={[
                          {
                            label: row.status === "disabled" ? "Enable" : "Disable",
                            onClick: async () => {
                              if (!tenantId) {
                                return;
                              }
                              try {
                                const next = await tenantApi.updateMember(tenantId, row.id, { status: row.status === "disabled" ? "active" : "disabled" });
                                setMembers((current) => current.map((item) => (item.id === row.id ? next : item)));
                              } catch (err) {
                                setError(err instanceof Error ? err.message : "Unable to update member.");
                              }
                            },
                          },
                          {
                            label: "Remove",
                            danger: true,
                            onClick: async () => {
                              if (!tenantId) {
                                return;
                              }
                              const ok = await confirm({
                                title: "Remove teammate",
                                description: `${row.email} will lose access to this workspace.`,
                                confirmLabel: "Remove",
                              });
                              if (!ok) {
                                return;
                              }
                              try {
                                await tenantApi.removeMember(tenantId, row.id);
                                setMembers((current) => current.filter((item) => item.id !== row.id));
                              } catch (err) {
                                setError(err instanceof Error ? err.message : "Unable to remove member.");
                              }
                            },
                          },
                        ]}
                      />
                    ) : null,
                },
              ]}
            />
          ) : (
            <EmptyState title="No teammates yet" description="People you add will appear here with their roles." />
          )}
        </Stack>
      ) : null}
      {ready && section === "roles" ? (
        <Stack spacing={2}>
          {canManageRoles ? (
            <Box>
              <Button variant="contained" onClick={() => setRoleDraft({ name: "", permission_codes: ["website.view"] })}>
                New role
              </Button>
            </Box>
          ) : (
            <Typography color="text.secondary">Owners and admins can create roles and change permissions for this tenant.</Typography>
          )}
          {roles.length ? (
            roles.map((role) => (
              <Card key={role.id} variant="outlined">
                <CardContent>
                  <Stack direction="row" spacing={1} sx={{ justifyContent: "space-between", alignItems: "flex-start" }}>
                    <Box>
                      <Typography variant="h4">{role.name}</Typography>
                      <Typography variant="body2" color="text.secondary">
                        {role.code}
                        {role.is_system ? " · system" : ""}
                      </Typography>
                      <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                        {role.permissions.length} permissions
                      </Typography>
                    </Box>
                    {canManageRoles && role.code !== "owner" ? (
                      <RowMenu
                        items={[
                          { label: "Edit permissions", onClick: () => setRoleDraft({ id: role.id, name: role.name, permission_codes: role.permissions }) },
                          ...(!role.is_system
                            ? [
                                {
                                  label: "Delete",
                                  danger: true,
                                  onClick: async () => {
                                    const ok = await confirm({
                                      title: "Delete role",
                                      description: `${role.name} will be deleted. Members using this role must be reassigned.`,
                                      confirmLabel: "Delete",
                                    });
                                    if (!ok) {
                                      return;
                                    }
                                    try {
                                      await accessApi.deleteRole(role.id);
                                      setRoles((current) => current.filter((item) => item.id !== role.id));
                                    } catch (err) {
                                      setError(err instanceof Error ? err.message : "Unable to delete role.");
                                    }
                                  },
                                },
                              ]
                            : []),
                        ]}
                      />
                    ) : null}
                  </Stack>
                </CardContent>
              </Card>
            ))
          ) : (
            <EmptyState title="No roles yet" description="System roles appear here after the workspace is provisioned." />
          )}
        </Stack>
      ) : null}
      {ready && section === "api" ? <ApiKeysPage embedded /> : null}
      <Dialog open={Boolean(invite)} onClose={() => setInvite(null)} fullWidth maxWidth="sm">
        {invite ? (
          <>
            <DialogTitle>Add teammate</DialogTitle>
            <DialogContent>
              <Stack spacing={2} sx={{ mt: 1 }}>
                <TextField label="Email" value={invite.email} onChange={(event) => setInvite({ ...invite, email: event.target.value })} />
                <TextField label="Name" value={invite.first_name} onChange={(event) => setInvite({ ...invite, first_name: event.target.value })} />
                <TextField select label="Role" value={invite.role_code} onChange={(event) => setInvite({ ...invite, role_code: event.target.value })}>
                  {roles.map((role) => (
                    <MenuItem key={role.code} value={role.code}>
                      {role.name}
                    </MenuItem>
                  ))}
                </TextField>
                <TextField
                  label="Temporary password"
                  type="password"
                  value={invite.password}
                  onChange={(event) => setInvite({ ...invite, password: event.target.value })}
                  helperText="Optional. If empty, they receive an email to set a password."
                />
              </Stack>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setInvite(null)}>Cancel</Button>
              <Button
                variant="contained"
                onClick={async () => {
                  if (!tenantId || !invite.email) {
                    return;
                  }
                  try {
                    const created = await tenantApi.addMember(tenantId, {
                      email: invite.email,
                      first_name: invite.first_name,
                      role_code: invite.role_code,
                      password: invite.password || undefined,
                    });
                    setMembers((current) => [...current, created]);
                    setInvite(null);
                    setSaved("Teammate added.");
                    setError("");
                    dispatch(bootstrapRequested());
                  } catch (err) {
                    setError(err instanceof Error ? err.message : "Unable to add teammate.");
                  }
                }}
              >
                Add
              </Button>
            </DialogActions>
          </>
        ) : null}
      </Dialog>
      <Dialog open={Boolean(roleDraft)} onClose={() => setRoleDraft(null)} fullWidth maxWidth="md">
        {roleDraft ? (
          <>
            <DialogTitle>{roleDraft.id ? "Edit role" : "New role"}</DialogTitle>
            <DialogContent>
              <Stack spacing={2} sx={{ mt: 1 }}>
                <TextField label="Name" value={roleDraft.name} onChange={(event) => setRoleDraft({ ...roleDraft, name: roleDraft.name })} />
                {groupedPermissions.map(([module, items]) => (
                  <Box key={module}>
                    <Typography variant="subtitle2" sx={{ mb: 0.5, textTransform: "capitalize" }}>
                      {module}
                    </Typography>
                    <Stack>
                      {items.map((item) => (
                        <FormControlLabel
                          key={item.code}
                          control={
                            <Checkbox
                              checked={roleDraft.permission_codes.includes(item.code)}
                              onChange={(_event, checked) => {
                                const next = new Set(roleDraft.permission_codes);
                                if (checked) {
                                  next.add(item.code);
                                } else {
                                  next.delete(item.code);
                                }
                                setRoleDraft({ ...roleDraft, permission_codes: [...next] });
                              }}
                            />
                          }
                          label={`${item.name} (${item.code})`}
                        />
                      ))}
                    </Stack>
                  </Box>
                ))}
              </Stack>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setRoleDraft(null)}>Cancel</Button>
              <Button
                variant="contained"
                onClick={async () => {
                  if (!roleDraft.name) {
                    return;
                  }
                  try {
                    const next = roleDraft.id
                      ? await accessApi.updateRole(roleDraft.id, { name: roleDraft.name, permission_codes: roleDraft.permission_codes })
                      : await accessApi.createRole({ name: roleDraft.name, permission_codes: roleDraft.permission_codes });
                    setRoles((current) => {
                      const others = current.filter((item) => item.id !== next.id);
                      return [...others, next].sort((a, b) => a.name.localeCompare(b.name));
                    });
                    setRoleDraft(null);
                    setSaved("Role saved.");
                    setError("");
                  } catch (err) {
                    setError(err instanceof Error ? err.message : "Unable to save role.");
                  }
                }}
              >
                Save role
              </Button>
            </DialogActions>
          </>
        ) : null}
      </Dialog>
    </Stack>
  );
}
