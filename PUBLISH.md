# Publish checklist (do in this order)

The DOI is the **last** step — it permanently stamps whatever is in the repo, so fill the
blanks first. You do the account/login/click steps; the files here make them one-click.

## 0. Fill the blanks (before anything is public)
- [x] ~~Fill author name / affiliation~~ — done (Taj Anderson, Independent researcher)
- [x] ~~Fill CITATION.cff / .zenodo.json~~ — done
- [x] ~~Run canonical τ and fill the slot~~ — done (τ ≈ 3 yr, +6.2 pp/yr, §7.2)

## 1. Put it on GitHub
- [ ] Create a public repo (e.g. `consumer-return-latency`)
- [ ] Add all files (papers, `*.py`, `*.csv`, figures, `README.md`, `CITATION.cff`, `.zenodo.json`)
- [ ] Add a `LICENSE` file: CC-BY-4.0 for text, MIT for code (note this split in the README)

## 2. Mint the DOI (Zenodo) — YOU click these
- [ ] Sign in at https://zenodo.org with your GitHub account (your login — I can't do this)
- [ ] **Settings → GitHub** → flip the toggle **ON** for your repo
- [ ] Back on GitHub: **Releases → Create a new release** → tag `v1.0` → Publish release
- [ ] Zenodo auto-archives it and issues a DOI (badge appears on the Zenodo GitHub page)
- [ ] Paste the DOI back into `CITATION.cff`, `.zenodo.json`, and the white paper header, then cut a small `v1.0.1` release so the record matches

## 3. Post the preprint
- [ ] **SSRN** (fastest, no gatekeeper) or **RePEc/MPRA** — upload the white paper PDF, link the repo + DOI
- [ ] *(arXiv `econ.GN` needs a first-time endorsement; skip for v1 unless you have one)*

## 4. Post the essay
- [ ] Substack/Medium: publish the summary paper; link the preprint + repo at the top
- [ ] Title with the searchable terms ("consumer-return latency", "K-shaped", "Goodwin")

## 5. Seed it
- [ ] Short, humble notes to 1–2 people working on Goodwin cycles / basic-dividend design
- [ ] Keep a dated version log as live cases (government stakes, fast-transfer episodes) come in
