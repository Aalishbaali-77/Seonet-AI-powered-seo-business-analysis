"use client";

import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutlined";
import { Alert, Box, Chip, Stack, Typography } from "@mui/material";

import { ScoreRing, scoreRating } from "@/components/common/ScoreRing";
import type { Job } from "@/types/domain";

type Stage = { key: string; label: string; min: number; hint: string };

const AUDIT_STAGES: Stage[] = [
  { key: "Queued", label: "Queued", min: 0, hint: "Waiting to start." },
  { key: "Preparing audit", label: "Preparing", min: 1, hint: "Validating the public URL." },
  { key: "Crawling", label: "Crawling pages", min: 20, hint: "Fetching live HTML." },
  { key: "Measuring performance", label: "Measuring performance", min: 56, hint: "Optional lab overlay when a PageSpeed key is stored." },
  { key: "Technical analysis", label: "Technical analysis", min: 62, hint: "HTTPS, robots, sitemap, canonicals, crawl TTFB." },
  { key: "Content analysis", label: "Content & AEO", min: 75, hint: "On-page, schema, GEO, accessibility." },
  { key: "Generating report", label: "Building report", min: 90, hint: "Writing issues and scores." },
  { key: "Completed", label: "Completed", min: 100, hint: "Findings are ready." },
];

const IMPORT_STAGES: Stage[] = [
  { key: "Queued", label: "Queued", min: 0, hint: "Waiting to start." },
  { key: "Reading file", label: "Reading file", min: 1, hint: "Parsing the CSV you uploaded." },
  { key: "Importing rows", label: "Importing rows", min: 15, hint: "Storing filled rows from the template." },
  { key: "Analyzing", label: "Analyzing", min: 85, hint: "Updating business analysis from stored orders." },
  { key: "Completed", label: "Completed", min: 100, hint: "Imported rows are ready." },
];

const SYNC_STAGES: Stage[] = [
  { key: "Queued", label: "Queued", min: 0, hint: "Waiting to start." },
  { key: "Fetching store", label: "Fetching store", min: 1, hint: "Pulling catalog and orders from the connected store." },
  { key: "Storing rows", label: "Storing rows", min: 40, hint: "Writing products, orders, and reviews." },
  { key: "Analyzed", label: "Analyzing", min: 75, hint: "Served markets and product research from stored rows." },
  { key: "Completed", label: "Completed", min: 100, hint: "Store data is ready." },
];

const ANALYZE_STAGES: Stage[] = [
  { key: "Queued", label: "Queued", min: 0, hint: "Waiting to start." },
  { key: "Counting stored orders", label: "Counting orders", min: 1, hint: "Reading placed orders in this workspace." },
  { key: "Product research", label: "Product research", min: 40, hint: "Top sellers, unsold catalog, and review ratings." },
  { key: "Recording opportunities", label: "Recording opportunities", min: 70, hint: "Evidence-backed rows only — no invented city grades." },
  { key: "Completed", label: "Completed", min: 100, hint: "Analysis is ready." },
];

const DISCOVERY_STAGES: Stage[] = [
  { key: "Queued", label: "Queued", min: 0, hint: "Waiting to start." },
  { key: "Starting discovery", label: "Starting", min: 1, hint: "Confirming the ICP and enabled sources." },
  { key: "Searching", label: "Searching sources", min: 20, hint: "Querying enabled lead sources." },
  { key: "Completed", label: "Completed", min: 100, hint: "Stored leads are ready." },
];

const ANALYZE_MARKET_STAGES: Stage[] = [
  { key: "Queued", label: "Queued", min: 0, hint: "Waiting to start." },
  { key: "Reading business input", label: "Business input", min: 1, hint: "Industry, category, current market, and goal." },
  { key: "Loading commerce facts", label: "Commerce facts", min: 30, hint: "Served cities from placed orders." },
  { key: "Scoring stored signals", label: "Stored signals", min: 55, hint: "Scores only where this workspace ingested values." },
  { key: "Drafting analysis", label: "Drafting", min: 75, hint: "Heuristic findings, plus AI inference if the module is on." },
  { key: "Completed", label: "Completed", min: 100, hint: "Cited analysis is ready." },
];

