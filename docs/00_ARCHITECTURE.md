# Hockey Roster Manager — Initial Architecture

## Purpose

Build a self-hosted Fantasy Hockey Roster Management Tool that helps make
daily roster, lineup, free-agent, add/drop, streaming, and schedule decisions.

The first supported league is NFHL.

The immediate goal is a useful NFHL Roster Manager, not a generic fantasy
sports platform.

## Project Boundary

Project root:

`/Volume1/Bots/fantasy/RosterManagers/hockey`

This is an independent application.

It must not runtime-depend on:

- `/Volume1/Bots/fantasy/mlf_roster_manager`
- `/Volume1/Bots/fantasy/DraftBoards/nfhl`

Existing projects may be inspected for proven patterns, but Hockey owns its
own source, configuration, runtime, deployment lifecycle, and state.

`/Volume1/Bots/fantasy/RosterManagers` is organizational only and must not
become a shared application/code repository.

## Application vs League Instance

Hockey is the application.

NFHL is the first league instance.

Conceptually:

    hockey/
        application code
        provider integrations
        recommendation logic
        evaluation
        UI
        instances/
            nfhl/

Future hockey leagues may become additional instances when justified.

Do not create separate copies of the Hockey application for each league.

## Provider Boundary

Yahoo is the initial fantasy-platform provider.

Provider-specific acquisition and authentication must remain separated from
the internal Hockey analytical model.

Conceptual flow:

    Yahoo
      ->
    provider adapter
      ->
    canonical Hockey data
      ->
    projections / context
      ->
    strategy / optimization
      ->
    recommendations
      ->
    evaluation / UI

Do not make Yahoo identifiers or Yahoo response structures the analytical
model when a provider-neutral Hockey concept is appropriate.

Yahoo player keys remain authoritative provider identities for Yahoo players.

## NFHL Verified Facts

Yahoo league key:

`477.l.10961`

Yahoo team:

`477.l.10961.t.1` — Drop The Gloves

League:

- 14 teams
- Private
- Head-to-Head Points
- Redraft
- Daily/date-based rosters
- Intraday lineup deadline
- 7 weekly adds
- Rolling waivers
- No FAAB
- 6 playoff teams

Normal roster:

- C: 2
- LW: 2
- RW: 2
- F: 1
- D: 4
- Util: 1
- G: 2
- BN: 4
- IR+: 2
- NA: 1

Scoring:

Skaters:

- G: 4
- A: 2.5
- PIM: 0.2
- PPP: 1
- SHP: 1.25
- SOG: 0.25
- HIT: 0.5
- BLK: 0.5

Goalies:

- W: 3
- GA: -1
- SV: 0.25
- SHO: 2.5

These facts should normally be refreshed from authoritative Yahoo settings
rather than duplicated as permanent hard-coded application logic.

## Analytical Boundaries

Keep these concepts distinct:

1. League Definition
   - What are the league's factual rules?

2. Competitive Context
   - What is happening in the league, matchup, schedule, and roster now?

3. Strategy Policy
   - What should the manager optimize given league format and goals?

4. Recommendation Engine
   - Which action best satisfies that objective?

Do not scatter league-name checks such as `if league == NFHL` through the
analytical engine when the behavior can be driven by league rules or policy.

## Primary Product Goals

The application should eventually answer:

- Who should start today?
- Who should be benched?
- Who is injured, scratched, inactive, or not playing?
- Which rostered players play today?
- What is each player's expected fantasy-point value?
- Which free agents are meaningful upgrades?
- Who should be dropped for an add?
- What is the incremental today and rest-of-week value of a move?
- Where are roster-position/game-day bottlenecks?
- Which streaming opportunities create meaningful incremental value?
- Why is each recommendation being made?

Avoid manufacturing transactions when HOLD is the best action.

## Evaluation

Recommendations must eventually be evaluated against actual results.

Preserve enough historical evidence to reconstruct:

- available roster
- projections
- statuses
- recommendations
- actual roster
- actual starters
- actual results
- realized fantasy points

Missing result data must not silently become zero.

Raw provider captures should be preserved when useful for reproducibility,
debugging, identity resolution, and evaluation.

## Future Commercialization

Commercialization is a future design consideration, not current scope.

