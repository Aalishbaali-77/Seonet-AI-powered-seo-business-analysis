"use client";

import { useEffect, useState } from "react";
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  FormControlLabel,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Switch,
  TextField,
  Typography,
} from "@mui/material";

import { useConfirm } from "@/components/common/ConfirmDialog";
import { PageHeader } from "@/components/common/PageHeader";
import { ResponsiveDataList } from "@/components/common/ResponsiveDataList";
import { RowMenu } from "@/components/common/RowMenu";
import { StatusChip } from "@/components/common/StatusChip";
import { EmptyState } from "@/components/feedback/EmptyState";
import { ErrorState } from "@/components/feedback/ErrorState";
import { LoadingState } from "@/components/feedback/LoadingState";
import { platformAdminApi } from "@/services/platformAdminApi";
import type { PlanPackage, PlatformTenant, ProductModule } from "@/types/api";

const emptyCreate = {
  name: "",
  owner_email: "",
  owner_first_name: "",
  owner_last_name: "",
  owner_password: "",
  plan_id: "",
};

export function TenantsManager() {
  const confirm = useConfirm();
  const [tenants, setTenants] = useState<PlatformTenant[]>([]);
  const [packages, setPackages] = useState<PlanPackage[]>([]);
  const [modules, setModules] = useState<ProductModule[]>([]);
  const [error, setError] = useState("");
  const [ready, setReady] = useState(false);
  const [selected, setSelected] = useState<PlatformTenant | null>(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState(emptyCreate);

  const load = () =>
    Promise.all([platformAdminApi.tenants(), platformAdminApi.packages(), platformAdminApi.modules()])
      .then(([tenantPage, packagePage, modulePage]) => {
        setTenants(tenantPage.results);
        setPackages(packagePage.results);
        setModules(modulePage.results);
        setError("");
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setReady(true));

  useEffect(() => {
    void load();
  }, []);

  const refreshSelected = async (id: string) => {
    const tenant = await platformAdminApi.tenant(id);
    setSelected(tenant);
    setTenants((current) => current.map((item) => (item.id === id ? tenant : item)));
  };

  return (
    <Stack spacing={3}>
      <PageHeader
        eyebrow="Tenants"
        title="Workspace directory"
        description="Create workspaces, assign packages, override modules, suspend accounts, or remove a tenant from the platform."
        actions={
          <Button variant="contained" onClick={() => setCreating(true)}>
            New tenant
          </Button>
        }
      />
      {error ? <ErrorState message={error} onRetry={() => void load()} /> : null}
      {!ready && !error ? <LoadingState /> : null}
      {ready && !tenants.length && !error ? (
        <EmptyState title="No tenants yet" description="Create a workspace and owner account from this console." />
      ) : null}
      {tenants.length ? (
        <ResponsiveDataList
          rows={tenants}
          cardTitle={(row) => row.name}
          columns={[
            { key: "name", label: "Workspace", render: (row) => row.name },
            { key: "status", label: "Status", render: (row) => <StatusChip value={row.status} /> },
            { key: "plan", label: "Package", render: (row) => row.subscription?.plan.name ?? "None" },
            {
              key: "ai",
              label: "AI credits",
              hideOnMobile: true,
              render: (row) =>
                row.ai_usage ? `${row.ai_usage.credits_used} / ${row.ai_usage.credits_limit}` : "—",
            },
            { key: "members", label: "Members", hideOnMobile: true, render: (row) => row.member_count },
            {
              key: "modules",
              label: "Modules",
              hideOnMobile: true,
              render: (row) => row.modules.filter((item) => item.is_enabled).map((item) => item.name).join(", ") || "—",
            },
            {
              key: "actions",
              label: "",
              render: (row) => (
                <RowMenu
                  items={[
                    { label: "Edit", onClick: () => setSelected(row) },
                    {
                      label: row.status === "suspended" ? "Activate" : "Suspend",
                      onClick: async () => {
                        await platformAdminApi.updateTenant(row.id, { status: row.status === "suspended" ? "active" : "suspended" });
                        await load();
                      },
                    },
                    {
                      label: "Delete",
                      danger: true,
                      onClick: async () => {
                        const ok = await confirm({
                          title: "Delete tenant",
                          description: `${row.name} will be hidden from the platform.`,
                          confirmLabel: "Delete",
                        });
                        if (!ok) {
                          return;
                        }
                        await platformAdminApi.deleteTenant(row.id);
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
      <Dialog open={creating} onClose={() => setCreating(false)} fullWidth maxWidth="sm">
        <DialogTitle>New tenant</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField label="Workspace name" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
            <TextField label="Owner email" type="email" value={form.owner_email} onChange={(event) => setForm({ ...form, owner_email: event.target.value })} />
            <TextField label="Owner first name" value={form.owner_first_name} onChange={(event) => setForm({ ...form, owner_first_name: event.target.value })} />
            <TextField label="Owner last name" value={form.owner_last_name} onChange={(event) => setForm({ ...form, owner_last_name: event.target.value })} />
            <TextField label="Owner password" type="password" helperText="Required when the email is new" value={form.owner_password} onChange={(event) => setForm({ ...form, owner_password: event.target.value })} />
            <TextField select label="Package" value={form.plan_id} onChange={(event) => setForm({ ...form, plan_id: event.target.value })}>
              <MenuItem value="">Starter (default)</MenuItem>
              {packages.map((item) => (
                <MenuItem key={item.id} value={item.id}>
                  {item.name}
                </MenuItem>
              ))}
            </TextField>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreating(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={async () => {
              await platformAdminApi.createTenant({
                ...form,
                plan_id: form.plan_id || undefined,
                owner_password: form.owner_password || undefined,
              });
              setCreating(false);
              setForm(emptyCreate);
              await load();
            }}
          >
            Create
          </Button>
        </DialogActions>
      </Dialog>
      <Dialog open={Boolean(selected)} onClose={() => setSelected(null)} fullWidth maxWidth="sm">
        {selected ? (
          <>
            <DialogTitle>Edit {selected.name}</DialogTitle>
            <DialogContent>
              <Stack spacing={2} sx={{ mt: 1 }}>
                <TextField
                  label="Workspace name"
                  value={selected.name}
                  onChange={(event) => setSelected({ ...selected, name: event.target.value })}
                />
                <FormControl>
                  <InputLabel>Status</InputLabel>
                  <Select
                    label="Status"
                    value={selected.status}
                    onChange={(event) => setSelected({ ...selected, status: event.target.value })}
                  >
                    <MenuItem value="pending">Pending</MenuItem>
                    <MenuItem value="active">Active</MenuItem>
                    <MenuItem value="suspended">Suspended</MenuItem>
                  </Select>
                </FormControl>
                <FormControl>
                  <InputLabel>Package</InputLabel>
                  <Select
                    label="Package"
                    value={selected.subscription?.plan.id ?? ""}
                    onChange={async (event) => {
                      await platformAdminApi.assignPlan(selected.id, { plan_id: event.target.value, status: "active" });
                      await refreshSelected(selected.id);
                    }}
                  >
                    {packages.map((item) => (
                      <MenuItem key={item.id} value={item.id}>
                        {item.name}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
                <Typography variant="subtitle2">Module assignment</Typography>
                {modules.map((module) => {
                  const assignment = selected.modules.find((item) => item.code === module.code);
                  return (
                    <FormControlLabel
                      key={module.id}
                      control={
                        <Switch
                          checked={Boolean(assignment?.is_enabled)}
                          onChange={async (_event, checked) => {
                            await platformAdminApi.assignModule(selected.id, { module_code: module.code, is_enabled: checked });
                            await refreshSelected(selected.id);
                          }}
                        />
                      }
                      label={`${module.name} (${assignment?.source ?? "off"})`}
                    />
                  );
                })}
              </Stack>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setSelected(null)}>Cancel</Button>
              <Button
                variant="contained"
                onClick={async () => {
                  await platformAdminApi.updateTenant(selected.id, { name: selected.name, status: selected.status });
                  setSelected(null);
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
