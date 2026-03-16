YOU HAVE TO BE 100% CERTAIN AND SURE THAT YOU ARE IMPLEMENTING THEM IN THE EXACT PLACE THEY ARE SUPPOSED TO BE. DO NOT IMPLEMENT IN A WRONG LOCATION.


---

#### What's Actually Missing for Dashboard Integration

After examining the **complete** codebase, the picture is much clearer. The system already has extensive coverage. Here are the **genuine gaps**:

**1. Analysis Statistics/Aggregates Endpoint** - STILL MISSING
The `AnalysisRepository` only has `get_latest_by_pair` and `get_by_analysis_id`. No aggregation queries exist (success rate, grade distribution, average score, provider usage). The dashboard needs a `GET /api/analysis/stats` endpoint. This requires adding a new repository method.

**2. Analysis History with Pagination/Filtering** - PARTIALLY MISSING
`GET /api/analysis/latest` exists but has no `offset`/cursor pagination, no date range filtering (`since`/`until`), no status filtering, no grade filtering. For a production dashboard browsing hundreds of analyses, this needs enhancement.

**3. Available Models Per Provider** - MISSING
`GET /api/processor/config` returns the current config but doesn't expose what models are available per provider. The `DEFAULT_MODELS` dict in `constants.py` has defaults, but the dashboard's model selector needs a `GET /api/processor/models` endpoint.
THE USER SHOULD ABLE TO SELECT THE MODEL THEY WANT TO USE. WHEN THEY SELECT A PARTICULAR MODEL, IT SHOULD OVERIDE THE DEFAULT AND BE PERSISTED.

FOR EXAMPLE, IF THE SELECT GPT-4.0 THEN IT SHOULD OVERIDE THE DEFAULT AND ONLY THE GPT-4.0 WILL ALWAYS BE USED UNTIL THE USER CHANGES IT


**7. Re-run Analysis** - GENUINELY MISSING
No endpoint to re-trigger analysis for a specific symbol on demand (outside the scheduled cycle). The gRPC `RunCycle` can trigger a full cycle, but there's no lightweight "re-analyze this one symbol with the current processor config" REST endpoint accessible from the dashboard.