Current architecture should avoid obvious barriers to:

- multiple users
- multiple leagues
- multiple fantasy providers
- sport-specific strategy
- tenant/user isolation

Do not currently build:

- billing
- subscriptions
- multi-tenant SaaS infrastructure
- generic cross-sport frameworks

Prove the NFHL Hockey decision engine first.

## Development Rules

- Proof-first
- Deterministic micro-steps
- Read before write
- No Zombie Code
- No speculative compatibility layers
- No duplicate implementations
- No cross-project runtime dependencies
- Document major architecture decisions before implementing them
- NAS/runtime/Docker work is performed through Bash/SSH on Apollo
- Git operations are performed from Windows PowerShell

## Player Identity Resolution

Yahoo and NHL player identifiers are different provider namespaces.

The Hockey Roster Manager resolves them through a provider-neutral identity
layer before NHL statistics or projections are joined to Yahoo players.

NHL-side identity source:
- NHL player search registry is the primary NHL identity universe.
- NHL season-stat rows are statistical facts keyed by NHL playerId; they are
  not the canonical identity registry because players may have no NHL stat
  row for a particular season.

Resolution policy:
- normalize exact player names deterministically, including Unicode marks;
- a globally unique Yahoo name plus globally unique NHL name may resolve
  directly;
- duplicate-name groups are resolved one-to-one using canonical NHL team and
  position evidence;
- within a duplicate-name group, position-only or team-only resolution is
  allowed only when exactly one Yahoo and one NHL candidate remain for that
  evidence;
- final one-to-one elimination is allowed only when exactly one Yahoo and one
  NHL candidate remain;
- the same NHL playerId may never be assigned to multiple Yahoo players;
- fuzzy-name matching must never silently assign an identity;
- unresolved identities remain explicitly unresolved and may be handled by a
  separately reviewed alias/exception mechanism when justified.

The provider_player_key remains the authoritative Yahoo identity and NHL
playerId remains the authoritative NHL identity. Recommendation logic must
not join player data across providers by display name.

Reviewed provider-specific identity exceptions:
- exact provider-player-key to NHL-playerId mappings may be used when the
  normal deterministic resolver cannot reconcile legitimate provider display
  differences such as nicknames, formal names, or position-label differences;
- every exception must be manually verified against NHL identity evidence;
- exceptions must be explicit and auditable;
- fuzzy matching must not create or modify exceptions automatically;
- exceptions are provider/season identity data, not recommendation logic.

## Historical NHL Statistical Baseline

Official NHL season statistics are the baseline source for historical player
performance under NFHL scoring.

NHL Stats REST retrieval policy:
- request season aggregate reports with `limit=-1`;
- sort deterministically by `playerId` ascending;
- validate returned row count against the API-reported total;
- require one unique row per NHL playerId;
- require every scoring field used by NFHL to be present;
- treat the requested seasonId in the API filter as authoritative; aggregate result rows may omit seasonId;
- if a result row does include seasonId, require it to match the requested season;
- require skater summary and realtime reports to contain the same playerId set;
- do not silently deduplicate unsafe offset-paginated responses;
- do not silently treat missing reports or missing statistical fields as zero.

The baseline converts official NHL statistics through the live Yahoo NFHL
scoring definition. Yahoo rankings are not player-quality inputs.

Historical fantasy points are descriptive actual performance, not a projection.
Projection models will be layered separately on top of canonical historical
statistics and other validated predictive inputs.

## Yahoo Player Historical Value Baseline

The Roster Manager operates on the Yahoo fantasy player universe, so historical
NHL value must be joined back to Yahoo players through the canonical player
identity layer.

Each Yahoo player receives exactly one historical coverage state:

- `historical_value_available`: NHL identity resolved and historical NFHL value
  exists for the requested season;
- `resolved_no_history`: NHL identity resolved but no historical NHL value row
  exists for the requested season;
- `identity_unresolved`: cross-provider NHL identity remains unresolved.

Missing historical value is represented explicitly as absent data. It must not
be converted to zero fantasy points or zero fantasy points per game.

Historical FPPG remains descriptive prior performance. It is not itself a
projection, and small-sample historical rates must not be allowed to dominate
future player-value recommendations without projection-specific reliability
handling.

