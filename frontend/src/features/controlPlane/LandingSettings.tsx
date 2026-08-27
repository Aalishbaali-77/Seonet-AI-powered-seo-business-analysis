"use client";

import { Alert, Box, Button, Card, CardContent, Stack, TextField, Typography } from "@mui/material";
import { useEffect, useState } from "react";

import { PageHeader } from "@/components/common/PageHeader";
import { ErrorState } from "@/components/feedback/ErrorState";
import { LoadingState } from "@/components/feedback/LoadingState";
import { platformAdminApi } from "@/services/platformAdminApi";
import { useAppDispatch } from "@/store/hooks";
import { landingSet } from "@/store/slices/uiSlice";
import { defaultLanding, type LandingContent } from "@/types/api";

type FieldSpec<T> = { key: keyof T & string; label: string; multiline?: boolean };

function RepeatEditor<T extends Record<string, string>>({
  items,
  blank,
  fields,
  onChange,
  addLabel,
}: {
  items: T[];
  blank: T;
  fields: FieldSpec<T>[];
  onChange: (items: T[]) => void;
  addLabel: string;
}) {
  return (
    <Stack spacing={2}>
      {items.map((item, index) => (
        <Box key={index} sx={{ p: 2, border: 1, borderColor: "divider", borderRadius: 2 }}>
          <Stack spacing={1.5}>
            {fields.map((field) => (
              <TextField
                key={field.key}
                label={field.label}
                value={item[field.key] ?? ""}
                multiline={field.multiline}
                minRows={field.multiline ? 2 : undefined}
                onChange={(event) => {
                  const next = items.map((row, rowIndex) => (rowIndex === index ? { ...row, [field.key]: event.target.value } : row));
                  onChange(next);
                }}
              />
            ))}
            <Button
              size="small"
              onClick={() => onChange(items.filter((_, rowIndex) => rowIndex !== index))}
              sx={{ alignSelf: "flex-start" }}
            >
              Remove
            </Button>
          </Stack>
        </Box>
      ))}
      <Button variant="outlined" onClick={() => onChange([...items, { ...blank }])} sx={{ alignSelf: "flex-start" }}>
        {addLabel}
      </Button>
    </Stack>
  );
}

