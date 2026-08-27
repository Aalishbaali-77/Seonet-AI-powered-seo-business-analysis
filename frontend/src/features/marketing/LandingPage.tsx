"use client";

import CheckCircleOutlined from "@mui/icons-material/CheckCircleOutlined";
import ShieldOutlined from "@mui/icons-material/ShieldOutlined";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { Accordion, AccordionDetails, AccordionSummary, Box, Button, Chip, Container, Stack, Typography } from "@mui/material";
import NextLink from "next/link";

import { ProductPreview } from "@/features/marketing/ProductPreview";
import { PublicShell } from "@/features/marketing/PublicShell";
import { fillCopy, formatPlanPrice, interpolateLanding, planCadence, planCta, planFeatureList } from "@/features/marketing/copy";
import { postAuthPath } from "@/lib/authPaths";
import { useAppSelector } from "@/store/hooks";

const sectionSx = { py: { xs: 8, md: 12 }, scrollMarginTop: 88 };

function SectionHeading({ eyebrow, title, body }: { eyebrow: string; title: string; body?: string }) {
  return (
    <Stack spacing={1.25} sx={{ maxWidth: 720, mb: { xs: 4, md: 6 } }}>
      {eyebrow ? (
        <Typography variant="subtitle2" color="secondary">
          {eyebrow}
        </Typography>
      ) : null}
      <Typography variant="h1" sx={{ fontSize: { xs: "1.75rem", md: "2.35rem" } }}>
        {title}
      </Typography>
      {body ? (
        <Typography color="text.secondary" sx={{ fontSize: { xs: "1rem", md: "1.05rem" } }}>
          {body}
        </Typography>
      ) : null}
    </Stack>
  );
}

