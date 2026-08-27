"use client";

import { Alert, Box, Button, Card, CardContent, MenuItem, Stack, TextField, Typography } from "@mui/material";
import { useEffect, useState } from "react";

import { useConfirm } from "@/components/common/ConfirmDialog";
import { ErrorState } from "@/components/feedback/ErrorState";
import { LoadingState } from "@/components/feedback/LoadingState";
import { platformAdminApi } from "@/services/platformAdminApi";
import { useAppDispatch } from "@/store/hooks";
import { brandingSet } from "@/store/slices/uiSlice";
import { defaultBranding, type AppearanceAssetSlot, type PlatformBranding } from "@/types/api";

type AssetSpec = { slot: AppearanceAssetSlot; label: string; hint: string; urlKey: keyof PlatformBranding };

const MASTER_ASSETS: AssetSpec[] = [
  { slot: "logo", label: "Master logo — light", hint: "Used anywhere a placement is empty. PNG, JPEG, WEBP, or GIF. Max 2 MB.", urlKey: "logo_url" },
  { slot: "logo_dark", label: "Master logo — dark", hint: "Optional reverse of the master logo for dark chrome.", urlKey: "logo_dark_url" },
  { slot: "logo_mark", label: "Mark / icon — light", hint: "Square mark for the collapsed sidebar. Falls back to the master logo.", urlKey: "logo_mark_url" },
  { slot: "logo_mark_dark", label: "Mark / icon — dark", hint: "Optional reverse mark for dark chrome.", urlKey: "logo_mark_dark_url" },
];

const PLACEMENT_ASSETS: Array<{ title: string; body: string; items: AssetSpec[] }> = [
  {
    title: "Public navigation",
    body: "Header on the marketing site, sign-in, and register. Empty inherits the master logo.",
    items: [
      { slot: "logo_nav", label: "Nav logo — light", hint: "Compact horizontal lockup recommended.", urlKey: "logo_nav_url" },
      { slot: "logo_nav_dark", label: "Nav logo — dark", hint: "Optional reverse for dark header chrome.", urlKey: "logo_nav_dark_url" },
    ],
  },
  {
    title: "Workspace sidebar",
    body: "Tenant and control-plane sidebars. Empty inherits the master logo; collapsed uses the mark.",
    items: [
      { slot: "logo_sidebar", label: "Sidebar logo — light", hint: "Expanded sidebar lockup.", urlKey: "logo_sidebar_url" },
      { slot: "logo_sidebar_dark", label: "Sidebar logo — dark", hint: "Optional reverse for dark sidebar.", urlKey: "logo_sidebar_dark_url" },
    ],
  },
  {
    title: "Footer",
    body: "Public footer. Empty inherits the master logo.",
    items: [
      { slot: "logo_footer", label: "Footer logo — light", hint: "Can be larger than the nav lockup.", urlKey: "logo_footer_url" },
      { slot: "logo_footer_dark", label: "Footer logo — dark", hint: "Optional reverse for dark footer.", urlKey: "logo_footer_dark_url" },
    ],
  },
  {
    title: "Browser and home screen",
    body: "Tab icon and installed-app icon. Static /favicon.png is only used when these are empty.",
    items: [
      { slot: "favicon", label: "Favicon", hint: "ICO, PNG, or WEBP. Max 512 KB.", urlKey: "favicon_url" },
      { slot: "app_icon", label: "App icon", hint: "Square PNG for bookmarks and home screens.", urlKey: "app_icon_url" },
    ],
  },
];

