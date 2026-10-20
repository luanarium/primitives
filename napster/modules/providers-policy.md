# `napster/providers/policy.py` -- MOTD, limits, level gating

**Role.** The defaults, and the one table that says which messages need which
level.

**In the primitive.** `Backend.motd` / `max_results` / `stat_interval` /
`login_timeout` / `level_required`, plus `LEVEL_REQUIRED` lifted whole, §7.

## What it provides the client

- **MOTD (621)**, one message per line, pushed right after login. **The first
  thing a user sees**, and the cheapest announcement surface there is -- no
  HTTP, no pages, no browser. If something needs to reach the user and does
  not need pictures, it goes here.
- **The result cap.** 100, as period servers used. A live client asked for
  `MAX_RESULTS 4976092`, so **clamping is a defence, not an optimisation**.
- **The stats cadence** (214, 60s default) that drives the status bar.
- **The pre-login idle timeout.**

## The level table

Roughly thirty messages are gated: kill, nuke, ban, muzzle, kick, cloak,
redirect, cycle, the config pair, the channel-admin pair, the two broadcast
messages, and `setdataport`. **Declaring it in one place means every
deployment enforces the same thing and a provider cannot forget to.**

`reloadconfig` and `setconfig` are `ELITE`, which the client itself knows:
its syntax strings read `Proper syntax (Elite only): /%s <channel>`.

## Findings encoded here

- **Bans accept a nick *or* an IP**, which is why `is_banned(nick, ip)` takes
  both and checks one set.
- The period tunables worth knowing, none of them implemented here:
  `max_shared` 5000, `max_browse_result` 500, `index_path_depth` 2,
  `max_hotlist` 32, `max_ignore` 32, `max_user_channels` 5, a new channel's
  limit 200, `max_command_length` 2048, plus `flood_commands`/`flood_time`
  and the `eject_when_full` family.
- **A channel's limit can be changed by any member with no notification sent**
  (826). A preserved griefing vector; reproduce it rather than fixing it.

## Lifting it
Lift `LEVEL_REQUIRED` verbatim. The rest is defaults and will be replaced.