export function LandingPage() {
  const branding = useAppSelector((state) => state.ui.branding);
  const landing = interpolateLanding(useAppSelector((state) => state.ui.landing), branding);
  const packages = useAppSelector((state) => state.ui.packages);
  const modules = useAppSelector((state) => state.ui.modules);
  const user = useAppSelector((state) => state.auth.user);
  const appHref = user ? postAuthPath(user) : "/register";
  const signedInCta = user?.is_platform_admin ? "Open control plane" : "Open workspace";
  const primaryCta = user ? signedInCta : landing.hero_primary_cta || "Create workspace";
  const heroTitle = landing.hero_title || branding.tagline;
  const heroEyebrow = landing.hero_eyebrow || branding.legal_name;
  const heroBody = landing.hero_body || fillCopy("{description}", branding);

  return (
    <PublicShell>
      <Box
        component="section"
        sx={{
          position: "relative",
          overflow: "hidden",
          pt: { xs: 6, md: 10 },
          pb: { xs: 8, md: 12 },
        }}
      >
        <Box
          sx={{
            position: "absolute",
            inset: 0,
            background: "radial-gradient(900px 420px at 12% -10%, rgba(27, 154, 170, 0.16), transparent 60%), radial-gradient(700px 380px at 92% 0%, rgba(11, 79, 108, 0.12), transparent 55%)",
            pointerEvents: "none",
          }}
        />
        <Container maxWidth="lg" sx={{ position: "relative", px: { xs: 2, sm: 3 } }}>
          <Box sx={{ display: "grid", gap: { xs: 5, md: 7 }, gridTemplateColumns: { xs: "1fr", lg: "1fr 1.05fr" }, alignItems: "center" }}>
            <Stack spacing={3}>
              {heroEyebrow ? <Chip label={heroEyebrow} color="secondary" variant="outlined" sx={{ alignSelf: "flex-start" }} /> : null}
              <Typography component="h1" sx={{ fontSize: { xs: "2.15rem", sm: "2.75rem", md: "3.35rem" }, fontWeight: 650, letterSpacing: "-0.04em", lineHeight: 1.08 }}>
                {heroTitle}
              </Typography>
              {heroBody ? (
                <Typography color="text.secondary" sx={{ fontSize: { xs: "1.05rem", md: "1.15rem" }, maxWidth: 560 }}>
                  {heroBody}
                </Typography>
              ) : null}
              <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
                <Button component={NextLink} href={appHref} variant="contained" size="large" sx={{ width: { xs: "100%", sm: "auto" } }}>
                  {primaryCta}
                </Button>
                {landing.hero_secondary_cta ? (
                  <Button href={landing.hero_secondary_href || "#product"} variant="outlined" size="large" sx={{ width: { xs: "100%", sm: "auto" } }}>
                    {landing.hero_secondary_cta}
                  </Button>
                ) : null}
              </Stack>
              {landing.stats.length ? (
                <Stack direction="row" spacing={3} sx={{ flexWrap: "wrap", pt: 1 }}>
                  {landing.stats.map((item) => (
                    <Box key={item.label}>
                      <Typography variant="h4">{item.value}</Typography>
                      <Typography variant="body2" color="text.secondary">
                        {item.label}
                      </Typography>
                    </Box>
                  ))}
                </Stack>
              ) : null}
            </Stack>
            <ProductPreview />
          </Box>
        </Container>
      </Box>

      {landing.pains.length ? (
        <Box component="section" id="product" sx={{ ...sectionSx, bgcolor: "background.paper", borderTop: 1, borderBottom: 1, borderColor: "divider" }}>
          <Container maxWidth="lg" sx={{ px: { xs: 2, sm: 3 } }}>
            <SectionHeading eyebrow={landing.pains_eyebrow} title={landing.pains_title} body={landing.pains_body} />
            <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "repeat(2, 1fr)" } }}>
              {landing.pains.map((item, index) => (
                <Box key={`${item.title}-${index}`} sx={{ p: { xs: 2.5, md: 3 }, borderRadius: 3, border: 1, borderColor: "divider", bgcolor: "background.default", height: "100%" }}>
                  <Typography variant="subtitle2" color="secondary" sx={{ mb: 1 }}>
                    0{index + 1}
                  </Typography>
                  <Typography variant="h4" sx={{ mb: 1 }}>
                    {item.title}
                  </Typography>
                  <Typography color="text.secondary">{item.body}</Typography>
                </Box>
              ))}
            </Box>
          </Container>
        </Box>
      ) : null}

      {modules.length ? (
        <Box component="section" sx={sectionSx}>
          <Container maxWidth="lg" sx={{ px: { xs: 2, sm: 3 } }}>
            <SectionHeading eyebrow={landing.product_eyebrow} title={landing.product_title} body={landing.product_body} />
            <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr", lg: "repeat(4, 1fr)" } }}>
              {modules.map((item) => (
                <Box
                  key={item.id}
                  sx={{
                    p: 2.5,
                    borderRadius: 3,
                    border: 1,
                    borderColor: "divider",
                    bgcolor: "background.paper",
                    height: "100%",
                    transition: "transform 160ms ease, box-shadow 160ms ease",
                    "&:hover": { transform: "translateY(-2px)", boxShadow: "0 12px 32px rgba(18, 32, 51, 0.08)" },
                  }}
                >
                  <Typography variant="h4" sx={{ mb: 1 }}>
                    {item.name}
                  </Typography>
                  <Typography color="text.secondary">{item.description}</Typography>
                </Box>
              ))}
            </Box>
          </Container>
        </Box>
      ) : null}

      {landing.steps.length ? (
        <Box component="section" id="how-it-works" sx={{ ...sectionSx, bgcolor: "background.paper", borderTop: 1, borderBottom: 1, borderColor: "divider" }}>
          <Container maxWidth="lg" sx={{ px: { xs: 2, sm: 3 } }}>
            <SectionHeading eyebrow={landing.steps_eyebrow} title={landing.steps_title} body={landing.steps_body} />
            <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr", lg: "repeat(4, 1fr)" } }}>
              {landing.steps.map((item) => (
                <Box key={item.step} sx={{ p: 2.5, borderRadius: 3, border: 1, borderColor: "divider", bgcolor: "background.default" }}>
                  <Typography variant="subtitle2" color="secondary">
                    {item.step}
                  </Typography>
                  <Typography variant="h4" sx={{ my: 1 }}>
                    {item.title}
                  </Typography>
                  <Typography color="text.secondary">{item.body}</Typography>
                </Box>
              ))}
            </Box>
            <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" }, mt: 4 }}>
              <Box sx={{ p: { xs: 3, md: 4 }, borderRadius: 3, border: 1, borderColor: "divider", bgcolor: "background.default" }}>
                <Typography variant="subtitle2" color="secondary">
                  {landing.workspace_eyebrow}
                </Typography>
                <Typography variant="h3" sx={{ my: 1 }}>
                  {landing.workspace_title}
                </Typography>
                <Typography color="text.secondary">{landing.workspace_body}</Typography>
              </Box>
              <Box sx={{ p: { xs: 3, md: 4 }, borderRadius: 3, bgcolor: "primary.main", color: "primary.contrastText" }}>
                <Typography variant="subtitle2" sx={{ color: "inherit", opacity: 0.8 }}>
                  {landing.control_plane_eyebrow}
                </Typography>
                <Typography variant="h3" sx={{ my: 1, color: "inherit" }}>
                  {landing.control_plane_title}
                </Typography>
                <Typography sx={{ color: "inherit", opacity: 0.88 }}>{landing.control_plane_body}</Typography>
              </Box>
            </Box>
          </Container>
        </Box>
      ) : null}

      {packages.length ? (
        <Box component="section" id="pricing" sx={sectionSx}>
          <Container maxWidth="lg" sx={{ px: { xs: 2, sm: 3 } }}>
            <SectionHeading eyebrow={landing.pricing_eyebrow} title={landing.pricing_title} body={landing.pricing_body} />
            <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "repeat(2, 1fr)", lg: `repeat(${Math.min(packages.length, 4)}, 1fr)` } }}>
              {packages.map((plan, index) => {
                const previous = index > 0 ? packages[index - 1] : undefined;
                const cta = planCta(plan, branding.support_url);
                return (
                  <Box
                    key={plan.id}
                    sx={{
                      p: 3,
                      borderRadius: 3,
                      border: 2,
                      borderColor: plan.is_featured ? "primary.main" : "divider",
                      bgcolor: plan.is_featured ? "background.paper" : "background.default",
                      display: "flex",
                      flexDirection: "column",
                      height: "100%",
                    }}
                  >
                    {plan.is_featured ? <Chip size="small" color="primary" label="Most teams" sx={{ alignSelf: "flex-start", mb: 1.5 }} /> : null}
                    <Typography variant="h4">{plan.name}</Typography>
                    <Stack direction="row" spacing={0.75} sx={{ alignItems: "baseline", my: 1.5 }}>
                      <Typography sx={{ fontSize: "2rem", fontWeight: 650, letterSpacing: "-0.03em" }}>{formatPlanPrice(plan)}</Typography>
                      {planCadence(plan) ? (
                        <Typography color="text.secondary" variant="body2">
                          {planCadence(plan)}
                        </Typography>
                      ) : null}
                    </Stack>
                    <Typography color="text.secondary" sx={{ mb: 2 }}>
                      {plan.description}
                    </Typography>
                    <Stack spacing={1} sx={{ flex: 1, mb: 3 }}>
                      {planFeatureList(plan, previous).map((feature) => (
                        <Stack key={feature} direction="row" spacing={1} sx={{ alignItems: "flex-start" }}>
                          <CheckCircleOutlined fontSize="small" color="secondary" />
                          <Typography variant="body2">{feature}</Typography>
                        </Stack>
                      ))}
                    </Stack>
                    <Button
                      component={cta.external ? "a" : NextLink}
                      href={cta.href}
                      variant={plan.is_featured ? "contained" : "outlined"}
                      {...(cta.external ? { target: "_blank", rel: "noreferrer" } : {})}
                    >
                      {cta.label}
                    </Button>
                  </Box>
                );
              })}
            </Box>
          </Container>
        </Box>
      ) : null}

      {landing.security.length ? (
        <Box component="section" id="security" sx={{ ...sectionSx, bgcolor: "background.paper", borderTop: 1, borderBottom: 1, borderColor: "divider" }}>
          <Container maxWidth="lg" sx={{ px: { xs: 2, sm: 3 } }}>
            <SectionHeading eyebrow={landing.security_eyebrow} title={landing.security_title} body={landing.security_body} />
            <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr", lg: "repeat(3, 1fr)" } }}>
              {landing.security.map((item) => (
                <Box key={item.title} sx={{ p: 3, borderRadius: 3, border: 1, borderColor: "divider", bgcolor: "background.default" }}>
                  <ShieldOutlined color="secondary" sx={{ mb: 1.5 }} />
                  <Typography variant="h4" sx={{ mb: 1 }}>
                    {item.title}
                  </Typography>
                  <Typography color="text.secondary">{item.body}</Typography>
                </Box>
              ))}
            </Box>
          </Container>
        </Box>
      ) : null}

      {landing.faqs.length ? (
        <Box component="section" id="faq" sx={sectionSx}>
          <Container maxWidth="md" sx={{ px: { xs: 2, sm: 3 } }}>
            <SectionHeading eyebrow={landing.faq_eyebrow} title={landing.faq_title} />
            {landing.faqs.map((item) => (
              <Accordion key={item.q} disableGutters elevation={0} sx={{ "&:before": { display: "none" }, borderBottom: 1, borderColor: "divider", bgcolor: "transparent" }}>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Typography variant="h4">{item.q}</Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <Typography color="text.secondary">{item.a}</Typography>
                </AccordionDetails>
              </Accordion>
            ))}
          </Container>
        </Box>
      ) : null}

      {landing.cta_title ? (
        <Box sx={{ py: { xs: 8, md: 10 }, bgcolor: "primary.main", color: "primary.contrastText" }}>
          <Container maxWidth="md" sx={{ px: { xs: 2, sm: 3 }, textAlign: "center" }}>
            <Typography variant="h1" sx={{ color: "inherit", fontSize: { xs: "1.8rem", md: "2.4rem" }, mb: 1.5 }}>
              {landing.cta_title}
            </Typography>
            {landing.cta_body ? (
              <Typography sx={{ color: "inherit", opacity: 0.88, mb: 3 }}>
                {landing.cta_body}
              </Typography>
            ) : null}
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} sx={{ justifyContent: "center" }}>
              <Button component={NextLink} href={appHref} variant="contained" size="large" color="secondary" sx={{ width: { xs: "100%", sm: "auto" } }}>
                {user ? signedInCta : landing.cta_primary || primaryCta}
              </Button>
              {landing.cta_secondary ? (
                <Button component={NextLink} href="/login" size="large" sx={{ width: { xs: "100%", sm: "auto" }, color: "inherit", borderColor: "currentColor" }} variant="outlined">
                  {landing.cta_secondary}
                </Button>
              ) : null}
            </Stack>
          </Container>
        </Box>
      ) : null}
    </PublicShell>
  );
}
