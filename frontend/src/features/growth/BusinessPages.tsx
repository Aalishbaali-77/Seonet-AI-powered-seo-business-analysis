"use client";

import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { Download as DownloadIcon, History as HistoryIcon, Upload as UploadIcon } from "@mui/icons-material";
import { useEffect, useRef, useState, type RefObject } from "react";
import { useRouter } from "next/navigation";

import { MiniBarChart } from "@/components/charts/MiniCharts";
import { PageHeader } from "@/components/common/PageHeader";
import { PrintReportChrome } from "@/components/common/PrintReportChrome";
import { ResponsiveDataList } from "@/components/common/ResponsiveDataList";
import { RowMenu } from "@/components/common/RowMenu";
import { StatCard } from "@/components/common/StatCard";
import { StatusChip } from "@/components/common/StatusChip";
import { EmptyState } from "@/components/feedback/EmptyState";
import { ErrorState } from "@/components/feedback/ErrorState";
import { LoadingState } from "@/components/feedback/LoadingState";
import { useJobSession } from "@/features/websites/auditSession";
import { businessApi, type IntegrationItem } from "@/services/domainApi";
import { useAppSelector } from "@/store/hooks";
import type {
  BusinessProfile,
  CatalogProduct,
  CommerceAnalysis,
  CommerceCustomer,
  CommerceExpert,
  CommerceKpis,
  CommerceOrder,
  CommerceReview,
  ImportBatch,
} from "@/types/domain";
import { CommerceInsightPanels } from "@/features/growth/CommerceInsightPanels";

const TYPES = [
  { value: "ecommerce", label: "E-commerce" },
  { value: "retail", label: "Retail" },
  { value: "services", label: "Services" },
  { value: "b2b", label: "B2B" },
  { value: "manufacturing", label: "Manufacturing" },
];

export function BusinessOverviewPage() {
  const router = useRouter();
  const [profile, setProfile] = useState<BusinessProfile | null>(null);
  const [kpis, setKpis] = useState<CommerceKpis | null>(null);
  const [analysis, setAnalysis] = useState<CommerceAnalysis | null>(null);
  const [expert, setExpert] = useState<CommerceExpert | null>(null);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState("");

  const load = () =>
    businessApi
      .overview()
      .then((data) => {
        setProfile(data.profile);
        setKpis(data.kpis);
        setAnalysis(data.analysis);
        setExpert(data.expert);
        setError("");
      })
      .catch((err: Error) => setError(err.message));

  useEffect(() => {
    void load();
  }, []);

  if (!profile && !error) return <LoadingState />;

  return (
    <PrintReportChrome title="Business analysis">
      <Stack spacing={3}>
        <PageHeader
          title="Business analysis"
          description="Your workspace business — not invented revenue. Connect a store, or download a CSV template, fill it, and import. Lead generation stays a separate module."
        />
        {error ? (
          <ErrorState message={error} onRetry={() => void load()} />
        ) : null}
        {saved ? <Alert severity="success">{saved}</Alert> : null}
        {profile ? (
          <Card variant="outlined">
            <CardContent>
              <Stack spacing={2}>
                <Typography variant="h4">Business profile</Typography>
                <TextField
                  select
                  label="Business type"
                  value={profile.business_type}
                  onChange={(event) =>
                    setProfile({
                      ...profile,
                      business_type: event.target.value,
                    })
                  }
                >
                  {TYPES.map((item) => (
                    <MenuItem key={item.value} value={item.value}>
                      {item.label}
                    </MenuItem>
                  ))}
                </TextField>
                <TextField
                  label="Industry"
                  value={profile.industry}
                  onChange={(event) =>
                    setProfile({ ...profile, industry: event.target.value })
                  }
                />
                <TextField
                  label="Category"
                  value={profile.category}
                  onChange={(event) =>
                    setProfile({ ...profile, category: event.target.value })
                  }
                />
                <TextField
                  label="Current market"
                  value={profile.current_market}
                  onChange={(event) =>
                    setProfile({
                      ...profile,
                      current_market: event.target.value,
                    })
                  }
                />
                <TextField
                  label="Goal"
                  multiline
                  minRows={2}
                  value={profile.goal}
                  onChange={(event) =>
                    setProfile({ ...profile, goal: event.target.value })
                  }
                />
                <Button
                  variant="contained"
                  onClick={async () => {
                    try {
                      setProfile(await businessApi.saveProfile(profile));
                      setSaved("Profile saved.");
                      setError("");
                    } catch (err) {
                      setError(
                        err instanceof Error
                          ? err.message
                          : "Unable to save profile.",
                      );
                    }
                  }}
                >
                  Save profile
                </Button>
              </Stack>
            </CardContent>
          </Card>
        ) : null}
        {kpis ? (
          kpis.available ? (
            <>
              <Box
                sx={{
                  display: "grid",
                  gap: 2,
                  gridTemplateColumns: {
                    xs: "1fr",
                    sm: "1fr 1fr",
                    md: "repeat(4, minmax(0, 1fr))",
                  },
                }}
              >
                <StatCard label="Products" value={kpis.products} />
                <StatCard label="Customers" value={kpis.customers} />
                <StatCard label="Orders" value={kpis.orders} />
                <StatCard
                  label="Revenue"
                  value={kpis.revenue ?? "—"}
                  hint="From imported order lines only"
                />
              </Box>
              {analysis || expert ? (
                <CommerceInsightPanels analysis={analysis} expert={expert} />
              ) : null}
            </>
          ) : (
            <EmptyState
              title="No commerce KPIs yet"
              description={kpis.reason}
              actionLabel="Connect a store"
              onAction={() => router.push("/app/business/ecommerce")}
            />
          )
        ) : null}
      </Stack>
    </PrintReportChrome>
  );
}

