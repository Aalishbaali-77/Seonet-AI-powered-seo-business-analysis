"use client";

import { useEffect, useState } from "react";
import {
  Button,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  Stack,
  TextField,
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
import type { PlanPackage, ProductModule } from "@/types/api";

type PackageDraft = Partial<PlanPackage> & { module_codes?: string[] };

export function PackagesManager() {
  const [packages, setPackages] = useState<PlanPackage[]>([]);
  const [modules, setModules] = useState<ProductModule[]>([]);
  const [error, setError] = useState("");
  const [ready, setReady] = useState(false);
  const [editing, setEditing] = useState<PackageDraft | null>(null);
  const confirm = useConfirm();

  const load = () =>
    Promise.all([platformAdminApi.packages(), platformAdminApi.modules()])
      .then(([packagePage, modulePage]) => {
        setPackages(packagePage.results);
        setModules(modulePage.results);
        setError("");
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setReady(true));

  useEffect(() => {
    void load();
  }, []);

  const save = async () => {
    if (!editing?.code || !editing.name) {
      return;
    }
    const payload = {
      code: editing.code,
      name: editing.name,
      description: editing.description ?? "",
      price_amount: editing.price_amount ?? "0.00",
      interval: editing.interval ?? "month",
      trial_days: Number(editing.trial_days ?? 14),
      max_pages: Number(editing.max_pages ?? 25),
      max_audits_per_month: Number(editing.max_audits_per_month ?? 20),
      ai_credits: Number(editing.ai_credits ?? 1000),
      max_users: Number(editing.max_users ?? 5),
      is_active: editing.is_active ?? true,
      is_public: editing.is_public ?? true,
      is_featured: editing.is_featured ?? false,
      cta_label: editing.cta_label ?? "",
      cta_href: editing.cta_href ?? "",
      sort_order: Number(editing.sort_order ?? 0),
      module_codes: editing.module_codes ?? [],
    };
    if (editing.id) {
      await platformAdminApi.updatePackage(editing.id, payload);
    } else {
      await platformAdminApi.createPackage(payload);
    }
    setEditing(null);
    await load();
  };

  return (
    <Stack spacing={3}>
      <PageHeader
        eyebrow="Commercial catalog"
        title="Subscription packages"
        description="Create, edit, duplicate, deactivate, or delete sellable plans. A package in use cannot be deleted until subscriptions move off it."
        actions={
          <Button variant="contained" onClick={() => setEditing({ interval: "month", is_active: true, is_public: true, is_featured: false, module_codes: [] })}>
            New package
          </Button>
        }
      />
      {error ? <ErrorState message={error} onRetry={() => void load()} /> : null}
      {!ready && !error ? <LoadingState /> : null}
      {ready && !packages.length && !error ? <EmptyState title="No packages" description="Create the first commercial package." /> : null}
      {packages.length ? (
        <ResponsiveDataList
          rows={packages}
          cardTitle={(row) => row.name}
          columns={[
            { key: "name", label: "Package", render: (row) => row.name },
            { key: "price", label: "Price", render: (row) => `${row.currency} ${row.price_amount}/${row.interval}` },
            { key: "status", label: "Status", render: (row) => <StatusChip value={row.is_active ? "active" : "canceled"} /> },
            { key: "public", label: "Landing", hideOnMobile: true, render: (row) => (row.is_public ? (row.is_featured ? "Featured" : "Public") : "Hidden") },
            { key: "modules", label: "Modules", hideOnMobile: true, render: (row) => row.modules.map((item) => item.name).join(", ") },
            {
              key: "actions",
              label: "",
              render: (row) => (
                <RowMenu
                  items={[
                    { label: "Edit", onClick: () => setEditing({ ...row, module_codes: row.modules.map((item) => item.code) }) },
                    {
                      label: "Duplicate",
                      onClick: () =>
                        setEditing({
                          ...row,
                          id: undefined,
                          code: `${row.code}-copy`,
                          name: `${row.name} copy`,
                          module_codes: row.modules.map((item) => item.code),
                        }),
                    },
                    {
                      label: row.is_active ? "Deactivate" : "Activate",
                      onClick: async () => {
                        await platformAdminApi.updatePackage(row.id, { is_active: !row.is_active });
                        await load();
                      },
                    },
                    {
                      label: "Delete",
                      danger: true,
                      onClick: async () => {
                        const ok = await confirm({
                          title: "Delete package",
                          description: `${row.name} will be deleted. A package in use cannot be removed until subscriptions move off it.`,
                          confirmLabel: "Delete",
                        });
                        if (!ok) {
                          return;
                        }
                        try {
                          await platformAdminApi.deletePackage(row.id);
                          await load();
                        } catch (err) {
                          setError(err instanceof Error ? err.message : "Unable to delete package.");
                        }
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
            <DialogTitle>{editing.id ? "Edit package" : "New package"}</DialogTitle>
            <DialogContent>
              <Stack spacing={2} sx={{ mt: 1 }}>
                <TextField label="Code" value={editing.code ?? ""} disabled={Boolean(editing.id)} onChange={(event) => setEditing({ ...editing, code: event.target.value })} />
                <TextField label="Name" value={editing.name ?? ""} onChange={(event) => setEditing({ ...editing, name: event.target.value })} />
                <TextField label="Description" multiline minRows={2} value={editing.description ?? ""} onChange={(event) => setEditing({ ...editing, description: event.target.value })} />
                <TextField label="Price" value={editing.price_amount ?? ""} onChange={(event) => setEditing({ ...editing, price_amount: event.target.value })} />
                <TextField label="Trial days" type="number" value={editing.trial_days ?? 14} onChange={(event) => setEditing({ ...editing, trial_days: Number(event.target.value) })} />
                <TextField label="Max pages" type="number" value={editing.max_pages ?? 25} onChange={(event) => setEditing({ ...editing, max_pages: Number(event.target.value) })} />
                <TextField label="Audits / month" type="number" value={editing.max_audits_per_month ?? 20} onChange={(event) => setEditing({ ...editing, max_audits_per_month: Number(event.target.value) })} />
                <TextField
                  label="AI credits"
                  type="number"
                  value={editing.ai_credits ?? 1000}
                  onChange={(event) => setEditing({ ...editing, ai_credits: Number(event.target.value) })}
                  helperText="Prompt + completion tokens from the platform Claude/OpenAI key, per workspace per billing period."
                />
                <TextField label="Max users" type="number" value={editing.max_users ?? 5} onChange={(event) => setEditing({ ...editing, max_users: Number(event.target.value) })} />
                <FormControlLabel
                  control={<Checkbox checked={editing.is_public ?? true} onChange={(_event, checked) => setEditing({ ...editing, is_public: checked })} />}
                  label="Show on public landing page"
                />
                <FormControlLabel
                  control={<Checkbox checked={editing.is_featured ?? false} onChange={(_event, checked) => setEditing({ ...editing, is_featured: checked })} />}
                  label="Featured plan"
                />
                <TextField label="CTA label" value={editing.cta_label ?? ""} onChange={(event) => setEditing({ ...editing, cta_label: event.target.value })} />
                <TextField label="CTA link" value={editing.cta_href ?? ""} onChange={(event) => setEditing({ ...editing, cta_href: event.target.value })} helperText="Empty uses /register, or the support URL when price is 0." />
                <TextField label="Sort order" type="number" value={editing.sort_order ?? 0} onChange={(event) => setEditing({ ...editing, sort_order: Number(event.target.value) })} />
                {modules.map((module) => (
                  <FormControlLabel
                    key={module.id}
                    control={
                      <Checkbox
                        checked={(editing.module_codes ?? []).includes(module.code)}
                        onChange={(_event, checked) => {
                          const current = new Set(editing.module_codes ?? []);
                          if (checked) {
                            current.add(module.code);
                          } else {
                            current.delete(module.code);
                          }
                          setEditing({ ...editing, module_codes: [...current] });
                        }}
                      />
                    }
                    label={module.name}
                  />
                ))}
              </Stack>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setEditing(null)}>Cancel</Button>
              <Button variant="contained" onClick={() => void save()}>
                Save
              </Button>
            </DialogActions>
          </>
        ) : null}
      </Dialog>
    </Stack>
  );
}
