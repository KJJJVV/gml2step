# Documentation Site

This directory contains the Astro + Starlight documentation site for `gml2step`.

## Local development

```bash
cd docs
npm ci
npm run dev
```

## Build

```bash
cd docs
npm run build
```

The static output is generated in `docs/dist/` and deployed by `.github/workflows/deploy-docs.yml`.
