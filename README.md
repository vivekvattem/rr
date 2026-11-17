# RR SupeRR Selector Season 2 - Round 1

The **primary submission is `output/pdf/rr_methodology_rankings.pdf`**. The nine-page report contains a concise overview, both final rankings, the pressure definition, performance measurement, reliability checks, one worked example, a data-quality audit and limitations. It follows the Round 1 problem statement. Auction decisions, status snapshots and operational commentary are excluded. Use `unstop_rankings.txt` for entering the two top-10 dropdown lists.

`rr_auction_dashboard.html` is an **optional aggregate-only companion**. Double-click it to open locally: no server, internet connection, sign-in or CDN is needed. Its main views are Rankings, Player comparison, and Methodology and robustness. The dated auction research is available separately in the Research archive. Official rankings are the default; search, phase checks and alternative models are clearly labeled exploratory. The worked delivery is kept in the primary PDF and its reproducible evidence JSON, while the dashboard displays only the corresponding aggregate comparison.

After your review, upload `output/pdf/rr_methodology_rankings.pdf` as the methodology report and use `unstop_rankings.txt` for the two dropdown lists. The separate dashboard retains the earlier dated auction research as optional supporting material. Final upload and dropdown entry are left to the user.

## Reproduce

Python 3.13 was used. Keep the six original CSVs together outside this submission folder. They are not distributed in the bundle.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 .venv/bin/python analysis/analyze.py --data-dir "/path/to/Data Pack"
.venv/bin/python analysis/refresh_player_status.py --data-dir "/path/to/Data Pack" --as-of 2026-11-13
OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 .venv/bin/python analysis/refine_evidence.py --data-dir "/path/to/Data Pack"
.venv/bin/python analysis/build.py
.venv/bin/python analysis/verify.py
.venv/bin/python analysis/package.py
```

Actual input location for this run: `/Users/vivekvattem/Desktop/Data Pack`. Analysis cutoff and status snapshot: **13 November 2026, India time**. The analysis, status refresh, build and verification commands use local files only. Public-source verification was performed separately. The optional public roster downloader is the only network-enabled script and never opens proprietary files. `build.py` is idempotent and reads aggregated outputs and the materialized reference CSV only. Both ranked tables and dropdown names derive from `output/rankings.json`; availability comes from `data/reference/ipl_2027_player_status.csv`.

Round 1 requires historical top-10 pressure-performance lists and a reproducible methodology. Retired players remain eligible if they satisfy the same performance sample rules. The organiser clarified that this is not an RR retention or auction recommendation task, and the user confirmed that the Unstop listing includes retired players. That evidence is recorded in `data/reference/historical_eligibility_policy.json`. The earlier four-player retirement screen has been removed from all ranking specifications. Franchise and retirement status remain relevant only to the separate dated auction research in the optional dashboard.

## Files

- `analysis/analyze.py`: audit, safe joins, reconstruction, pressure, ordinary references, scores, shrinkage, match bootstrap and sensitivity models. Raw data remains in memory; no delivery-level outputs are written.
- `analysis/build.py`: standalone HTML and ReportLab PDF from the same JSON rankings; no raw CSV inputs.
- `analysis/methodology_report.py`: submission-focused PDF layout and wording, including the final rankings, formulas and validation.
- `analysis/pdf_branding.py`: centred RR logo watermark, preserved across report builds.
- `analysis/dashboard.template.html`: editable offline HTML and interaction template.
- `analysis/dashboard.css`, `analysis/dashboard_ui.py`: responsive presentation and the offline renderer; styles and the RR logo are embedded into the final HTML.
- `analysis/content.py`: roster interpretation, role-led shortlist, limitations and public source register.
- `analysis/verify.py`: artifact agreement checks and optional offline browser interaction tests.
- `analysis/refresh_player_status.py`: local ID joins, alias resolution, dated event materialization, authority gates and auction-action policy.
- `analysis/status_layer.py`: one shared status/fallback presentation layer for PDF, dashboard and machine-readable recommendations.
- `analysis/refine_evidence.py`: reuses the unchanged pressure/peer model to verify target baselines and create IPL phase/cohort aggregates plus the single requested worked delivery. Checks original input hashes and frozen model outputs; never overwrites the rankings.
- `analysis/auction_brief.py`: generates the same page-one auction calls for the PDF and optional dashboard from the supplementary evidence.
- `analysis/fetch_public_rosters.py`: optional public-only IPL roster downloader; see refresh safeguards below.
- `analysis/package.py`: deterministic allowlisted bundle and SHA-256 manifest; excludes raw inputs, temporary research, screenshots and system metadata.
- `output/rankings.json`, `batters_top10.csv`, `bowlers_top10.csv`: official ordered selections with stable player IDs, scores, exposure, lift and uncertainty.
- `output/batters_all.csv`, `bowlers_all.csv`, `players.json`: all players meeting official sample rules and supported context breakdowns.
- `output/scenarios.json`, `robustness.json`: five exploratory alternative models and rank movements.
- `output/audit.json`: exact competition/date/season coverage, all missing counts, duplicate keys, join coverage, file SHA-256 hashes, sequential exclusions and total/margin checks.
- `output/pressure_diagnostics.json`: aggregate pressure counts by league, innings and phase.
- `output/competition_coverage.csv`, `included_seasons.csv`: readable aggregate competition inventory and retained season coverage.
- `output/eligibility.json`: historical ranking policy, no retirement-based exclusions, and the policy evidence path.
- `output/eligibility_revision.json`: before/after lists, cohort counts and evidence that input data, pressure rules and existing scores were preserved.
- `output/auction_shortlist.json`, `sources.json`: auction interpretation and dated citations.
- `output/auction_target_reviews.json`: every original target and its action/fallback, including any subsequently unavailable or existing-RR option. The active `auction_shortlist.json` includes only monitor-for-release or pursue-if-listed records.
- `output/rankings_with_status.json`: the exact official 20 with the current status record attached by ID.
- `output/status_review_summary.json`, `recommendation_changes.json`: checked-player counts, unresolved cases, retirement scopes, commitments and the recommendation change log.
- `output/auction_brief_evidence.json`: numerical source for the refined report: existing pooled/IPL target metrics, fresh IPL phase aggregates, comparable chase/death states, and the single traceable delivery at `(30072, 2, 117)`.
- `output/auction_calls.json`, `refinement_summary.json`: shared page-one decisions, ranking-change audit and review judgments.
- `data/reference/ipl_2027_player_status.csv`: one row per supplied player ID, with source URLs, scopes, dates, status and auction action.
- `data/reference/status_sources.csv`, `status_events.csv`, `player_status_evidence.csv`: source catalog, editable field-level claims and the expanded field-to-source evidence ledger.
- `data/reference/public_rosters_2026.json`, `official_roster_identity_join.csv`: public roster snapshot, response hashes and complete identity joins.
- `data/reference/player_aliases.csv`, `alias_join_review.csv`: curated aliases and the nontrivial roster-join decisions, with candidate IDs and review flags.
- `data/reference/official_rankings_lock.json`: hash and ordered identities for the current rankings, with the user-confirmed eligibility revision recorded.
- `output/verification.json`: verification result for the delivered artifacts.

## Model contract

All cumulative match state is **before** the current delivery. `innings_ball_num` is a sequence counter, not a legal-ball counter. Wides, `Overstep`, and `other` are illegal deliveries; the latter consistently carry one no-ball penalty and have the expected over-length behavior. Team runs are `runs + extras1_runs + extras_2_runs`; `runs` is the batter component. Secondary no-ball extras are treated as byes/legbyes and excluded from bowler charges. This interpretation is checked against over counts and match-result margins, with ambiguous matches excluded.

Revised-over fields contain ball limits (90 = 15 overs). Whole revised/DLS matches are excluded because the revision timing is unavailable. Result text catches DLS cases with empty revision fields. Innings 3/4 are Super Overs. Known incomplete or irregular interior overs and the one unresolved wicket-margin mismatch are excluded. Unknown non-wicket retirement IDs do not remove wickets. `audit.json` counts exclusions sequentially to avoid double counting.

Situational par is trained only on earlier calendar years, separately by league and phase, with declared priors. Pressure has no current-ball or future-result inputs. First-innings pressure uses phase-par deficit and wicket depletion; chases use required rate relative to a wicket-adjusted phase baseline, urgency and a live-contest gate. The full formula and illustrative high/low late-over scenarios are in both dashboard and PDF.

Ordinary performance references use **retrospective** non-pressure outcomes over the full window, excluding the entire current match. They are not prospective forecasts. Hierarchical context: phase/role, then league/season/innings/phase/role/wicket band, then opposition team. International series pool within T20I. Venue IDs are available but sparse venue effects are not fitted.

Batter utility weights scoring 65%, dismissal avoidance 35%. Bowler utility weights run prevention 60%, credited wickets 40%. Scale constants are 1.70 runs and 0.22 wickets. Batting opportunities exclude wides but include no-balls; bowling attempts include illegal deliveries. Bowling economy uses legal balls. Only actual striker outs count against the striker. Run-outs, retired outs and obstruction do not earn bowling wickets.

Own ordinary phase residuals shrink with 100 pseudo-observations, pressure quality with 150. Absolute index is 50+20A; own ordinary index is 50+20O; lift is 20(A-O). Final score = 50+20[0.8A+0.2(A-O)] - 0.35SE. A positive lift cannot outweigh low absolute quality. Different ordinary/pressure priors make the lift conservative; the index is not a probability.

Eligibility: batters 120 pressure opportunities / 12 pressure matches / 200 ordinary opportunities; bowlers 180 / 15 / 240. Supported comparison segments need 30 pressure and 30 ordinary attempts, plus four pressure matches. Final historical cohort: 72 batters and 54 bowlers, including retired players who meet the sample rules.

400 joint whole-match bootstrap resamples, seed 202711, recompute player pressure/ordinary estimates. Peer references and candidate eligibility stay fixed within each model; intervals therefore omit model-choice and reference-estimation uncertainty. Alternative cutoffs 0.57/0.67, IPL-only data, and run/wicket weights 75/25 and 50/50 rebuild contextual references. Rank changes include exposure-rule effects, clearly represented as missing ranks rather than poor performance. All seasons receive equal weight.

## Findings and unresolved issues

- Suryakumar Yadav and Mustafizur Rahman lead the official historical rankings. Dinesh Karthik ranks second in batting after removing the retirement-only screen; Axar Patel moves to rank 11. The bowling top-10 order is unchanged. Several cutoff positions are fragile; bootstrap intervals overlap and alternative models change the lower picks substantially.
- Shashank is a conditional Indian No. 6 depth option, proposed to enter around overs 11-15. His pooled pressure index is 51.37 vs own ordinary 50.77 (lift +0.60), with 176 pressure opportunities in 18 matches. Comparable Indian finisher Rahul Tewatia has 49.18 vs 50.49 (208 / 28). These are pooled-reference indices with IPL observations. Their final-score intervals overlap. In the rebuilt IPL-only phase check, Shashank's middle lift is +0.47 (105 / 12), while death lift is -0.27 (64 / 13): the evidence limits a pure death-specialist claim.
- **Avesh is downgraded to a backup**, provisionally for overs 17 and 19 if RR needs reserve Indian late-over cover. He is pooled bowling rank 16, IPL-only rank 3, with IPL score 51.16, lift +1.39, 252 pressure attempts / 28 matches. Bhuvneshwar is IPL rank 4 with score 51.06, 232 / 30; their overall score intervals overlap. IPL death-phase indices are 51.46 vs 51.63 (Avesh/Bhuvneshwar), with 174 / 23 and 178 / 23 attempts/matches. Avesh's IPL middle lift is -0.17 (78 / 11), so the earlier attacking middle-over recommendation is withdrawn. Exact proposed over numbers are an editorial deployment hypothesis, not an over-level skill model.
- The report's only real match example is GT-PBKS, 4 April 2024, before 18.6: 187/6, target 200, seven legal balls left and four wickets in hand. The trace key is match 30072 / innings 2 / sequence 117. R=1.4024, inside the live gate; pressure is 0.9510, above 0.62, before Shashank's six. Across comparable IPL chase/death high-pressure states he scores 113 runs from 44 non-wide opportunities in nine matches, with one dismissal. The adjusted cohort lift is only +0.08. Excluding the whole example match leaves 100 runs from 38 opportunities in eight matches. A closer 3-6-wickets-in-hand slice is 27 / 7 and is reported descriptively because it falls below the 30-opportunity segment rule. These are explanatory cohorts, not held-out prediction tests.
- RR's published roster and Jurel's reported No. 3 role refine the need toward conditional lower-order depth and reserve pace cover. Existing Hetmyer/Ferreira/Jadeja/Dubey batting options and Archer/Sandeep/Deshpande pace options could eliminate either acquisition need. Sources S1 and S16-S19 were checked on 13 November 2026. No 2027 release, entry or price is inferred from a 2026 roster.
- Dinesh Karthik, Andre Russell, R. Ashwin and Mohit Sharma are eligible for historical ranking under the ordinary sample rules. The retirement-only screen was removed following the organiser clarification and user confirmation. Mark Chapman and Taskin Ahmed have no IPL pressure observations in this pack. Availability and clearance conditions belong only to the separate optional auction research.
- The public Unstop listing was checked, but player dropdown options were not exposed. All names are exact source labels and IDs are preserved. Manually check whether the dropdown offers these historical players and aliases, including data aliases. Do not silently substitute names or alter one deliverable independently.
- This is selected IPL/T20I coverage, not a census of T20 cricket. No explicitly named T20 World Cup appears. Two other domestic competitions are excluded. The included cohort has 186,089 records in 779 matches; 14,910 records (7.4%) are excluded from the 200,999-row input.

## Browser and PDF QA

Artifact checks require only the pinned core dependencies. For optional UI tests, use Playwright with a compatible Chromium installation:

```bash
.venv/bin/python -m pip install playwright==1.51.0
.venv/bin/python -m playwright install chromium
.venv/bin/python analysis/verify.py --browser
```

The delivered HTML was tested from a `file://` URL, without a server. Checks cover both official orders, search/reset, category filtering, all five alternative models, same-category comparison, all four views, zero JavaScript errors, no external requests and mobile document overflow. Comparison is restricted to the official eligible cohort; an alternative-model player below those sample rules is labeled rather than compared to an unrelated player.