export function LandingSettings() {
  const dispatch = useAppDispatch();
  const [form, setForm] = useState<LandingContent>(defaultLanding);
  const [ready, setReady] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState("");

  const apply = (next: LandingContent) => {
    setForm(next);
    dispatch(landingSet(next));
  };

  const load = () =>
    platformAdminApi
      .landing()
      .then((data) => {
        apply(data);
        setError("");
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setReady(true));

  useEffect(() => {
    void load();
  }, []);

  const setField = <K extends keyof LandingContent>(key: K, value: LandingContent[K]) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  return (
    <Stack spacing={3}>
      <PageHeader
        eyebrow="Website"
        title="Landing page"
        description="Edit public copy here. Pricing cards come from Packages (public catalog). Product cards come from active Modules. Placeholders: {product} {owner} {description} {tagline}."
        actions={
          <Button
            variant="contained"
            disabled={saving}
            onClick={async () => {
              setSaving(true);
              setSaved("");
              try {
                apply(await platformAdminApi.updateLanding(form));
                setSaved("Landing page saved.");
                setError("");
              } catch (err) {
                setError(err instanceof Error ? err.message : "Unable to save landing page.");
              } finally {
                setSaving(false);
              }
            }}
          >
            {saving ? "Saving…" : "Save landing page"}
          </Button>
        }
      />
      {error ? <ErrorState message={error} onRetry={() => void load()} /> : null}
      {saved ? <Alert severity="success">{saved}</Alert> : null}
      {!ready && !error ? <LoadingState /> : null}
      {ready ? (
        <>
          <Card variant="outlined">
            <CardContent>
              <Stack spacing={2}>
                <Typography variant="h4">Navigation</Typography>
                <RepeatEditor
                  items={form.nav}
                  blank={{ id: "", label: "" }}
                  fields={[
                    { key: "id", label: "Section id (product, how-it-works, pricing, security, faq)" },
                    { key: "label", label: "Label" },
                  ]}
                  onChange={(nav) => setField("nav", nav)}
                  addLabel="Add link"
                />
              </Stack>
            </CardContent>
          </Card>
          <Card variant="outlined">
            <CardContent>
              <Stack spacing={2}>
                <Typography variant="h4">Hero</Typography>
                <TextField label="Eyebrow" value={form.hero_eyebrow} onChange={(event) => setField("hero_eyebrow", event.target.value)} helperText="Empty uses the legal name." />
                <TextField label="Headline" value={form.hero_title} onChange={(event) => setField("hero_title", event.target.value)} helperText="Empty uses the product tagline." />
                <TextField label="Body" value={form.hero_body} onChange={(event) => setField("hero_body", event.target.value)} multiline minRows={3} />
                <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                  <TextField label="Primary CTA" value={form.hero_primary_cta} onChange={(event) => setField("hero_primary_cta", event.target.value)} fullWidth />
                  <TextField label="Secondary CTA" value={form.hero_secondary_cta} onChange={(event) => setField("hero_secondary_cta", event.target.value)} fullWidth />
                  <TextField label="Secondary link" value={form.hero_secondary_href} onChange={(event) => setField("hero_secondary_href", event.target.value)} fullWidth />
                </Stack>
              </Stack>
            </CardContent>
          </Card>
          <Card variant="outlined">
            <CardContent>
              <Stack spacing={2}>
                <Typography variant="h4">Stats</Typography>
                <RepeatEditor
                  items={form.stats}
                  blank={{ value: "", label: "" }}
                  fields={[
                    { key: "value", label: "Value" },
                    { key: "label", label: "Label" },
                  ]}
                  onChange={(stats) => setField("stats", stats)}
                  addLabel="Add stat"
                />
              </Stack>
            </CardContent>
          </Card>
          <Card variant="outlined">
            <CardContent>
              <Stack spacing={2}>
                <Typography variant="h4">Why switch</Typography>
                <TextField label="Eyebrow" value={form.pains_eyebrow} onChange={(event) => setField("pains_eyebrow", event.target.value)} />
                <TextField label="Title" value={form.pains_title} onChange={(event) => setField("pains_title", event.target.value)} />
                <TextField label="Body" value={form.pains_body} onChange={(event) => setField("pains_body", event.target.value)} multiline minRows={2} />
                <RepeatEditor
                  items={form.pains}
                  blank={{ title: "", body: "" }}
                  fields={[
                    { key: "title", label: "Title" },
                    { key: "body", label: "Body", multiline: true },
                  ]}
                  onChange={(pains) => setField("pains", pains)}
                  addLabel="Add card"
                />
              </Stack>
            </CardContent>
          </Card>
          <Card variant="outlined">
            <CardContent>
              <Stack spacing={2}>
                <Typography variant="h4">Product modules</Typography>
                <Typography color="text.secondary">Cards list every active module. Edit names and descriptions under Modules & features.</Typography>
                <TextField label="Eyebrow" value={form.product_eyebrow} onChange={(event) => setField("product_eyebrow", event.target.value)} />
                <TextField label="Title" value={form.product_title} onChange={(event) => setField("product_title", event.target.value)} />
                <TextField label="Body" value={form.product_body} onChange={(event) => setField("product_body", event.target.value)} multiline minRows={2} />
              </Stack>
            </CardContent>
          </Card>
          <Card variant="outlined">
            <CardContent>
              <Stack spacing={2}>
                <Typography variant="h4">How it works</Typography>
                <TextField label="Eyebrow" value={form.steps_eyebrow} onChange={(event) => setField("steps_eyebrow", event.target.value)} />
                <TextField label="Title" value={form.steps_title} onChange={(event) => setField("steps_title", event.target.value)} />
                <TextField label="Body" value={form.steps_body} onChange={(event) => setField("steps_body", event.target.value)} multiline minRows={2} />
                <RepeatEditor
                  items={form.steps}
                  blank={{ step: "", title: "", body: "" }}
                  fields={[
                    { key: "step", label: "Step" },
                    { key: "title", label: "Title" },
                    { key: "body", label: "Body", multiline: true },
                  ]}
                  onChange={(steps) => setField("steps", steps)}
                  addLabel="Add step"
                />
                <Typography variant="subtitle1">Workspace and control plane</Typography>
                <TextField label="Workspace eyebrow" value={form.workspace_eyebrow} onChange={(event) => setField("workspace_eyebrow", event.target.value)} />
                <TextField label="Workspace title" value={form.workspace_title} onChange={(event) => setField("workspace_title", event.target.value)} />
                <TextField label="Workspace body" value={form.workspace_body} onChange={(event) => setField("workspace_body", event.target.value)} multiline minRows={2} />
                <TextField label="Control-plane eyebrow" value={form.control_plane_eyebrow} onChange={(event) => setField("control_plane_eyebrow", event.target.value)} />
                <TextField label="Control-plane title" value={form.control_plane_title} onChange={(event) => setField("control_plane_title", event.target.value)} />
                <TextField label="Control-plane body" value={form.control_plane_body} onChange={(event) => setField("control_plane_body", event.target.value)} multiline minRows={2} />
              </Stack>
            </CardContent>
          </Card>
          <Card variant="outlined">
            <CardContent>
              <Stack spacing={2}>
                <Typography variant="h4">Pricing section</Typography>
                <Typography color="text.secondary">Cards list public, active packages. Featured, price, CTA, and included modules are edited on each package.</Typography>
                <TextField label="Eyebrow" value={form.pricing_eyebrow} onChange={(event) => setField("pricing_eyebrow", event.target.value)} />
                <TextField label="Title" value={form.pricing_title} onChange={(event) => setField("pricing_title", event.target.value)} />
                <TextField label="Body" value={form.pricing_body} onChange={(event) => setField("pricing_body", event.target.value)} multiline minRows={2} />
              </Stack>
            </CardContent>
          </Card>
          <Card variant="outlined">
            <CardContent>
              <Stack spacing={2}>
                <Typography variant="h4">Security</Typography>
                <TextField label="Eyebrow" value={form.security_eyebrow} onChange={(event) => setField("security_eyebrow", event.target.value)} />
                <TextField label="Title" value={form.security_title} onChange={(event) => setField("security_title", event.target.value)} />
                <TextField label="Body" value={form.security_body} onChange={(event) => setField("security_body", event.target.value)} multiline minRows={2} />
                <RepeatEditor
                  items={form.security}
                  blank={{ title: "", body: "" }}
                  fields={[
                    { key: "title", label: "Title" },
                    { key: "body", label: "Body", multiline: true },
                  ]}
                  onChange={(security) => setField("security", security)}
                  addLabel="Add item"
                />
              </Stack>
            </CardContent>
          </Card>
          <Card variant="outlined">
            <CardContent>
              <Stack spacing={2}>
                <Typography variant="h4">FAQ</Typography>
                <TextField label="Eyebrow" value={form.faq_eyebrow} onChange={(event) => setField("faq_eyebrow", event.target.value)} />
                <TextField label="Title" value={form.faq_title} onChange={(event) => setField("faq_title", event.target.value)} />
                <RepeatEditor
                  items={form.faqs}
                  blank={{ q: "", a: "" }}
                  fields={[
                    { key: "q", label: "Question" },
                    { key: "a", label: "Answer", multiline: true },
                  ]}
                  onChange={(faqs) => setField("faqs", faqs)}
                  addLabel="Add question"
                />
              </Stack>
            </CardContent>
          </Card>
          <Card variant="outlined">
            <CardContent>
              <Stack spacing={2}>
                <Typography variant="h4">Closing CTA</Typography>
                <TextField label="Title" value={form.cta_title} onChange={(event) => setField("cta_title", event.target.value)} />
                <TextField label="Body" value={form.cta_body} onChange={(event) => setField("cta_body", event.target.value)} multiline minRows={2} />
                <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                  <TextField label="Primary CTA" value={form.cta_primary} onChange={(event) => setField("cta_primary", event.target.value)} fullWidth />
                  <TextField label="Secondary CTA" value={form.cta_secondary} onChange={(event) => setField("cta_secondary", event.target.value)} fullWidth />
                </Stack>
              </Stack>
            </CardContent>
          </Card>
        </>
      ) : null}
    </Stack>
  );
}