## Backtested Historical Projection Baseline

The first predictive baseline is derived only from prior official NHL
performance scored under the current NFHL scoring definition.

Backtesting against the 2024-25 and 2025-26 seasons selected:

- prior-season decay weights, oldest to newest: 0.25, 0.50, 1.00;
- skaters: regress the decay-weighted rate toward the skater population mean
  using 10 effective games of prior strength;
- goalies: regress the decay-weighted rate toward the goalie population mean
  using 40 effective games of prior strength.

These parameters were chosen from out-of-season historical backtests rather
than arbitrary tuning.

The model is a historical projection baseline, not the finished player
projection system.

In particular:
- historical FPPG must not simply be copied forward;
- small samples are explicitly regressed;
- players with older NHL history but no most-recent-season line may still
  receive a historical projection;
- players with no NHL history receive no historical projection rather than
  zero value;
- goalie historical-rate predictability is materially weaker than skater
  predictability, so goalie role, expected starts, team context, and current
  depth-chart information must be modeled separately before goalie
  recommendations are considered complete;
- observed backtest bias remains an evaluation metric and is not yet applied
  as an automatic correction.

## Established NHL Skater Projection

For skaters with NHL history, the production preseason projection begins with
the backtested historical-rate baseline and then applies a separately
backtested calibration layer.

The historical baseline uses:
- three prior NHL seasons;
- decay weights of 0.25, 0.50, and 1.00 from oldest to newest;
- 10 effective games of regression toward the skater population mean.

A linear age adjustment was retained only after out-of-sample testing showed
incremental improvement beyond a generic prior-season bias correction.

Across the two backtest seasons:
- 20+ GP skaters improved approximately 2.47% MAE versus bias correction alone;
- 40+ GP skaters improved approximately 3.42% MAE versus bias correction alone.

A quadratic age term was rejected because it produced no meaningful
out-of-sample improvement over the simpler linear model.

The production calibration is fitted from the most recently completed season,
using only players with at least 20 games in that target season. The model
preserves separate explainable values for:
- historical baseline FPPG;
- general calibration adjustment;
- age adjustment;
- final calibrated projected FPPG.

Age is measured against an October 1 season reference date so the age feature
is stable and comparable across historical backtests and production seasons.

This remains a season-level player-strength projection. Current-season form,
usage, role, matchup, and daily game context are separate downstream inputs to
daily expected fantasy value.

## Rookie Skater Projection

Skaters with no prior NHL regular-season history use a separate preseason
rookie projection rather than the established-player historical-rate model.

The rookie model was developed from first-year NHL skaters in the 2023-24,
2024-25, and 2025-26 seasons. Only rookies who played at least 20 NHL games in
their first season were used as the modeling target, producing 102 historical
training observations.

Candidate preseason inputs included:
- age;
- NHL draft capital;
- primary pre-NHL league production;
- position.

Out-of-sample testing showed that age plus draft capital consistently improved
on a rookie-population mean. Pre-NHL production and position did not provide
stable incremental improvement across forward test seasons and are therefore
not used in the Version 1 projection.

Draft capital is represented as the inverse square root of overall draft pick.
This treatment materially improved forecasting for the fantasy-relevant upper
tail compared with a logarithmic draft-pick model while also improving overall
rookie MAE.

Across the two forward tests, the inverse-square-root model produced:
- overall rookie average MAE of approximately 0.5837 NFHL FPPG;
- top-10 draft-pick average MAE of approximately 0.9027;
- 3.0+ actual FPPG rookie average MAE of approximately 0.8442.

The model remains intentionally conservative. Current NHL roster status,
ice time, power-play role, current-season performance, and daily matchup are
separate downstream signals and may rapidly supersede the preseason rookie
prior once NHL games begin.

Undrafted players use an effective draft pick of 250 for this model.

Players with older NHL regular-season history are not classified as rookies
and are handled separately. Goalies are excluded from this rookie-skater model
and are handled by the goalie projection system.

## Long-Absence NHL Skater Projection

Skaters who have prior NHL regular-season experience but no NHL history within
the established player's three-season projection window are treated separately
from both established NHL skaters and true rookies.

A historical backtest examined NHL skaters who returned after missing at least
three consecutive NHL seasons.

