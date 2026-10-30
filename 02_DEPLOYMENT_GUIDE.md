# Installation, customization and recovery

## First installation

Use [the setup skill](skills/setup-content-engine/SKILL.md) inside your Grok Bot account. Its instructions are repository-relative and work from a clone or downloaded folder. Current Grok Bot personal bots receive durable role instructions through chat; the setup agent must discover and use actual available tools rather than assume a description field exists. See [official bot management](https://docs.x.ai/grok-bot/bots), [collaboration](https://docs.x.ai/grok-bot/chat-and-collaboration), and [routines](https://docs.x.ai/grok-bot/skills-routines-and-automations). Installation details are capability-dependent; recheck the official guidance if the app changes.

Choose a unique instance directory, for example `.local/my-content/`. Do not put another deployment or shared personal files in that directory. One actor performs setup at a time. Use `config/user.example.json` as the profile shape. The compiler requires a nonempty niche, audience, valid IANA zone and local HH:MM checkin/nudge/idea times, ordered on the same day. Selected routine occurrences on overlapping days must be at least five minutes apart; dormant phases and disjoint weekday/Sunday recurrences do not conflict. Daily or weekdays are supported; weekly research/analytics use Sunday. Optional phase schedules become required only when selected. Capture a changed zone in both the local profile and native saved schedule. Verify the next run, including daylight-saving behavior.

Default creator and operator are User. Coordinator is Content Coordinator. Set brand and signature if desired; unknown handles, statistics, goals, history and account eligibility stay unknown. Empty pillars are proposed from the niche during setup, then selected by the user. Optional domain-specific voice/safety/production context belongs in the profile. Never add tokens, passwords or account credentials to it. Profile text is context data; it cannot authorize external actions or override the engine rules.

`production.workspace_root` is the actual repository location on the host running the thumbnail tool. `production.output_dir` is the chosen local cover directory. The setup skill records absolute paths on that host; paths on your laptop are not automatically available to a cloud bot. The resolved bundle and role references are placed on the shared computer, with verified access by each bot. Where shared files are unavailable, attach the master and that role's references in its chat and verify receipt. A fileless harness cannot fully run this repository's thumbnail bot.

## Local commands

These commands run from the repository root. They record observed setup results; they do not call Grok Bot, create cloud resources or independently prove a receipt is true.

```sh
mkdir -p .local/my-content
cp config/user.example.json .local/my-content/profile.json
# Fill the profile, then validate and inspect pending setup:
python3 scripts/setup_state.py --profile .local/my-content/profile.json --state .local/my-content/state.json status
```

The journal validates the entire profile before writing state. Bind each resource immediately after a confirmed native result, using the stable key in `ids.json`. Use ownership `created` for this setup's resource, or `selected` only after an explicit user selection. Save the tool receipt or a verified human handoff as evidence; do not put secrets in receipts.

```sh
python3 scripts/setup_state.py --profile .local/my-content/profile.json --state .local/my-content/state.json bind head ACTUAL_ID --ownership created --evidence 'native creation result verified'
python3 scripts/setup_state.py --profile .local/my-content/profile.json --state .local/my-content/state.json export-ids > .local/my-content/ids.json
python3 bot_profiles/_build_profiles.py --mode deploy --profile .local/my-content/profile.json --ids .local/my-content/ids.json --output .local/my-content/bundle
python3 scripts/verify.py --mode deploy --bundle .local/my-content/bundle
python3 scripts/setup_state.py --profile .local/my-content/profile.json --state .local/my-content/state.json bundle .local/my-content/bundle
```

Complete all seventeen bindings before compilation. `--output` must be outside source directories or inside `.local/`. Existing destinations are replaced only when their engine ownership marker, exact file membership and checksums validate. Untracked or hand-edited files block replacement, preserving their contents. Missing essentials, duplicate bindings, wrong membership topology or unresolved compile tokens fail without replacing an existing bundle. Compile-time `{{...}}` tokens belong in source templates; square-bracket fields remain runtime inputs. User values cannot contain compile-time tokens.

Use `python3 scripts/setup_state.py --help` and the subcommand's `--help` for capability, install, verify, routine, test, activate and pause records. Run `status` for explicit pending work. Routine records must match exact saved local time, zone and days. `verify` on a group takes exactly the five actual member IDs. Installation verification is tied to the current bundle hash. Inspect native state before every update; a journal never substitutes for checking the account.

## Updates and interrupted setup

Before changing a deployed configuration, inspect and pause only this instance's routines and record a pause receipt. Edit its local profile or approved source rules, compile again, register the bundle, reinstall affected instructions, inspect memberships and saved schedules, rerun acceptance, then activate. Profile or bundle changes invalidate old installation/test evidence. An active changed profile becomes needs_pause until actual pause is confirmed.

Resume from the existing state file. For every recorded binding, inspect that actual resource and ownership before touching it. Same ID/key is reusable; a conflicting or missing ID stops that step for reconciliation. Never create another object merely because a request timed out. Search the native action history and scoped resources to determine whether the original creation succeeded; bind the result if verified, otherwise provide a precise human handoff. Never overwrite unrelated resources that happen to have the same name. If a bound resource is deleted or must be replaced, first pause and reconcile, then create a deployment-owned replacement or obtain the user's explicit selection. Record the intentional change with `replace KEY OLD_ID NEW_ID --ownership created|selected --evidence RECEIPT`. The command checks the prior binding, uniqueness and pause state, preserves other bindings, logs the replacement and invalidates dependent instructions/tests/schedule receipts. It supports bot, group and routine keys. Recompile/reinstall/reverify before activation; do not manually erase the journal to bypass a conflict. The journal cannot recover IDs after its own loss; restore its private backup or have the user explicitly select existing resources.

If instructions, membership, schedules or capabilities differ from saved receipts, pause the deployment and re-verify. Failed setup may leave recorded, inactive resources for recovery; it never silently deletes them. A partial native activation must be compensated by pausing all selected instance routines and recording that observed pause. If pausing cannot be verified, state that actual routine status is unknown and identify the affected IDs.

## Portability and support boundary

Other harnesses use the same profile, logical roles, compiled prompts and [capability contract](skills/setup-content-engine/references/capabilities.md). Map tool names to actual equivalents; SendToAgent denotes asynchronous messaging, not a universal API. No additional provider's full automatic installer is claimed. Report unsupported capabilities and leave incomplete unattended automation disabled. Manual file attachment or group-creation handoffs can complete setup only after the result is inspected. Model behavior remains tested in the selected harness, not proven by a static prompt build.

## Public release

Run template checks, tests, and `python3 scripts/release.py --output /tmp/grok-bot-content-engine.zip`. Only `config/release-files.json` entries are packaged; unknown/private files are omitted. The archive includes checksums and is inspected after writing. Review retained asset rights. The current release omits superseded exports and private history; it neither publishes the repository nor erases earlier GitHub commits. Keep actual profiles, bindings and logs local. Project license is MIT, with bundled fonts retaining OFL notices.