The PDF was rendered with PyMuPDF and visually reviewed after the document cleanup. It has nine pages, with a centred RR logo watermark and no decision or status-snapshot pages. Model outputs, HTML rankings, PDF tables and dropdown text were checked for identical names, order and scores. The ranking tables show both pressure and usual-performance indices. Checks also cover the worked example, required methodology sections and absence of removed auction commentary. Dashboard checks continue to cover its separate auction calls, phase/cohort tables, status filters, aliases and source-authority gates. To render independently, install PyMuPDF (optional) and call `page.get_pixmap().save(...)`, or use Poppler `pdftoppm -png`.

## Availability review and refresh

The snapshot represents **1,217 unique supplied IDs**. All were screened against the ICC 2023-24 and 2024-25 retirement registers, a 2026 discovery register and additional documented announcements. This is a bounded documentary screen, not an exhaustive individual internet search for 1,217 people. **876 players have register screening only**. An unmatched name stays `unknown`, never implicitly active or eligible.

All **274 published 2026 roster-history entries** across ten franchises matched supplied IDs, with no unresolved public-roster identity. There were **26 roster aliases and two homonyms** resolved by country/franchise context and 2026 membership. The alias register also documents two retirement-source aliases (28 curated aliases overall). Rashid Khan (4722 vs 20172) and Abdul Samad (7446 vs 6922) were resolved through GT/LSG membership. Public IPL `externalId` values are a separate namespace and are never equated with supplied `player_id` values. No fuzzy auto-join is used.