For returners who subsequently played at least 20 NHL games:
- sample size was 10 players;
- a generic skater population baseline produced approximately 0.6411 MAE;
- raw stale NHL FPPG produced approximately 0.9715 MAE;
- stale NHL FPPG regressed with 10 effective games produced approximately
  0.8144 MAE.

For returners with at least 10 games, the same ordering held:
- population baseline MAE approximately 0.6820;
- raw stale NHL FPPG approximately 0.9150;
- shrunk stale NHL FPPG approximately 0.8335.

Although stale NHL performance retained some rank signal in the small
meaningful-returner cohort, it was not reliable enough as a numerical preseason
forecast.

The Version 1 long-absence skater policy therefore:
- does not use stale player-specific NHL FPPG as a projection adjustment;
- uses the most recently completed NHL season's skater population mean under
  current NFHL scoring as a conservative preseason prior;
- preserves the player's prior NHL season history for explanation and audit;
- marks the projection as a low-confidence fallback;
- allows current NHL roster status, role, ice time, power-play usage, and
  current-season production to supersede the fallback rapidly once new evidence
  becomes available.

Goalies are excluded from this policy and are handled by the goalie projection
system.

## Goalie Preseason Workload Projection

Goalie quality and goalie workload are modeled separately.

Historical NHL goalie fantasy-point rate remains a conservative preseason
quality prior. Backtesting did not support adding prior save percentage,
quality-start percentage, or shots-against rate as independent preseason
calibration factors.

Future goalie workload cannot be inferred reliably from historical starts
alone. Prior-season starts are useful as a fallback signal, but current team
hierarchy and coaching deployment require a forward-looking workload input.

The workload architecture is season-agnostic:

1. The fantasy league supplies the season start year.
2. The canonical NHL season identifier is derived from that year.
3. The NHL provider retrieves current canonical teams.
4. The NHL provider retrieves each club's complete schedule for that season.
5. Regular-season games are counted dynamically for each team.
6. The application discovers the newest available goalie-workload snapshot for
   the requested season.
7. A provider adapter converts that snapshot into canonical
   GoalieWorkloadProjection rows.
8. The source projection is validated against the actual NHL team universe and
   official regular-season game counts for that season.

No production behavior may depend on a hard-coded season identifier, snapshot
date, filename, 32-team assumption, or fixed regular-season game count.

Season-specific projection files are data, not application logic. The reference
layout is:

    data/reference/goalie_projections/<provider>/<season_id>/<snapshot-date>.csv

The newest valid snapshot for the requested season is selected automatically.

Daily Faceoff is the initial optional external workload provider. Its
provider-specific team vocabulary is isolated inside its adapter. Daily
Faceoff fantasy points, rankings, ADP, and scoring calculations are not part of
the NFHL player-value model.

A complete workload source allocates the team's entire official regular-season
schedule among its projected goalies. A current NHL roster goalie omitted from
such a complete source therefore has a source-implied zero workload rather
than missing workload data.

If no valid external workload snapshot exists for a season, the application may
use the internally backtested historical workload model as an explicitly
lower-confidence fallback. External and fallback workloads must never be added
together.

Once a season begins, actual starts, current role, injuries, transactions, and
daily starter information progressively supersede the preseason workload prior.

## Canonical Preseason Goalie Projection

Preseason goalie quality and workload remain separate inputs and are combined
only at the player-value layer.

Goalie quality:
- established goalies use the existing three-season historical NFHL
  fantasy-point-rate projection with 40 effective games of shrinkage;
- resolved goalies without usable recent NHL history use the same goalie
  population mean that established projections regress toward;
- the population prior is explicitly identified rather than represented as
  zero or missing quality.

Goalie workload:
- a valid complete external seasonal workload source is authoritative for its
  team allocation;
- a goalie explicitly present in that source receives the projected starts
  supplied by the source;
- a current NHL roster goalie omitted from a complete source receives a
  source-implied zero workload;
- a resolved Yahoo goalie not on a current NHL roster receives zero current NHL
  preseason workload and retains a distinct workload state;
- if no valid external snapshot exists, the internally backtested historical
  workload model may supply the lower-confidence workload instead;
- external and fallback workload projections are mutually exclusive.

