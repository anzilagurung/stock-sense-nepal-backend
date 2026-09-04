"""Data ingestion for NEPSE.

Two-layer design:
  - `stockmap` : one-time seed of the full company universe (540 companies) from a
                 bundled snapshot. This is what the app shows even when no upstream is available.
  - `nepse_unofficial` : live provider that hits the unofficial community NEPSE API for
                          prices, top movers, and market summary. Used on demand and on startup
                          with a short timeout so a downed upstream never crashes the backend.

The provider layer is deliberately abstract so a different data source (e.g. an official
paid feed) can be swapped in later without touching the rest of the app.
"""