function CsvImport({
  kind,
  onDone,
  inputRef,
}: {
  kind: "products" | "orders";
  onDone: () => void;
  inputRef?: RefObject<HTMLInputElement | null>;
}) {
  const { start, job } = useJobSession();
  const [startedId, setStartedId] = useState("");
  const [note, setNote] = useState("");
  const [failed, setFailed] = useState(false);
  const handled = useRef("");
  const onDoneRef = useRef(onDone);
  useEffect(() => {
    onDoneRef.current = onDone;
  });
  const hint =
    kind === "products"
      ? "Download the products template, fill your rows under the header, then import. Keep name, sku, category, unit_price, cost_price."
      : "Download the orders template, fill one row per line item, then import. Customers and cities come from those rows.";

  useEffect(() => {
    if (!startedId || job?.id !== startedId) {
      return;
    }
    const key = `${job.id}:${job.status}`;
    if (handled.current === key) {
      return;
    }
    if (job.status === "COMPLETED") {
      handled.current = key;
      // Reacting to external job-polling state, not a prop; setState here is unavoidable.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setFailed(false);
      const created = Number(job.result.created ?? 0);
      const skipped = Number(job.result.skipped ?? 0);
      const extra =
        kind === "orders" && job.result.opportunities_created
          ? ` ${job.result.opportunities_created} opportunities recorded from evidence.`
          : "";
      setNote(`${created} rows imported, ${skipped} skipped.${extra}`);
      onDoneRef.current();
    }
    if (job.status === "FAILED") {
      handled.current = key;
      setFailed(true);
      setNote(job.error || "Import failed.");
    }
  }, [job, kind, startedId]);

  return (
    <Stack
      spacing={1}
      sx={{
        alignItems: { xs: "stretch", sm: "flex-end" },
        maxWidth: { sm: 420 },
      }}
    >
      <Stack
        direction="row"
        spacing={1}
        sx={{ flexWrap: "wrap", justifyContent: { sm: "flex-end" } }}
      >
        <Button
          variant="outlined"
          startIcon={<DownloadIcon />}
          onClick={() =>
            void businessApi.downloadCsvTemplate(kind).catch((err: Error) => {
              setFailed(true);
              setNote(err.message);
            })
          }
        >
          Download template
        </Button>
        <Button component="label" variant="contained" startIcon={<UploadIcon />}>
          Import filled CSV
          <Box
            component="input"
            type="file"
            hidden
            accept=".csv,text/csv,.txt"
            ref={inputRef}
            onChange={async (event) => {
              const file = (event.target as HTMLInputElement).files?.[0];
              (event.target as HTMLInputElement).value = "";
              if (!file) return;
              try {
                const created = await businessApi.importCsv(kind, file);
                setFailed(false);
                setNote("");
                setStartedId(created.id);
                start({
                  jobId: created.id,
                  kind: "import_commerce",
                  title: kind === "products" ? "Products CSV" : "Orders CSV",
                  href:
                    kind === "products"
                      ? "/app/business/products"
                      : "/app/business/sales",
                });
              } catch (err) {
                setFailed(true);
                setNote(err instanceof Error ? err.message : "Import failed.");
              }
            }}
          />
        </Button>
      </Stack>
      <Typography
        variant="caption"
        color="text.secondary"
        sx={{ textAlign: { sm: "right" } }}
      >
        {hint}
      </Typography>
      {note ? (
        <Alert severity={failed ? "error" : "success"}>{note}</Alert>
      ) : null}
    </Stack>
  );
}

