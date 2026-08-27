"use client";

import MenuIcon from "@mui/icons-material/Menu";
import {
  Alert,
  Box,
  Button,
  Chip,
  Divider,
  Drawer,
  IconButton,
  Link as MuiLink,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import NextLink from "next/link";
import { useMemo, useState } from "react";

import { PublicShell } from "@/features/marketing/PublicShell";
import { DOCS_GROUPS, DOCS_PAGES, type DocsBlock, type DocsPage } from "@/features/docs/content";

function BlockView({ block }: { block: DocsBlock }) {
  if (block.type === "p") {
    return (
      <Typography color="text.secondary" sx={{ fontSize: "1.02rem", lineHeight: 1.75 }}>
        {block.text}
      </Typography>
    );
  }
  if (block.type === "h2") {
    return (
      <Typography variant="h3" sx={{ pt: 2 }}>
        {block.text}
      </Typography>
    );
  }
  if (block.type === "h3") {
    return (
      <Typography variant="h4" sx={{ pt: 1 }}>
        {block.text}
      </Typography>
    );
  }
  if (block.type === "ul" || block.type === "ol") {
    const ListTag = block.type === "ol" ? "ol" : "ul";
    return (
      <Box
        component={ListTag}
        sx={{ m: 0, pl: 3, color: "text.secondary", "& li": { mb: 1, lineHeight: 1.7, fontSize: "1.02rem" } }}
      >
        {block.items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </Box>
    );
  }
  if (block.type === "callout") {
    const severity = block.tone === "warning" ? "warning" : block.tone === "success" ? "success" : "info";
    return (
      <Alert severity={severity}>
        <Typography sx={{ fontWeight: 600 }}>{block.title}</Typography>
        <Typography variant="body2" sx={{ mt: 0.5 }}>
          {block.text}
        </Typography>
      </Alert>
    );
  }
  if (block.type === "steps") {
    return (
      <Stack spacing={1.5}>
        {block.items.map((item, index) => (
          <Paper key={item.title} variant="outlined" sx={{ p: 2 }}>
            <Typography sx={{ fontWeight: 600 }}>
              {index + 1}. {item.title}
            </Typography>
            <Typography color="text.secondary" sx={{ mt: 0.5 }}>
              {item.body}
            </Typography>
          </Paper>
        ))}
      </Stack>
    );
  }
  return (
    <Box sx={{ overflowX: "auto" }}>
      <Table size="small">
        <TableHead>
          <TableRow>
            {block.headers.map((header) => (
              <TableCell key={header} sx={{ fontWeight: 600 }}>
                {header}
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {block.rows.map((row) => (
            <TableRow key={row[0]}>
              {row.map((cell) => (
                <TableCell key={cell} sx={{ verticalAlign: "top", color: "text.secondary" }}>
                  {cell}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Box>
  );
}

function NavList({ current, onNavigate }: { current: string; onNavigate?: () => void }) {
  return (
    <Stack spacing={2.5}>
      {DOCS_GROUPS.map((group) => (
        <Box key={group}>
          <Typography variant="caption" color="text.secondary" sx={{ px: 1, letterSpacing: "0.06em", textTransform: "uppercase" }}>
            {group}
          </Typography>
          <Stack spacing={0.25} sx={{ mt: 0.75 }}>
            {DOCS_PAGES.filter((page) => page.group === group).map((page) => {
              const active = page.href === current;
              return (
                <Button
                  key={page.href}
                  component={NextLink}
                  href={page.href}
                  onClick={onNavigate}
                  sx={{
                    justifyContent: "flex-start",
                    textAlign: "left",
                    color: active ? "primary.main" : "text.secondary",
                    bgcolor: active ? "action.selected" : "transparent",
                    fontWeight: active ? 600 : 500,
                    px: 1.25,
                  }}
                >
                  {page.title}
                </Button>
              );
            })}
          </Stack>
        </Box>
      ))}
    </Stack>
  );
}

export function DocsSite({ page }: { page: DocsPage }) {
  const [open, setOpen] = useState(false);
  const index = useMemo(() => DOCS_PAGES.findIndex((item) => item.href === page.href), [page.href]);
  const previous = index > 0 ? DOCS_PAGES[index - 1] : null;
  const next = index >= 0 && index < DOCS_PAGES.length - 1 ? DOCS_PAGES[index + 1] : null;

  return (
    <PublicShell>
      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "280px minmax(0, 1fr)" }, minHeight: "70vh" }}>
        <Box
          component="nav"
          sx={{
            display: { xs: "none", md: "block" },
            borderRight: 1,
            borderColor: "divider",
            px: 2,
            py: 4,
            bgcolor: "background.paper",
          }}
        >
          <Typography variant="subtitle2" color="secondary" sx={{ px: 1, mb: 2 }}>
            Documentation
          </Typography>
          <NavList current={page.href} />
        </Box>
        <Box sx={{ px: { xs: 2, sm: 3, lg: 6 }, py: { xs: 3, md: 5 }, maxWidth: 880 }}>
          <Stack direction="row" spacing={1} sx={{ alignItems: "center", mb: 2, display: { md: "none" } }}>
            <IconButton aria-label="Open documentation menu" onClick={() => setOpen(true)}>
              <MenuIcon />
            </IconButton>
            <Typography variant="subtitle2">Documentation</Typography>
          </Stack>
          <Chip label={page.group} size="small" variant="outlined" color="secondary" sx={{ mb: 1.5 }} />
          <Typography variant="h1" sx={{ fontSize: { xs: "1.85rem", md: "2.35rem" }, mb: 1.25 }}>
            {page.title}
          </Typography>
          <Typography color="text.secondary" sx={{ mb: 3, fontSize: "1.05rem" }}>
            {page.description}
          </Typography>
          <Stack spacing={2.25}>
            {page.blocks.map((block, index) => (
              <BlockView key={`${page.href}-${index}`} block={block} />
            ))}
          </Stack>
          <Divider sx={{ my: 4 }} />
          <Box sx={{ display: "flex", justifyContent: "space-between", gap: 2, flexWrap: "wrap" }}>
            {previous ? (
              <MuiLink component={NextLink} href={previous.href} underline="hover">
                Previous: {previous.title}
              </MuiLink>
            ) : (
              <span />
            )}
            {next ? (
              <MuiLink component={NextLink} href={next.href} underline="hover">
                Next: {next.title}
              </MuiLink>
            ) : null}
          </Box>
        </Box>
      </Box>
      <Drawer anchor="left" open={open} onClose={() => setOpen(false)}>
        <Box sx={{ width: 300, p: 2 }}>
          <Typography variant="subtitle2" color="secondary" sx={{ mb: 2 }}>
            Documentation
          </Typography>
          <NavList current={page.href} onNavigate={() => setOpen(false)} />
        </Box>
      </Drawer>
    </PublicShell>
  );
}
