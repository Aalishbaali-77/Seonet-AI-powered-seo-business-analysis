"use client";

import { useEffect, useState } from "react";
import { Alert, Button, Card, CardContent, Chip, Dialog, DialogActions, DialogContent, DialogTitle, Stack, TextField, Typography } from "@mui/material";

import { PageHeader } from "@/components/common/PageHeader";
import { RowMenu } from "@/components/common/RowMenu";
import { StatusChip } from "@/components/common/StatusChip";
import { EmptyState } from "@/components/feedback/EmptyState";
import { ErrorState } from "@/components/feedback/ErrorState";
import { LoadingState } from "@/components/feedback/LoadingState";
import { platformAdminApi } from "@/services/platformAdminApi";
import type { LeadSource } from "@/types/api";

const GROUPS: Array<{ key: LeadSource["category"]; title: string; description: string }> = [
  {
    key: "discovery",
    title: "Lead discovery",
    description:
      "Official directory APIs and licensed feeds. Enable every source you have credentials for; discovery queries all enabled sources. Sites without a public API need a search URL you control — SIPulse does not scrape directory websites.",
  },
  {
    key: "enrichment",
    title: "Lead enrichment",
    description:
      "Hunter, Clearbit, and Apollo fill published emails and firmographics from a domain. Wikidata is an open SPARQL lookup. The lead’s own website is always fetched when a URL is stored. SIPulse does not invent contact fields or scrape google.com.",
  },
  {
    key: "ai",
    title: "AI models",
    description: "OpenAI, Claude, Grok, and Gemini. One platform key is shared by every workspace. Enable Claude (or another model) here; tenants never see the secret. Token use is metered per tenant against that workspace’s package AI credits. If more than one model is enabled, SIPulse uses the first source that has a stored key (OpenAI, then Claude, then Grok, then Gemini).",
  },
  {
    key: "diagnostics",
    title: "Diagnostics",
    description: "PageSpeed Insights overlay, plus licensed Google Custom Search or SerpAPI for keyword first-page checks. SIPulse does not scrape google.com.",
  },
];

type Editor = {
  id: string;
  code: string;
  display_name: string;
  purpose: string;
  setup_hint: string;
  api_key: string;
  model: string;
  search_url: string;
  homepage_url: string;
  category: LeadSource["category"];
  requires_key: boolean;
};

