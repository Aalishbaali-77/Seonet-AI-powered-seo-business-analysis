"use client";

import { useEffect, useState } from "react";
import { Button, Card, CardContent, Chip, Dialog, DialogActions, DialogContent, DialogTitle, Stack, TextField, Typography } from "@mui/material";

import { useConfirm } from "@/components/common/ConfirmDialog";
import { PageHeader } from "@/components/common/PageHeader";
import { RowMenu } from "@/components/common/RowMenu";
import { EmptyState } from "@/components/feedback/EmptyState";
import { ErrorState } from "@/components/feedback/ErrorState";
import { LoadingState } from "@/components/feedback/LoadingState";
import { platformAdminApi } from "@/services/platformAdminApi";
import type { ProductModule } from "@/types/api";

type ModuleDraft = Partial<ProductModule> & { code?: string };
type FeatureDraft = { moduleId: string; id?: string; code: string; name: string; description: string };

export function ModulesManager() {
  const [modules, setModules] = useState<ProductModule[]>([]);
  const [error, setError] = useState("");
  const [ready, setReady] = useState(false);
  const [editing, setEditing] = useState<ModuleDraft | null>(null);
  const [feature, setFeature] = useState<FeatureDraft | null>(null);
  const confirm = useConfirm();

  const load = () =>
    platformAdminApi
      .modules()
      .then((page) => {
        setModules(page.results);
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
        eyebrow="Product catalog"
        title="Modules and features"
        description="Create product modules, edit their features, hide them from new assignments, or delete unused modules."
        actions={
          <Button variant="contained" onClick={() => setEditing({ category: "operations", is_active: true, sort_order: 90 })}>
            New module
          </Button>
        }
      />
      {error ? <ErrorState message={error} onRetry={() => void load()} /> : null}
      {!ready && !error ? <LoadingState /> : null}
      {ready && !modules.length && !error ? <EmptyState title="No modules" description="Create the first product module." /> : null}
      <Stack spacing={2}>
        {modules.map((module) => (
          <Card key={module.id} variant="outlined">
            <CardContent>
              <Stack direction="row" spacing={1} sx={{ justifyContent: "space-between", alignItems: "flex-start" }}>
                <Stack spacing={0.5} sx={{ minWidth: 0 }}>
                  <Typography variant="h4">{module.name}</Typography>
                  <Typography color="text.secondary">{module.description}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {module.category} · {module.is_active ? "active" : "hidden"}
                  </Typography>
                </Stack>
                <RowMenu
                  items={[
                    { label: "Edit", onClick: () => setEditing(module) },
                    { label: "Add feature", onClick: () => setFeature({ moduleId: module.id, code: "", name: "", description: "" }) },
                    {
                      label: module.is_active ? "Deactivate" : "Activate",
                      onClick: async () => {
                        await platformAdminApi.updateModule(module.id, { is_active: !module.is_active });
                        await load();
                      },
                    },
                    {
                      label: "Delete",
                      danger: true,
                      onClick: async () => {
                        const ok = await confirm({
                          title: "Delete module",
                          description: `${module.name} will be deleted.`,
                          confirmLabel: "Delete",
                        });
                        if (!ok) {
                          return;
                        }
                        try {
                          await platformAdminApi.deleteModule(module.id);
                          await load();
                        } catch (err) {
                          setError(err instanceof Error ? err.message : "Unable to delete module.");
                        }
                      },
                    },
                  ]}
                />
              </Stack>
              <Stack direction="row" spacing={1} sx={{ mt: 2, flexWrap: "wrap", gap: 1 }}>
                {module.features.map((item) => (
                  <Chip
                    key={item.id}
                    label={item.name}
                    size="small"
                    variant="outlined"
                    onClick={() => setFeature({ moduleId: module.id, id: item.id, code: item.code, name: item.name, description: item.description })}
                    onDelete={async () => {
                      const ok = await confirm({
                        title: "Delete feature",
                        description: `${item.name} will be removed from this module.`,
                        confirmLabel: "Delete",
                      });
                      if (!ok) {
                        return;
                      }
                      await platformAdminApi.deleteFeature(item.id);
                      await load();
                    }}
                  />
                ))}
              </Stack>
            </CardContent>
          </Card>
        ))}
      </Stack>
      <Dialog open={Boolean(editing)} onClose={() => setEditing(null)} fullWidth maxWidth="sm">
        {editing ? (
          <>
            <DialogTitle>{editing.id ? "Edit module" : "New module"}</DialogTitle>
            <DialogContent>
              <Stack spacing={2} sx={{ mt: 1 }}>
                <TextField label="Code" value={editing.code ?? ""} disabled={Boolean(editing.id)} onChange={(event) => setEditing({ ...editing, code: event.target.value })} />
                <TextField label="Name" value={editing.name ?? ""} onChange={(event) => setEditing({ ...editing, name: event.target.value })} />
                <TextField label="Description" multiline minRows={2} value={editing.description ?? ""} onChange={(event) => setEditing({ ...editing, description: event.target.value })} />
                <TextField label="Category" value={editing.category ?? ""} onChange={(event) => setEditing({ ...editing, category: event.target.value })} />
                <TextField label="Sort order" type="number" value={editing.sort_order ?? 0} onChange={(event) => setEditing({ ...editing, sort_order: Number(event.target.value) })} />
              </Stack>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setEditing(null)}>Cancel</Button>
              <Button
                variant="contained"
                onClick={async () => {
                  if (!editing.code || !editing.name) {
                    return;
                  }
                  if (editing.id) {
                    await platformAdminApi.updateModule(editing.id, editing);
                  } else {
                    await platformAdminApi.createModule({ code: editing.code, name: editing.name, description: editing.description, category: editing.category, sort_order: editing.sort_order, is_active: true });
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
      <Dialog open={Boolean(feature)} onClose={() => setFeature(null)} fullWidth maxWidth="sm">
        {feature ? (
          <>
            <DialogTitle>{feature.id ? "Edit feature" : "New feature"}</DialogTitle>
            <DialogContent>
              <Stack spacing={2} sx={{ mt: 1 }}>
                <TextField label="Code" value={feature.code} disabled={Boolean(feature.id)} onChange={(event) => setFeature({ ...feature, code: event.target.value })} />
                <TextField label="Name" value={feature.name} onChange={(event) => setFeature({ ...feature, name: event.target.value })} />
                <TextField label="Description" value={feature.description} onChange={(event) => setFeature({ ...feature, description: event.target.value })} />
              </Stack>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setFeature(null)}>Cancel</Button>
              <Button
                variant="contained"
                onClick={async () => {
                  if (feature.id) {
                    await platformAdminApi.updateFeature(feature.id, { name: feature.name, description: feature.description });
                  } else {
                    await platformAdminApi.createFeature(feature.moduleId, feature);
                  }
                  setFeature(null);
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
