# International Pharmaceutical Regulation

Interactive dashboard of pharmaceutical regulatory reliance across 250 countries and areas, 2000–2025. Updated 17 October 2026.

## Open the dashboard

**View and share the live charts:** [International Pharmaceutical Regulation dashboard](https://hunternbh.github.io/international-pharmaceutical-regulation/).

GitHub Pages publishes `index.html` from the root of the `main` branch. You can also download **index.html** and open it in a web browser. The HTML is self-contained: its data, styling and chart logic are embedded, with no external libraries required.

The dashboard combines the timeline and legal-wording results:

1. A country-by-year heatmap showing the documented reliance arrangement and identified reference count.
2. A combined line plot showing the reach of 58 individually identified national regulatory systems and regional/global reference bodies.
3. A descending bar chart of conditions in 89 selected national approval-pathway texts, followed by text comparisons and a one-country-at-a-time viewer of exact legal wording.

The wording review covers 117 jurisdictions and 182 individual passages, plus nine shared-procedure passages. The heatmap includes an optional grouping into six broader approaches plus unknown history, with plain-language explanations. Completion/resumption notes and literature comparisons remain available.

Search for countries, highlight or hide authority lines, inspect a year, and click cells or lines for sources and product restrictions. CSV download buttons are included. The public country-data download contains reviewed evidence, results and research code components; full raw-source downloads remain in the local archive.

## Read the counts

- A number counts distinct foreign national regulatory systems and separately named regional/global bodies.
- **\*** marks a known subset where additional eligible references have not been fully enumerated.
- **†** marks a later/current list assigned retrospectively to an unresolved earlier list, following the research convention used here. It is not verified historical membership.
- **n** denotes an explicitly supported provision allowing consideration of reviews from any foreign authority, subject to national discretion.
- **NS** means a named roster could not be established from the reviewed public evidence.
- Grey means unverified history, not confirmed absence.

Adopted provisions are carried forward unless a documented end is recorded. The timeline retains known complete historical lists and existing adoption-date precision. Counts include recorded limited product/evidence scopes, frameworks and pilots; they do not mean every new medicine qualifies or that a pathway was actually used. Multiple agencies within one national system, such as Germany's BfArM and PEI, are grouped consistently with country-based statutory lists. EMA is separate from national EU systems.

Current-source follow-up addressed the 42 jurisdictions with previously unresolved count labels. The heatmap contains 6,500 country-year cells; 248 carry retrospective list assignments. Five jurisdictions retain NS: Botswana, Cook Islands, Federated States of Micronesia, Panama and Tuvalu.

## Files

`data/` contains the chart-linked CSV/Parquet panel, authority-destination links, annual reference reach, reference-system roster, source profiles, dictionary, methods and validation results. Individual legal sources are cited in the HTML and source-profile export.

This repository contains the dashboard and its supporting exports. It is not the full raw-document archive or the complete collection/extraction project. Public access to a cited source does not by itself grant an open redistribution licence for that source.

The supplied validation checks cover panel size, unique links, reference counts, chart controls and source-detail rendering. No causal interpretation is implied by the descriptive figures.
