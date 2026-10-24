# Build log: A (data and labels)

- Kiro did well: built both specs (01-ingest-and-labels, 01b-cells-and-flags) with Hypothesis property tests (25 passing). It found that 3 re-closed cases repeat the "Case Closed ... Case Resolved" system text, and that a tests/data_pipeline/__init__.py shadowed the real package.
- I corrected: Bedrock has not been run (no AWS access), so every label is rule-based.

## Numbers (DRAINFAST_FALLBACK=1 make data, make cells)

- 311 input 7,313 rows, kept 7,269. Dropped: 4 missing coordinates, 39 "1 City Hall Plz" placeholders, 1 closed before opened.
- Labels: clogged_basin 1,527; grading_capacity 177; coastal_tide 7; unclear 5,558 (3,557 blank notes, mostly open cases; 298 excluded). Label source: rule 7,269, llm 0.
- Cells 8,818 (8,641 with basins, 3,367 with reports). Owners: BWSC 5,678, Mixed 1,826, Private 1,129, Unknown 177, City 8. EJ 6,883, flood area 547.
