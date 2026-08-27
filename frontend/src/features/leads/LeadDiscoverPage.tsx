"use client";

import { Alert, Button, MenuItem, Paper, Stack, TextField, Typography } from "@mui/material";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { PageHeader } from "@/components/common/PageHeader";
import { useJobSession } from "@/features/websites/auditSession";
import { leadApi, marketApi } from "@/services/domainApi";
import type { GeoPlace, ICP } from "@/types/domain";

export function LeadDiscoverPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { start } = useJobSession();
  const [input, setInput] = useState("We sell ERP software to packaging companies with 20+ employees in Karachi and Lahore.");
  const [icp, setIcp] = useState<ICP | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [places, setPlaces] = useState<GeoPlace[]>([]);
  const [placeId, setPlaceId] = useState("");

  useEffect(() => {
    void marketApi.places({ kind: "city" }).then((data) => setPlaces(Array.isArray(data) ? data : [])).catch(() => setPlaces([]));
  }, []);

  useEffect(() => {
    const fromQuery = searchParams.get("geo_place");
    if (fromQuery) setPlaceId(fromQuery);
  }, [searchParams]);

  return (
    <Stack spacing={3}>
      <PageHeader title="Lead discovery" description="Describe your offer and ideal customer. Discovery uses every lead source enabled in the platform console (Places, Yelp, OSM, LinkedIn Sales Navigator, and licensed directory APIs). Confirm the ICP before discovery runs." />
      {error ? <Alert severity="error">{error}</Alert> : null}
      {!icp ? (
        <Paper variant="outlined" sx={{ p: 3 }}>
          <Typography variant="h5" gutterBottom>
            What do you sell?
          </Typography>
          <TextField multiline minRows={4} value={input} onChange={(event) => setInput(event.target.value)} sx={{ mb: 2 }} />
          <Button
            variant="contained"
            disabled={busy}
            onClick={async () => {
              setBusy(true);
              setError("");
              try {
                setIcp(await leadApi.createIcp({ raw_input: input, name: "Generated ICP" }));
              } catch (err) {
                setError(err instanceof Error ? err.message : "Unable to generate ICP.");
              } finally {
                setBusy(false);
              }
            }}
          >
            Generate ICP
          </Button>
        </Paper>
      ) : (
        <Paper variant="outlined" sx={{ p: 3 }}>
          <Typography variant="h5" gutterBottom>
            Review ICP
          </Typography>
          <Alert severity="info" sx={{ mb: 2 }}>
            Origin: {icp.origin}. Confirm before discovery. Discovery uses every enabled platform source. ICP extraction uses OpenAI, Claude, Grok, or Gemini when those keys are enabled.
          </Alert>
          <Typography>Industry: {icp.industry || "—"}</Typography>
          <Typography>Employee count: {icp.employee_count || "—"}</Typography>
          <Typography>Locations: {icp.locations.join(", ") || "—"}</Typography>
          <Typography>Keywords: {icp.keywords.join(", ") || "—"}</Typography>
          {places.length ? (
            <TextField
              select
              label="Optional market"
              value={placeId}
              onChange={(event) => setPlaceId(event.target.value)}
              sx={{ mt: 2, minWidth: 240 }}
              helperText="Uses the existing Leads pipeline. Does not create a second finder."
            >
              <MenuItem value="">ICP locations only</MenuItem>
              {places.map((item) => (
                <MenuItem key={item.id} value={item.id}>
                  {item.name}
                </MenuItem>
              ))}
            </TextField>
          ) : null}
          <Stack direction="row" spacing={2} sx={{ mt: 2 }}>
            <Button
              variant="contained"
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                try {
                  const confirmed = await leadApi.confirmIcp(icp.id);
                  const started = await leadApi.startSearch(confirmed.id, placeId ? { geo_place: placeId } : undefined);
                  start({ jobId: started.job.id, kind: "discover_leads", title: "Lead discovery", href: "/app/leads" });
                  router.push("/app/leads");
                } catch (err) {
                  setError(err instanceof Error ? err.message : "Unable to start discovery.");
                } finally {
                  setBusy(false);
                }
              }}
            >
              Confirm ICP and start discovery
            </Button>
            <Button onClick={() => setIcp(null)}>Edit description</Button>
          </Stack>
        </Paper>
      )}
    </Stack>
  );
}