function AssetCards({
  items,
  form,
  onUpload,
  onClear,
}: {
  items: AssetSpec[];
  form: PlatformBranding;
  onUpload: (slot: AppearanceAssetSlot, file: File, label: string) => void;
  onClear: (slot: AppearanceAssetSlot, label: string) => void;
}) {
  return (
    <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" } }}>
      {items.map((asset) => {
        const url = form[asset.urlKey];
        return (
          <Box key={asset.slot} sx={{ p: 2, border: 1, borderColor: "divider", borderRadius: 2 }}>
            <Stack spacing={1.5}>
              <Typography variant="subtitle2">{asset.label}</Typography>
              <Typography variant="body2" color="text.secondary">
                {asset.hint}
              </Typography>
              {typeof url === "string" && url ? (
                <Box component="img" src={url} alt={asset.label} sx={{ height: 48, maxWidth: "100%", objectFit: "contain", alignSelf: "flex-start" }} />
              ) : (
                <Typography variant="body2" color="text.secondary">
                  Inherits master / static fallback
                </Typography>
              )}
              <Stack direction="row" spacing={1}>
                <Button variant="outlined" component="label" size="small">
                  Upload
                  <Box
                    component="input"
                    type="file"
                    hidden
                    accept="image/png,image/jpeg,image/webp,image/gif,image/x-icon,.ico"
                    onChange={(event) => {
                      const file = (event.target as HTMLInputElement).files?.[0];
                      (event.target as HTMLInputElement).value = "";
                      if (file) {
                        onUpload(asset.slot, file, asset.label);
                      }
                    }}
                  />
                </Button>
                {typeof url === "string" && url ? (
                  <Button size="small" onClick={() => onClear(asset.slot, asset.label)}>
                    Remove
                  </Button>
                ) : null}
              </Stack>
            </Stack>
          </Box>
        );
      })}
    </Box>
  );
}

