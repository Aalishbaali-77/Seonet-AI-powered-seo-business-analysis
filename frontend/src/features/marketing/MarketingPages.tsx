"use client";

import { Alert, Button, MenuItem, Stack, TextField } from "@mui/material";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { PageHeader } from "@/components/common/PageHeader";
import { ResponsiveDataList } from "@/components/common/ResponsiveDataList";
import { StatusChip } from "@/components/common/StatusChip";
import { EmptyState } from "@/components/feedback/EmptyState";
import { ErrorState } from "@/components/feedback/ErrorState";
import { LoadingState } from "@/components/feedback/LoadingState";
import { businessApi, leadApi, marketingApi, opportunityApi } from "@/services/domainApi";
import type { Campaign, GrowthOpportunity, LeadSavedList } from "@/types/domain";

const AUDIENCES = [
  { value: "lead_list", label: "Lead list" },
  { value: "commerce_city", label: "Imported customers in a city" },
  { value: "opportunity", label: "Opportunity-linked leads" },
];

export function CampaignListPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [rows, setRows] = useState<Campaign[]>([]);
  const [lists, setLists] = useState<LeadSavedList[]>([]);
  const [opps, setOpps] = useState<GrowthOpportunity[]>([]);
  const [cities, setCities] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [name, setName] = useState("");
  const [audienceType, setAudienceType] = useState("lead_list");
  const [listId, setListId] = useState("");
  const [city, setCity] = useState("");
  const [opportunityId, setOpportunityId] = useState("");
  const [preview, setPreview] = useState<{ count: number; why: string } | null>(null);

  const load = () =>
    marketingApi
      .campaigns()
      .then((data) => {
        setRows(data.results);
        setError("");
      })
      .catch((err: Error) => setError(err.message));

  useEffect(() => {
    void load();
    void leadApi.lists().then((data) => setLists(data.results)).catch(() => setLists([]));
    void opportunityApi.list().then((data) => setOpps(data.results)).catch(() => setOpps([]));
    void businessApi
      .overview()
      .then((data) => setCities(data.kpis.customer_cities ?? []))
      .catch(() => setCities([]));
  }, []);

  useEffect(() => {
    const fromQuery = searchParams.get("opportunity");
    if (fromQuery) {
      setAudienceType("opportunity");
      setOpportunityId(fromQuery);
    }
  }, [searchParams]);

  useEffect(() => {
    const params: Record<string, string> = { audience_type: audienceType };
    if (audienceType === "lead_list" && listId) params.lead_list = listId;
    if (audienceType === "commerce_city" && city) params.city = city;
    if (audienceType === "opportunity" && opportunityId) params.opportunity = opportunityId;
    void marketingApi
      .preview(params)
      .then((data) => setPreview({ count: data.count, why: data.why }))
      .catch(() => setPreview(null));
  }, [audienceType, listId, city, opportunityId]);

  return (
    <Stack spacing={3}>
      <PageHeader
        title="Marketing"
        description="Campaigns use existing lead lists, imported customers, or opportunity-linked leads. Audience size is a stored count. Export the audience CSV to send in your own channel. SIPulse does not invent open rates."
        actions={
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1} sx={{ flexWrap: "wrap" }}>
            <TextField size="small" label="Campaign name" value={name} onChange={(event) => setName(event.target.value)} />
            <TextField
              select
              size="small"
              label="Audience"
              value={audienceType}
              onChange={(event) => setAudienceType(event.target.value)}
              sx={{ minWidth: 220 }}
            >
              {AUDIENCES.map((item) => (
                <MenuItem key={item.value} value={item.value}>
                  {item.label}
                </MenuItem>
              ))}
            </TextField>
            {audienceType === "lead_list" ? (
              <TextField select size="small" label="Lead list" value={listId} onChange={(event) => setListId(event.target.value)} sx={{ minWidth: 180 }}>
                {lists.map((item) => (
                  <MenuItem key={item.id} value={item.id}>
                    {item.name}
                  </MenuItem>
                ))}
              </TextField>
            ) : null}
            {audienceType === "commerce_city" ? (
              <TextField select size="small" label="Customer city" value={city} onChange={(event) => setCity(event.target.value)} sx={{ minWidth: 160 }}>
                {cities.map((item) => (
                  <MenuItem key={item} value={item}>
                    {item}
                  </MenuItem>
                ))}
              </TextField>
            ) : null}
            {audienceType === "opportunity" ? (
              <TextField
                select
                size="small"
                label="Opportunity"
                value={opportunityId}
                onChange={(event) => setOpportunityId(event.target.value)}
                sx={{ minWidth: 180 }}
              >
                {opps.map((item) => (
                  <MenuItem key={item.id} value={item.id}>
                    {item.title}
                  </MenuItem>
                ))}
              </TextField>
            ) : null}
            <Button
              onClick={() => {
                const params: Record<string, string> = { audience_type: audienceType };
                if (audienceType === "lead_list" && listId) params.lead_list = listId;
                if (audienceType === "commerce_city" && city) params.city = city;
                if (audienceType === "opportunity" && opportunityId) params.opportunity = opportunityId;
                void marketingApi.exportAudience(params).catch((err: Error) => setError(err.message));
              }}
            >
              Export audience
            </Button>
            <Button
              variant="contained"
              onClick={async () => {
                if (!name.trim()) return;
                await marketingApi.create({
                  name: name.trim(),
                  audience_type: audienceType,
                  channel: "offer",
                  ...(audienceType === "lead_list" && listId ? { lead_list: listId } : {}),
                  ...(audienceType === "commerce_city" && city ? { city } : {}),
                  ...(audienceType === "opportunity" && opportunityId ? { opportunity: opportunityId } : {}),
                });
                setName("");
                await load();
              }}
            >
              Create
            </Button>
          </Stack>
        }
      />
      {preview ? (
        <Alert severity="info">
          Live audience: {preview.count}. {preview.why}
        </Alert>
      ) : null}
      {error ? <ErrorState message={error} onRetry={() => void load()} /> : null}
      {rows.length ? (
        <ResponsiveDataList
          rows={rows}
          cardTitle={(row) => row.name}
          onRowClick={(row) => router.push(`/app/marketing/${row.id}`)}
          columns={[
            { key: "name", label: "Campaign", render: (row) => row.name },
            { key: "audience", label: "Audience", render: (row) => row.lead_list_name || row.city || row.opportunity_title || "—" },
            { key: "live", label: "Live count", render: (row) => row.live_audience_count },
            { key: "status", label: "Status", render: (row) => <StatusChip value={row.status} /> },
          ]}
        />
      ) : (
        <EmptyState title="No campaigns" description="Create a campaign against a saved lead list, imported customer city, or linked opportunity leads. Empty audiences stay at zero." />
      )}
    </Stack>
  );
}

