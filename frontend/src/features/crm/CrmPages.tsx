"use client";

import { Alert, Button, Card, CardContent, Chip, MenuItem, Paper, Stack, TextField, Typography } from "@mui/material";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { MiniBarChart } from "@/components/charts/MiniCharts";
import { useConfirm } from "@/components/common/ConfirmDialog";
import { PageHeader } from "@/components/common/PageHeader";
import { ResponsiveDataList } from "@/components/common/ResponsiveDataList";
import { EmptyState } from "@/components/feedback/EmptyState";
import { ErrorState } from "@/components/feedback/ErrorState";
import { LoadingState } from "@/components/feedback/LoadingState";
import { crmApi } from "@/services/domainApi";
import type { Activity, Company, Contact, CrmAssignee, Deal, Pipeline } from "@/types/domain";

function money(amount: string, currency = "PKR") {
  return `${currency} ${amount}`;
}

function asError(err: unknown, fallback: string) {
  return err instanceof Error ? err.message : fallback;
}

export function CrmKanbanPage() {
  const router = useRouter();
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [pipelineId, setPipelineId] = useState("");
  const [deals, setDeals] = useState<Deal[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [assignees, setAssignees] = useState<CrmAssignee[]>([]);
  const [funnel, setFunnel] = useState<{ why: string; stages: Array<{ name: string; deals: number; amount: string }> } | null>(null);
  const [search, setSearch] = useState("");
  const [ownerFilter, setOwnerFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [closeAfter, setCloseAfter] = useState("");
  const [closeBefore, setCloseBefore] = useState("");
  const [creating, setCreating] = useState(false);
  const [closing, setClosing] = useState<{ deal: Deal; stageId: string; name: string; won: boolean } | null>(null);
  const [closeReason, setCloseReason] = useState("");
  const [form, setForm] = useState({
    name: "",
    amount: "0",
    currency: "PKR",
    company: "",
    contact: "",
    stage: "",
    owner: "",
    expected_close_at: "",
    priority: "normal",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const pipeline = pipelines.find((item) => item.id === pipelineId) ?? pipelines.find((item) => item.is_default) ?? pipelines[0] ?? null;

  const load = async (selected?: string) => {
    const next = selected || pipelineId;
    const dealParams: Record<string, string> = {};
    if (next) dealParams.pipeline = next;
    if (ownerFilter) dealParams.owner = ownerFilter;
    if (priorityFilter) dealParams.priority = priorityFilter;
    if (search.trim()) dealParams.search = search.trim();
    if (closeAfter) dealParams.expected_close_after = closeAfter;
    if (closeBefore) dealParams.expected_close_before = closeBefore;
    const [pipelineRows, dealRows, companyRows, contactRows, assigneeRows] = await Promise.all([
      crmApi.pipelines(),
      crmApi.dealsAll(dealParams),
      crmApi.companiesAll(),
      crmApi.contactsAll(),
      crmApi.assignees(),
    ]);
    const chosen = next || pipelineRows.find((item) => item.is_default)?.id || pipelineRows[0]?.id || "";
    setPipelines(pipelineRows);
    setPipelineId(chosen);
    setDeals(dealRows);
    setCompanies(companyRows);
    setContacts(contactRows);
    setAssignees(assigneeRows);
    const funnelData = await crmApi.funnel(chosen ? { pipeline: chosen } : undefined);
    setFunnel({ why: funnelData.why, stages: funnelData.stages });
    setForm((current) => ({
      ...current,
      stage: current.stage || pipelineRows.find((item) => item.id === chosen)?.stages[0]?.id || "",
    }));
  };

  useEffect(() => {
    void load()
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingState />;
  if (error && !pipeline) return <ErrorState message={error} onRetry={() => void load().catch((err: Error) => setError(err.message))} />;
  if (!pipeline) {
    return <EmptyState title="CRM pipeline" description="A default sales pipeline is created with your workspace." />;
  }

  const move = async (deal: Deal, stageId: string) => {
    const stage = pipeline.stages.find((item) => item.id === stageId);
    if (stage && (stage.is_won || stage.is_lost) && deal.stage !== stageId) {
      setClosing({ deal, stageId, name: stage.name, won: Boolean(stage.is_won) });
      setCloseReason(stage.is_won ? deal.won_reason || "" : deal.lost_reason || "");
      return;
    }
    try {
      await crmApi.updateDeal(deal.id, { stage: stageId });
      await load(pipeline.id);
    } catch (err) {
      setError(asError(err, "Unable to move deal."));
    }
  };

  const createDeal = async () => {
    if (!form.name.trim() || !form.company || !form.stage) return;
    try {
      await crmApi.createDeal({
        pipeline: pipeline.id,
        stage: form.stage,
        company: form.company,
        name: form.name.trim(),
        amount: form.amount || "0",
        currency: form.currency || "PKR",
        ...(form.contact ? { contact: form.contact } : {}),
        ...(form.owner ? { owner: form.owner } : {}),
        ...(form.expected_close_at ? { expected_close_at: form.expected_close_at } : {}),
        priority: form.priority || "normal",
      });
      setForm({ name: "", amount: "0", currency: form.currency, company: form.company, contact: "", stage: form.stage, owner: form.owner, expected_close_at: "", priority: form.priority });
      setCreating(false);
      await load(pipeline.id);
    } catch (err) {
      setError(asError(err, "Unable to create deal."));
    }
  };

  return (
    <Stack spacing={3}>
      <PageHeader
        title="Deals"
        description={`${pipeline.name}. Stage changes call the deal API and can emit deal.updated webhooks. Amounts are stored values, not a forecast.`}
        actions={
          <Button variant="contained" onClick={() => setCreating((open) => !open)}>
            {creating ? "Cancel" : "New deal"}
          </Button>
        }
      />
      {error ? <Alert severity="error">{error}</Alert> : null}
      <Stack direction={{ xs: "column", md: "row" }} spacing={1}>
        {pipelines.length > 1 ? (
          <TextField
            select
            size="small"
            label="Pipeline"
            value={pipeline.id}
            onChange={(event) => {
              setPipelineId(event.target.value);
              void load(event.target.value).catch((err: Error) => setError(err.message));
            }}
            sx={{ minWidth: 180 }}
          >
            {pipelines.map((item) => (
              <MenuItem key={item.id} value={item.id}>
                {item.name}
              </MenuItem>
            ))}
          </TextField>
        ) : null}
        <TextField size="small" label="Search deals" value={search} onChange={(event) => setSearch(event.target.value)} onKeyDown={(event) => event.key === "Enter" && void load(pipeline.id)} />
        <TextField select size="small" label="Owner" value={ownerFilter} onChange={(event) => setOwnerFilter(event.target.value)} sx={{ minWidth: 180 }}>
          <MenuItem value="">All owners</MenuItem>
          {assignees.map((person) => (
            <MenuItem key={person.id} value={person.id}>
              {person.name}
            </MenuItem>
          ))}
        </TextField>
        <TextField select size="small" label="Priority" value={priorityFilter} onChange={(event) => setPriorityFilter(event.target.value)} sx={{ minWidth: 140 }}>
          <MenuItem value="">All</MenuItem>
          {["low", "normal", "high"].map((item) => (
            <MenuItem key={item} value={item}>
              {item}
            </MenuItem>
          ))}
        </TextField>
        <TextField size="small" type="date" label="Close after" value={closeAfter} onChange={(event) => setCloseAfter(event.target.value)} slotProps={{ inputLabel: { shrink: true } }} />
        <TextField size="small" type="date" label="Close before" value={closeBefore} onChange={(event) => setCloseBefore(event.target.value)} slotProps={{ inputLabel: { shrink: true } }} />
        <Button onClick={() => void load(pipeline.id).catch((err: Error) => setError(err.message))}>Apply</Button>
        <Button onClick={() => void crmApi.exportCsv("deals").catch((err: Error) => setError(err.message))}>Export</Button>
      </Stack>
      {closing ? (
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography sx={{ mb: 1 }}>
            Move {closing.deal.name} to {closing.name}. Store a {closing.won ? "won" : "lost"} reason — this is a fact, not a forecast.
          </Typography>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
            <TextField size="small" label={closing.won ? "Won reason" : "Lost reason"} value={closeReason} onChange={(event) => setCloseReason(event.target.value)} sx={{ flex: 1 }} />
            <Button
              variant="contained"
              onClick={async () => {
                try {
                  await crmApi.updateDeal(closing.deal.id, {
                    stage: closing.stageId,
                    ...(closing.won ? { won_reason: closeReason } : { lost_reason: closeReason }),
                  });
                  setClosing(null);
                  setCloseReason("");
                  await load(pipeline.id);
                } catch (err) {
                  setError(asError(err, "Unable to move deal."));
                }
              }}
            >
              Save stage
            </Button>
            <Button onClick={() => setClosing(null)}>Cancel</Button>
          </Stack>
        </Paper>
      ) : null}
      {creating ? (
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Stack direction={{ xs: "column", md: "row" }} spacing={1} sx={{ flexWrap: "wrap" }}>
            <TextField size="small" label="Deal name" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
            <TextField size="small" label="Amount" value={form.amount} onChange={(event) => setForm({ ...form, amount: event.target.value })} />
            <TextField size="small" label="Currency" value={form.currency} onChange={(event) => setForm({ ...form, currency: event.target.value.toUpperCase() })} sx={{ width: 100 }} />
            <TextField select size="small" label="Company" value={form.company} onChange={(event) => setForm({ ...form, company: event.target.value, contact: "" })} sx={{ minWidth: 180 }}>
              {companies.map((item) => (
                <MenuItem key={item.id} value={item.id}>
                  {item.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField select size="small" label="Contact" value={form.contact} onChange={(event) => setForm({ ...form, contact: event.target.value })} sx={{ minWidth: 160 }}>
              <MenuItem value="">None</MenuItem>
              {contacts
                .filter((item) => item.company === form.company)
                .map((item) => (
                  <MenuItem key={item.id} value={item.id}>
                    {`${item.first_name} ${item.last_name}`.trim()}
                  </MenuItem>
                ))}
            </TextField>
            <TextField select size="small" label="Stage" value={form.stage} onChange={(event) => setForm({ ...form, stage: event.target.value })} sx={{ minWidth: 160 }}>
              {pipeline.stages.map((item) => (
                <MenuItem key={item.id} value={item.id}>
                  {item.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField select size="small" label="Owner" value={form.owner} onChange={(event) => setForm({ ...form, owner: event.target.value })} sx={{ minWidth: 160 }}>
              <MenuItem value="">Me</MenuItem>
              {assignees.map((person) => (
                <MenuItem key={person.id} value={person.id}>
                  {person.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField select size="small" label="Priority" value={form.priority} onChange={(event) => setForm({ ...form, priority: event.target.value })} sx={{ minWidth: 120 }}>
              {["low", "normal", "high"].map((item) => (
                <MenuItem key={item} value={item}>
                  {item}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              size="small"
              type="date"
              label="Expected close"
              value={form.expected_close_at}
              onChange={(event) => setForm({ ...form, expected_close_at: event.target.value })}
              slotProps={{ inputLabel: { shrink: true } }}
            />
            <Button variant="contained" onClick={() => void createDeal()}>
              Create
            </Button>
          </Stack>
        </Paper>
      ) : null}
      {funnel ? (
        <Card variant="outlined">
          <CardContent>
            <Typography variant="h4" sx={{ mb: 1 }}>
              Funnel
            </Typography>
            <Typography color="text.secondary" sx={{ mb: 2 }}>
              {funnel.why}
            </Typography>
            {funnel.stages.some((row) => row.deals > 0) ? (
              <>
                <MiniBarChart items={funnel.stages.map((row) => ({ label: row.name, value: row.deals }))} />
                <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", mt: 2 }}>
                  {funnel.stages.map((row) => (
                    <Chip key={row.name} size="small" label={`${row.name}: ${row.deals} · ${money(row.amount)}`} />
                  ))}
                </Stack>
              </>
            ) : (
              <Typography color="text.secondary">No deals in this pipeline yet.</Typography>
            )}
          </CardContent>
        </Card>
      ) : null}
      <Stack direction="row" spacing={2} sx={{ overflowX: "auto", pb: 2 }}>
        {pipeline.stages.map((stage) => (
          <Paper key={stage.id} variant="outlined" sx={{ minWidth: 240, p: 1.5, bgcolor: "background.paper" }}>
            <Typography variant="subtitle2">{stage.name}</Typography>
            <Typography variant="caption" color="text.secondary">
              {deals.filter((deal) => deal.stage === stage.id).length} deals
            </Typography>
            {deals
              .filter((deal) => deal.stage === stage.id)
              .map((deal) => (
                <Paper
                  key={deal.id}
                  sx={{ p: 1.5, mt: 1, cursor: "pointer" }}
                  variant="outlined"
                  onClick={() => router.push(`/app/crm/deals/${deal.id}`)}
                >
                  <Typography sx={{ fontWeight: 600 }}>{deal.name}</Typography>
                  <Typography variant="body2">{deal.company_name || "—"}</Typography>
                  <Typography variant="body2">{money(deal.amount, deal.currency)}</Typography>
                  {deal.priority && deal.priority !== "normal" ? <Chip size="small" label={deal.priority} sx={{ mt: 0.5 }} /> : null}
                  {deal.owner_name ? (
                    <Typography variant="caption" color="text.secondary">
                      {deal.owner_name}
                    </Typography>
                  ) : null}
                  {deal.last_activity_at ? (
                    <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
                      Last activity {new Date(deal.last_activity_at).toLocaleDateString()}
                    </Typography>
                  ) : null}
                  <TextField
                    select
                    size="small"
                    label="Stage"
                    value={deal.stage}
                    onClick={(event) => event.stopPropagation()}
                    onChange={(event) => {
                      event.stopPropagation();
                      void move(deal, event.target.value);
                    }}
                    sx={{ mt: 1, minWidth: 160 }}
                  >
                    {pipeline.stages.map((item) => (
                      <MenuItem key={item.id} value={item.id}>
                        {item.name}
                      </MenuItem>
                    ))}
                  </TextField>
                </Paper>
              ))}
          </Paper>
        ))}
      </Stack>
    </Stack>
  );
}

export function CrmCompaniesPage() {
  const router = useRouter();
  const [rows, setRows] = useState<Company[]>([]);
  const [assignees, setAssignees] = useState<CrmAssignee[]>([]);
  const [search, setSearch] = useState("");
  const [ownerFilter, setOwnerFilter] = useState("");
  const [industryFilter, setIndustryFilter] = useState("");
  const [name, setName] = useState("");
  const [domain, setDomain] = useState("");
  const [industry, setIndustry] = useState("");
  const [location, setLocation] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = async (query = search) => {
    const params: Record<string, string> = {};
    if (query.trim()) params.search = query.trim();
    if (ownerFilter) params.owner = ownerFilter;
    if (industryFilter.trim()) params.industry = industryFilter.trim();
    const [companyRows, people] = await Promise.all([crmApi.companiesAll(params), crmApi.assignees()]);
    setRows(companyRows);
    setAssignees(people);
  };

  useEffect(() => {
    void load()
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingState />;

  return (
    <Stack spacing={3}>
      <PageHeader
        title="Companies"
        description="Prospect accounts in the native CRM. First-party buyers live under Business Analysis."
        actions={
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
            <TextField size="small" label="Search" value={search} onChange={(event) => setSearch(event.target.value)} onKeyDown={(event) => event.key === "Enter" && void load()} />
            <TextField size="small" label="Industry" value={industryFilter} onChange={(event) => setIndustryFilter(event.target.value)} />
            <TextField select size="small" label="Owner" value={ownerFilter} onChange={(event) => setOwnerFilter(event.target.value)} sx={{ minWidth: 160 }}>
              <MenuItem value="">All owners</MenuItem>
              {assignees.map((person) => (
                <MenuItem key={person.id} value={person.id}>
                  {person.name}
                </MenuItem>
              ))}
            </TextField>
            <Button onClick={() => void load().catch((err: Error) => setError(err.message))}>Search</Button>
            <Button onClick={() => void crmApi.exportCsv("companies").catch((err: Error) => setError(err.message))}>Export</Button>
          </Stack>
        }
      />
      {error ? <Alert severity="error">{error}</Alert> : null}
      <Stack direction={{ xs: "column", md: "row" }} spacing={1} sx={{ flexWrap: "wrap" }}>
        <TextField size="small" label="Name" value={name} onChange={(event) => setName(event.target.value)} />
        <TextField size="small" label="Domain" value={domain} onChange={(event) => setDomain(event.target.value)} />
        <TextField size="small" label="Industry" value={industry} onChange={(event) => setIndustry(event.target.value)} />
        <TextField size="small" label="Location" value={location} onChange={(event) => setLocation(event.target.value)} />
        <TextField size="small" label="Phone" value={phone} onChange={(event) => setPhone(event.target.value)} />
        <TextField size="small" label="Email" value={email} onChange={(event) => setEmail(event.target.value)} />
        <Button
          variant="contained"
          onClick={async () => {
            if (!name.trim()) return;
            try {
              await crmApi.createCompany({
                name: name.trim(),
                domain: domain.trim(),
                industry: industry.trim(),
                location: location.trim(),
                phone: phone.trim(),
                email: email.trim(),
              });
              setName("");
              setDomain("");
              setIndustry("");
              setLocation("");
              setPhone("");
              setEmail("");
              await load();
            } catch (err) {
              setError(asError(err, "Unable to add company."));
            }
          }}
        >
          Add
        </Button>
      </Stack>
      {rows.length ? (
        <ResponsiveDataList
          rows={rows}
          cardTitle={(row) => row.name}
          onRowClick={(row) => router.push(`/app/crm/companies/${row.id}`)}
          columns={[
            { key: "name", label: "Company", render: (row) => row.name },
            { key: "domain", label: "Domain", render: (row) => row.domain || "—" },
            { key: "industry", label: "Industry", render: (row) => row.industry || "—" },
            { key: "location", label: "Location", render: (row) => row.location || "—" },
            { key: "phone", label: "Phone", render: (row) => row.phone || "—" },
            { key: "owner", label: "Owner", render: (row) => row.owner_name || "—" },
            {
              key: "last",
              label: "Last activity",
              render: (row) => (row.last_activity_at ? new Date(row.last_activity_at).toLocaleString() : "—"),
            },
          ]}
        />
      ) : (
        <EmptyState title="No companies" description="Promote a SIPulse lead or add a company here." />
      )}
    </Stack>
  );
}

export function CrmContactsPage() {
  const router = useRouter();
  const [rows, setRows] = useState<Contact[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [assignees, setAssignees] = useState<CrmAssignee[]>([]);
  const [search, setSearch] = useState("");
  const [companyFilter, setCompanyFilter] = useState("");
  const [ownerFilter, setOwnerFilter] = useState("");
  const [form, setForm] = useState({ company: "", first_name: "", last_name: "", title: "", email: "", phone: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = async (query = search) => {
    const params: Record<string, string> = {};
    if (query.trim()) params.search = query.trim();
    if (companyFilter) params.company = companyFilter;
    if (ownerFilter) params.owner = ownerFilter;
    const [contactRows, companyRows, people] = await Promise.all([
      crmApi.contactsAll(params),
      crmApi.companiesAll(),
      crmApi.assignees(),
    ]);
    setRows(contactRows);
    setCompanies(companyRows);
    setAssignees(people);
  };

  useEffect(() => {
    void load()
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingState />;

  return (
    <Stack spacing={3}>
      <PageHeader
        title="Contacts"
        description="People at CRM companies. These are not lead-generation prospects until you add them from Leads."
        actions={
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
            <TextField size="small" label="Search" value={search} onChange={(event) => setSearch(event.target.value)} onKeyDown={(event) => event.key === "Enter" && void load()} />
            <TextField select size="small" label="Company" value={companyFilter} onChange={(event) => setCompanyFilter(event.target.value)} sx={{ minWidth: 160 }}>
              <MenuItem value="">All companies</MenuItem>
              {companies.map((item) => (
                <MenuItem key={item.id} value={item.id}>
                  {item.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField select size="small" label="Owner" value={ownerFilter} onChange={(event) => setOwnerFilter(event.target.value)} sx={{ minWidth: 160 }}>
              <MenuItem value="">All owners</MenuItem>
              {assignees.map((person) => (
                <MenuItem key={person.id} value={person.id}>
                  {person.name}
                </MenuItem>
              ))}
            </TextField>
            <Button onClick={() => void load().catch((err: Error) => setError(err.message))}>Search</Button>
            <Button onClick={() => void crmApi.exportCsv("contacts").catch((err: Error) => setError(err.message))}>Export</Button>
          </Stack>
        }
      />
      {error ? <Alert severity="error">{error}</Alert> : null}
      <Stack direction={{ xs: "column", md: "row" }} spacing={1} sx={{ flexWrap: "wrap" }}>
        <TextField select size="small" label="Company" value={form.company} onChange={(event) => setForm({ ...form, company: event.target.value })} sx={{ minWidth: 180 }}>
          {companies.map((item) => (
            <MenuItem key={item.id} value={item.id}>
              {item.name}
            </MenuItem>
          ))}
        </TextField>
        <TextField size="small" label="First name" value={form.first_name} onChange={(event) => setForm({ ...form, first_name: event.target.value })} />
        <TextField size="small" label="Last name" value={form.last_name} onChange={(event) => setForm({ ...form, last_name: event.target.value })} />
        <TextField size="small" label="Title" value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} />
        <TextField size="small" label="Email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} />
        <TextField size="small" label="Phone" value={form.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} />
        <Button
          variant="contained"
          onClick={async () => {
            if (!form.company || !form.first_name.trim()) return;
            try {
              await crmApi.createContact(form);
              setForm({ company: form.company, first_name: "", last_name: "", title: "", email: "", phone: "" });
              await load();
            } catch (err) {
              setError(asError(err, "Unable to add contact."));
            }
          }}
        >
          Add
        </Button>
      </Stack>
      {rows.length ? (
        <ResponsiveDataList
          rows={rows}
          cardTitle={(row) => `${row.first_name} ${row.last_name}`.trim()}
          onRowClick={(row) => router.push(`/app/crm/contacts/${row.id}`)}
          columns={[
            { key: "name", label: "Contact", render: (row) => `${row.first_name} ${row.last_name}`.trim() },
            { key: "title", label: "Title", render: (row) => row.title || "—" },
            { key: "company", label: "Company", render: (row) => row.company_name || "—" },
            { key: "email", label: "Email", render: (row) => row.email || "—" },
            { key: "phone", label: "Phone", render: (row) => row.phone || "—" },
            { key: "owner", label: "Owner", render: (row) => row.owner_name || "—" },
          ]}
        />
      ) : (
        <EmptyState title="No contacts" description="Add a contact to a CRM company." />
      )}
    </Stack>
  );
}

export function CrmActivitiesPage() {
  const [rows, setRows] = useState<Activity[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [deals, setDeals] = useState<Deal[]>([]);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [overdueOnly, setOverdueOnly] = useState(false);
  const [companyFilter, setCompanyFilter] = useState("");
  const [kindFilter, setKindFilter] = useState("");
  const [completedFilter, setCompletedFilter] = useState("");
  const [form, setForm] = useState({ company: "", deal: "", contact: "", title: "", kind: "task", body: "", due_at: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = async (onlyOverdue = overdueOnly) => {
    const params: Record<string, string> = {};
    if (onlyOverdue) params.overdue = "true";
    if (companyFilter) params.company = companyFilter;
    if (kindFilter) params.kind = kindFilter;
    if (completedFilter) params.completed = completedFilter;
    const [activityRows, companyRows, dealRows, contactRows] = await Promise.all([
      crmApi.activitiesAll(params),
      crmApi.companiesAll(),
      crmApi.dealsAll(),
      crmApi.contactsAll(),
    ]);
    setRows(activityRows);
    setCompanies(companyRows);
    setDeals(dealRows);
    setContacts(contactRows);
  };

  useEffect(() => {
    void load()
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingState />;

  const overdue = rows.filter((row) => row.due_at && !row.completed_at && new Date(row.due_at).getTime() < Date.now());

  return (
    <Stack spacing={3}>
      <PageHeader
        title="Activities"
        description="Notes and follow-ups on CRM companies and deals. Overdue means due_at is in the past and the activity is not completed."
        actions={
          <Stack direction="row" spacing={1}>
            <Button
              variant={overdueOnly ? "contained" : "outlined"}
              onClick={() => {
                const next = !overdueOnly;
                setOverdueOnly(next);
                void load(next).catch((err: Error) => setError(err.message));
              }}
            >
              {overdueOnly ? "Showing overdue" : "Overdue only"}
            </Button>
            <Button onClick={() => void crmApi.exportCsv("activities").catch((err: Error) => setError(err.message))}>Export</Button>
          </Stack>
        }
      />
      {error ? <Alert severity="error">{error}</Alert> : null}
      {overdue.length ? (
        <Alert severity="warning">
          {overdue.length} follow-up{overdue.length === 1 ? "" : "s"} past due.
        </Alert>
      ) : null}
      <Stack direction={{ xs: "column", md: "row" }} spacing={1} sx={{ flexWrap: "wrap" }}>
        <TextField select size="small" label="Filter company" value={companyFilter} onChange={(event) => setCompanyFilter(event.target.value)} sx={{ minWidth: 180 }}>
          <MenuItem value="">All companies</MenuItem>
          {companies.map((item) => (
            <MenuItem key={item.id} value={item.id}>
              {item.name}
            </MenuItem>
          ))}
        </TextField>
        <TextField select size="small" label="Kind" value={kindFilter} onChange={(event) => setKindFilter(event.target.value)} sx={{ minWidth: 120 }}>
          <MenuItem value="">All kinds</MenuItem>
          {["note", "call", "meeting", "task", "email"].map((kind) => (
            <MenuItem key={kind} value={kind}>
              {kind}
            </MenuItem>
          ))}
        </TextField>
        <TextField select size="small" label="Status" value={completedFilter} onChange={(event) => setCompletedFilter(event.target.value)} sx={{ minWidth: 140 }}>
          <MenuItem value="">All</MenuItem>
          <MenuItem value="false">Open</MenuItem>
          <MenuItem value="true">Completed</MenuItem>
        </TextField>
        <Button onClick={() => void load().catch((err: Error) => setError(err.message))}>Apply</Button>
      </Stack>
      <Stack direction={{ xs: "column", md: "row" }} spacing={1} sx={{ flexWrap: "wrap" }}>
        <TextField select size="small" label="Company" value={form.company} onChange={(event) => setForm({ ...form, company: event.target.value, deal: "", contact: "" })} sx={{ minWidth: 180 }}>
          <MenuItem value="">None</MenuItem>
          {companies.map((item) => (
            <MenuItem key={item.id} value={item.id}>
              {item.name}
            </MenuItem>
          ))}
        </TextField>
        <TextField select size="small" label="Deal" value={form.deal} onChange={(event) => setForm({ ...form, deal: event.target.value })} sx={{ minWidth: 180 }}>
          <MenuItem value="">None</MenuItem>
          {deals
            .filter((item) => !form.company || item.company === form.company)
            .map((item) => (
              <MenuItem key={item.id} value={item.id}>
                {item.name}
              </MenuItem>
            ))}
        </TextField>
        <TextField select size="small" label="Contact" value={form.contact} onChange={(event) => setForm({ ...form, contact: event.target.value })} sx={{ minWidth: 160 }}>
          <MenuItem value="">None</MenuItem>
          {contacts
            .filter((item) => !form.company || item.company === form.company)
            .map((item) => (
              <MenuItem key={item.id} value={item.id}>
                {`${item.first_name} ${item.last_name}`.trim()}
              </MenuItem>
            ))}
        </TextField>
        <TextField select size="small" label="Kind" value={form.kind} onChange={(event) => setForm({ ...form, kind: event.target.value })} sx={{ minWidth: 120 }}>
          {["note", "call", "meeting", "task", "email"].map((kind) => (
            <MenuItem key={kind} value={kind}>
              {kind}
            </MenuItem>
          ))}
        </TextField>
        <TextField size="small" label="Title" value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} />
        <TextField size="small" label="Note" value={form.body} onChange={(event) => setForm({ ...form, body: event.target.value })} />
        <TextField
          size="small"
          type="datetime-local"
          label="Due"
          value={form.due_at}
          onChange={(event) => setForm({ ...form, due_at: event.target.value })}
          slotProps={{ inputLabel: { shrink: true } }}
        />
        <Button
          variant="contained"
          onClick={async () => {
            if (!form.title.trim()) return;
            try {
              await crmApi.createActivity({
                title: form.title.trim(),
                kind: form.kind,
                body: form.body,
                ...(form.company ? { company: form.company } : {}),
                ...(form.deal ? { deal: form.deal } : {}),
                ...(form.contact ? { contact: form.contact } : {}),
                ...(form.due_at ? { due_at: new Date(form.due_at).toISOString() } : {}),
              });
              setForm({ ...form, title: "", body: "", due_at: "" });
              await load();
            } catch (err) {
              setError(asError(err, "Unable to add activity."));
            }
          }}
        >
          Add
        </Button>
      </Stack>
      {rows.length ? (
        <ResponsiveDataList
          rows={rows}
          cardTitle={(row) => row.title}
          columns={[
            { key: "title", label: "Activity", render: (row) => row.title },
            { key: "company", label: "Company", render: (row) => row.company_name || "—" },
            { key: "deal", label: "Deal", render: (row) => row.deal_name || "—" },
            { key: "contact", label: "Contact", render: (row) => row.contact_name || "—" },
            { key: "kind", label: "Kind", render: (row) => row.kind },
            {
              key: "due",
              label: "Due",
              render: (row) =>
                row.due_at ? (
                  <Chip
                    size="small"
                    color={row.completed_at ? "success" : new Date(row.due_at).getTime() < Date.now() ? "warning" : "default"}
                    label={new Date(row.due_at).toLocaleString()}
                  />
                ) : (
                  "—"
                ),
            },
            {
              key: "done",
              label: "Done",
              render: (row) => (
                <Button
                  size="small"
                  onClick={() =>
                    void crmApi
                      .updateActivity(row.id, { completed_at: row.completed_at ? null : new Date().toISOString() })
                      .then(() => load())
                      .catch((err: Error) => setError(err.message))
                  }
                >
                  {row.completed_at ? "Reopen" : "Complete"}
                </Button>
              ),
            },
          ]}
        />
      ) : (
        <EmptyState title="No activities" description="Log a note or a follow-up with a due date after a call or meeting." />
      )}
    </Stack>
  );
}

export function CrmLeadsPage() {
  const router = useRouter();
  const [rows, setRows] = useState<Deal[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    void crmApi
      .dealsAll({ has_lead: "true" })
      .then(setRows)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;

  return (
    <Stack spacing={3}>
      <PageHeader title="CRM leads" description="SIPulse leads promoted into this CRM. This is not a second lead-generation product." />
      {rows.length ? (
        <ResponsiveDataList
          rows={rows}
          cardTitle={(row) => row.name}
          onRowClick={(row) => router.push(`/app/crm/deals/${row.id}`)}
          columns={[
            { key: "name", label: "Deal", render: (row) => row.name },
            { key: "company", label: "Company", render: (row) => row.company_name || "—" },
            { key: "stage", label: "Stage", render: (row) => row.stage_name || "—" },
            { key: "amount", label: "Amount", render: (row) => money(row.amount, row.currency) },
            { key: "owner", label: "Owner", render: (row) => row.owner_name || "—" },
            {
              key: "lead",
              label: "Lead",
              render: (row) =>
                row.lead ? (
                  <Button size="small" onClick={(event) => { event.stopPropagation(); router.push(`/app/leads/${row.lead}`); }}>
                    Open lead
                  </Button>
                ) : (
                  "—"
                ),
            },
          ]}
        />
      ) : (
        <EmptyState title="No promoted leads" description="Open Leads and use Add to CRM. Discovery stays in the Leads module." />
      )}
    </Stack>
  );
}

export function CrmCompanyDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const confirm = useConfirm();
  const [item, setItem] = useState<Company | null>(null);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [deals, setDeals] = useState<Deal[]>([]);
  const [assignees, setAssignees] = useState<CrmAssignee[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    void Promise.all([
      crmApi.getCompany(params.id),
      crmApi.contactsAll({ company: params.id }),
      crmApi.dealsAll({ company: params.id }),
      crmApi.assignees(),
    ])
      .then(([company, contactRows, dealRows, people]) => {
        setItem(company);
        setContacts(contactRows);
        setDeals(dealRows);
        setAssignees(people);
      })
      .catch((err: Error) => setError(err.message));
  }, [params.id]);

  if (error && !item) return <ErrorState message={error} />;
  if (!item) return <LoadingState />;

  return (
    <Stack spacing={2}>
      <PageHeader title={item.name} description="CRM company. First-party buyers stay in Business Analysis." />
      {error ? <Alert severity="error">{error}</Alert> : null}
      <TextField label="Name" value={item.name} onChange={(event) => setItem({ ...item, name: event.target.value })} />
      <TextField label="Domain" value={item.domain} onChange={(event) => setItem({ ...item, domain: event.target.value })} />
      <TextField label="Industry" value={item.industry} onChange={(event) => setItem({ ...item, industry: event.target.value })} />
      <TextField label="Location" value={item.location} onChange={(event) => setItem({ ...item, location: event.target.value })} />
      <TextField label="Phone" value={item.phone || ""} onChange={(event) => setItem({ ...item, phone: event.target.value })} />
      <TextField label="Email" value={item.email || ""} onChange={(event) => setItem({ ...item, email: event.target.value })} />
      <TextField label="Tags" value={(item.tags || []).join(", ")} onChange={(event) => setItem({ ...item, tags: event.target.value.split(",").map((part) => part.trim()).filter(Boolean) })} helperText="Comma-separated stored labels." />
      <TextField label="Notes" value={item.notes || ""} onChange={(event) => setItem({ ...item, notes: event.target.value })} multiline minRows={3} />
      <TextField select label="Owner" value={item.owner || ""} onChange={(event) => setItem({ ...item, owner: event.target.value || null })}>
        <MenuItem value="">Unassigned</MenuItem>
        {assignees.map((person) => (
          <MenuItem key={person.id} value={person.id}>
            {person.name}
          </MenuItem>
        ))}
      </TextField>
      <Stack direction="row" spacing={1}>
        <Button
          variant="contained"
          onClick={async () => {
            try {
              setItem(await crmApi.updateCompany(item.id, { name: item.name, domain: item.domain, industry: item.industry, location: item.location, phone: item.phone, email: item.email, notes: item.notes, tags: item.tags, owner: item.owner || null }));
              setError("");
            } catch (err) {
              setError(asError(err, "Unable to save company."));
            }
          }}
        >
          Save
        </Button>
        <Button
          color="error"
          onClick={async () => {
            const ok = await confirm({ title: "Delete company", description: `${item.name} and its related CRM records will be removed from this workspace.`, confirmLabel: "Delete", danger: true });
            if (!ok) return;
            try {
              await crmApi.deleteCompany(item.id);
              router.push("/app/crm/companies");
            } catch (err) {
              setError(asError(err, "Unable to delete company."));
            }
          }}
        >
          Delete
        </Button>
        <Button onClick={() => router.push("/app/crm/companies")}>Back</Button>
      </Stack>
      <Typography variant="h4">Contacts</Typography>
      {contacts.length ? (
        contacts.map((row) => (
          <Typography key={row.id} sx={{ cursor: "pointer" }} onClick={() => router.push(`/app/crm/contacts/${row.id}`)}>
            {row.first_name} {row.last_name} · {row.title || "no title"} · {row.email || "no email"}
          </Typography>
        ))
      ) : (
        <Typography color="text.secondary">No contacts on this company.</Typography>
      )}
      <Typography variant="h4">Deals</Typography>
      {deals.length ? (
        deals.map((row) => (
          <Typography key={row.id} sx={{ cursor: "pointer" }} onClick={() => router.push(`/app/crm/deals/${row.id}`)}>
            {row.name} · {row.stage_name || "—"} · {money(row.amount, row.currency)}
          </Typography>
        ))
      ) : (
        <Typography color="text.secondary">No deals on this company.</Typography>
      )}
      <CompanyActivityBlock companyId={item.id} onError={setError} />
    </Stack>
  );
}

export function CrmContactDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const confirm = useConfirm();
  const [item, setItem] = useState<Contact | null>(null);
  const [assignees, setAssignees] = useState<CrmAssignee[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    void Promise.all([crmApi.getContact(params.id), crmApi.assignees()])
      .then(([contact, people]) => {
        setItem(contact);
        setAssignees(people);
      })
      .catch((err: Error) => setError(err.message));
  }, [params.id]);

  if (error && !item) return <ErrorState message={error} />;
  if (!item) return <LoadingState />;

  return (
    <Stack spacing={2}>
      <PageHeader
        title={`${item.first_name} ${item.last_name}`.trim()}
        description={item.company_name || "CRM contact"}
        actions={
          item.company ? (
            <Button onClick={() => router.push(`/app/crm/companies/${item.company}`)}>Open company</Button>
          ) : null
        }
      />
      {error ? <Alert severity="error">{error}</Alert> : null}
      <TextField label="First name" value={item.first_name} onChange={(event) => setItem({ ...item, first_name: event.target.value })} />
      <TextField label="Last name" value={item.last_name} onChange={(event) => setItem({ ...item, last_name: event.target.value })} />
      <TextField label="Title" value={item.title || ""} onChange={(event) => setItem({ ...item, title: event.target.value })} />
      <TextField label="Email" value={item.email} onChange={(event) => setItem({ ...item, email: event.target.value })} />
      <TextField label="Phone" value={item.phone} onChange={(event) => setItem({ ...item, phone: event.target.value })} />
      <TextField select label="Owner" value={item.owner || ""} onChange={(event) => setItem({ ...item, owner: event.target.value || null })}>
        <MenuItem value="">Unassigned</MenuItem>
        {assignees.map((person) => (
          <MenuItem key={person.id} value={person.id}>
            {person.name}
          </MenuItem>
        ))}
      </TextField>
      <Stack direction="row" spacing={1}>
        <Button
          variant="contained"
          onClick={async () => {
            try {
              setItem(
                await crmApi.updateContact(item.id, {
                  first_name: item.first_name,
                  last_name: item.last_name,
                  title: item.title,
                  email: item.email,
                  phone: item.phone,
                  owner: item.owner || null,
                }),
              );
              setError("");
            } catch (err) {
              setError(asError(err, "Unable to save contact."));
            }
          }}
        >
          Save
        </Button>
        <Button
          color="error"
          onClick={async () => {
            const ok = await confirm({ title: "Delete contact", description: `${item.first_name} ${item.last_name} will be removed from this workspace.`.trim(), confirmLabel: "Delete", danger: true });
            if (!ok) return;
            try {
              await crmApi.deleteContact(item.id);
              router.push("/app/crm/contacts");
            } catch (err) {
              setError(asError(err, "Unable to delete contact."));
            }
          }}
        >
          Delete
        </Button>
        <Button onClick={() => router.push("/app/crm/contacts")}>Back</Button>
      </Stack>
      <ContactRelatedBlock contact={item} onError={setError} />
    </Stack>
  );
}

function CompanyActivityBlock({ companyId, onError }: { companyId: string; onError: (message: string) => void }) {
  const [rows, setRows] = useState<Activity[]>([]);
  const [note, setNote] = useState("");

  const load = () =>
    crmApi
      .activitiesAll({ company: companyId })
      .then(setRows)
      .catch((err: Error) => onError(err.message));

  useEffect(() => {
    void load();
  }, [companyId]);

  return (
    <Stack spacing={1}>
      <Typography variant="h4">Activities</Typography>
      <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
        <TextField size="small" label="Note" value={note} onChange={(event) => setNote(event.target.value)} sx={{ flex: 1 }} />
        <Button
          onClick={async () => {
            if (!note.trim()) return;
            try {
              await crmApi.createActivity({ title: note.trim(), kind: "note", company: companyId });
              setNote("");
              await load();
            } catch (err) {
              onError(asError(err, "Unable to add note."));
            }
          }}
        >
          Log note
        </Button>
      </Stack>
      {rows.length ? (
        rows.map((row) => (
          <Typography key={row.id}>
            {row.title}
            {row.due_at ? ` · due ${new Date(row.due_at).toLocaleString()}` : ""}
            {row.completed_at ? " · done" : ""}
          </Typography>
        ))
      ) : (
        <Typography color="text.secondary">No activities on this company.</Typography>
      )}
    </Stack>
  );
}

function ContactRelatedBlock({ contact, onError }: { contact: Contact; onError: (message: string) => void }) {
  const router = useRouter();
  const [activities, setActivities] = useState<Activity[]>([]);
  const [deals, setDeals] = useState<Deal[]>([]);
  const [note, setNote] = useState("");

  const load = () =>
    Promise.all([crmApi.activitiesAll({ contact: contact.id }), crmApi.dealsAll({ contact: contact.id })])
      .then(([activityRows, dealRows]) => {
        setActivities(activityRows);
        setDeals(dealRows);
      })
      .catch((err: Error) => onError(err.message));

  useEffect(() => {
    void load();
  }, [contact.id]);

  return (
    <Stack spacing={1}>
      <Typography variant="h4">Deals</Typography>
      {deals.length ? (
        deals.map((row) => (
          <Typography key={row.id} sx={{ cursor: "pointer" }} onClick={() => router.push(`/app/crm/deals/${row.id}`)}>
            {row.name} · {row.stage_name || "—"} · {money(row.amount, row.currency)}
          </Typography>
        ))
      ) : (
        <Typography color="text.secondary">No deals on this contact.</Typography>
      )}
      <Typography variant="h4">Activities</Typography>
      <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
        <TextField size="small" label="Note" value={note} onChange={(event) => setNote(event.target.value)} sx={{ flex: 1 }} />
        <Button
          onClick={async () => {
            if (!note.trim()) return;
            try {
              await crmApi.createActivity({ title: note.trim(), kind: "note", company: contact.company, contact: contact.id });
              setNote("");
              await load();
            } catch (err) {
              onError(asError(err, "Unable to add note."));
            }
          }}
        >
          Log note
        </Button>
      </Stack>
      {activities.length ? (
        activities.map((row) => (
          <Typography key={row.id}>
            {row.title}
            {row.due_at ? ` · due ${new Date(row.due_at).toLocaleString()}` : ""}
          </Typography>
        ))
      ) : (
        <Typography color="text.secondary">No activities on this contact.</Typography>
      )}
    </Stack>
  );
}