function ColorField({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  const safe = /^#[0-9A-Fa-f]{6}$/.test(value) ? value : "#0B4F6C";
  return (
    <Stack direction="row" spacing={1.5} sx={{ alignItems: "center" }}>
      <Box
        component="input"
        type="color"
        value={safe}
        onChange={(event) => onChange((event.target as HTMLInputElement).value.toUpperCase())}
        aria-label={label}
        sx={{ width: 48, height: 40, p: 0, border: 1, borderColor: "divider", borderRadius: 1, bgcolor: "transparent", cursor: "pointer" }}
      />
      <TextField label={label} value={value} onChange={(event) => onChange(event.target.value)} sx={{ flex: 1 }} />
    </Stack>
  );
}

export function AppearanceSettings() {
  const dispatch = useAppDispatch();
  const confirm = useConfirm();
  const [form, setForm] = useState<PlatformBranding>(defaultBranding);
  const [ready, setReady] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState("");

  const apply = (next: PlatformBranding) => {
    setForm(next);
    dispatch(brandingSet(next));
  };

  const load = () =>
    platformAdminApi
      .appearance()
      .then((data) => {
        apply(data);
        setError("");
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setReady(true));

  useEffect(() => {
    void load();
  }, []);

  const setField = <K extends keyof PlatformBranding>(key: K, value: PlatformBranding[K]) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  const uploadAsset = async (slot: AppearanceAssetSlot, file: File, label: string) => {
    try {
      apply(await platformAdminApi.uploadAppearanceAsset(slot, file));
      setSaved(`${label} updated.`);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to upload file.");
    }
  };

  const clearAsset = async (slot: AppearanceAssetSlot, label: string) => {
    const ok = await confirm({
      title: "Remove file",
      description: `${label} will be removed. Empty placements inherit the master logo.`,
      confirmLabel: "Remove",
    });
    if (!ok) {
      return;
    }
    try {
      apply(await platformAdminApi.clearAppearanceAsset(slot));
      setSaved(`${label} removed.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to remove file.");
    }
  };

  return (
    <Stack spacing={3}>
      <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center" }}>
        <Typography color="text.secondary">
          Product identity, logos, favicon, and theme used across login, workspaces, and the control plane.
        </Typography>
        <Button
          variant="contained"
          disabled={saving}
          onClick={async () => {
            setSaving(true);
            setSaved("");
            try {
              const next = await platformAdminApi.updateAppearance({
                product_name: form.product_name,
                legal_name: form.legal_name,
                tagline: form.tagline,
                description: form.description,
                support_email: form.support_email,
                support_url: form.support_url,
                login_footer: form.login_footer,
                copyright_text: form.copyright_text,
                default_theme: form.default_theme,
                primary_color: form.primary_color,
                secondary_color: form.secondary_color,
              });
              apply(next);
              setSaved("Appearance saved.");
              setError("");
            } catch (err) {
              setError(err instanceof Error ? err.message : "Unable to save appearance.");
            } finally {
              setSaving(false);
            }
          }}
        >
          {saving ? "Saving…" : "Save appearance"}
        </Button>
      </Stack>
      {error ? <ErrorState message={error} onRetry={() => void load()} /> : null}
      {saved ? <Alert severity="success">{saved}</Alert> : null}
      {!ready && !error ? <LoadingState /> : null}
      {ready ? (
        <>
          <Card variant="outlined">
            <CardContent>
              <Stack spacing={2}>
                <Typography variant="h4">Identity</Typography>
                <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                  <TextField label="Product name" value={form.product_name} onChange={(event) => setField("product_name", event.target.value)} fullWidth />
                  <TextField label="Legal / owner name" value={form.legal_name} onChange={(event) => setField("legal_name", event.target.value)} fullWidth />
                </Stack>
                <TextField label="Tagline" value={form.tagline} onChange={(event) => setField("tagline", event.target.value)} />
                <TextField
                  label="Public description"
                  value={form.description}
                  onChange={(event) => setField("description", event.target.value)}
                  multiline
                  minRows={3}
                />
              </Stack>
            </CardContent>
          </Card>
          <Card variant="outlined">
            <CardContent>
              <Stack spacing={2}>
                <Typography variant="h4">Logos and icons</Typography>
                <Typography color="text.secondary">
                  Each placement can have its own file. Empty slots inherit the master logo, then the static public fallback.
                  SVG is not accepted. Uploads replace the current file immediately.
                </Typography>
                <Typography variant="subtitle1">Master</Typography>
                <AssetCards items={MASTER_ASSETS} form={form} onUpload={uploadAsset} onClear={clearAsset} />
                {PLACEMENT_ASSETS.map((group) => (
                  <Stack key={group.title} spacing={1.5}>
                    <Typography variant="subtitle1">{group.title}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      {group.body}
                    </Typography>
                    <AssetCards items={group.items} form={form} onUpload={uploadAsset} onClear={clearAsset} />
                  </Stack>
                ))}
              </Stack>
            </CardContent>
          </Card>
          <Card variant="outlined">
            <CardContent>
              <Stack spacing={2}>
                <Typography variant="h4">Theme</Typography>
                <TextField
                  select
                  label="Default theme"
                  value={form.default_theme}
                  onChange={(event) => setField("default_theme", event.target.value as PlatformBranding["default_theme"])}
                  helperText="Used on public pages. Signed-in users keep their own preference."
                >
                  <MenuItem value="light">Light (default)</MenuItem>
                  <MenuItem value="dark">Dark</MenuItem>
                  <MenuItem value="system">Match device</MenuItem>
                </TextField>
                <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                  <Box sx={{ flex: 1 }}>
                    <ColorField label="Primary color" value={form.primary_color} onChange={(value) => setField("primary_color", value)} />
                  </Box>
                  <Box sx={{ flex: 1 }}>
                    <ColorField label="Secondary color" value={form.secondary_color} onChange={(value) => setField("secondary_color", value)} />
                  </Box>
                </Stack>
                <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
                  <Box sx={{ width: 28, height: 28, borderRadius: 1, bgcolor: form.primary_color, border: 1, borderColor: "divider" }} />
                  <Box sx={{ width: 28, height: 28, borderRadius: 1, bgcolor: form.secondary_color, border: 1, borderColor: "divider" }} />
                  <Typography variant="body2" color="text.secondary">
                    Live preview applies after save. Color pickers update the form immediately.
                  </Typography>
                </Stack>
              </Stack>
            </CardContent>
          </Card>
          <Card variant="outlined">
            <CardContent>
              <Stack spacing={2}>
                <Typography variant="h4">Support and login</Typography>
                <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                  <TextField label="Support email" value={form.support_email} onChange={(event) => setField("support_email", event.target.value)} fullWidth />
                  <TextField label="Support URL" value={form.support_url} onChange={(event) => setField("support_url", event.target.value)} fullWidth />
                </Stack>
                <TextField label="Login footer" value={form.login_footer} onChange={(event) => setField("login_footer", event.target.value)} helperText="Shown under the sign-in form." />
                <TextField label="Copyright" value={form.copyright_text} onChange={(event) => setField("copyright_text", event.target.value)} />
              </Stack>
            </CardContent>
          </Card>
        </>
      ) : null}
    </Stack>
  );
}
