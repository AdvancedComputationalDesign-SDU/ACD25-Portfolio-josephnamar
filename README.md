# ACD-E25 Portfolio Template

Use this repository to publish your final portfolio as a cohesive GitHub Pages site bringing together four assignments. The front matter and navigation are pre-wired; you are expected to add/edit the content, images, and code.

---

## 1. Fill Your Assignments
- Edit only the **body** of each assignment `README.md` (everything below the YAML front matter) and leave the front matter intact (example below).

  ```yaml
  ---
  layout: default
  title: Project Documentation
  parent: "A1: NumPy Array Manipulation for 2D Pattern Generation"
  nav_order: 2
  nav_exclude: false
  search_exclude: false
  ---
  ```

- Include (recommended): overview, methods/pseudo-code, parameters & seeds, intermediate + final results with images, reflections, AI acknowledgments (if used).
- Add/modify code in the assignment folder; store visuals in that assignment’s `images/` folder with descriptive filenames.
- Reference images using **relative paths** (from the Markdown file):
  - Example: When editing `A1/README.md`, use `![caption](images/your_image.png)`
- Do **not** edit `index.md` or `BRIEF.md` files; they provide routing and the brief content.

---

## 2. Update Site Config
Open `_config.yml` and set:
- `title`: your name (used in the site header).
- `baseurl`: `/<repo-name>`
  - Example: if your repo is `ACD-Portfolio`, use `baseurl: /ACD-Portfolio`

Do not change other settings (`remote_theme`, plugins, etc.) unless you take responsibility for implementing and debugging.

---

## 3. Publish with GitHub Pages
1. In GitHub, navigate to **Settings → Pages → Build and deployment**.
2. Set **Source** to “Deploy from a branch”, select branch `main`, folder `/ (root)`, then **Save**.
3. Wait for the first build. Your site will appear at:
   `https://<username>.github.io/<repo-name>/`

Pages rebuilds automatically after each push.

---

## Repository Layout
```text
README.md          # Landing page (this file)
_config.yml        # Site settings (edit only title/baseurl)
index.md           # Root redirect; do not edit
A1/ ... A4/        # One folder per assignment
  ├── index.md     # Front matter; do not edit
  ├── BRIEF.md     # Assignment brief; do not edit
  ├── README.md    # Your write-up (keep front matter, edit body)
  ├── images/      # Diagrams/intermediate/final images
  └── code files   # Provided scaffolds; extend/replace as needed
```

---

## Checklist Before Publishing
- [ ] Assignment `README.md` files are complete (no placeholders).
- [ ] Images are in the correct `images/` folder and referenced with relative paths.
- [ ] Code runs and matches what you document.
- [ ] `_config.yml` has your name and correct `baseurl`.
- [ ] Changes are committed and pushed; GitHub Pages build is green.

---

## Troubleshooting
- **Broken links/styles:** confirm `baseurl` matches your repo name and front matter is untouched.
- **Missing images:** verify filenames/paths and that images are committed to the right `images/` folder.
- **Pages not updating:** check the Pages build status in GitHub Actions (or re-save the Pages settings).
- **Common pitfalls:** editing/deleting front matter, wrong `baseurl`, images stored in the wrong assignment folder.

---

## Landing Page Template
Use the template below to draft your homepage, replacing the entire content of this `README.md`.
- First, **customize the text**. You are free to use the template below or craft your own.
- When you are ready to submit, **remove the surrounding code fence** (the triple backticks) so it renders as your landing page.
- **Delete the guide sections above** for a clean portfolio homepage.

```md
# <Your Name> — ACD-E25 Portfolio

## Overview
This portfolio documents four computational design studies developed for Advanced Computational Design. Across the series, I investigate <theme> through <methods/tools>, iterating through prototypes, parameter sweeps, and visual evaluation.

## Assignments

### A1: NumPy Array Manipulation for 2D Pattern Generation
In A1, I develop a pixel-based pattern generator using NumPy array operations to transform a blank canvas into structured, colorized images. The work focuses on compositional logic (rules + constraints) and controlled randomness to produce a family of variations.

### A2: Exploring Fractals through Recursive Geometric Patterns
In A2, I build a recursive geometric system to explore branching and fractal-like growth. I test how parameter choices (e.g., depth, angle, scaling, and spatial influences) affect density, hierarchy, and legibility of the resulting forms.

### A3: Parametric Structural Canopy
In A3, I design a canopy system driven by a heightmap/field and implemented in Grasshopper/GhPython. I evaluate panelization/tessellation strategies and generate a structural support logic that responds to curvature, span, and local conditions.

### A4: Agent-Based Modeling for Surface Panelization
In A4, I use agent behaviors to sample and rationalize a surface into a panelized system. I define sensing rules and constraints (e.g., proximity, alignment, boundaries) and iterate on behaviors to balance local decisions with global coherence.

## Highlights (optional)
- **Technique:** <one technique you used across assignments>
- **Best result:** <one outcome + where it appears (A#)>
- **Next step:** <one concrete extension you would test next>

## Contact (optional)
- GitHub: <link>
- Email: <email>
```