const KEYWORD_STAGES: Stage[] = [
  { key: "Queued", label: "Queued", min: 0, hint: "Waiting to start." },
  { key: "Collecting SEO keywords", label: "Collecting keywords", min: 1, hint: "Stored website keywords and homepage title." },
  { key: "Checking search results", label: "Checking search", min: 30, hint: "Licensed Google Custom Search or SerpAPI first-page sample." },
  { key: "Drafting keyword suggestions", label: "Suggestions", min: 78, hint: "Claude or other package AI drafts extra queries from the business and working SEO." },
  { key: "Completed", label: "Completed", min: 100, hint: "Positions and suggestions are ready." },
];

const FIX_STAGES: Stage[] = [
  { key: "Queued", label: "Queued", min: 0, hint: "Waiting to start." },
  { key: "Connecting site access", label: "Connecting", min: 1, hint: "Testing the stored WordPress, FTP, SFTP, or cPanel login." },
  { key: "Applying recommended fixes", label: "Applying fixes", min: 25, hint: "Writing only allowlisted files or WordPress settings." },
  { key: "Re-checking SEO / AEO / GEO", label: "Re-auditing", min: 55, hint: "New crawl. The first audit stays stored as the baseline." },
  { key: "Completed", label: "Completed", min: 100, hint: "Score comparison is ready." },
];

const COLLECT_STAGES: Stage[] = [
  { key: "Queued", label: "Queued", min: 0, hint: "Waiting to start." },
  { key: "Reading business input", label: "Business input", min: 1, hint: "Industry and category from this workspace." },
  { key: "Querying open market data", label: "Open market data", min: 20, hint: "Wikidata population and OpenStreetMap shop counts." },
  { key: "Storing estimated signals", label: "Storing signals", min: 80, hint: "Writing estimated rows with a source. Not invented grades." },
  { key: "Completed", label: "Completed", min: 100, hint: "Collected signals are ready." },
];

function isCsvImport(kind?: string) {
  return kind === "import_commerce" || kind === "import_markets";
}

function stagesFor(job: Job | null, kind?: string): Stage[] {
  const type = job?.job_type || kind || "";
  if (isCsvImport(type)) return IMPORT_STAGES;
  if (type === "collect_markets") return COLLECT_STAGES;
  if (type === "sync_commerce") return SYNC_STAGES;
  if (type === "analyze_business") return ANALYZE_STAGES;
  if (type === "analyze_market") return ANALYZE_MARKET_STAGES;
  if (type === "apply_audit_fixes") return FIX_STAGES;
  if (type === "check_keyword_ranks") return KEYWORD_STAGES;
  if (type === "discover_leads") return DISCOVERY_STAGES;
  return AUDIT_STAGES;
}

function activeIndex(job: Job | null, stages: Stage[]) {
  if (!job) {
    return 0;
  }
  if (job.status === "COMPLETED") {
    return stages.length - 1;
  }
  const named = stages.findIndex((item) => item.key === String(job.result.stage ?? "") || String(job.result.stage ?? "").startsWith(item.key));
  if (named >= 0) {
    return named;
  }
  let index = 0;
  stages.forEach((item, i) => {
    if ((job.progress ?? 0) >= item.min) {
      index = i;
    }
  });
  return index;
}

function headline(job: Job | null, complete: boolean, failed: boolean) {
  if (complete) {
    if (isCsvImport(job?.job_type)) return "Import complete";
    if (job?.job_type === "collect_markets") return "Collect complete";
    if (job?.job_type === "sync_commerce") return "Store sync complete";
    if (job?.job_type === "analyze_business") return "Analysis complete";
    if (job?.job_type === "analyze_market") return "Market analysis complete";
    if (job?.job_type === "apply_audit_fixes") return "Fixes applied";
    if (job?.job_type === "check_keyword_ranks") return "Keyword check complete";
    if (job?.job_type === "discover_leads") return "Discovery complete";
    return "Audit complete";
  }
  if (failed) {
    if (isCsvImport(job?.job_type)) return "Import failed";
    if (job?.job_type === "collect_markets") return "Collect failed";
    if (job?.job_type === "sync_commerce") return "Store sync failed";
    if (job?.job_type === "analyze_business") return "Analysis failed";
    if (job?.job_type === "analyze_market") return "Market analysis failed";
    if (job?.job_type === "apply_audit_fixes") return "Apply failed";
    if (job?.job_type === "check_keyword_ranks") return "Keyword check failed";
    if (job?.job_type === "discover_leads") return "Discovery failed";
    return "Audit failed";
  }
  return job?.result.stage ? String(job.result.stage) : "Starting";
}