export function LeadSourcesManager() {
  const [sources, setSources] = useState<LeadSource[]>([]);
  const [error, setError] = useState("");
  const [ready, setReady] = useState(false);
  const [editing, setEditing] = useState<Editor | null>(null);
  const [testNote, setTestNote] = useState("");

  const load = () =>
    platformAdminApi
      .leadSources()
      .then((page) => {
        setSources(page.results);
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
        eyebrow="Platform"
        title="API sources"
        description="Seeded discovery, enrichment, AI, and diagnostics sources. Store Claude or another model key once. Every tenant uses that platform key; usage is counted against each workspace package. Tenant workspaces never see these secrets."
      />
      <Alert severity="info">
        Yelp, Foursquare, Geoapify, OpenStreetMap, OpenCorporates, NPI Registry, and LinkedIn Sales Navigator use official APIs. YellowPage.pk, BBB, and Manta stay off until you paste a licensed search endpoint. Payment gateways stay under Payment gateways.
      </Alert>
      {error ? <ErrorState message={error} onRetry={() => void load()} /> : null}
      {testNote ? <Alert severity="success">{testNote}</Alert> : null}
      {!ready && !error ? <LoadingState /> : null}
      {ready && !sources.length && !error ? <EmptyState title="No API sources" description="Open this page again after the catalog seeds." /> : null}
      {GROUPS.map((group) => {
        const items = sources.filter((source) => source.category === group.key);
        if (!items.length) return null;
        return (
          <Stack key={group.key} spacing={2}>
            <Stack spacing={0.5}>
              <Typography variant="h4">{group.title}</Typography>
              <Typography color="text.secondary">{group.description}</Typography>
            </Stack>
            {items.map((source) => (
              <Card key={source.id} variant="outlined">
                <CardContent>
                  <Stack direction="row" spacing={1} sx={{ justifyContent: "space-between", alignItems: "flex-start" }}>
                    <Stack spacing={0.5}>
                      <Stack direction="row" spacing={1} sx={{ alignItems: "center", flexWrap: "wrap" }}>
                        <Typography variant="h4">{source.display_name}</Typography>
                        <Chip size="small" label={source.category === "ai" ? "AI" : source.category === "diagnostics" ? "Diagnostics" : "Discovery"} />
                      </Stack>
                      <Typography color="text.secondary">{source.provider}</Typography>
                      <StatusChip value={source.is_enabled ? "active" : "disconnected"} />
                      <Typography variant="body2" color="text.secondary">
                        {source.requires_key === false
                          ? "No API key required"
                          : `API key ${source.credentials_configured ? "is stored on the server" : "is not configured"}`}
                        {source.model ? ` · model ${source.model}` : ""}
                      </Typography>
                      {source.homepage_url ? (
                        <Typography
                          component="a"
                          href={source.homepage_url}
                          target="_blank"
                          rel="noreferrer"
                          variant="body2"
                          color="secondary"
                        >
                          {source.homepage_url}
                        </Typography>
                      ) : null}
                      {source.search_url ? (
                        <Typography variant="body2" color="text.secondary">
                          Search URL configured
                        </Typography>
                      ) : null}
                      {source.purpose ? (
                        <Typography variant="body2" color="text.secondary">
                          {source.purpose}
                        </Typography>
                      ) : null}
                      {source.setup_hint ? (
                        <Typography variant="body2" color="text.secondary">
                          {source.setup_hint}
                        </Typography>
                      ) : null}
                    </Stack>
                    <RowMenu
                      items={[
                        {
                          label: "Edit",
                          onClick: () =>
                            setEditing({
                              id: source.id,
                              code: source.code,
                              display_name: source.display_name,
                              purpose: source.purpose || "",
                              setup_hint: source.setup_hint || "",
                              api_key: "",
                              model: source.model || "",
                              search_url: source.search_url || "",
                              homepage_url: source.homepage_url || "",
                              category: source.category,
                              requires_key: source.requires_key !== false,
                            }),
                        },
                        {
                          label: source.is_enabled ? "Disable" : "Enable",
                          disabled: !source.is_enabled && !source.credentials_configured,
                          onClick: async () => {
                            try {
                              await platformAdminApi.updateLeadSource(source.id, { is_enabled: !source.is_enabled });
                              await load();
                            } catch (err) {
                              setError(err instanceof Error ? err.message : "Unable to update API source.");
                            }
                          },
                        },
                        {
                          label: "Test",
                          disabled: source.requires_key !== false && !source.credentials_configured,
                          onClick: async () => {
                            try {
                              const result = await platformAdminApi.testLeadSource(source.id);
                              setTestNote(result.message || `${source.display_name} responded.`);
                              setError("");
                            } catch (err) {
                              setError(err instanceof Error ? err.message : `Unable to test ${source.display_name}.`);
                            }
                          },
                        },
                      ]}
                    />
                  </Stack>
                </CardContent>
              </Card>
            ))}
          </Stack>
        );
      })}
      <Dialog open={Boolean(editing)} onClose={() => setEditing(null)} fullWidth maxWidth="sm">
        {editing ? (
          <>
            <DialogTitle>Update {editing.display_name}</DialogTitle>
            <DialogContent>
              <Stack spacing={2} sx={{ mt: 1 }}>
                <Typography color="text.secondary">
                  Names, hints, and licensed search URLs can be changed here. Paste a new key to replace the stored secret. The current key is never shown again.
                </Typography>
                <TextField
                  label="Display name"
                  value={editing.display_name}
                  onChange={(event) => setEditing({ ...editing, display_name: event.target.value })}
                />
                <TextField
                  label="Purpose"
                  value={editing.purpose}
                  onChange={(event) => setEditing({ ...editing, purpose: event.target.value })}
                />
                <TextField
                  label="Setup hint"
                  multiline
                  minRows={2}
                  value={editing.setup_hint}
                  onChange={(event) => setEditing({ ...editing, setup_hint: event.target.value })}
                />
                {editing.category === "discovery" || editing.code === "google_custom_search" ? (
                  <>
                    <TextField
                      label="Homepage URL"
                      value={editing.homepage_url}
                      onChange={(event) => setEditing({ ...editing, homepage_url: event.target.value })}
                    />
                    <TextField
                      label="Licensed search URL"
                      value={editing.search_url}
                      onChange={(event) => setEditing({ ...editing, search_url: event.target.value })}
                      helperText={editing.code === "google_custom_search" ? "Paste the Programmable Search Engine ID (cx), not a google.com results URL." : "Required for YellowPage.pk, BBB, and Manta. Official API sources already have an endpoint."}
                    />
                  </>
                ) : null}
                {editing.requires_key ? (
                  <TextField
                    label="API key"
                    type="password"
                    value={editing.api_key}
                    onChange={(event) => setEditing({ ...editing, api_key: event.target.value })}
                  />
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    This source can run without a paid key. Optional contact email can still be stored as the API key.
                  </Typography>
                )}
                {editing.category === "ai" ? (
                  <TextField
                    label="Model"
                    value={editing.model}
                    onChange={(event) => setEditing({ ...editing, model: event.target.value })}
                    helperText="Leave as-is unless you need a specific model id."
                  />
                ) : null}
              </Stack>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setEditing(null)}>Cancel</Button>
              <Button
                variant="contained"
                onClick={async () => {
                  try {
                    await platformAdminApi.updateLeadSource(editing.id, {
                      display_name: editing.display_name,
                      purpose: editing.purpose,
                      setup_hint: editing.setup_hint,
                      homepage_url: editing.homepage_url,
                      search_url: editing.search_url,
                      ...(editing.api_key ? { api_key: editing.api_key } : {}),
                      ...(editing.category === "ai" ? { model: editing.model } : {}),
                      is_enabled: true,
                    });
                    setEditing(null);
                    await load();
                  } catch (err) {
                    setError(err instanceof Error ? err.message : "Unable to save API source.");
                  }
                }}
              >
                Save and enable
              </Button>
            </DialogActions>
          </>
        ) : null}
      </Dialog>
    </Stack>
  );
}
