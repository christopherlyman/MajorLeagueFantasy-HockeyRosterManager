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

## Daily Faceoff Player Identity Bridge

Daily Faceoff playerId values remain source-specific and are never treated as
NHL playerId values.

Daily Faceoff deployment identity uses the existing canonical NHL player
registry and the shared `normalize_player_name()` primitive. The Yahoo-specific
`resolve_player_identities()` workflow is not reused because its team and
provider-player contracts are Yahoo-specific.

The Daily Faceoff bridge is intentionally conservative. A source player is
resolved only when:

1. the normalized Daily Faceoff player name matches the normalized NHL player
   name exactly; and
2. exactly one matching NHL identity has the same NHL team abbreviation as the
   Daily Faceoff deployment snapshot.

No fuzzy name matching is allowed. Daily Faceoff deployment-position labels
are not used as identity evidence because special-teams and off-ice rows can
contain assignment positions such as `sk1`, `sk2`, or IR slots rather than the
player's canonical NHL position.

A unique normalized name does not override a team mismatch. A source/NHL team
disagreement may indicate stale or projected deployment data and therefore
remains explicitly unresolved.

The bridge returns the existing canonical `PlayerIdentityResolution` domain
type. The Daily Faceoff `source_player_id` is retained in
`provider_player_key`; the source deployment snapshot remains responsible for
the player's Daily Faceoff name, statuses, assignments, and freshness
metadata.

### Reviewed Daily Faceoff identity overrides

A reviewed Daily Faceoff playerId -> NHL playerId override may be added only
when official NHL evidence proves that a deterministic name mismatch represents
the same player.

An override may bridge the reviewed display-name difference, but it does not
override team identity. The NHL identity referenced by the override must still
have the same canonical NHL team abbreviation as the Daily Faceoff deployment
snapshot. Unknown source player IDs, unknown NHL player IDs, duplicate NHL
assignments, and override team mismatches are rejected.

The initial reviewed exception is Daily Faceoff playerId `31504`,
`Matthew Savoie`, mapped to official NHL playerId `8483512`, `Matt Savoie`.
The mapping was verified against both the official NHL player landing endpoint
and the official NHL current Edmonton roster on 2026-09-06.

## Current-Season NFHL Production

Current-season realized fantasy production is a separate downstream signal from
the season-strength projection.

Official NHL season aggregate statistics remain the authoritative source for
realized current-season counting statistics. The existing NFHL scoring
functions remain the single implementation of league category weights for both
historical and current-season aggregates. The current-production layer does not
reimplement fantasy scoring.

The existing `HistoricalFantasyValue` season aggregate is accepted as an
internal scored input because its fields are season-generic: NHL playerId,
player type, season, games played, total fantasy points, fantasy points per
game, and scoring components. The current-production adapter supplies the
distinct current-season semantics used downstream.

Current-season production is aligned to the canonical player-strength pool so
every fantasy-provider player has an explicit production state:

- `available`: the resolved NHL player has at least one current-season game and
  a valid NFHL fantasy-points-per-game value;
- `no_sample`: NHL identity is resolved, but no current-season game sample is
  available yet;
- `identity_unresolved`: the fantasy-provider player has no canonical NHL
  playerId.

`no_sample` and `identity_unresolved` never synthesize zero fantasy production.
Their total fantasy points, fantasy points per game, and scoring components
remain null. `games_played` is zero because that is the explicit sample-size
state, not a performance estimate.

The official NHL statistics API may legitimately return an empty current-season
population before regular-season games begin. That condition is represented as
`no_sample` for resolved players rather than as an error.

This layer does not decide how quickly current-season production supersedes the
preseason/season-strength prior. Blend weighting remains a separate daily-value
modeling decision and must be calibrated or otherwise explicitly justified.

## Baseline Daily Expected NFHL Value

Daily expected fantasy value is calculated for a specific NHL game date and is
separate from the season-level player-strength projection.

The first baseline implementation intentionally applies no current-production,
trend, deployment, injury, matchup, or goalie-start adjustment. It establishes
the deterministic target-date scoring contract onto which those downstream
adjustments can later be added.

Baseline semantics:

- `scheduled` plus an available season-strength projection produces baseline
  expected NFHL points equal to the player's projected season-strength FPPG;
- `off` produces exactly `0.0` expected fantasy points because a known
  non-playing date has no scoring opportunity;
- `unknown_team` produces `schedule_unknown` with null expected fantasy points;
- a scheduled player without an available strength projection produces
  `strength_unavailable` with null expected fantasy points.

A known off-day zero is therefore fundamentally different from missing player
value. Missing strength or unresolved scheduling must never be converted to
zero.