Roster counts CSK/DC/GT/KKR/LSG/MI/PBKS/RR/RCB/SRH are **30/26/27/29/26/29/25/27/26/29**. These pages preserve replacements and superseded signings; they do not certify simultaneous contracts or 2027 retention. The supplied IPL 2026 mapping contains 275 IDs. **Gideon Peters (7095)** appears there for DC but is absent from the public roster snapshot; his externally verified IPL team remains unknown.

The **48 unique priority players** cover both top tens, the next 15 in each category, all six original RR targets, Suryakumar as a benchmark watch and all six same-role fallbacks. **67 players have documented retirement-scope/reversal records**, including format-only retirements; **29 IPL/Indian-cricket/full professional retirements** block IPL acquisition. Ten players have official 2027 trade commitments. No official IPL 2027 auction list was located. Auction status remains unknown for 1,216 IDs; Mustafizur has a release record, which is not confirmed auction entry. IPL retirement status is unresolved for 1,188 IDs. Counts reconcile in `status_review_summary.json` and are not a certification that the unknown cases are active.

Actions changed from generic availability notes to explicit gates: Shashank (PBKS 2026), Avesh (LSG 2026), Nitish (DC 2026), Ferguson (PBKS 2026) and benchmark SKY (MI 2026) say **monitor for release / target only if released**. Mustafizur remains **pursue if listed**, with regulatory clearance still required; Chapman remains **pursue if listed / scouting only**. His Adelaide BBL signing is verified but does not establish IPL entry. Kuldeep keeps bowling rank 10 but is committed to LSG for 2027; Livingstone is committed to CSK and cannot be an auction fallback. None of the original six targets was removed by the availability screen. The current role refinement additionally downgrades Avesh to backup and narrows Shashank to No. 6 depth; their acquisition conditions remain explicit. Existing RR options are shown separately. Every conditional target has a role-matched fallback with its own pressure evidence, trade-off and status.

