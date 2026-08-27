export const fonts = {
  sans: 'var(--font-sans), "Plus Jakarta Sans", ui-sans-serif, system-ui, sans-serif',
  mono: 'var(--font-mono), "Geist Mono", ui-monospace, SFMono-Regular, Menlo, monospace',
};

export const typography = {
  fontFamily: fonts.sans,
  h1: { fontSize: "2.25rem", fontWeight: 700, letterSpacing: "-0.04em", lineHeight: 1.15 },
  h2: { fontSize: "1.5rem", fontWeight: 700, letterSpacing: "-0.03em", lineHeight: 1.22 },
  h3: { fontSize: "1.25rem", fontWeight: 650, letterSpacing: "-0.025em", lineHeight: 1.28 },
  h4: { fontSize: "1.05rem", fontWeight: 650, letterSpacing: "-0.02em", lineHeight: 1.35 },
  h5: { fontSize: "0.95rem", fontWeight: 650, lineHeight: 1.4 },
  h6: { fontSize: "0.82rem", fontWeight: 650, letterSpacing: "0.01em", lineHeight: 1.4 },
  body1: { fontSize: "0.9375rem", fontWeight: 450, lineHeight: 1.6 },
  body2: { fontSize: "0.8125rem", fontWeight: 450, lineHeight: 1.55 },
  button: { textTransform: "none" as const, fontWeight: 650, letterSpacing: "-0.01em" },
  subtitle2: { fontSize: "0.72rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase" as const },
  overline: { fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.1em" },
};