function subtitle(job: Job | null, complete: boolean) {
  if (!job) {
    return "Live from the workspace job — not a timer.";
  }
  if (isCsvImport(job.job_type)) {
    const created = Number(job.result.created ?? 0);
    const skipped = Number(job.result.skipped ?? 0);
    const processed = Number(job.result.processed ?? 0);
    const total = Number(job.result.total ?? 0);
    if (complete) {
      return `${created} rows imported${skipped ? `, ${skipped} skipped` : ""}.`;
    }
    if (total) {
      return `${processed} of ${total} rows.`;
    }
    return "Live from the import job — not a timer.";
  }
  if (job.job_type === "collect_markets") {
    const created = Number(job.result.created ?? 0);
    const updated = Number(job.result.updated ?? 0);
    if (complete) {
      return `${created} new, ${updated} updated estimated signals.`;
    }
    return "Live from Wikidata, OpenStreetMap, and enabled lead sources — not a timer.";
  }
  if (job.job_type === "sync_commerce") {
    if (complete) {
      return `${Number(job.result.products ?? 0)} products, ${Number(job.result.orders ?? 0)} orders, ${Number(job.result.reviews ?? 0)} reviews stored.`;
    }
    return "Live from the store sync — not a timer.";
  }
  if (job.job_type === "analyze_business") {
    if (complete) {
      const created = Number(job.result.opportunities_created ?? 0);
      return created ? `${created} opportunities recorded from stored evidence.` : "Analysis complete from stored orders.";
    }
    return "Live from stored commerce rows — not a timer.";
  }
  if (job.job_type === "analyze_market") {
    if (complete) {
      const served = Number(job.result.served_cities ?? 0);
      const scored = Number(job.result.scored_cities ?? 0);
      return `${served} served cities, ${scored} scored cities from stored rows.`;
    }
    return "Live from the saved profile, orders, and ingested signals — not a timer.";
  }
  if (job.job_type === "apply_audit_fixes") {
    if (complete) {
      const before = job.result.overall_before;
      const after = job.result.overall_after;
      return `Baseline kept. Audit score ${before ?? "—"} → ${after ?? "—"}. Not a Google rank.`;
    }
    return "Live from site access and a new crawl — not a timer.";
  }
  if (job.job_type === "check_keyword_ranks") {
    if (complete) {
      const sample = `${Number(job.result.first_page ?? 0)} of ${Number(job.result.checked ?? 0)} queries in the first-page sample.`;
      return job.result.ai_used ? `${sample} Package AI drafted extra queries.` : sample;
    }
    return "Live from the licensed search API — not a timer.";
  }
  if (job.job_type === "discover_leads") {
    if (complete) {
      const unique = Number(job.result.unique ?? job.result.discovered ?? 0);
      return unique ? `${unique} leads stored.` : String(job.result.message || "No matching businesses were returned.");
    }
    return "Live from enabled lead sources — not a timer.";
  }
  const score = typeof job.result.overall_score === "number" ? job.result.overall_score : null;
  const issues = typeof job.result.issues === "number" ? job.result.issues : null;
  if (complete) {
    return `${score !== null ? `${scoreRating(score)} · overall score ${score}` : "Verified findings are ready."}${issues !== null ? ` · ${issues} issues found` : ""}`;
  }
  return "Live from the crawl — not a timer.";
}