To refresh the status without changing the model:

1. Review new official IPL/BCCI/franchise announcements first. Append a source to `status_sources.csv`, using `source_type=official` or `credible_reporting`, its URL, publication date and verification date. Undated live pages use `unknown` publication dates.
2. Append field-level claims to `status_events.csv`, preserving old claims and recording actual announcement and effective dates separately. Unknown dates stay `unknown`; comeback years may have year-only precision. The wide CSV's `announcement_date`/`effective_date` are the latest known dates across that player's claims, not the dates of every fact. Use `player_status_evidence.csv` for field-level dates and source publication dates.
3. For an official retention/trade, set `ipl_2027_roster_status` to `retained_official`/`traded_official`, set `ipl_2027_franchise`, and update the latest verified franchise/season. A player committed elsewhere becomes unavailable and leaves the active shortlist; a player committed to RR becomes an existing option. For an official release use `released_official` and `auction_status=released_conditional`; release alone does not confirm entry.
4. Set `auction_status=officially_listed` only when a source with `document_kind=official_2027_auction_list` names the player. The script rejects a news registration report as proof. A reported process belongs in `reported_auction_status`. Keep reporting and official confirmation separate. International-only retirement never automatically excludes a player. An actual IPL comeback needs a scope-correct update of the retirement status, not merely an overseas signing or return intent.
5. Run `refresh_player_status.py --data-dir "/path/to/Data Pack" --as-of YYYY-MM-DD`, then `refine_evidence.py --data-dir "/path/to/Data Pack"`, `build.py`, `verify.py --browser`, visually inspect the PDF and rerun `package.py`. Current operational actions and ranking annotations come from the materialized CSV. Reassess editorial squad needs if RR's roster changes materially; the performance study remains historical.

