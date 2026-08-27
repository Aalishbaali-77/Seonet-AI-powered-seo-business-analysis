"use client";

import CloseIcon from "@mui/icons-material/Close";
import MenuIcon from "@mui/icons-material/Menu";
import {
  AppBar,
  Box,
  Button,
  Container,
  Divider,
  Drawer,
  IconButton,
  Link as MuiLink,
  Stack,
  Toolbar,
  Typography,
} from "@mui/material";
import { alpha } from "@mui/material/styles";
import NextLink from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { BrandMark } from "@/components/branding/BrandMark";
import { postAuthPath } from "@/lib/authPaths";
import { useAppSelector } from "@/store/hooks";

export function PublicShell({ children }: { children: ReactNode }) {
  const branding = useAppSelector((state) => state.ui.branding);
  const landingNav = useAppSelector((state) => state.ui.landing.nav);
  const user = useAppSelector((state) => state.auth.user);
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const appHref = user ? postAuthPath(user) : "/register";
  const primaryCta = user ? (user.is_platform_admin ? "Open control plane" : "Open workspace") : "Get started";
  const supportHref = branding.support_url || "mailto:hello@siglobalsolutions.com";
  const year = new Date().getFullYear();
  const onHome = pathname === "/";
  const sectionHref = (id: string) => (onHome ? `#${id}` : `/#${id}`);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <Box sx={{ minHeight: "100vh", display: "flex", flexDirection: "column", bgcolor: "background.default", color: "text.primary" }}>
      <AppBar
        position="fixed"
        color="inherit"
        elevation={0}
        sx={{
          top: 0,
          left: 0,
          right: 0,
          zIndex: (theme) => theme.zIndex.appBar,
          borderBottom: 1,
          borderColor: scrolled || !onHome ? "divider" : "transparent",
          bgcolor: (theme) => alpha(theme.palette.background.default, scrolled || !onHome ? 0.92 : 0.78),
          backdropFilter: "blur(18px)",
          boxShadow: scrolled ? "0 8px 24px rgba(15, 27, 45, 0.06)" : "none",
          transition: "background-color 160ms ease, border-color 160ms ease, box-shadow 160ms ease",
        }}
      >
        <Toolbar sx={{ minHeight: { xs: 64, md: 72 }, px: { xs: 2, md: 3 }, gap: 2 }}>
          <Box
            component={NextLink}
            href="/"
            sx={{
              textDecoration: "none",
              color: "inherit",
              display: "flex",
              alignItems: "center",
              flexShrink: 0,
              minWidth: 0,
              mr: { xs: 1, md: 0 },
            }}
          >
            <BrandMark variant="nav" />
          </Box>
          <Stack direction="row" spacing={0.5} sx={{ display: { xs: "none", md: "flex" }, mx: "auto" }}>
            {landingNav.map((item) => (
              <Button key={item.id} href={sectionHref(item.id)} color="inherit" sx={{ color: "text.secondary" }}>
                {item.label}
              </Button>
            ))}
            <Button component={NextLink} href="/docs" color="inherit" sx={{ color: pathname.startsWith("/docs") ? "primary.main" : "text.secondary" }}>
              Docs
            </Button>
          </Stack>
          <Stack direction="row" spacing={1} sx={{ ml: { xs: "auto", md: 0 } }}>
            {user ? (
              <Button component={NextLink} href={appHref} variant="contained">
                {primaryCta}
              </Button>
            ) : (
              <>
                <Button
                  component={NextLink}
                  href="/login"
                  color="inherit"
                  variant={pathname === "/login" ? "outlined" : "text"}
                  sx={{ display: { xs: "none", sm: "inline-flex" } }}
                >
                  Sign in
                </Button>
                <Button component={NextLink} href="/register" variant="contained">
                  Get started
                </Button>
              </>
            )}
            <IconButton aria-label="Open menu" onClick={() => setMenuOpen(true)} sx={{ display: { md: "none" } }}>
              <MenuIcon />
            </IconButton>
          </Stack>
        </Toolbar>
      </AppBar>
      <Toolbar sx={{ minHeight: { xs: 64, md: 72 }, flexShrink: 0 }} />

      <Drawer anchor="right" open={menuOpen} onClose={() => setMenuOpen(false)}>
        <Box sx={{ width: 280, p: 2 }}>
          <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center", mb: 2 }}>
            <BrandMark variant="nav" />
            <IconButton aria-label="Close menu" onClick={() => setMenuOpen(false)}>
              <CloseIcon />
            </IconButton>
          </Stack>
          <Stack spacing={0.5}>
            {landingNav.map((item) => (
              <Button key={item.id} href={sectionHref(item.id)} onClick={() => setMenuOpen(false)} sx={{ justifyContent: "flex-start" }}>
                {item.label}
              </Button>
            ))}
            <Button component={NextLink} href="/docs" onClick={() => setMenuOpen(false)} sx={{ justifyContent: "flex-start" }}>
              Docs
            </Button>
            <Divider sx={{ my: 1 }} />
            {user ? (
              <Button component={NextLink} href={appHref} variant="contained" onClick={() => setMenuOpen(false)}>
                {primaryCta}
              </Button>
            ) : (
              <>
                <Button component={NextLink} href="/login" onClick={() => setMenuOpen(false)} sx={{ justifyContent: "flex-start" }}>
                  Sign in
                </Button>
                <Button component={NextLink} href="/register" variant="contained" onClick={() => setMenuOpen(false)}>
                  Get started
                </Button>
              </>
            )}
          </Stack>
        </Box>
      </Drawer>

      <Box sx={{ flex: 1, display: "flex", flexDirection: "column" }}>{children}</Box>

      <Box component="footer" sx={{ py: { xs: 6, md: 8 }, borderTop: 1, borderColor: "divider", bgcolor: "background.paper" }}>
        <Container maxWidth="lg" sx={{ px: { xs: 2, sm: 3 } }}>
          <Box sx={{ display: "grid", gap: 4, gridTemplateColumns: { xs: "1fr", sm: "1.4fr 1fr 1fr 1fr" } }}>
            <Box>
              <BrandMark variant="footer" subtitle={branding.tagline} />
              <Typography variant="body2" color="text.secondary" sx={{ mt: 2, maxWidth: 320 }}>
                {branding.copyright_text || `© ${year} ${branding.legal_name}. All rights reserved.`}
              </Typography>
            </Box>
            <Stack spacing={1}>
              <Typography variant="h5">Product</Typography>
              {landingNav.map((item) => (
                <MuiLink key={item.id} href={sectionHref(item.id)} color="text.secondary" underline="hover">
                  {item.label}
                </MuiLink>
              ))}
              <MuiLink component={NextLink} href="/docs" color="text.secondary" underline="hover">
                User guide
              </MuiLink>
            </Stack>
            <Stack spacing={1}>
              <Typography variant="h5">Workspace</Typography>
              <MuiLink component={NextLink} href="/docs" color="text.secondary" underline="hover">
                User guide
              </MuiLink>
              <MuiLink component={NextLink} href="/login" color="text.secondary" underline="hover">
                Sign in
              </MuiLink>
              <MuiLink component={NextLink} href="/register" color="text.secondary" underline="hover">
                Create workspace
              </MuiLink>
              <MuiLink component={NextLink} href="/platform" color="text.secondary" underline="hover">
                Control plane
              </MuiLink>
            </Stack>
            <Stack spacing={1}>
              <Typography variant="h5">Company</Typography>
              <Typography variant="body2" color="text.secondary">
                {branding.legal_name}
              </Typography>
              {branding.support_email ? (
                <MuiLink href={`mailto:${branding.support_email}`} color="text.secondary" underline="hover">
                  {branding.support_email}
                </MuiLink>
              ) : (
                <MuiLink href={supportHref} color="text.secondary" underline="hover">
                  Contact
                </MuiLink>
              )}
            </Stack>
          </Box>
          {branding.login_footer ? (
            <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 4 }}>
              {branding.login_footer}
            </Typography>
          ) : null}
        </Container>
      </Box>
    </Box>
  );
}