Fantasy values are signed finite quantities. Negative expected values are
valid and must be preserved, particularly for goalies under NFHL scoring where
goals allowed carry a negative fantasy-point weight. Validation rejects
non-finite values but does not reject or clamp legitimate negative values.

The service requires exact provider-player-key coverage between player strength
and target-date game context, rejects duplicate keys and season/date
mismatches, and preserves player-strength input order.

The baseline season-strength FPPG remains available for explanation even when
the player is off or the schedule is unresolved. It is not itself interpreted
as target-date opportunity.

This baseline is not the final daily projection model. Current-season realized
production, MoneyPuck process/usage evidence, Daily Faceoff deployment,
injury/status evidence, opponent context, rest, and confirmed goalie starts
remain explicit downstream adjustments. Their weights are not implied by this
baseline.

## Three-Day Decision View

The NFHL Roster Manager's primary short-horizon decision surface is a permanent
three-day window:

- Today;
- Tomorrow;
- Day+2.

This horizon is a roster-management requirement rather than presentation-only
UI. NFHL drop, waiver, and reacquisition decisions can create a period during
which the manager cannot immediately recover a released player. Evaluating only
the current date would therefore hide relevant near-term opportunity cost.

For every Yahoo player, the three-day ranking layer preserves the three
individual daily expected values and produces:

- a rank for each date when the player has a usable expected value and is
  scheduled to play;
- the actual expected fantasy points for each date;
- opponent and home/away context for each date;
- the number of scheduled games in the three-day window;
- total expected NFHL points across the three dates when all three daily values
  are known;
- a deterministic three-day rank.

Known off-days contribute exactly zero expected points to the three-day total
but do not receive a daily playing rank. Missing or unresolved daily values do
not become zero; any such value keeps the three-day total unresolved.

Daily and three-day rankings preserve signed expected fantasy values. A player
with a legitimate negative playing expectation remains rankable below players
with higher values; negative performance is not converted to an off-day zero.

The initial Streamlit Three-Day Decision View is intentionally backed by the
baseline daily expected-value model. Current-season production, MoneyPuck
trend/process evidence, Daily Faceoff deployment, injury/status evidence,
goalie-start probability, and matchup effects will improve the same screen
without changing the three-day product contract.

Runtime ranking snapshots are presentation handoff artifacts, not sources of
business truth. Ranking logic remains in the Hockey Roster Manager domain and
service layers; Streamlit consumes the resulting snapshot.

### Compact Three-Day Decision Table

The Streamlit decision table uses the compact roster-management layout:
`Player | Type | Team | Today | Tmr | D+2 | Game`.

Today, Tomorrow, and Day+2 display only `rank (expected NFHL points)`, for
example `2 (7.24)`. Known off-days display `OFF`; unresolved or missing values
display `—`.

`Game` is a separate column containing today's matchup and puck-drop time only,
for example `vs VAN 10:00 PM`. Tomorrow and Day+2 game details remain available
in the canonical data but are intentionally omitted from the table.

Three-day aggregate rank remains available through the independent Sort control
and therefore does not require a visible table column.

Canonical NHL puck-drop time is `start_time_utc`. The UTC value is carried
through PlayerGameContext, daily expected value, three-day ranking, and runtime
snapshot. The NFHL presentation converts it to America/New_York.

### Signed Canonical Player Strength

Canonical projected fantasy points per game are signed finite quantities.
Negative projected FPPG is valid, particularly for goalies under NFHL scoring,
where goals allowed carry negative fantasy value. Canonical player-strength
assembly rejects non-finite values but does not reject or clamp a legitimate
negative fantasy projection.

### Preseason Canonical Strength Assembly

`services/preseason_strength.py` is the permanent Phase-3 to Phase-4 handoff
for preseason player strength. It does not perform Yahoo, NHL, MoneyPuck, or
Daily Faceoff retrieval. Provider orchestration remains outside the projection
model and supplies already-normalized inputs.

For the projection season, the assembler:
- builds the three-season historical skater baseline;
- fits the established-skater age/bias calibration against the immediately
  completed season using its own preceding three-season baseline;
- applies that calibration to current established skaters;
- fits the existing rookie age/draft-capital model from explicitly defined
  training seasons and projects current players with no NHL regular-season
  history;
- applies the existing long-absence population prior to current skaters with
  prior NHL history but no recent baseline;
- builds goalie quality from the three-season historical goalie baseline and
  delegates workload handling to the existing goalie projection service;
- hands the mutually exclusive projection families to
  `build_player_strength_projections()` for exact Yahoo-player coverage and
  canonical source precedence.

The assembler does not duplicate historical fantasy scoring, provider
retrieval, daily context, or lineup logic. Those remain separate layers.