The optional command `python3 analysis/fetch_public_rosters.py --as-of YYYY-MM-DD` downloads only public IPL data. Its endpoint is the site's live roster feed and this script labels the snapshot as 2026 roster history. **Review the page's season and replacement history before replacing the preserved 2026 baseline, especially after a season rollover.** Do not run it automatically as a 2027-retention detector. The refresh script itself has no network access.

The ranking lock prevents unrecorded score or order changes. The current eligibility revision is explicitly authorised by the organiser clarification and the user's confirmation that retired players appear in the dropdown listing. Future policy changes must record their evidence and regenerate all dependent outputs together. No upload or dropdown entry was performed.

## Privacy

This bundle contains code, public references, aggregate outputs and the **single worked delivery explicitly requested for the report**, reproduced in `auction_brief_evidence.json`. It contains no original CSVs or bulk delivery-level exports. The proprietary data pack was processed locally; no records were uploaded, committed to a repository or sent to external analysis services. The optional dashboard remains aggregate-only and does not transmit data. Public links open only when clicked.

## Judgments to review in your own words

1. Is Indian No. 6 flexibility worth an auction place if RR retains sufficient existing lower-order options? Shashank's overall lift supports a conditional watchlist; the death-phase evidence weakens a pure death-specialist pitch.
2. Does RR need reserve Indian death bowling after retention, and what would make you choose Avesh over Bhuvneshwar? Their scores do not establish a clear winner, and Avesh's IPL middle phase does not support the earlier upgrade claim.
3. Why is the pressure definition useful, and what does it miss? The worked ball is explanatory and the historical pooled rankings are not forecasts of future form or confirmed auction availability. Check actual dropdown eligibility before entering the final lists.

Public competition rules (source S11) allow AI assistance but require the final insights, picks and recommendations to be the participant's own; wholly AI-generated submissions may be disqualified. Review, validate and adapt this work before submitting it. The supplied brief controls the two separate top-10 lists; the public event listing does not expose the player dropdown choices.
