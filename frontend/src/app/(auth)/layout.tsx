"use client";

import { Box, Paper } from "@mui/material";

import { PublicShell } from "@/features/marketing/PublicShell";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <PublicShell>
      <Box
        sx={{
          position: "relative",
          overflow: "hidden",
          flex: 1,
          display: "grid",
          placeItems: "center",
          px: { xs: 2, sm: 3 },
          py: { xs: 6, md: 8 },
          minHeight: 480,
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
        <Paper
          elevation={0}
          sx={{
            position: "relative",
            width: "100%",
            maxWidth: 480,
            p: { xs: 2.5, sm: 4 },
            border: 1,
            borderColor: "divider",
            borderRadius: 3,
          }}
        >
          {children}
        </Paper>
      </Box>
    </PublicShell>
  );
}