function chips(job: Job | null) {
  if (!job) return [];
  if (job.job_type === "collect_markets") {
    const items = [];
    if (Array.isArray(job.result.sources)) items.push(`${job.result.sources.length} sources`);
    if (job.result.created != null) items.push(`${job.result.created} new`);
    return items;
  }
  if (isCsvImport(job.job_type)) {
    const items = [];
    if (job.result.kind) items.push(String(job.result.kind));
    if (job.result.created != null) items.push(`${job.result.created} imported`);
    return items;
  }
  if (job.job_type === "sync_commerce" && job.result.orders != null) {
    return [`${job.result.orders} orders`];
  }
  if (job.job_type === "discover_leads" && job.result.discovered != null) {
    return [`${job.result.discovered} found`];
  }
  if (job.job_type === "analyze_market") {
    const items = [];
    if (job.result.served_cities != null) items.push(`${job.result.served_cities} served`);
    if (job.result.scored_cities != null) items.push(`${job.result.scored_cities} scored`);
    return items;
  }
  const pages = typeof job.result.pages_discovered === "number" ? job.result.pages_discovered : typeof job.result.pages_crawled === "number" ? job.result.pages_crawled : null;
  return pages != null ? [`${pages} pages crawled`] : [];
}

function failureMessage(job: Job) {
  if (job.job_type === "collect_markets") {
    return job.error || "No enabled lead source or open-data API returned listings. Scores stay empty.";
  }
  if (isCsvImport(job.job_type)) {
    return job.error || "The CSV could not be imported. Download the template, keep the header row, then import the filled file.";
  }
  if (job.job_type === "sync_commerce") {
    return job.error || "Store sync failed. Test the connection, then try again.";
  }
  if (job.job_type === "analyze_business") {
    return job.error || "No placed orders to analyze. Import a filled orders CSV or sync a store first.";
  }
  if (job.job_type === "analyze_market") {
    return job.error || "Market analysis failed. Save business input, then try again.";
  }
  if (job.job_type === "apply_audit_fixes") {
    return job.error || "Recommended fixes could not be applied. Test access, then try again.";
  }
  if (job.job_type === "check_keyword_ranks") {
    return job.error || "Keyword check failed. Save website keywords and enable a licensed search source.";
  }
  if (job.job_type === "discover_leads") {
    return job.error || "Discovery failed. Check that a lead source is enabled.";
  }
  return job.error || "The audit failed. Check that the site is public HTTPS.";
}

function successMessage(job: Job) {
  if (job.job_type === "collect_markets") {
    return subtitle(job, true);
  }
  if (isCsvImport(job.job_type)) {
    const extra = Array.isArray(job.result.skip_reasons) && job.result.skip_reasons.length ? ` ${job.result.skip_reasons[0]}` : "";
    return `${subtitle(job, true)}${extra}`;
  }
  if (job.job_type === "sync_commerce") {
    const created = Number(job.result.opportunities_created ?? 0);
    return `${subtitle(job, true)}${created ? ` ${created} opportunities recorded from evidence.` : ""}`;
  }
  if (job.job_type === "analyze_business") {
    return subtitle(job, true);
  }
  if (job.job_type === "analyze_market") {
    return subtitle(job, true);
  }
  if (job.job_type === "apply_audit_fixes") {
    return subtitle(job, true);
  }
  if (job.job_type === "check_keyword_ranks") {
    return subtitle(job, true);
  }
  if (job.job_type === "discover_leads") {
    return subtitle(job, true);
  }
  const score = typeof job.result.overall_score === "number" ? job.result.overall_score : null;
  const issues = typeof job.result.issues === "number" ? job.result.issues : null;
  return `Audit complete${score !== null ? ` — overall score ${score}` : ""}.${issues !== null ? ` ${issues} issues found.` : " Findings are ready to review."}`;
}

