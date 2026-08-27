"use client";

import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { PageHeader } from "@/components/common/PageHeader";
import { PrintReportChrome } from "@/components/common/PrintReportChrome";
import { ResponsiveDataList } from "@/components/common/ResponsiveDataList";
import { StatCard } from "@/components/common/StatCard";
import { EmptyState } from "@/components/feedback/EmptyState";
import { ErrorState } from "@/components/feedback/ErrorState";
import { LoadingState } from "@/components/feedback/LoadingState";
import { MarketHeatmapButton } from "@/features/growth/MarketHeatmap";
import { useAuditSession } from "@/features/websites/auditSession";
import { marketApi } from "@/services/domainApi";
import type {
  BusinessProfile,
  GeoPlace,
  Job,
  MarketAnalysis,
  MarketAsk,
  MarketBrief,
  MarketCitation,
  MarketSignal,
} from "@/types/domain";

const TYPES = [
  { value: "ecommerce", label: "E-commerce" },
  { value: "retail", label: "Retail" },
  { value: "services", label: "Services" },
  { value: "b2b", label: "B2B" },
  { value: "manufacturing", label: "Manufacturing" },
];

function SignalCsvImport({ onDone }: { onDone: () => void }) {
  const { start } = useAuditSession();
  const [note, setNote] = useState("");
  const [failed, setFailed] = useState(false);
  return (
    <Stack spacing={1} sx={{ alignItems: { sm: "flex-end" } }}>
      <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap" }}>
        <Button
          variant="contained"
          onClick={async () => {
            try {
              const created = await marketApi.collect();
              setFailed(false);
              setNote("");
              start({
                jobId: created.id,
                kind: "collect_markets",
                title: "Collect market signals",
                href: "/app/markets",
              });
              onDone();
            } catch (err) {
              setFailed(true);
              setNote(err instanceof Error ? err.message : "Collect failed.");
            }
          }}
        >
          Collect from market sources
        </Button>
        <Button
          variant="outlined"
          onClick={() =>
            void marketApi.downloadSignalTemplate().catch((err: Error) => {
              setFailed(true);
              setNote(err.message);
            })
          }
        >
          Download template
        </Button>
        <Button component="label" variant="contained">
          Import filled CSV
          <Box
            component="input"
            type="file"
            hidden
            accept=".csv,text/csv,.txt"
            onChange={async (event) => {
              const file = (event.target as HTMLInputElement).files?.[0];
              (event.target as HTMLInputElement).value = "";
              if (!file) return;
              try {
                const created = await marketApi.importSignals(file);
                setFailed(false);
                setNote("");
                start({
                  jobId: created.id,
                  kind: "import_markets",
                  title: "Market signals CSV",
                  href: "/app/markets",
                });
                onDone();
              } catch (err) {
                setFailed(true);
                setNote(err instanceof Error ? err.message : "Import failed.");
              }
            }}
          />
        </Button>
      </Stack>
      {note ? (
        <Alert severity={failed ? "error" : "success"}>{note}</Alert>
      ) : null}
    </Stack>
  );
}

function CitationList({ citations }: { citations: MarketCitation[] }) {
  const router = useRouter();
  if (!citations.length) {
    return (
      <EmptyState
        title="No citations yet"
        description="Import orders or ingest market signals. SIPulse does not invent filings or city grades."
      />
    );
  }
  return (
    <Box sx={{ display: "grid", gap: 1.5 }}>
      {citations.slice(0, 18).map((item) => (
        <Card
          key={item.id}
          variant="outlined"
          sx={{ cursor: "pointer" }}
          onClick={() => router.push(item.href)}
        >
          <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
            <Typography variant="caption" color="text.secondary">
              FACT · {item.kind}
            </Typography>
            <Typography variant="subtitle2">{item.title}</Typography>
            <Typography variant="body2" color="text.secondary">
              {item.text}
            </Typography>
          </CardContent>
        </Card>
      ))}
    </Box>
  );
}

function asAsk(
  brief: MarketBrief,
  extra?: MarketAnalysis | null,
): MarketAsk | null {
  const src = extra ?? brief.last_analysis;
  if (!src) return null;
  return {
    question: src.question || "",
    inference: src.inference || "",
    recommendation: src.recommendation || "",
    origin: src.origin || "facts_only",
    findings: src.findings?.length ? src.findings : brief.findings,
    citations: src.citations?.length ? src.citations : brief.citations,
    brief,
  };
}

