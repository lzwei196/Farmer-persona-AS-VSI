# Prompt and model provenance

## Confirmatory experiments

| Experiment | Profiles | Conditions | Providers | Planned logical cells |
|---|---:|---:|---:|---:|
| Original benchmark | 280 | 1 | 3 | 840 |
| Three-country extension | 210 | 1 | 3 | 630 |
| Country-label ablation | 70 | 3 | 3 | 630 |
| Seven-country crossover | 70 | 7 | 3 | 1,470 |

The three ablation arms were: (1) `Country: Tanzania`; (2) `Broad region: East Africa`,
with no country name; and (3) `Country: Nigeria`. Profile-block order and the three arm
positions within each profile were randomized with seed 20260826.

The crossover was completed in a second stage. A new manifest randomized profile blocks and
all seven label positions with seed 20260827, but only Ethiopia, Malawi, Mali, Niger, and
Uganda were newly queried. The Tanzania and Nigeria cells reuse 420 responses from the
true-country and swapped-country ablation arms after byte-identical prompt hashes were
verified. Thus, the seven labels were not queried as one contemporaneously interleaved batch.
The crossover required 1,050 new calls, and the raw-response archive contains all 3,570
experiment-tagged records.

## Collection phases

| Phase | Accepted-response window (UTC) | Recorded CLI versions |
|---|---|---|
| Original four-country benchmark | April 2026; per-call times unavailable | Interface versions unavailable |
| Three-arm ablation | 2026-08-26 12:52:04 to 14:24:38 | Claude 2.1.246; Codex 0.149.1; Kimi 0.30.0 |
| Three-country extension | 2026-08-27 06:52:09 to 07:39:07 | Claude 2.1.247; Codex 0.149.1; Kimi 0.30.0 |
| Five newly queried crossover labels | 2026-08-27 06:53:36 to 08:40:28 | Claude 2.1.247; Codex 0.149.1; Kimi 0.30.0 |

Prompt-hash equality establishes prompt identity for the reused cells. It does not establish
that hosted backends or other provider-side runtime conditions were identical across the two
collection dates. Accordingly, seven-label contrasts may also reflect runtime-condition
differences between the reused 26 August responses and the newly collected 27 August responses.

August 2026 runs recorded Claude CLI 2.1.246-2.1.247, Codex CLI 0.149.1, and Kimi CLI 0.30.0.
Provider-facing names such as `claude-cli-current` describe the client route and are not
immutable backend model identifiers. The original four-country benchmark was collected in
April 2026, and its overwritten metadata did not preserve every client version. Prompt hashes
and randomized run order are retained in `config/manifests/` where available.

No credentials, API keys, command histories, or provider account information are included.
