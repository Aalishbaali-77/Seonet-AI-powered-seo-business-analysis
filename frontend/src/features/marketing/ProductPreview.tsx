"use client";

import FactCheckOutlined from "@mui/icons-material/FactCheckOutlined";
import HandshakeOutlined from "@mui/icons-material/HandshakeOutlined";
import LanguageOutlined from "@mui/icons-material/LanguageOutlined";
import StorefrontOutlined from "@mui/icons-material/StorefrontOutlined";
import { Box, Chip, LinearProgress, Stack, Typography } from "@mui/material";

import { useAppSelector } from "@/store/hooks";

const JOB_STAGES = [
  { label: "Collecting SEO keywords", value: 20 },
  { label: "Checking licensed search", value: 62 },
  { label: "Drafting suggestions", value: 84 },
];

export function ProductPreview() {
  const product = useAppSelector((state) => state.ui.branding.product_name);
  return (
    <Box
      sx={{
        borderRadius: 3,
        overflow: "hidden",
        border: 1,
        borderColor: "divider",
        bgcolor: "background.paper",
        boxShadow: "0 24px 80px rgba(11, 79, 108, 0.14)",
      }}
    >
      <Stack direction="row" spacing={1} sx={{ px: 2, py: 1.25, bgcolor: "action.hover", alignItems: "center", borderBottom: 1, borderColor: "divider" }}>
        <Box sx={{ width: 10, height: 10, borderRadius: "50%", bgcolor: "#E57373" }} />
        <Box sx={{ width: 10, height: 10, borderRadius: "50%", bgcolor: "#FFD54F" }} />
        <Box sx={{ width: 10, height: 10, borderRadius: "50%", bgcolor: "#81C784" }} />
        <Box sx={{ flex: 1, ml: 2, px: 1.5, py: 0.5, borderRadius: 999, bgcolor: "background.paper", border: 1, borderColor: "divider" }}>
          <Typography variant="caption" color="text.secondary">
            app · {product.toLowerCase().replace(/\s+/g, "")} · workspace
          </Typography>
        </Box>
      </Stack>
      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "72px 1fr" }, minHeight: { xs: 280, md: 420 } }}>
        <Box sx={{ display: { xs: "none", sm: "flex" }, flexDirection: "column", gap: 1.5, p: 1.5, borderRight: 1, borderColor: "divider", bgcolor: "background.default" }}>
          {[LanguageOutlined, FactCheckOutlined, StorefrontOutlined, HandshakeOutlined].map((Icon, index) => (
            <Box
              key={index}
              sx={{
                width: 40,
                height: 40,
                borderRadius: 1.5,
                display: "grid",
                placeItems: "center",
                bgcolor: index === 0 ? "primary.main" : "transparent",
                color: index === 0 ? "primary.contrastText" : "text.secondary",
                mx: "auto",
              }}
            >
              <Icon fontSize="small" />
            </Box>
          ))}
        </Box>
        <Box sx={{ p: { xs: 2, md: 3 } }}>
          <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center", mb: 2 }}>
            <Box>
              <Typography variant="subtitle2" color="secondary">
                Background job
              </Typography>
              <Typography variant="h4">Keyword ranks</Typography>
            </Box>
            <Chip size="small" color="secondary" variant="outlined" label="Working" />
          </Stack>
          <Box sx={{ display: "grid", gap: 1.5, gridTemplateColumns: { xs: "1fr 1fr", md: "repeat(4, 1fr)" }, mb: 2 }}>
            {[
              { label: "SEO audit", value: "From crawl" },
              { label: "Keywords", value: "Licensed sample" },
              { label: "Commerce", value: "Orders first" },
              { label: "Markets", value: "Signals only" },
            ].map((item) => (
              <Box key={item.label} sx={{ p: 1.5, borderRadius: 2, border: 1, borderColor: "divider", bgcolor: "background.default" }}>
                <Typography variant="caption" color="text.secondary">
                  {item.label}
                </Typography>
                <Typography variant="body2" sx={{ mt: 0.25, fontWeight: 600 }}>
                  {item.value}
                </Typography>
              </Box>
            ))}
          </Box>
          <Box sx={{ p: 2, borderRadius: 2, border: 1, borderColor: "divider" }}>
            <Stack direction="row" sx={{ justifyContent: "space-between", mb: 1 }}>
              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                Checking search results
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Live progress
              </Typography>
            </Stack>
            <LinearProgress variant="determinate" value={JOB_STAGES[1].value} sx={{ height: 8, borderRadius: 999 }} />
            <Stack spacing={1} sx={{ mt: 2 }}>
              {[
                "First-page sample via Custom Search or SerpAPI",
                "Missing position means not in that sample",
                "Claude drafts extra queries on Scale — tagged inference",
              ].map((row) => (
                <Typography key={row} variant="body2" color="text.secondary">
                  · {row}
                </Typography>
              ))}
            </Stack>
          </Box>
        </Box>
      </Box>
    </Box>
  );
}