function askFromJob(brief: MarketBrief, job: Job): MarketAsk {
  const citations = Array.isArray(job.result.citations)
    ? (job.result.citations as MarketCitation[])
    : brief.citations;
  const findings = Array.isArray(job.result.findings)
    ? (job.result.findings as string[])
    : brief.findings;
  return {
    question: String(job.result.question ?? ""),
    inference: String(job.result.inference ?? ""),
    recommendation: String(job.result.recommendation ?? ""),
    origin: String(job.result.origin ?? "facts_only"),
    findings,
    citations,
    brief,
  };
}

export function MarketOverviewPage() {
  const router = useRouter();
  const { start, job } = useAuditSession();
  const seen = useRef("");
  const [error, setError] = useState("");
  const [brief, setBrief] = useState<MarketBrief | null>(null);
  const [profile, setProfile] = useState<BusinessProfile | null>(null);
  const [question, setQuestion] = useState("");
  const [ask, setAsk] = useState<MarketAsk | null>(null);
  const analyzing = Boolean(
    job &&
    job.job_type === "analyze_market" &&
    job.status !== "COMPLETED" &&
    job.status !== "FAILED" &&
    job.status !== "CANCELLED",
  );

  const applyBrief = (data: MarketBrief, extra?: MarketAnalysis | null) => {
    setBrief(data);
    setProfile(data.profile);
    const next = asAsk(data, extra);
    if (next) setAsk(next);
  };

  const load = () =>
    marketApi
      .brief()
      .then((data) => {
        applyBrief(data);
        setError("");
      })
      .catch((err: Error) => setError(err.message));

  const run = async (nextQuestion: string) => {
    try {
      const created = await marketApi.ask({
        question: nextQuestion,
        profile: profile ?? undefined,
      });
      setError("");
      start({
        jobId: created.id,
        kind: "analyze_market",
        title: nextQuestion.trim() || "Analyze this business",
        href: "/app/markets",
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to analyze.");
    }
  };

  useEffect(() => {
    void load();
  }, []);

  useEffect(() => {
    if (job?.job_type !== "analyze_market") return;
    const key = `${job.id}:${job.status}`;
    if (seen.current === key) return;
    if (job.status === "COMPLETED") {
      seen.current = key;
      marketApi
        .brief()
        .then((data) => {
          applyBrief(data, {
            question: String(job.result.question ?? ""),
            inference: String(job.result.inference ?? ""),
            recommendation: String(job.result.recommendation ?? ""),
            origin: String(job.result.origin ?? "facts_only"),
            findings: Array.isArray(job.result.findings)
              ? (job.result.findings as string[])
              : data.findings,
            citations: Array.isArray(job.result.citations)
              ? (job.result.citations as MarketCitation[])
              : data.citations,
          });
          setAsk(askFromJob(data, job));
          setError("");
        })
        .catch((err: Error) => setError(err.message));
    }
    if (job.status === "FAILED") {
      seen.current = key;
      setError(job.error || "Market analysis failed.");
    }
  }, [job]);

  if (!brief && !error) return <LoadingState />;

  return (
    <PrintReportChrome title="Market brief">
      <Stack spacing={3}>
        <PageHeader
          title="Market brief"
          description="Enter this tenant's business, then analyze its market. Collect pulls Wikidata, OpenStreetMap shops, and every enabled lead source. Scores stay estimated from those counts — they are not invented."
          actions={<SignalCsvImport onDone={() => void load()} />}
        />
        {error ? (
          <ErrorState message={error} onRetry={() => void load()} />
        ) : null}
        {brief && profile ? (
          <>
            <Card variant="outlined">
              <CardContent>
                <Stack spacing={2}>
                  <Typography variant="h4">Business input</Typography>
                  <Box
                    sx={{
                      display: "grid",
                      gap: 2,
                      gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
                    }}
                  >
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
                  </Box>
                  <TextField
                    label="Goal"
                    multiline
                    minRows={2}
                    value={profile.goal}
                    onChange={(event) =>
                      setProfile({ ...profile, goal: event.target.value })
                    }
                  />
                  <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
                    <Button
                      variant="contained"
                      disabled={analyzing}
                      onClick={() => void run("")}
                    >
                      Analyze this business
                    </Button>
                    <MarketHeatmapButton brief={brief} />
                  </Stack>
                </Stack>
              </CardContent>
            </Card>
            <Box
              sx={{
                display: "grid",
                gap: 2,
                gridTemplateColumns: { xs: "1fr", md: "repeat(4, 1fr)" },
              }}
            >
              <StatCard
                label="Served cities"
                value={brief.served.length}
                hint="From placed orders"
              />
              <StatCard
                label="Scored cities"
                value={brief.scored.length}
                hint={`${brief.unscored_cities} catalog cities have no signals`}
              />
              <StatCard
                label="Overlap"
                value={brief.overlap.length}
                hint="Cities you serve that also have a score"
              />
              <StatCard
                label="Signals"
                value={brief.signal_count}
                hint="Ingested for this workspace"
              />
            </Box>
            <Alert severity="info">{brief.why}</Alert>
            {brief.findings.length ? (
              <Stack spacing={1}>
                {brief.findings.map((line) => (
                  <Typography key={line}>FACT: {line}</Typography>
                ))}
              </Stack>
            ) : null}
            <Stack direction={{ xs: "column", md: "row" }} spacing={1}>
              <TextField
                fullWidth
                size="small"
                label="Ask about this business market"
                placeholder="Where do we already serve chocolate, and which scored cities have no orders?"
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
              />
              <Button
                variant="contained"
                disabled={analyzing || !question.trim()}
                onClick={() => void run(question.trim())}
              >
                Ask
              </Button>
            </Stack>
            {ask ? (
              <Stack spacing={1}>
                <Alert severity="info">
                  Origin: {ask.origin}. Inference is not stored as fact.
                </Alert>
                {ask.findings?.map((line) => (
                  <Typography key={line}>FACT: {line}</Typography>
                ))}
                {ask.inference ? (
                  <Typography>INFERENCE: {ask.inference}</Typography>
                ) : null}
                {ask.recommendation ? (
                  <Typography>RECOMMENDATION: {ask.recommendation}</Typography>
                ) : null}
              </Stack>
            ) : null}
            {brief.overlap.length ? (
              <ResponsiveDataList
                rows={brief.overlap}
                cardTitle={(row) => row.name}
                onRowClick={(row) =>
                  router.push(`/app/markets/places/${row.id}`)
                }
                columns={[
                  {
                    key: "name",
                    label: "You serve + scored",
                    render: (row) => row.name,
                  },
                  {
                    key: "score",
                    label: "Score",
                    render: (row) => `${row.score}/100`,
                  },
                  {
                    key: "origin",
                    label: "Origin",
                    render: (row) => row.origin,
                  },
                  { key: "why", label: "Why", render: (row) => row.why },
                ]}
              />
            ) : null}
            {brief.signal_without_orders.length ? (
              <ResponsiveDataList
                rows={brief.signal_without_orders}
                cardTitle={(row) => row.name}
                onRowClick={(row) =>
                  router.push(`/app/markets/places/${row.id}`)
                }
                columns={[
                  {
                    key: "name",
                    label: "Scored, no orders",
                    render: (row) => row.name,
                  },
                  {
                    key: "score",
                    label: "Score",
                    render: (row) => `${row.score}/100`,
                  },
                  { key: "why", label: "Why", render: (row) => row.why },
                ]}
              />
            ) : null}
            {brief.served.length ? (
              <ResponsiveDataList
                rows={brief.served.map((row) => ({ ...row, id: row.city }))}
                cardTitle={(row) => row.city}
                columns={[
                  {
                    key: "city",
                    label: "Served city",
                    render: (row) => row.city,
                  },
                  {
                    key: "orders",
                    label: "Orders",
                    render: (row) => row.orders ?? "—",
                  },
                  { key: "why", label: "Why", render: (row) => row.why || "" },
                ]}
              />
            ) : null}
            {brief.scored.length ? (
              <ResponsiveDataList
                rows={brief.scored}
                cardTitle={(row) => row.name}
                onRowClick={(row) =>
                  router.push(`/app/markets/places/${row.id}`)
                }
                columns={[
                  {
                    key: "city",
                    label: "Scored city",
                    render: (row) => row.name,
                  },
                  {
                    key: "score",
                    label: "Opportunity",
                    render: (row) => `${row.score}/100`,
                  },
                  {
                    key: "origin",
                    label: "Origin",
                    render: (row) => row.origin,
                  },
                  { key: "why", label: "Why", render: (row) => row.why },
                ]}
              />
            ) : (
              <EmptyState
                title="No scored cities"
                description="Download the signals template, fill licensed or operator values, then import. Catalog cities stay unscored until then."
              />
            )}
            <Typography variant="h3">Citations</Typography>
            <CitationList citations={ask?.citations ?? brief.citations} />
          </>
        ) : null}
      </Stack>
    </PrintReportChrome>
  );
}

export function MarketPlacesPage() {
  const router = useRouter();
  const [kind, setKind] = useState("city");
  const [rows, setRows] = useState<GeoPlace[]>([]);
  useEffect(() => {
    void marketApi
      .places({ kind })
      .then((data) =>
        setRows(
          Array.isArray(data)
            ? data
            : ((data as { results?: GeoPlace[] }).results ?? []),
        ),
      );
  }, [kind]);
  return (
    <Stack spacing={3}>
      <PageHeader
        title="Markets"
        description="Drill from country → region → city → area. These names are geographic, not demand scores."
      />
      <Stack direction="row" spacing={1}>
        {["country", "region", "city", "area"].map((item) => (
          <Button
            key={item}
            variant={kind === item ? "contained" : "outlined"}
            onClick={() => setKind(item)}
          >
            {item}
          </Button>
        ))}
      </Stack>
      <ResponsiveDataList
        rows={rows}
        cardTitle={(row) => row.name}
        onRowClick={(row) => router.push(`/app/markets/places/${row.id}`)}
        columns={[
          { key: "name", label: "Name", render: (row) => row.name },
          { key: "kind", label: "Level", render: (row) => row.kind },
          {
            key: "parent",
            label: "Parent",
            render: (row) => row.parent_name || "—",
          },
          { key: "code", label: "Code", render: (row) => row.code },
        ]}
      />
    </Stack>
  );
}

export function MarketPlaceDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [error, setError] = useState("");
  const [data, setData] = useState<Awaited<
    ReturnType<typeof marketApi.place>
  > | null>(null);
  useEffect(() => {
    marketApi
      .place(params.id)
      .then(setData)
      .catch((err: Error) => setError(err.message));
  }, [params.id]);
  if (error) return <ErrorState message={error} />;
  if (!data) return <LoadingState />;
  return (
    <Stack spacing={3}>
      <PageHeader
        title={data.place.name}
        description={`${data.place.kind} · ${data.place.code}`}
        actions={
          <Button
            variant="contained"
            onClick={() => router.push("/app/leads/discover")}
          >
            Find leads
          </Button>
        }
      />
      <Alert severity={data.score.score == null ? "info" : "success"}>
        {data.score.why}
      </Alert>
      <Typography>
        Score: {data.score.score == null ? "—" : `${data.score.score}/100`} (
        {data.score.origin})
      </Typography>
      {Object.entries(data.score.parts).map(([key, value]) => (
        <Typography key={key} color="text.secondary">
          {key.replaceAll("_", " ")}: {value == null ? "no signal" : value}
        </Typography>
      ))}
      {Array.isArray(data.signals) && data.signals.length ? (
        <ResponsiveDataList
          rows={data.signals as MarketSignal[]}
          cardTitle={(row) => row.kind}
          columns={[
            { key: "kind", label: "Kind", render: (row) => row.kind },
            { key: "value", label: "Value", render: (row) => row.value },
            { key: "source", label: "Source", render: (row) => row.source },
            {
              key: "status",
              label: "Status",
              render: (row) => row.verification_status,
            },
          ]}
        />
      ) : null}
      {data.children.length ? (
        <ResponsiveDataList
          rows={data.children}
          cardTitle={(row) => row.name}
          onRowClick={(row) => router.push(`/app/markets/places/${row.id}`)}
          columns={[{ key: "name", label: "Area", render: (row) => row.name }]}
        />
      ) : null}
    </Stack>
  );
}

export function MarketScoringPage() {
  const [weights, setWeights] = useState<Record<string, number>>({});
  const [defaults, setDefaults] = useState<Record<string, number>>({});
  const [saved, setSaved] = useState("");
  useEffect(() => {
    void marketApi.scoring().then((data) => {
      setWeights(data.weights);
      setDefaults(data.defaults);
    });
  }, []);
  return (
    <Stack spacing={3}>
      <PageHeader
        title="Opportunity scoring"
        description="Administrators can change weights. Scores still require ingested signals — weights alone do not grade cities."
      />
      {saved ? <Alert severity="success">{saved}</Alert> : null}
      <Box
        sx={{
          display: "grid",
          gap: 2,
          gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
        }}
      >
        {Object.keys(defaults).map((key) => (
          <TextField
            key={key}
            type="number"
            label={key.replaceAll("_", " ")}
            value={weights[key] ?? 0}
            onChange={(event) =>
              setWeights({ ...weights, [key]: Number(event.target.value) })
            }
          />
        ))}
      </Box>
      <Button
        variant="contained"
        onClick={async () => {
          const next = await marketApi.saveScoring(weights);
          setWeights(next.weights);
          setSaved("Weights saved. They apply to this workspace only.");
        }}
      >
        Save weights
      </Button>
    </Stack>
  );
}

export function MarketSignalsPage({
  title,
  kinds,
}: {
  title: string;
  kinds: Array<{ value: string; label: string }>;
}) {
  const [rows, setRows] = useState<MarketSignal[]>([]);
  const [places, setPlaces] = useState<GeoPlace[]>([]);
  const [form, setForm] = useState({
    place: "",
    kind: kinds[0]?.value ?? "demand",
    value: "50",
    source: "",
  });
  const [note, setNote] = useState("");
  const [failed, setFailed] = useState(false);

  const load = () => {
    void marketApi
      .places({ kind: "city" })
      .then((data) => setPlaces(Array.isArray(data) ? data : []));
    void marketApi
      .signals()
      .then((data) =>
        setRows(
          data.results.filter((item) =>
            kinds.some((kind) => kind.value === item.kind),
          ),
        ),
      );
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <Stack spacing={3}>
      <PageHeader
        title={title}
        description="Ingest a signal with a source. Scores stay empty until rows exist. Directory scraping is not used."
        actions={<SignalCsvImport onDone={load} />}
      />
      {note ? (
        <Alert severity={failed ? "error" : "success"}>{note}</Alert>
      ) : null}
      <Stack direction={{ xs: "column", md: "row" }} spacing={1}>
        <TextField
          select
          size="small"
          label="City"
          value={form.place}
          onChange={(event) => setForm({ ...form, place: event.target.value })}
          sx={{ minWidth: 180 }}
        >
          {places.map((item) => (
            <MenuItem key={item.id} value={item.id}>
              {item.name}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          select
          size="small"
          label="Kind"
          value={form.kind}
          onChange={(event) => setForm({ ...form, kind: event.target.value })}
          sx={{ minWidth: 180 }}
        >
          {kinds.map((item) => (
            <MenuItem key={item.value} value={item.value}>
              {item.label}
            </MenuItem>
          ))}
        </TextField>

        <TextField
          size="small"
          type="number"
          label="Value 0-100"
          value={form.value}
          onChange={(event) => setForm({ ...form, value: event.target.value })}
          slotProps={{ htmlInput: { min: 0, max: 100 } }}
        />

        <TextField
          size="small"
          label="Source"
          value={form.source}
          onChange={(event) => setForm({ ...form, source: event.target.value })}
        />
        <Button
          variant="contained"
          onClick={async () => {
            const numericValue = Number(form.value);
            if (
              !form.place ||
              !form.source.trim() ||
              numericValue < 0 ||
              numericValue > 100
            ) {
              setFailed(true);
              setNote(
                "Please enter a value between 0 and 100, and fill in city and source.",
              );
              return;
            }
            await marketApi.createSignal({
              place: form.place,
              kind: form.kind,
              value: Number(form.value),
              source: form.source.trim(),
              verification_status: "unverified",
            });
            setFailed(false);
            setNote("Signal stored for this workspace only.");
            setForm({ ...form, source: "" });
            load();
          }}
        >
          Ingest
        </Button>
      </Stack>
      {rows.length ? (
        <ResponsiveDataList
          rows={rows}
          cardTitle={(row) => row.place_name || row.kind}
          columns={[
            {
              key: "place",
              label: "City",
              render: (row) => row.place_name || "—",
            },
            { key: "kind", label: "Kind", render: (row) => row.kind },
            { key: "value", label: "Value", render: (row) => row.value },
            { key: "source", label: "Source", render: (row) => row.source },
            {
              key: "status",
              label: "Status",
              render: (row) => row.verification_status,
            },
          ]}
        />
      ) : (
        <EmptyState
          title="No signals ingested"
          description="Download the template, fill a known city, kind, value, and source, then import. City lists stay unscored until then."
        />
      )}
    </Stack>
  );
}

export function MarketSignalsPendingPage({ title }: { title: string }) {
  return (
    <MarketSignalsPage
      title={title}
      kinds={[{ value: "demand", label: "Demand" }]}
    />
  );
}
