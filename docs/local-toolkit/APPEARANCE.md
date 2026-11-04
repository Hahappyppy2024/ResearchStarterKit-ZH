# Shared appearance and conference deadlines

The local desktop offers green and blue palettes. Python HTML responses load shared assets through theme_assets.py; the scholar navigator server serves the same assets from web-shared. The conference library also includes an explicit shared-asset link. The hub sends the selected palette to its iframe children. Standalone pages load the saved choice from the allowlisted local appearance endpoint. The preference is stored in ignored local-data/appearance.json.

Existing CSS colors are mapped to shared accent, surface, text and border tokens. Warm warning/error colors and actual uploaded images are preserved. The hub uses a static stylesheet override under its existing CSP; it does not enable inline scripts or weaken its CSP.

The conference panel appears below the Daily Effort schedule. web/conference-deadlines.json contains an official-source snapshot checked on 2026-10-21. Countdown values refresh every minute; the site does not automatically fetch revised conference deadlines. Unknown submission dates are explicitly pending confirmation; closed main-track dates remain labeled closed. AoE is UTC-12 and is converted to Asia/Shanghai for display. Registration/abstract and full-paper stages are shown separately.

Sources: CVPR 2027 CFP, AAAI-27 conference timetable, ICLR 2027 author guidelines, ICCV 2027 Dates, ECCV 2026 Dates, and the official ICML/NeurIPS homepages. Unknown dates are never inferred from previous years.

Validation: 57 existing Python tests passed, theme save/restore and HTML-only/idempotent injection checks passed, deadline AoE conversion and boundary checks passed. Browser QA covered scholar green/blue palette changes, hub-child synchronization, persisted choice after asynchronous reload, and the seven-conference deadline panel. No deployment, Git push or database export was performed.

The active schedule task now uses a deep palette background with white text. The DDL panel uses compact cards, with detailed stages and official sources inside disclosures. Daily Quiz is the final sleep-before task after the complete daily task area and before DDL. Flash Card statistics appear above paper-reading statistics.