function ImportHistoryDialog({
  open,
  onClose,
  onStartImport,
}: {
  open: boolean;
  onClose: () => void;
  onStartImport: () => void;
}) {
  const [batches, setBatches] = useState<ImportBatch[] | null>(null);
  const [error, setError] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<ImportBatch | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState("");

  const load = () => {
    void businessApi
      .imports()
      .then((data) => {
        setBatches(data.results);
        setError("");
      })
      .catch((err: Error) => setError(err.message));
  };

  useEffect(() => {
    if (open) {
      // Resetting local state alongside a network fetch triggered by `open`; can't be derived purely at render time.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setBatches(null);
      setExpandedId(null);
      setDeleteTarget(null);
      setDeleteError("");
      load();
    }
  }, [open]);

  const closeDeleteDialog = () => {
    if (deleting) return;
    setDeleteTarget(null);
    setDeleteError("");
  };

  const handleDelete = async (mode: "log_only" | "log_and_rows") => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await businessApi.deleteImportBatch(deleteTarget.id, mode);
      setDeleteTarget(null);
      setDeleteError("");
      load();
    } catch (err) {
      setDeleteError(
        err instanceof Error ? err.message : "Unable to delete this import.",
      );
    } finally {
      setDeleting(false);
    }
  };

  return (
    <>
      <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
        <DialogTitle>Import history</DialogTitle>
        <DialogContent>
          {error ? (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          ) : null}
          {batches === null ? (
            <LoadingState />
          ) : batches.length === 0 ? (
            <EmptyState
              title="No imports yet"
              description="Once you import an orders CSV, each import is tracked here — file name, rows imported, and status."
              actionLabel="Import a CSV"
              onAction={() => {
                onClose();
                onStartImport();
              }}
            />
          ) : (
            <Stack spacing={1}>
              {batches.map((batch) => (
                <Card key={batch.id} variant="outlined">
                  <CardContent
                    sx={{
                      display: "flex",
                      alignItems: "flex-start",
                      justifyContent: "space-between",
                      gap: 1.5,
                      "&:last-child": { pb: 2 },
                    }}
                  >
                    <Box sx={{ minWidth: 0, flex: 1 }}>
                      <Typography noWrap fontWeight={600}>
                        {batch.file_name || "Untitled file"}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {batch.rows_imported}/{batch.rows_total} rows imported ·{" "}
                        {new Date(batch.created_at).toLocaleString()}
                      </Typography>
                      {expandedId === batch.id ? (
                        <Box
                          sx={{
                            mt: 1,
                            p: 1.5,
                            bgcolor: "action.hover",
                            borderRadius: 1,
                          }}
                        >
                          <Typography variant="body2">
                            Kind: {batch.kind}
                          </Typography>
                          <Typography variant="body2">
                            Status: {batch.status}
                          </Typography>
                          <Typography variant="body2">
                            Rows imported: {batch.rows_imported} of{" "}
                            {batch.rows_total}
                          </Typography>
                          <Typography variant="body2">
                            Imported:{" "}
                            {new Date(batch.created_at).toLocaleString()}
                          </Typography>
                        </Box>
                      ) : null}
                    </Box>
                    <Stack
                      direction="row"
                      spacing={1}
                      sx={{ alignItems: "center", flexShrink: 0 }}
                    >
                      <StatusChip value={batch.status} />
                      <RowMenu
                        label="Import actions"
                        items={[
                          {
                            label:
                              expandedId === batch.id ? "Hide details" : "View",
                            onClick: () =>
                              setExpandedId(
                                expandedId === batch.id ? null : batch.id,
                              ),
                          },
                          {
                            label: "Download",
                            onClick: () => {},
                            disabled: true,
                          },
                          {
                            label: "Delete",
                            danger: true,
                            onClick: () => {
                              setDeleteTarget(batch);
                              setDeleteError("");
                            },
                          },
                        ]}
                      />
                    </Stack>
                  </CardContent>
                </Card>
              ))}
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Close</Button>
        </DialogActions>
      </Dialog>

      <Dialog
        open={Boolean(deleteTarget)}
        onClose={closeDeleteDialog}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle>Remove this import?</DialogTitle>
        <DialogContent>
          <Typography sx={{ mb: 1 }}>
            &ldquo;{deleteTarget?.file_name || "This import"}&rdquo; imported{" "}
            {deleteTarget?.rows_imported ?? 0} row
            {deleteTarget?.rows_imported === 1 ? "" : "s"}.
          </Typography>
          <Typography color="text.secondary" sx={{ mb: 2 }}>
            Choose what to remove. This cannot be undone.
          </Typography>
          {deleteError ? (
            <Alert severity="error" sx={{ mb: 2 }}>
              {deleteError}
            </Alert>
          ) : null}
        </DialogContent>
        <DialogActions
          sx={{
            flexDirection: "column",
            alignItems: "stretch",
            gap: 1,
            px: 3,
            pb: 3,
          }}
        >
          <Button
            variant="outlined"
            disabled={deleting}
            onClick={() => void handleDelete("log_only")}
          >
            Remove history record only
          </Button>
          <Button
            variant="contained"
            color="error"
            disabled={deleting}
            onClick={() => void handleDelete("log_and_rows")}
          >
            Remove import and its rows
          </Button>
          <Button disabled={deleting} onClick={closeDeleteDialog}>
            Cancel
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}

export function BusinessProductsPage() {
  const router = useRouter();
  const [rows, setRows] = useState<CatalogProduct[]>([]);
  const [analysis, setAnalysis] = useState<CommerceAnalysis | null>(null);
  const [error, setError] = useState("");
  const load = () =>
    Promise.all([businessApi.products(), businessApi.overview()])
      .then(([data, overview]) => {
        setRows(data.results);
        setAnalysis(overview.analysis);
        setError("");
      })
      .catch((err: Error) => setError(err.message));
  useEffect(() => {
    void load();
  }, []);
  return (
    <Stack spacing={3}>
      <PageHeader
        title="Products"
        description="Download the products template, fill your catalog, then import — or sync a store. Rankings use stored order lines only."
        actions={<CsvImport kind="products" onDone={() => void load()} />}
      />
      {error ? (
        <ErrorState message={error} onRetry={() => void load()} />
      ) : null}
      <CommerceInsightPanels analysis={analysis} sections={["products"]} />
      {rows.length ? (
        <ResponsiveDataList
          rows={rows}
          cardTitle={(row) => row.name}
          columns={[
            { key: "name", label: "Product", render: (row) => row.name },
            { key: "sku", label: "SKU", render: (row) => row.sku || "—" },
            {
              key: "category",
              label: "Category",
              render: (row) => row.category || "—",
            },
            {
              key: "price",
              label: "Price",
              render: (row) => row.unit_price || "—",
            },
            {
              key: "origin",
              label: "Source",
              render: (row) => `${row.source} · ${row.verification_status}`,
            },
          ]}
        />
      ) : (
        <EmptyState
          title="No products"
          description="Download the products CSV template, fill it, then import — or sync a store."
          actionLabel="Open e-commerce"
          onAction={() => router.push("/app/business/ecommerce")}
        />
      )}
    </Stack>
  );
}

export function BusinessCustomersPage() {
  const router = useRouter();
  const [rows, setRows] = useState<CommerceCustomer[]>([]);
  const [note, setNote] = useState("");
  const [failed, setFailed] = useState(false);
  const permissions = useAppSelector(
    (state) => state.auth.user?.permissions ?? [],
  );
  const canManage = permissions.includes("business.manage");
  const load = () =>
    void businessApi.customers().then((data) => setRows(data.results));
  useEffect(() => {
    load();
  }, []);
  return (
    <Stack spacing={3}>
      <PageHeader
        title="Customers"
        description="First-party buyers from an orders CSV or a store sync. Download the orders template on Sales, fill customer_name and city, then import. These are existing buyers, not discovered prospects."
        actions={
          canManage && rows.length ? (
            <Button
              variant="outlined"
              onClick={async () => {
                try {
                  const result = await businessApi.promoteCustomers();
                  setFailed(false);
                  setNote(
                    `${result.created} buyers copied into Leads, ${result.skipped} already there.`,
                  );
                } catch (err) {
                  setFailed(true);
                  setNote(
                    err instanceof Error
                      ? err.message
                      : "Unable to copy buyers into Leads.",
                  );
                }
              }}
            >
              Copy buyers into Leads
            </Button>
          ) : undefined
        }
      />
      {note ? (
        <Alert severity={failed ? "error" : "success"}>{note}</Alert>
      ) : null}
      {rows.length ? (
        <ResponsiveDataList
          rows={rows}
          cardTitle={(row) => row.name}
          columns={[
            { key: "name", label: "Customer", render: (row) => row.name },
            { key: "city", label: "City", render: (row) => row.city || "—" },
            { key: "email", label: "Email", render: (row) => row.email || "—" },
            { key: "source", label: "Source", render: (row) => row.source },
          ]}
        />
      ) : (
        <EmptyState
          title="No customers"
          description="Download the orders template on Sales, fill customer_name, then import — or sync a store."
          actionLabel="Open sales"
          onAction={() => router.push("/app/business/sales")}
        />
      )}
    </Stack>
  );
}

const ORDER_STATUS_OPTIONS = [
  { value: "placed", label: "Placed" },
  { value: "cancelled", label: "Cancelled" },
  { value: "returned", label: "Returned" },
  { value: "refunded", label: "Refunded" },
];

function toDatetimeLocal(value: string | null): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function OrderViewDialog({ orderId, onClose }: { orderId: string | null; onClose: () => void }) {
  const [order, setOrder] = useState<CommerceOrder | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!orderId) {
      // Resetting local state alongside a network fetch triggered by `orderId`; can't be derived purely at render time.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setOrder(null);
      setError("");
      return;
    }
    void businessApi
      .orderDetail(orderId)
      .then((data) => {
        setOrder(data);
        setError("");
      })
      .catch((err: Error) => setError(err.message));
  }, [orderId]);

  return (
    <Dialog open={Boolean(orderId)} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>Order detail</DialogTitle>
      <DialogContent>
        {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}
        {!order && !error ? <LoadingState /> : null}
        {order ? (
          <Stack spacing={2}>
            <Box sx={{ display: "grid", gap: 1.5, gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" } }}>
              <Typography variant="body2"><strong>Order:</strong> {order.external_id || order.id.slice(0, 8)}</Typography>
              <Typography variant="body2"><strong>Status:</strong> {order.status}</Typography>
              <Typography variant="body2"><strong>Customer:</strong> {order.customer_name || "—"}</Typography>
              <Typography variant="body2"><strong>City:</strong> {order.city || "—"}</Typography>
              <Typography variant="body2"><strong>Channel:</strong> {order.channel || "—"}</Typography>
              <Typography variant="body2"><strong>Currency:</strong> {order.currency}</Typography>
              <Typography variant="body2"><strong>Source:</strong> {order.source}</Typography>
              <Typography variant="body2"><strong>Ordered at:</strong> {order.ordered_at ? new Date(order.ordered_at).toLocaleString() : "—"}</Typography>
            </Box>
            <Typography variant="h4">Line items</Typography>
            {order.items.length ? (
              <ResponsiveDataList
                rows={order.items}
                cardTitle={(item) => item.name || item.sku}
                columns={[
                  { key: "sku", label: "SKU", render: (item) => item.sku || "—" },
                  { key: "name", label: "Product", render: (item) => item.name || "—" },
                  { key: "quantity", label: "Qty", render: (item) => item.quantity },
                  { key: "unit_price", label: "Unit price", render: (item) => item.unit_price },
                  { key: "discount", label: "Discount", render: (item) => item.discount },
                  { key: "cost", label: "Cost", render: (item) => item.cost ?? "—" },
                ]}
              />
            ) : (
              <Typography color="text.secondary">No line items on this order.</Typography>
            )}
          </Stack>
        ) : null}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
}

function OrderEditDialog({ order, onClose, onSaved }: { order: CommerceOrder | null; onClose: () => void; onSaved: () => void }) {
  return (
    <OrderEditDialogInner
      key={order?.id ?? "none"}
      order={order}
      onClose={onClose}
      onSaved={onSaved}
    />
  );
}

function OrderEditDialogInner({ order, onClose, onSaved }: { order: CommerceOrder | null; onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState(() =>
    order
      ? {
          ordered_at: toDatetimeLocal(order.ordered_at),
          city: order.city,
          channel: order.channel,
          status: order.status,
          currency: order.currency,
        }
      : { ordered_at: "", city: "", channel: "", status: "placed", currency: "" },
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  return (
    <Dialog open={Boolean(order)} onClose={() => (saving ? null : onClose())} fullWidth maxWidth="xs">
      <DialogTitle>Edit order {order?.external_id || order?.id.slice(0, 8)}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 1 }}>
          {error ? <Alert severity="error">{error}</Alert> : null}
          <TextField
            type="datetime-local"
            label="Ordered at"
            value={form.ordered_at}
            onChange={(event) => setForm({ ...form, ordered_at: event.target.value })}
            slotProps={{ inputLabel: { shrink: true } }}
          />
          <TextField label="City" value={form.city} onChange={(event) => setForm({ ...form, city: event.target.value })} />
          <TextField label="Channel" value={form.channel} onChange={(event) => setForm({ ...form, channel: event.target.value })} />
          <TextField select label="Status" value={form.status} onChange={(event) => setForm({ ...form, status: event.target.value })}>
            {ORDER_STATUS_OPTIONS.map((option) => (
              <MenuItem key={option.value} value={option.value}>
                {option.label}
              </MenuItem>
            ))}
          </TextField>
          <TextField label="Currency" value={form.currency} onChange={(event) => setForm({ ...form, currency: event.target.value })} />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button disabled={saving} onClick={onClose}>
          Cancel
        </Button>
        <Button
          variant="contained"
          disabled={saving || !order}
          onClick={async () => {
            if (!order) return;
            setSaving(true);
            try {
              await businessApi.updateOrder(order.id, {
                ordered_at: form.ordered_at ? new Date(form.ordered_at).toISOString() : null,
                city: form.city,
                channel: form.channel,
                status: form.status,
                currency: form.currency,
              });
              onSaved();
              onClose();
            } catch (err) {
              setError(err instanceof Error ? err.message : "Unable to save this order.");
            } finally {
              setSaving(false);
            }
          }}
        >
          Save
        </Button>
      </DialogActions>
    </Dialog>
  );
}

export function BusinessSalesPage() {
  const [kpis, setKpis] = useState<CommerceKpis | null>(null);
  const [orders, setOrders] = useState<CommerceOrder[]>([]);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [viewOrderId, setViewOrderId] = useState<string | null>(null);
  const [editOrder, setEditOrder] = useState<CommerceOrder | null>(null);
  const importInputRef = useRef<HTMLInputElement>(null);
  const load = () => {
    void businessApi.overview().then((data) => setKpis(data.kpis));
    void businessApi.orders().then((data) => setOrders(data.results));
  };
  useEffect(() => {
    load();
  }, []);
  return (
    <Stack spacing={3}>
      <PageHeader
        title="Sales"
        description="Download the orders template, fill one row per line item, then import — or sync a store. After import, analysis records opportunities from stored evidence."
        actions={
          <Stack
            direction="row"
            spacing={1}
            sx={{
              flexWrap: "wrap",
              justifyContent: { sm: "flex-end" },
              alignItems: "flex-start",
            }}
          >
            <Button
              variant="outlined"
              size="medium"
              sx={{ height: 36 }}
              startIcon={<HistoryIcon />}
              onClick={() => setHistoryOpen(true)}
            >
              Import history
            </Button>
            <CsvImport kind="orders" onDone={load} inputRef={importInputRef} />
          </Stack>
        }
      />
      {kpis && !kpis.available ? (
        <EmptyState title="No orders imported" description={kpis.reason} />
      ) : null}
      {kpis?.available ? (
        <Box
          sx={{
            display: "grid",
            gap: 2,
            gridTemplateColumns: { xs: "1fr", md: "repeat(3, 1fr)" },
          }}
        >
          <StatCard label="Orders" value={kpis.orders} />
          <StatCard label="Revenue" value={kpis.revenue ?? "—"} />
          <StatCard
            label="Average order"
            value={kpis.average_order_value ?? "—"}
          />
        </Box>
      ) : null}
      {orders.length ? (
        <ResponsiveDataList
          rows={orders}
          cardTitle={(row) => row.external_id || row.id}
          columns={[
            {
              key: "id",
              label: "Order",
              render: (row) => row.external_id || row.id.slice(0, 8),
            },
            {
              key: "customer",
              label: "Customer",
              render: (row) => row.customer_name || "—",
            },
            { key: "city", label: "City", render: (row) => row.city || "—" },
            {
              key: "channel",
              label: "Channel",
              render: (row) => row.channel || "—",
            },
            { key: "status", label: "Status", render: (row) => row.status },
            {
              key: "actions",
              label: "Actions",
              render: (row) => (
                <RowMenu
                  label={`Actions for order ${row.external_id || row.id.slice(0, 8)}`}
                  items={[
                    { label: "View", onClick: () => setViewOrderId(row.id) },
                    { label: "Edit", onClick: () => setEditOrder(row) },
                  ]}
                />
              ),
            },
          ]}
        />
      ) : null}
      <ImportHistoryDialog
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        onStartImport={() => importInputRef.current?.click()}
      />
      <OrderViewDialog orderId={viewOrderId} onClose={() => setViewOrderId(null)} />
      <OrderEditDialog order={editOrder} onClose={() => setEditOrder(null)} onSaved={load} />
    </Stack>
  );
}

export function BusinessAwaitingPage({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  const router = useRouter();
  return (
    <Stack spacing={3}>
      <PageHeader title={title} description={description} />
      <EmptyState
        title="Needs imported commerce data"
        description="This view only renders when this workspace has imported orders. No sample cities, margins, or conversion rates are shown."
        actionLabel="Open sales import"
        onAction={() => router.push("/app/business/sales")}
      />
    </Stack>
  );
}

export function BusinessGeographyPage() {
  const router = useRouter();
  const [kpis, setKpis] = useState<CommerceKpis | null>(null);
  const [analysis, setAnalysis] = useState<CommerceAnalysis | null>(null);
  useEffect(() => {
    void businessApi.overview().then((data) => {
      setKpis(data.kpis);
      setAnalysis(data.analysis);
    });
  }, []);
  return (
    <PrintReportChrome title="Geographic sales">
      <Stack spacing={3}>
        <PageHeader
          title="Geographic sales"
          description="Served cities come from stored order.city values. Expansion cities appear only with evidence — never as an invented league table."
        />
        {!kpis ? <LoadingState /> : null}
        {kpis && !kpis.available ? (
          <EmptyState
            title="Needs imported commerce data"
            description={kpis.reason}
            actionLabel="Open e-commerce"
            onAction={() => router.push("/app/business/ecommerce")}
          />
        ) : null}
        <CommerceInsightPanels
          analysis={analysis}
          sections={["demand", "actions"]}
        />
      </Stack>
    </PrintReportChrome>
  );
}

export function BusinessEcommercePage() {
  const permissions = useAppSelector(
    (state) => state.auth.user?.permissions ?? [],
  );
  const canManage = permissions.includes("business.manage");
  const { start, job } = useJobSession();
  const seenSync = useRef("");
  const [kpis, setKpis] = useState<CommerceKpis | null>(null);
  const [analysis, setAnalysis] = useState<CommerceAnalysis | null>(null);
  const [expert, setExpert] = useState<CommerceExpert | null>(null);
  const [stores, setStores] = useState<IntegrationItem[]>([]);
  const [reviews, setReviews] = useState<CommerceReview[]>([]);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState<IntegrationItem | null>(null);
  const [draft, setDraft] = useState<Record<string, string>>({});

  const load = () =>
    Promise.all([
      businessApi.overview(),
      businessApi.stores(),
      businessApi.reviews(),
    ])
      .then(([overview, storePayload, reviewPayload]) => {
        setKpis(overview.kpis);
        setAnalysis(overview.analysis);
        setExpert(overview.expert);
        setStores(storePayload.items);
        setReviews(reviewPayload.results ?? []);
        setError("");
      })
      .catch((err: Error) => setError(err.message));

  useEffect(() => {
    void load();
  }, []);

  useEffect(() => {
    if (
      job?.job_type !== "sync_commerce" &&
      job?.job_type !== "analyze_business" &&
      job?.job_type !== "import_commerce"
    ) {
      return;
    }
    const key = `${job.id}:${job.status}`;
    if (seenSync.current === key) {
      return;
    }
    if (job.status === "COMPLETED") {
      seenSync.current = key;
      void load();
      if (job.job_type === "sync_commerce") {
        const counts = job.result || {};
        // Reacting to external job-polling state, not a prop; setState here is unavoidable.
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setNote(
          `Synced ${counts.products ?? 0} products, ${counts.orders ?? 0} orders, ${counts.reviews ?? 0} reviews. Analysis ran${
            counts.opportunities_created
              ? `; ${counts.opportunities_created} opportunities recorded from evidence`
              : ""
          }.`,
        );
      }
      if (job.job_type === "analyze_business") {
        const created = Number(job.result.opportunities_created ?? 0);
        setNote(
          created
            ? `Analysis complete. ${created} opportunities recorded from evidence.`
            : "Analysis complete from stored orders.",
        );
      }
    }
    if (job.status === "FAILED") {
      seenSync.current = key;
      setError(job.error || "Store sync failed.");
    }
  }, [job]);

  const rows = (kpis?.by_channel ?? []).map((row) => ({
    id: row.channel,
    ...row,
  }));
  const sentiment = kpis?.reviews;

  return (
    <PrintReportChrome title="E-commerce analysis">
      <Stack spacing={3}>
        <PageHeader
          title="E-commerce"
          description="Connect a store, test, then sync — or download a CSV template, fill it, and import. SIPulse then analyzes served markets, product mix, and expansion evidence from stored rows — not invented demand grades."
          actions={
            canManage ? (
              <Button
                variant="outlined"
                disabled={busy}
                onClick={async () => {
                  setBusy(true);
                  try {
                    const created = await businessApi.analyze();
                    start({
                      jobId: created.id,
                      kind: "analyze_business",
                      title: "Business analysis",
                      href: "/app/business/ecommerce",
                    });
                  } catch (err) {
                    setError(
                      err instanceof Error ? err.message : "Unable to analyze.",
                    );
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                Run business analysis
              </Button>
            ) : undefined
          }
        />
        {error ? (
          <ErrorState message={error} onRetry={() => void load()} />
        ) : null}
        {note ? <Alert severity="info">{note}</Alert> : null}
        <Box
          sx={{
            display: "grid",
            gap: 2,
            gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" },
          }}
        >
          {stores.map((item) => (
            <Card key={item.code} variant="outlined">
              <CardContent>
                <Stack spacing={1.25}>
                  <Stack
                    direction="row"
                    spacing={1}
                    sx={{
                      justifyContent: "space-between",
                      alignItems: "flex-start",
                    }}
                  >
                    <Typography variant="h4">{item.name}</Typography>
                    <StatusChip value={item.status} />
                  </Stack>
                  <Typography color="text.secondary">
                    {item.description}
                  </Typography>
                  {item.last_sync_at ? (
                    <Typography variant="body2" color="text.secondary">
                      Last sync{" "}
                      {item.last_sync_at.slice(0, 16).replace("T", " ")}
                      {item.records_synced
                        ? ` · ${item.records_synced} rows stored`
                        : ""}
                    </Typography>
                  ) : null}
                  {item.last_error ? (
                    <Alert severity="error">{item.last_error}</Alert>
                  ) : null}
                  {canManage ? (
                    <Stack
                      direction="row"
                      spacing={1}
                      sx={{ flexWrap: "wrap", gap: 1 }}
                    >
                      <Button
                        variant="contained"
                        disabled={busy}
                        onClick={() => {
                          setEditing(item);
                          const next: Record<string, string> = {};
                          item.fields.forEach((field) => {
                            next[field.key] = field.secret
                              ? ""
                              : String(item.config[field.key] ?? "");
                          });
                          setDraft(next);
                        }}
                      >
                        {item.credentials_configured ? "Update" : "Connect"}
                      </Button>
                      {item.credentials_configured ? (
                        <Button
                          disabled={busy}
                          onClick={() => void act(item, "test")}
                        >
                          Test
                        </Button>
                      ) : null}
                      {item.credentials_configured ? (
                        <Button
                          disabled={busy}
                          onClick={() => void act(item, "sync")}
                        >
                          Sync store
                        </Button>
                      ) : null}
                      {item.credentials_configured ? (
                        <Button
                          color="error"
                          disabled={busy}
                          onClick={() => void act(item, "disconnect")}
                        >
                          Disconnect
                        </Button>
                      ) : null}
                    </Stack>
                  ) : null}
                </Stack>
              </CardContent>
            </Card>
          ))}
        </Box>
        <Card variant="outlined">
          <CardContent>
            <Stack spacing={2}>
              <Typography variant="h4">CSV import</Typography>
              <Typography color="text.secondary">
                Download a template, fill your real rows, then import the filled
                file. Keep the header names. Customers come from the orders
                file.
              </Typography>
              <Box
                sx={{
                  display: "grid",
                  gap: 2,
                  gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
                }}
              >
                <CsvImport kind="products" onDone={() => void load()} />
                <CsvImport kind="orders" onDone={() => void load()} />
              </Box>
            </Stack>
          </CardContent>
        </Card>
        {!kpis ? <LoadingState /> : null}
        {kpis?.available ? (
          <Box
            sx={{
              display: "grid",
              gap: 2,
              gridTemplateColumns: {
                xs: "1fr",
                sm: "1fr 1fr",
                md: "repeat(4, minmax(0, 1fr))",
              },
            }}
          >
            <StatCard label="Orders" value={kpis.orders} />
            <StatCard
              label="Revenue"
              value={kpis.revenue ?? "—"}
              hint="From stored order lines only"
            />
            <StatCard label="Reviews" value={sentiment?.count ?? 0} />
            <StatCard
              label="Avg rating"
              value={sentiment?.average_rating ?? "—"}
              hint="From fetched reviews"
            />
          </Box>
        ) : kpis ? (
          <EmptyState
            title="No store or CSV orders yet"
            description="Connect a store above, or download the orders template, fill it, and import."
          />
        ) : null}
        {sentiment && sentiment.count > 0 ? (
          <Card variant="outlined">
            <CardContent>
              <Typography variant="h4" sx={{ mb: 1.5 }}>
                Review sentiment
              </Typography>
              <MiniBarChart
                items={[
                  { label: "Positive", value: sentiment.positive },
                  { label: "Neutral", value: sentiment.neutral },
                  { label: "Negative", value: sentiment.negative },
                ]}
              />
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                FACT: 4–5 stars positive, 3 mixed, 1–2 negative. WooCommerce and
                Etsy sync reviews. Shopify and eBay do not in this release.
              </Typography>
            </CardContent>
          </Card>
        ) : sentiment?.reason ? (
          <Alert severity="info">{sentiment.reason}</Alert>
        ) : null}
        {expert?.recommendation || expert?.inference || analysis?.available ? (
          <CommerceInsightPanels analysis={analysis} expert={expert} />
        ) : null}
        {rows.length ? (
          <ResponsiveDataList
            rows={rows}
            cardTitle={(row) => row.channel}
            columns={[
              {
                key: "channel",
                label: "Channel",
                render: (row) => row.channel,
              },
              { key: "orders", label: "Orders", render: (row) => row.orders },
            ]}
          />
        ) : null}
        {reviews.length ? (
          <ResponsiveDataList
            rows={reviews}
            cardTitle={(row) => row.product_name || row.reviewer || row.source}
            columns={[
              {
                key: "product",
                label: "Product",
                render: (row) => row.product_name || "—",
              },
              {
                key: "rating",
                label: "Rating",
                render: (row) => row.rating ?? "—",
              },
              {
                key: "sentiment",
                label: "Sentiment",
                render: (row) => row.sentiment || "—",
              },
              { key: "source", label: "Source", render: (row) => row.source },
            ]}
          />
        ) : null}
        <Dialog
          open={Boolean(editing)}
          onClose={() => setEditing(null)}
          fullWidth
          maxWidth="md"
        >
          {editing ? (
            <>
              <DialogTitle>Connect {editing.name}</DialogTitle>
              <DialogContent>
                <Stack spacing={2} sx={{ mt: 1 }}>
                  {editing.setup_steps?.length ? (
                    <Box component="ol" sx={{ pl: 2.5, m: 0 }}>
                      {editing.setup_steps.map((step) => (
                        <Typography
                          key={step}
                          component="li"
                          variant="body2"
                          color="text.secondary"
                          sx={{ mb: 1 }}
                        >
                          {step}
                        </Typography>
                      ))}
                    </Box>
                  ) : null}
                  {editing.fields.map((field) => (
                    <TextField
                      key={field.key}
                      label={field.label}
                      type={field.input === "password" ? "password" : "text"}
                      value={draft[field.key] ?? ""}
                      onChange={(event) =>
                        setDraft({ ...draft, [field.key]: event.target.value })
                      }
                      helperText={
                        field.secret
                          ? [
                              field.help,
                              "Write-only. Never returned to the browser.",
                            ]
                              .filter(Boolean)
                              .join(" ")
                          : field.help
                      }
                    />
                  ))}
                </Stack>
              </DialogContent>
              <DialogActions>
                <Button onClick={() => setEditing(null)}>Cancel</Button>
                <Button
                  variant="contained"
                  disabled={busy}
                  onClick={async () => {
                    if (!editing) return;
                    setBusy(true);
                    try {
                      const payload: Record<string, unknown> = {};
                      editing.fields.forEach((field) => {
                        const value = draft[field.key];
                        if (field.secret && !value) return;
                        payload[field.key] = value;
                      });
                      await businessApi.saveStore(editing.code, payload);
                      setEditing(null);
                      setNote(
                        `${editing.name} credentials saved. Test, then Sync store.`,
                      );
                      await load();
                    } catch (err) {
                      setError(
                        err instanceof Error
                          ? err.message
                          : "Unable to save store.",
                      );
                    } finally {
                      setBusy(false);
                    }
                  }}
                >
                  Save
                </Button>
              </DialogActions>
            </>
          ) : null}
        </Dialog>
      </Stack>
    </PrintReportChrome>
  );

  async function act(
    item: IntegrationItem,
    action: "test" | "sync" | "disconnect",
  ) {
    setBusy(true);
    try {
      if (action === "test") {
        await businessApi.testStore(item.code);
        setNote(`${item.name} connection succeeded.`);
      } else if (action === "disconnect") {
        await businessApi.disconnectStore(item.code);
        setNote(`${item.name} disconnected.`);
      } else {
        const created = await businessApi.syncStore(item.code);
        start({
          jobId: created.id,
          kind: "sync_commerce",
          title: `${item.name} sync`,
          href: "/app/business/ecommerce",
        });
        setNote(`${item.name} sync started.`);
        return;
      }
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Store action failed.");
    } finally {
      setBusy(false);
    }
  }
}