The combined preseason start-based value is:

    projected goalie fantasy points per appearance
    × projected games started

This combined value is a preseason ranking aid, not a daily-start projection.
Quality rate, workload, workload provenance, and combined value remain separate
canonical fields so that confirmed starts, current role, opponent context, and
current-season performance can supersede preseason workload independently.

### Internal Goalie Workload Fallback

The external preseason workload snapshot is preferred because current goalie
hierarchy is not reliably represented by historical starts alone.

When no valid external workload snapshot exists for the requested season,
Version 1 uses each current NHL roster goalie's games started from the most
recent completed NHL regular season as the internal lower-confidence workload
fallback.

This choice follows the workload backtest:
- prior-season starts were more predictive than the tested three-season
  decay-weighted starts model;
- a fitted regression produced only modest average improvement and was not
  sufficiently stable across validation seasons to justify production
  coefficients;
- therefore no season-specific regression coefficients are embedded in the
  application.

A current NHL roster goalie with no starts in the immediately preceding NHL
season receives a zero-start historical fallback. This represents absence of
historical workload evidence, not a claim that the goalie cannot earn starts
in the new season.

The fallback does not claim to reproduce the current team's exact schedule
allocation. It is deliberately lower confidence and is superseded by a valid
forward-looking workload snapshot or, once play begins, by current role and
daily starter information.


## Canonical Player Strength Projection

The established-skater, rookie-skater, long-absence-skater, and goalie
preseason models remain separate projection models. A canonical join exposes
their season-level projected NFHL fantasy-point rate through one Yahoo-player
interface for downstream roster-management logic.

The join does not recalculate projections. It preserves the source model and
its projected fantasy points per game.

Skater projection families are mutually exclusive. If the same NHL playerId
appears in more than one established, rookie, or long-absence projection
family, construction fails explicitly rather than selecting a model by
precedence.

Yahoo-to-NHL identity resolution is the authoritative join for skaters.
Unresolved identities remain explicitly unresolved. A resolved Yahoo skater
with no current preseason projection receives an explicit no-projection state;
missing projection value is never converted to zero.

Goalie preseason projections already carry the Yahoo player key and canonical
NHL playerId. Their projected fantasy points per game represents goalie
quality strength. Projected season starts and start-based season value remain
separate workload fields and are not substituted for daily expected fantasy
value.

Daily schedule, current-season form, ice time, special-teams role, injury
status, matchup context, and confirmed goalie-start information remain
downstream inputs. The canonical player-strength projection is a season-level
strength input only.


## Phase 4 Daily Data Source Policy

Phase 4 separates stable fantasy-provider state, official NHL facts,
underlying-performance analytics, tracking enrichment, and volatile deployment
information rather than treating any one external source as authoritative for
all daily decisions.

The initial source policy is:

- Yahoo is authoritative for fantasy roster state, player eligibility, fantasy
  market ownership, fantasy status, league rules, and transaction context.
- Official NHL data is authoritative for canonical NHL identity, schedule,
  game facts, official box-score production, and official shift information.
- MoneyPuck is the initial underlying-performance and recent-trend provider.
  Approved downloadable datasets are used rather than scraping unlisted pages.
  MoneyPuck playerId is the canonical numeric NHL playerId, so no additional
  player-identity crosswalk is required.
- NHL EDGE is an optional advanced-tracking enrichment source. Its skating,
  shot-location, zone, and goalie tracking signals must demonstrate useful
  incremental predictive value before they receive material model weight.
- Daily Faceoff is the initial volatile deployment source for current lines,
  power-play units, injuries, and starting-goalie confirmation.

MoneyPuck season-summary skater data is preserved at its native situation
grain: all, 5on5, 5on4, 4on5, and other. Season, last-10, and last-20 windows
remain distinct source observations. The provider layer does not decide their
model weights.

Current-season trend data remains downstream from the season-strength
projection. Recent production or underlying-process signals must not silently
replace the preseason/season-strength prior. The daily-value model will define
how evidence is blended as the current-season sample grows.

Provider failures or unavailable early-season data must remain explicit.
Missing current-season trend data must not be converted to zero performance.

MoneyPuck normalization contract:

- `games_played` is retained from the source for sample-size and per-game usage
  calculations;