export function CampaignDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [item, setItem] = useState<Campaign | null>(null);
  const [opps, setOpps] = useState<GrowthOpportunity[]>([]);
  const [error, setError] = useState("");

  const load = () =>
    marketingApi
      .get(params.id)
      .then(setItem)
      .catch((err: Error) => setError(err.message));

  useEffect(() => {
    void load();
    void opportunityApi.list().then((data) => setOpps(data.results)).catch(() => setOpps([]));
  }, [params.id]);

  if (error) return <ErrorState message={error} />;
  if (!item) return <LoadingState />;

  return (
    <Stack spacing={2}>
      <PageHeader title={item.name} description={`${item.channel} · ${item.audience_type}`} />
      <StatusChip value={item.status} />
      <Alert severity="info">
        Live audience: {item.live_audience_count}. {item.audience_count != null ? `Recorded send count: ${item.audience_count}.` : "Not marked sent."}
      </Alert>
      <TextField
        label="Offer title"
        value={item.offer_title}
        onChange={(event) => setItem({ ...item, offer_title: event.target.value })}
      />
      <TextField
        label="Offer body"
        multiline
        minRows={3}
        value={item.offer_body}
        onChange={(event) => setItem({ ...item, offer_body: event.target.value })}
      />
      <TextField
        select
        label="Link opportunity (optional)"
        value={item.opportunity || ""}
        onChange={(event) => setItem({ ...item, opportunity: event.target.value || null })}
      >
        <MenuItem value="">None</MenuItem>
        {opps.map((row) => (
          <MenuItem key={row.id} value={row.id}>
            {row.title}
          </MenuItem>
        ))}
      </TextField>
      <Stack direction="row" spacing={1}>
        <Button
          variant="outlined"
          onClick={async () => {
            setItem(await marketingApi.update(item.id, { offer_title: item.offer_title, offer_body: item.offer_body, opportunity: item.opportunity }));
          }}
        >
          Save offer
        </Button>
        <Button
          onClick={() => {
            const params: Record<string, string> = { audience_type: item.audience_type };
            if (item.lead_list) params.lead_list = item.lead_list;
            if (item.city) params.city = item.city;
            if (item.opportunity) params.opportunity = item.opportunity;
            void marketingApi.exportAudience(params).catch((err: Error) => setError(err.message));
          }}
        >
          Export audience
        </Button>
        {item.status !== "sent" ? (
          <Button
            variant="contained"
            onClick={async () => {
              setItem(await marketingApi.send(item.id));
            }}
          >
            Record send
          </Button>
        ) : null}
        <Button onClick={() => router.push("/app/leads/lists")}>Open lead lists</Button>
      </Stack>
      {item.send_note ? <Alert severity="success">{item.send_note}</Alert> : null}
    </Stack>
  );
}
