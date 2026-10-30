# Routine instructions — initially inactive

Owner: {{coordinator.name}} ({{bindings.head}}). Time zone: {{timezone}}. Verify native saved schedules and next run, not just the request text. Use local wall-clock recurrence. Check-in/nudge/idea follow {{schedule.days}}. Research and analytics use Sunday. Only selected phases may be created; complete installation and live acceptance before activating routines.

## checkin — {{schedule.checkin}}
```text
Run STEP 1 of the daily loop in this chat once per local day. Set internal mode/bottleneck, rotate the opener and send the four-line check-in. On a reply run intake → summary → three teams → logs → QC → one all-delivered message. Use the resolved master and agents/daily_briefing_orchestrator.md. Never duplicate today's check-in or summary.
```
## nudge — {{schedule.nudge}}
```text
Check today's coordinator chat. If the user already replied or was nudged, send nothing. Otherwise send one brief check-in nudge. If reply detection is unavailable, do not run unattended; record this setup limitation.
```
## idea — {{schedule.idea}}
```text
If the user already replied, send nothing. Otherwise offer one complete filmable idea with hook, 3–6 shots, on-screen text, search phrase and CTA; exclude ideas used in fourteen days, offered in seven days or expired. Go selects it; a new user idea wins. Log the offer. If no reply by local day end, append one silent-day log row; no more messages and no notification to anyone else.
```
## comments — {{schedule.comments}} — Phase 2 only
```text
Run agents/comment_strategy.md in this chat. Draft replies only. Never post comments or contact outsiders.
```
## research — Sunday {{schedule.research}} — Phase 2 only
```text
Run agents/strategy_rd.md using the configured niche, audience and real constraints. Cite current research, label unavailable or unverified facts, and propose changes rather than silently rewriting configuration.
```
## analytics — Sunday {{schedule.analytics}} — Phase 3 only
```text
Run agents/analytics_feedback.md. Ask once for screenshots; missing numbers are unknown. Do not infer analytics from public profiles.
```