- MoneyPuck `icetime` is measured in seconds and is stored canonically as
  `ice_time_seconds`;
- all-situation ice time equals the sum of 5on5, 5on4, 4on5, and other ice
  time;
- TOI/game is calculated as `ice_time_seconds / games_played / 60`;
- event-rate metrics are normalized per 60 minutes using source ice time;
- a zero-game or zero-ice-time observation has explicit `no_sample` state and
  derived rate values remain null rather than becoming zero;
- normalization does not assign recommendation weight or fantasy-point
  adjustment. Trend weighting remains a downstream modeling decision.

## Current-Season Trend Interpretation

Current-season trend interpretation remains separate from the season-strength
projection and from final daily expected fantasy value.

The first interpretation layer produces transparent evidence labels rather
than a single opaque score.

Role/usage evidence compares season, last-20, and last-10 observations for:

- total TOI per game;
- 5-on-4 TOI per game.

A sustained change of at least 1.0 total minute per game or 0.5 power-play
minutes per game is provisionally treated as meaningful role movement.
Role evidence is labeled expanding, stable, shrinking, mixed, or
insufficient_sample.

Underlying-process evidence compares normalized per-60 rates for:

- individual expected goals;
- shots on goal;
- individual shot attempts;
- individual high-danger shots;
- primary assists.

A metric receives improving or declining evidence only when both last-20 and
last-10 differ from the season rate by at least 15 percent in the same
direction. Three of the five process metrics must agree, with no more than one
opposing metric, before the aggregate process label becomes improving or
declining. Otherwise the result remains stable or mixed.

Very small season baselines use an explicit metric-specific denominator floor
so near-zero values do not create arbitrarily large percentage changes.

Finishing evidence compares actual goals minus expected goals per 60 against
the player's own season baseline. Recent finishing at least 0.25 goals per 60
above the season baseline in both last-20 and last-10 is labeled hot; the
inverse is labeled cold. This describes recent finishing behavior only and
does not assume that the difference is purely luck or automatically regress
it.

Role evidence requires at least 10 season games, 10 last-20 games, and 5
last-10 games. Underlying-process and finishing evidence require at least 20
season games, 10 last-20 games, and 5 last-10 games. Smaller samples remain
explicitly insufficient rather than forcing a directional label.

These thresholds are provisional interpretable heuristics. They do not alter
projected fantasy points or recommendations until retrospective evaluation
shows that the signals improve prediction of future NFHL production.

## Daily Faceoff Current Deployment

Daily Faceoff team line-combination pages expose structured deployment data in
the page's `__NEXT_DATA__` payload under `props.pageProps.combinations`.

The `combinations.lines` collection describes deployment groups and ratings;
player membership is carried by repeated rows in `combinations.players`.
A player may therefore appear multiple times across even-strength,
power-play, penalty-kill, or goalie deployment groups.

The Daily Faceoff provider collapses those repeated source rows to one
source-player deployment record while preserving every category/group
assignment.

Daily Faceoff `playerId` is source-specific and is not an NHL playerId.
The raw deployment provider therefore preserves it only as
`source_player_id`. NHL identity is resolved downstream through a
deterministic bridge. Fuzzy name matching is prohibited.

The provider also preserves:

- team abbreviation and source page;
- `sourceName`;
- `updatedAt`;
- injury status;
- game-time-decision state;
- all deployment category/group assignments.

`sourceName` and `updatedAt` are required freshness metadata. For example, an
offseason page may explicitly describe its combinations as projected.
Projected or stale deployment must not silently be treated as confirmed
same-day deployment.

Missing or inconsistent source data remains explicit and must not be converted
to a healthy/active/current-player assumption.

Repeated Daily Faceoff player rows may differ in status fields because one
player can simultaneously have active deployment assignments and an off-ice
injured-reserve assignment. Player-level status is therefore collapsed
deterministically:

- repeated rows for the same Daily Faceoff playerId must have the same exact
  player name;
- null or blank injury statuses do not override a non-null injury status;
- one unique non-null injury status is preserved;
- conflicting non-null injury statuses are rejected;
- game-time-decision is true if any repeated source row marks the player as a
  game-time decision;
- all unique deployment assignments remain preserved.
