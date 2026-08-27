"use client";

import { Alert, Button, Chip, MenuItem, Stack, TextField, Typography } from "@mui/material";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { useConfirm } from "@/components/common/ConfirmDialog";
import { PageHeader } from "@/components/common/PageHeader";
import { ErrorState } from "@/components/feedback/ErrorState";
import { LoadingState } from "@/components/feedback/LoadingState";
import { crmApi } from "@/services/domainApi";
import type { Activity, Company, Contact, CrmAssignee, Deal, Pipeline } from "@/types/domain";

export function CrmDealPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const confirm = useConfirm();
  const [deal, setDeal] = useState<Deal | null>(null);
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [assignees, setAssignees] = useState<CrmAssignee[]>([]);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [note, setNote] = useState("");
  const [error, setError] = useState("");

  const load = async () => {
    const [item, pipelineRows, companyRows, people] = await Promise.all([
      crmApi.getDeal(params.id),
      crmApi.pipelines(),
      crmApi.companiesAll(),
      crmApi.assignees(),
    ]);
    const [contactRows, activityRows] = await Promise.all([
      crmApi.contactsAll({ company: item.company }),
      crmApi.activitiesAll({ deal: item.id }),
    ]);
    setDeal(item);
    setPipelines(pipelineRows);
    setCompanies(companyRows);
    setContacts(contactRows);
    setAssignees(people);
    setActivities(activityRows);
  };

  useEffect(() => {
    void load().catch((err: Error) => setError(err.message));
  }, [params.id]);

  if (error && !deal) return <ErrorState message={error} onRetry={() => void load().catch((err: Error) => setError(err.message))} />;
  if (!deal) return <LoadingState />;

  const pipeline = pipelines.find((item) => item.id === deal.pipeline) ?? pipelines[0];

  return (
    <Stack spacing={2}>
      <PageHeader title={deal.name} description={`${deal.company_name || "CRM deal"} · ${deal.stage_name || "No stage"}`} />
      {error ? <Alert severity="error">{error}</Alert> : null}
      <TextField label="Name" value={deal.name} onChange={(event) => setDeal({ ...deal, name: event.target.value })} />
      <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
        <TextField label="Amount" value={deal.amount} onChange={(event) => setDeal({ ...deal, amount: event.target.value })} sx={{ flex: 1 }} />
        <TextField label="Currency" value={deal.currency || "PKR"} onChange={(event) => setDeal({ ...deal, currency: event.target.value.toUpperCase() })} sx={{ width: 140 }} />
        <TextField
          type="date"
          label="Expected close"
          value={deal.expected_close_at || ""}
          onChange={(event) => setDeal({ ...deal, expected_close_at: event.target.value || null })}
          slotProps={{ inputLabel: { shrink: true } }}
          sx={{ flex: 1 }}
        />
      </Stack>
      <TextField
        select
        label="Company"
        value={deal.company}
        onChange={(event) => {
          const company = event.target.value;
          setDeal({ ...deal, company, contact: null });
          void crmApi.contactsAll({ company }).then(setContacts);
        }}
      >
        {companies.map((item) => (
          <MenuItem key={item.id} value={item.id}>
            {item.name}
          </MenuItem>
        ))}
      </TextField>
      <TextField select label="Contact" value={deal.contact || ""} onChange={(event) => setDeal({ ...deal, contact: event.target.value || null })}>
        <MenuItem value="">None</MenuItem>
        {contacts.map((item) => (
          <MenuItem key={item.id} value={item.id}>
            {`${item.first_name} ${item.last_name}`.trim()}
          </MenuItem>
        ))}
      </TextField>
      <TextField select label="Stage" value={deal.stage} onChange={(event) => setDeal({ ...deal, stage: event.target.value })}>
        {(pipeline?.stages ?? []).map((item) => (
          <MenuItem key={item.id} value={item.id}>
            {item.name}
          </MenuItem>
        ))}
      </TextField>
      <TextField select label="Priority" value={deal.priority || "normal"} onChange={(event) => setDeal({ ...deal, priority: event.target.value })}>
        {["low", "normal", "high"].map((item) => (
          <MenuItem key={item} value={item}>
            {item}
          </MenuItem>
        ))}
      </TextField>
      <TextField label="Next step" value={deal.next_step || ""} onChange={(event) => setDeal({ ...deal, next_step: event.target.value })} />
      <TextField label="Won reason" value={deal.won_reason || ""} onChange={(event) => setDeal({ ...deal, won_reason: event.target.value })} />
      <TextField label="Lost reason" value={deal.lost_reason || ""} onChange={(event) => setDeal({ ...deal, lost_reason: event.target.value })} />
      {deal.closed_at ? <Typography color="text.secondary">Closed {deal.closed_at}</Typography> : null}
      <TextField select label="Owner" value={deal.owner || ""} onChange={(event) => setDeal({ ...deal, owner: event.target.value || null })}>
        <MenuItem value="">Unassigned</MenuItem>
        {assignees.map((person) => (
          <MenuItem key={person.id} value={person.id}>
            {person.name}
          </MenuItem>
        ))}
      </TextField>
      {deal.lead ? (
        <Button onClick={() => router.push(`/app/leads/${deal.lead}`)} sx={{ alignSelf: "flex-start" }}>
          Open original lead
        </Button>
      ) : null}
      <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap" }}>
        <Button
          variant="contained"
          onClick={async () => {
            try {
              setDeal(
                await crmApi.updateDeal(deal.id, {
                  name: deal.name,
                  amount: deal.amount,
                  currency: deal.currency || "PKR",
                  company: deal.company,
                  contact: deal.contact || null,
                  stage: deal.stage,
                  owner: deal.owner || null,
                  expected_close_at: deal.expected_close_at || null,
                  priority: deal.priority || "normal",
                  next_step: deal.next_step || "",
                  won_reason: deal.won_reason || "",
                  lost_reason: deal.lost_reason || "",
                }),
              );
              setError("");
            } catch (err) {
              setError(err instanceof Error ? err.message : "Unable to save deal.");
            }
          }}
        >
          Save
        </Button>
        <Button
          color="error"
          onClick={async () => {
            const ok = await confirm({
              title: "Delete deal",
              description: `${deal.name} will be removed from the pipeline. Stored lead history is not deleted.`,
              confirmLabel: "Delete",
              danger: true,
            });
            if (!ok) return;
            try {
              await crmApi.deleteDeal(deal.id);
              router.push("/app/crm/deals");
            } catch (err) {
              setError(err instanceof Error ? err.message : "Unable to delete deal.");
            }
          }}
        >
          Delete
        </Button>
        <Button onClick={() => router.push("/app/crm/deals")}>Back</Button>
      </Stack>
      <Typography variant="h4">Activities</Typography>
      <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
        <TextField size="small" label="Note" value={note} onChange={(event) => setNote(event.target.value)} sx={{ flex: 1 }} />
        <Button
          onClick={async () => {
            if (!note.trim()) return;
            try {
              await crmApi.createActivity({ title: note.trim(), kind: "note", company: deal.company, deal: deal.id });
              setNote("");
              await load();
            } catch (err) {
              setError(err instanceof Error ? err.message : "Unable to add note.");
            }
          }}
        >
          Log note
        </Button>
      </Stack>
      {activities.length ? (
        activities.map((row) => (
          <Stack key={row.id} direction="row" spacing={1} sx={{ alignItems: "center" }}>
            <Typography sx={{ flex: 1 }}>
              {row.title}
              {row.due_at ? ` · due ${new Date(row.due_at).toLocaleString()}` : ""}
            </Typography>
            {row.completed_at ? <Chip size="small" color="success" label="Done" /> : null}
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
          </Stack>
        ))
      ) : (
        <Typography color="text.secondary">No activities on this deal.</Typography>
      )}
    </Stack>
  );
}