export function JobProgressPanel({ job, error, kind }: { job: Job | null; error?: string; kind?: string }) {
  const stages = stagesFor(job, kind);
  const current = activeIndex(job, stages);
  const failed = job?.status === "FAILED";
  const complete = job?.status === "COMPLETED";
  const percent = complete ? 100 : Math.min(job?.progress ?? 0, 99);
  const stageLabel = headline(job, complete, failed);
  const visible = stages.filter((item) => item.key !== "Queued");
  const ringTone = failed ? "error" : "progress";
  const labels = chips(job);

  return (
    <Stack spacing={3}>
      <Stack spacing={1.5} sx={{ alignItems: "center", textAlign: "center" }}>
        <Box
          sx={{
            position: "relative",
            "@keyframes seonetGlow": {
              "0%, 100%": { opacity: 0.45, transform: "scale(0.92)" },
              "50%": { opacity: 1, transform: "scale(1.06)" },
            },
            "&::before": {
              content: '""',
              position: "absolute",
              inset: -18,
              borderRadius: "50%",
              background: failed
                ? "radial-gradient(circle, rgba(192,57,43,0.28), transparent 68%)"
                : "radial-gradient(circle, rgba(46,196,182,0.32), transparent 68%)",
              animation: !complete && !failed ? "seonetGlow 2.4s ease-in-out infinite" : "none",
              pointerEvents: "none",
            },
          }}
        >
          <ScoreRing
            value={job ? percent : null}
            size={148}
            stroke={11}
            label={stageLabel}
            tone={ringTone}
            suffix={complete || failed ? undefined : "%"}
            icon={complete ? "check" : failed ? "error" : undefined}
          />
        </Box>
        <Typography variant="h4">{stageLabel}</Typography>
        <Typography color="text.secondary">{subtitle(job, complete)}</Typography>
        {labels.map((item) => (
          <Chip key={item} size="small" label={item} />
        ))}
      </Stack>
      <Box>
        {visible.map((item, index) => {
          const stageNumber = index + 1;
          const done = current > stageNumber || complete;
          const active = current === stageNumber && !complete && !failed;
          const failedHere = failed && current === stageNumber;
          const last = index === visible.length - 1;
          return (
            <Stack key={item.key} direction="row" spacing={1.5} sx={{ alignItems: "stretch" }}>
              <Box sx={{ width: 22, display: "flex", flexDirection: "column", alignItems: "center" }}>
                <Box
                  sx={{
                    width: 22,
                    height: 22,
                    borderRadius: "50%",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                    color: done ? "secondary.main" : failedHere ? "error.main" : active ? "secondary.main" : "text.disabled",
                    border: done || failedHere ? "none" : "2px solid",
                    borderColor: active ? "secondary.main" : "divider",
                    "@keyframes seonetDot": {
                      "0%, 100%": { boxShadow: "0 0 0 0 rgba(20,138,153,0.4)" },
                      "50%": { boxShadow: "0 0 0 7px rgba(20,138,153,0)" },
                    },
                    animation: active ? "seonetDot 1.6s ease-out infinite" : "none",
                  }}
                >
                  {done ? (
                    <CheckCircleIcon sx={{ fontSize: 22 }} />
                  ) : failedHere ? (
                    <ErrorOutlineIcon sx={{ fontSize: 20 }} />
                  ) : (
                    <Box sx={{ width: 6, height: 6, borderRadius: "50%", bgcolor: "currentColor" }} />
                  )}
                </Box>
                {last ? null : (
                  <Box
                    sx={{
                      width: 2,
                      flex: 1,
                      minHeight: 18,
                      my: 0.4,
                      borderRadius: 1,
                      bgcolor: done ? "secondary.main" : "divider",
                    }}
                  />
                )}
              </Box>
              <Box sx={{ pb: last ? 0 : 1.75, pt: 0.1 }}>
                <Typography sx={{ fontWeight: active || done ? 650 : 500, color: failedHere ? "error.main" : "text.primary" }}>
                  {item.label}
                </Typography>
                {active || failedHere ? (
                  <Typography variant="body2" color="text.secondary">
                    {failedHere ? "This step did not finish." : item.hint}
                  </Typography>
                ) : null}
              </Box>
            </Stack>
          );
        })}
      </Box>
      {error ? <Alert severity="warning">{error}</Alert> : null}
      {failed && job ? <Alert severity="error">{failureMessage(job)}</Alert> : null}
      {complete && job ? <Alert severity="success">{successMessage(job)}</Alert> : null}
    </Stack>
  );
}
