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

