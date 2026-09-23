# Masepala web

Static Next.js site built from the files in `data/` (written by `../engine`).

```bash
npm install
npm run dev     # or: npm run build  (static output in out/)
```

`npm run build` first runs `scripts/prepare.mjs`, which splits the data into the small map files the browser loads.
