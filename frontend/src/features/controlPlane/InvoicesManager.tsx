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
import type { PlatformInvoice, PlatformTenant } from "@/types/api";

const emptyForm = { tenant_id: "", description: "", amount: "", notes: "" };

export function InvoicesManager() {
  const confirm = useConfirm();
  const [invoices, setInvoices] = useState<PlatformInvoice[]>([]);
  const [tenants, setTenants] = useState<PlatformTenant[]>([]);
  const [error, setError] = useState("");
  const [ready, setReady] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [open, setOpen] = useState(false);

  const load = () =>
    Promise.all([platformAdminApi.invoices(), platformAdminApi.tenants()])
      .then(([invoicePage, tenantPage]) => {
        setInvoices(invoicePage.results);
        setTenants(tenantPage.results);
        setError("");
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setReady(true));

  useEffect(() => {
    void load();
  }, []);

  const openCreate = () => {
    setEditingId(null);
    setForm(emptyForm);
    setOpen(true);
  };

  const openEdit = (row: PlatformInvoice) => {
    setEditingId(row.id);
    setForm({
      tenant_id: row.tenant_id,
      description: row.lines[0]?.description ?? "",
      amount: row.total,
      notes: row.notes,
    });
    setOpen(true);
  };

  return (
    <Stack spacing={3}>
      <PageHeader
        eyebrow="Revenue operations"
        title="Invoicing"
        description="Create drafts, issue them, mark collection, void unpaid invoices, or delete drafts. Paid invoices stay as the financial record."
        actions={
          <Button variant="contained" onClick={openCreate}>
            New invoice
          </Button>
        }
      />
      {error ? <ErrorState message={error} onRetry={() => void load()} /> : null}
      {!ready && !error ? <LoadingState /> : null}
      {ready && !invoices.length && !error ? (
        <EmptyState title="No invoices yet" description="Create an invoice for a tenant, issue it, then mark it paid when collection is confirmed." />
      ) : null}
      {invoices.length ? (
        <ResponsiveDataList
          rows={invoices}
          cardTitle={(row) => row.number}
          columns={[
            { key: "number", label: "Invoice", render: (row) => row.number },
            { key: "tenant", label: "Tenant", render: (row) => row.tenant_name },
            { key: "total", label: "Total", render: (row) => `${row.currency} ${row.total}` },
            { key: "status", label: "Status", render: (row) => <StatusChip value={row.status} /> },
            {
              key: "actions",
              label: "",
              render: (row) => (
                <RowMenu
                  items={[
                    { label: "Edit draft", disabled: row.status !== "draft", onClick: () => openEdit(row) },
                    {
                      label: "Issue",
                      disabled: row.status !== "draft",
                      onClick: async () => {
                        await platformAdminApi.issueInvoice(row.id);
                        await load();
                      },
                    },
                    {
                      label: "Mark paid",
                      disabled: row.status !== "issued" && row.status !== "overdue",
                      onClick: async () => {
                        const ok = await confirm({
                          title: "Mark invoice paid",
                          description: `Record ${row.number} as collected.`,
                          confirmLabel: "Mark paid",
                          danger: false,
                        });
                        if (!ok) {
                          return;
                        }
                        await platformAdminApi.markInvoicePaid(row.id);
                        await load();
                      },
                    },
                    {
                      label: "Void",
                      disabled: row.status === "paid" || row.status === "void",
                      onClick: async () => {
                        const ok = await confirm({
                          title: "Void invoice",
                          description: `${row.number} will be voided and can no longer be collected.`,
                          confirmLabel: "Void",
                        });
                        if (!ok) {
                          return;
                        }
                        await platformAdminApi.voidInvoice(row.id);
                        await load();
                      },
                    },
                    {
                      label: "Delete",
                      danger: true,
                      disabled: row.status !== "draft" && row.status !== "void",
                      onClick: async () => {
                        const ok = await confirm({
                          title: "Delete invoice",
                          description: `${row.number} will be permanently deleted.`,
                          confirmLabel: "Delete",
                        });
                        if (!ok) {
                          return;
                        }
                        await platformAdminApi.deleteInvoice(row.id);
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
      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>{editingId ? "Edit invoice" : "Create invoice"}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField select label="Tenant" value={form.tenant_id} disabled={Boolean(editingId)} onChange={(event) => setForm({ ...form, tenant_id: event.target.value })}>
              {tenants.map((tenant) => (
                <MenuItem key={tenant.id} value={tenant.id}>
                  {tenant.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField label="Description" value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} />
            <TextField label="Amount" value={form.amount} onChange={(event) => setForm({ ...form, amount: event.target.value })} />
            <TextField label="Notes" multiline minRows={2} value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={async () => {
              if (editingId) {
                await platformAdminApi.updateInvoice(editingId, { description: form.description, amount: form.amount, notes: form.notes });
              } else {
                await platformAdminApi.createInvoice(form);
              }
              setOpen(false);
              setForm(emptyForm);
              await load();
            }}
          >
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}
