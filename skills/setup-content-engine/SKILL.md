---
name: setup-content-engine
description: Install, customize, update or recover this content engine in a user's Grok Bot account, using the repository profile, native account tools and a local setup journal. Use for this engine's setup rather than general content drafting.
license: MIT
---

# Set up the content engine

Produce a verified, user-aligned deployment of the existing fourteen-bot/three-group system. Use actual native tools in the current harness; do not invent API endpoints or claim unsupported integration. This skill installs this repository, not an unrelated skill package. Read `../../02_DEPLOYMENT_GUIDE.md` for local commands, [capabilities](references/capabilities.md) for tool mapping and [acceptance](references/acceptance.md) before tests.

## Context and capability check

Locate the repository and inspect its master, topology and example profile. Ask only for missing essential niche, audience, IANA time zone and checkin/nudge/idea schedule (daily or weekdays). Default creator/operator User and coordinator Content Coordinator. Optional facts, account statistics, credentials and growth targets are unknown unless supplied. Propose pillars from the niche if absent, obtain selection, and adapt neutral idea/openers/hashtag/watch-list seeds to actual constraints; no fabricated trends or personal facts. Do not repeat an interview when a local profile already answers it.

Resolve repository and cover paths on the actual host. Use a unique ignored `.local/<instance>/` directory. Save the profile there and validate with `setup_state.py ... status` before making any remote resource. Use one setup actor per instance. Discover supported creation, inspection, messaging, membership, durable instruction, file, routine, reply detection and renderer operations. Record verified capabilities and limitations. If you cannot read/write local files or run scripts, hand over the precise missing preparation operation and wait for verified files, not an invented success.

A request to set up this engine authorizes its resources and selected routines. Host approvals still apply. Credentials use the host secure flow, never the profile or journal. No social account access, public publishing, unrelated bot edits or external outreach is implied.

## Create and bind

Inspect an existing journal first, and reconcile every recorded resource against native state. Record creation receipts immediately with `bind KEY ACTUAL_ID --ownership created --evidence RECEIPT`. Explicit user selection permits `--ownership selected`; a matching name alone does not. If using the current bot as coordinator, get the user's explicit selection; otherwise create a focused coordinator. Do not change the account's global primary bot or timezone setting silently.

Create/select the coordinator, twelve specialists and standalone IG Thumbnail; create the three groups with the coordinator and the four matching specialists from `ids.json`. Creation may use the host's native tools or verified UI. Keep instructions inert until bound: tell new bots setup is in progress, do not start work, schedule, message outsiders or publish. Where a native step is not exposed, give exact UI instructions and inspect the result after the human completes them. No speculative REST calls. On timeout inspect scoped resources/action history before retrying; never create a duplicate to clear uncertainty.

Export bindings using `export-ids`; only when all seventeen are complete, compile with `--mode deploy --profile ... --ids ... --output .local/<instance>/bundle`. Run `verify.py --mode deploy --bundle ...`, then register with journal `bundle PATH`. This is two-pass installation: resources first, resolved instructions second. All IDs remain local; source templates stay unbound.

## Install and verify

Put the resolved bundle on the shared host and make the root/references accessible. Deliver each role's fenced instructions from the matching compiled `bot_profiles` file, the resolved master and relevant references. On current personal Grok Bots use a durable role message/skill and ask the bot to retain role ownership and reopen the current master before work. Use a description field only if the actual bot type exposes one. Keep the complete module instructions in accessible files if a message is too long; never silently truncate. Verify the bot can open them and state its role, current configuration hash, coordinator/group IDs and boundaries. Record `install` only after delivery, and `verify` only after readback. Post each compiled shared team context to its own group and verify it is available to members.

Verify exact group membership by actual IDs: coordinator + four matching specialists, no extras; record `verify GROUP_KEY --members ...`. Group instructions must keep replies in that group. IG Thumbnail stays standalone. Install the renderer on the configured workspace using its setup script; render one real text-only sample, inspect the 1080×1920 JPEG and record thumbnail capability. Prefer no optional model download unless needed.

Create only selected routines, initially paused, owned by the coordinator. Use the compiled routine prompts and `schedule.json`. If native creation cannot start paused, temporarily schedule nothing and obtain the human pause/verification step before continuing; do not leave unattended partially installed routines. Inspect instruction, owner, local time, days, IANA zone, next-run and paused status, then record each using `routine`. Never change an account-wide timezone automatically: if the provider cannot honor this deployment's zone independently, explain the exact account setting to the user and verify the saved schedule after they change it. Missing reply detection leaves automatic nudge/idea disabled and the full setup incomplete; a manual conversation is still usable but is not a successful automated install.

## Acceptance and activation

Run every relevant case in [acceptance](references/acceptance.md) with safe test content and routines paused. Capture receipts/timestamps and actual outputs; never prefill or manufacture evidence. Store per-case results locally. Record `test --kind live --passed yes` only after all required cases pass in this account; offline journal/compiler tests are `simulation` and cannot unlock activation. Check `status`. Missing steps, unsupported required capabilities, failed QC or unverified schedules leave automation inactive with precise handoffs.

When ready, enable only this deployment's selected routines through native tools, inspect the actual enabled state and record `activate --evidence ...`. The command records evidence, not the remote action itself. If partial native activation fails, pause all instance routines, inspect the result and record pause; if actual status cannot be verified report affected IDs and unknown state. Return created/selected resources, installed profile version/hash, enabled schedules, acceptance evidence and any outstanding limitation. Never call it fully tested from a local build alone.

## Update and resume

Inspect and pause the instance's actual routines before changing active configuration; record pause. Preserve IDs and logs. Profile or bundle changes invalidate old installed/test receipts. Compile/register the new bundle, install current instructions/references, verify all memberships and selected schedules, rerun acceptance, then activate. Changed or missing bound resources require reconciliation. After verified pause, use journal `replace KEY OLD_ID NEW_ID --ownership created|selected --evidence RECEIPT` only for an intentionally created deployment replacement or a resource explicitly selected by the user. This retains the other bindings, records the prior ID and invalidates dependent installation/schedule/test evidence. Recompile, reinstall and reverify; never overwrite an unrelated resource. Do not delete old resources or clear their memories as a default migration strategy. Leave partial failures recorded and inactive for recovery.
