"use client";

import { Box, Button, Stack, Typography } from "@mui/material";
import NextLink from "next/link";

import { PublicShell } from "@/features/marketing/PublicShell";

export default function NotFound() {
  return (
    <PublicShell>
      <Box
        sx={{
          position: "relative",
          overflow: "hidden",
          minHeight: { xs: "calc(100vh - 64px)", md: "calc(100vh - 72px)" },
          display: "grid",
          placeItems: "center",
          px: 2,
          py: 8,
        }}
      >
        <Box
          sx={{
            position: "absolute",
            inset: 0,
            background:
              "radial-gradient(900px 420px at 12% -10%, rgba(27, 154, 170, 0.16), transparent 60%), radial-gradient(700px 380px at 92% 0%, rgba(11, 79, 108, 0.12), transparent 55%)",
            pointerEvents: "none",
          }}
        />
        <Stack spacing={2} sx={{ position: "relative", maxWidth: 480, textAlign: "center" }}>
          <Typography variant="subtitle2" color="secondary">
            404
          </Typography>
          <Typography variant="h1" sx={{ fontSize: { xs: "1.8rem", md: "2.2rem" } }}>
            This page is not on the map.
          </Typography>
          <Typography color="text.secondary">The link may be out of date, or the workspace route requires a signed-in session.</Typography>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} sx={{ justifyContent: "center" }}>
            <Button component={NextLink} href="/" variant="contained">
              Back to home
            </Button>
            <Button component={NextLink} href="/login" variant="outlined">
              Sign in
            </Button>
          </Stack>
        </Stack>
      </Box>
    </PublicShell>
  );
}