## Yahoo Market Metadata in Three-Day Snapshot

Yahoo is authoritative for fantasy ownership, availability, player eligibility,
and the managed fantasy-team boundary. These facts are roster-management and
presentation context; they do not alter canonical player-strength or daily
expected-points calculations.

The three-day runtime snapshot may be enriched after ranking with one complete
additive market-metadata group on every player row:

- `eligible_positions` — Yahoo fantasy-position eligibility in Yahoo order;
- `market_state` — canonical fantasy market state from `PlayerMarketState`;
- `is_on_managed_team` — whether ownership belongs to the fantasy team managed
  by the current user.

The additive group is backward-compatible with earlier schema-version-1
snapshots. A snapshot contains either all three market fields for every player
row or none of them. Partial or mixed market coverage is invalid.

Predraft Yahoo state is valid. If Yahoo reports empty team rosters and every
player as a free agent, the Roster Manager preserves that state rather than
inventing roster ownership from the DraftBoard or another source. Once Yahoo
publishes roster ownership, the same contract supports My Roster, Free Agents,
Waivers, and Other Teams without changing projection logic.

The Streamlit decision table exposes Yahoo `Eligible Pos.` and a Market filter
when market metadata is present. Three-day rank remains the default decision
sort. Yahoo percent-rostered is not inferred or fabricated; it requires a
separate authoritative provider field before display.

Runtime ranking snapshots remain generated presentation artifacts and are not
committed to source control.

### Yahoo Percent Rostered

Yahoo `percent_owned` is the authoritative source for `% Ros` in the NFHL
decision view. The resource is league-scoped and supplies weekly integer
percentages from 0 through 100.

Yahoo omits `percent_owned.value` for the zero-percent population. This
behavior was validated across the complete Yahoo player pool and independently
through both the league-player and single-player `percent_owned` resources.
The canonical provider therefore maps an omitted week-level `value` to `0`;
explicit values are validated as integers from 0 through 100.

`percent_rostered` is market/presentation context only. It does not alter
player-strength projections, expected fantasy points, ranks, ownership state,
or roster optimization logic.

The three-day snapshot carries `percent_rostered` as an independently optional
additive schema-v1 field. If present on one player row it must be present on
every player row and must be an integer from 0 through 100. Older snapshots
without this field remain valid.

Streamlit displays the field as `% Ros`. Missing snapshot metadata is rendered
as an em dash rather than inferred.

## Current Player Availability

Yahoo player status is the current fantasy-provider signal for whether a
player can reasonably be treated as playable. Provider status is canonicalized
before daily expected value is ranked.

Canonical availability states are:

- `available` — Yahoo status is blank;
- `uncertain` — Yahoo status is `DTD`, or a future nonblank status is not
  explicitly classified;
- `unavailable` — Yahoo status is `NA`, `O`, `IR`, `IR-LT`, or `IR-NR`.

Unknown nonblank statuses fail safe to `uncertain`, not `unavailable`, so a new
Yahoo status cannot silently zero a player's projection.

Schedule state retains precedence. An off-day remains `off`, and an unresolved
team remains schedule-unknown. For a scheduled player whose current canonical
availability is `unavailable`, daily expected value uses
`player_unavailable`, expected fantasy points are `0.0`, and the player is
excluded from the daily rank because only `available` daily-value rows are
ranked.

An `uncertain` player remains projected and rankable. The status is retained
through daily-value data so the presentation layer can flag the risk instead
of pretending certainty.

The current Yahoo status is applied to each game context generated from that
player record until the next provider refresh. This is intentionally a
current-state signal; it is not a forecast of the player's recovery date.

## Canonical Player Strength Artifact

The expensive preseason projection build produces the canonical
`PlayerStrengthProjection` universe for one NHL projection season.

That result is persisted as a season-scoped runtime artifact rather than
recomputed during every daily refresh. For 2026-27 the canonical path is:

`data/runtime/player_strengths_20262027.json`

The artifact contains only canonical player-strength output: provider player
identity, NHL player identity, projection season, player type, strength state,
projection source/state, and projected fantasy points per game.

The preseason-strength artifact is regenerated only when the underlying
preseason model or its source inputs intentionally change. Normal daily
refreshes load this artifact and combine it with fresh provider state,
including Yahoo player/status data, market state, percent rostered, the
official NHL schedule, and subsequent current-season adjustment layers.

The artifact uses schema version 1. Loading is fail-closed: duplicate player
keys, season mismatches, invalid field types, non-finite projected values, or
unsupported schema versions are rejected. Signed finite projected fantasy
points per game remain valid because some canonical goalie strengths may be
negative.

Writes are atomic.

This separation keeps the historical/calibration model reproducible without
making an ordinary daily refresh refetch and recalibrate the entire historical
projection universe.

## Permanent Three-Day Daily Refresh

The ordinary NFHL three-day refresh loads the season-scoped canonical player
strength artifact rather than rebuilding the expensive preseason model.

The refresh combines:

- canonical player strength;
- current Yahoo player/status data;
- current Yahoo market state and percent rostered;
- current official NHL team and schedule data;
- canonical player availability.

It then builds availability-aware daily values, Today/Tomorrow/Day+2 ranks,
the hidden three-day aggregate rank, and the Streamlit snapshot.

Availability metadata is an additive schema-v1 row group:
`availability_state`, `provider_status`, and `provider_status_full`.
The group is all-or-none across snapshot rows. Legacy schema-v1 snapshots
without this group remain valid.

A scheduled hard-unavailable player receives `player_unavailable`, expected
points `0.0`, and no daily rank. A `DTD` player remains projected/rankable
while the provider status remains visible.

The Streamlit decision table displays a compact `Status` column. Blank status
displays as an em dash.

The permanent refresh entrypoint is:

`python -m hockey_rmt.refresh_three_day`

Before the regular season starts, the default base date is the NFHL opening
date. During the season it is the current America/New_York calendar date.
`--base-date YYYY-MM-DD` provides a deterministic override.

## Bounded Current-State Projection Adjustment

Current-state evidence modifies the canonical season-long player strength only
at daily valuation time. It never overwrites or mutates the canonical
player-strength artifact.

For skaters, the adjustment combines four independent signals:

1. Daily Faceoff current deployment;
2. MoneyPuck role trend;
3. MoneyPuck underlying-process trend;
4. official current-season NFHL fantasy production.

Daily Faceoff is the fastest-moving role signal. Its bounded opportunity
effects are:

- EV `f1`: +1.5%;
- EV `f2`: +0.5%;
- EV `f3`: -0.5%;
- EV `f4`: -1.5%;
- EV `d1`: +1.0%;
- EV `d2`: 0%;
- EV `d3`: -1.0%;
- PP `pp1`: +2.5%;
- PP `pp2`: +0.5%;
- a player with an EV assignment but no PP assignment: -1.0%.

The combined Daily Faceoff deployment effect is capped from -3% to +4%.
Unknown or future deployment group identifiers are retained as evidence but
produce no numerical adjustment until explicitly supported.

MoneyPuck interpreted role contributes +3% for `expanding` and -3% for
`shrinking`. `stable`, `mixed`, and `insufficient_sample` are neutral.

MoneyPuck process contributes +1.5% for `improving` and -1.5% for
`declining`. `stable`, `mixed`, and `insufficient_sample` are neutral.
Finishing state never independently raises or lowers the projection.

Current-season fantasy production is progressively blended only for skaters
with a positive canonical baseline. Its maximum weight is 30%, reached at
60 games. The current/baseline FPPG ratio is clipped to 0.75 through 1.25
before blending. When production is above baseline while finishing is `hot`,
or below baseline while finishing is `cold`, the production weight is halved
to reduce reaction to likely finishing variance.

All component factors are combined multiplicatively and the final current-state
factor is hard-capped to 0.88 through 1.12. Thus role, process, and recent
production together can move canonical skater FPPG by no more than 12% before
future matchup adjustments.

Goalies are not adjusted by this skater layer. Their current-form model remains
a separate goalie-specific concern.

The adjustment output preserves each component factor and interpreted state so
future WHY/explainability surfaces can show how the final daily value was
derived.

### Daily-Value Adjustment Seam

Daily valuation preserves both the canonical season-strength baseline and the
bounded current-state adjusted FPPG.

When a complete projection-adjustment set is supplied, a scheduled and
available player uses `adjusted_fantasy_points_per_game` as the pre-matchup
daily expected value. The canonical baseline remains separately retained for
audit and explanation.

When projection adjustments are omitted, daily valuation remains exactly
backward-compatible with the existing season-strength baseline.

Schedule and availability retain precedence:

- unknown schedule remains unknown;
- an off day remains zero;
- a hard-unavailable scheduled player remains zero;
- unavailable canonical strength remains unavailable;
- an adjustment cannot make an otherwise unavailable player playable.

A supplied adjustment set must exactly match the canonical player-strength
provider-key universe. Season, canonical player type, NHL identity, and
canonical baseline FPPG must agree before any adjusted value may be used.

The permanent three-day refresh accepts adjustment rows as an optional
dependency. Provider orchestration remains separate: until the refresh CLI
constructs and supplies current-state evidence, production output remains on
the canonical baseline path.
