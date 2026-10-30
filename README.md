# Grok Bot Content Engine

![Grok Bot banner](assets/grokbot.png)

A customizable content team for TikTok, Instagram and YouTube. Give the coordinator one idea or voice note; three platform teams turn it into hooks, captions, titles, hashtags and copyable drafts. You choose what to film and publish manually.

One coordinator, twelve specialists, three team chats and one standalone thumbnail bot. The architecture stays the same for every niche. Your identity, audience, voice, pillars, schedule and goals come from one local profile.

## Start with your agent

Download or clone this repository, then send your Grok Bot this message with the folder attached or available on its shared computer:

> Set up this Grok Bot Content Engine for me using skills/setup-content-engine/SKILL.md. Ask only for missing context, use my niche and audience, and verify the installation before enabling any routines. Use only resources belonging to this deployment. I will publish content myself.

The [setup skill](skills/setup-content-engine/SKILL.md) automates through the actual tools available in your account. It collects essentials, records created resources, compiles bound instructions and reports human-only steps. **This release has local automated tests; live account provisioning and model behavior still require the acceptance run.** It is not an external Grok Bot API client. Missing capabilities are reported, never simulated as success.

## What you customize

Copy `config/user.example.json` to ignored `config/user.json`, or let the setup skill do it. Supply niche, audience, IANA time zone and three ordered daily routine times; choose daily or weekdays. Defaults: display name User, coordinator Content Coordinator, clear practical voice, optional facts unknown. Phase 2 (comments/research) and Phase 3 (analytics) are opt-in. There is no assumed follower target, fixed deadline, personal baseline or account eligibility.

- [Start here](00_README_START_HERE.md): workflow and user experience.
- [Deployment guide](02_DEPLOYMENT_GUIDE.md): setup, updates, recovery and portability.
- [Master rules](01_MASTER_CONFIG.md): authoritative source; the deployment copy resolves your profile.
- [Architecture](architecture/README.md): the same ten layers, with configurable context.
- [Examples](examples/): illustrative sessions, never seeded history.

## Local preparation and checks

Python 3.10+ with IANA time-zone data is required for the stdlib preparation scripts. On systems without time-zone data install `tzdata`. Thumbnail rendering additionally needs Pillow and NumPy; `bash tools/thumbnail/setup.sh` creates its environment. The optional cut-out model uses a separate requirements file.

```sh
python3 scripts/verify.py --mode template
python3 -m unittest discover -s tests -v
python3 scripts/release.py --output /tmp/grok-bot-content-engine.zip
```

Tests for images use the current Python interpreter; install `tools/thumbnail/requirements.txt` in that environment first. Profile generation and journal tests need no model credentials or network. `python3 bot_profiles/_build_profiles.py` rebuilds committed neutral previews. Never install these unbound previews as a working deployment.

Personal profiles, IDs, generated deployments and logs belong in ignored `.local/<instance>/` (or `config/user.json`). Releases use an explicit allowlist, not everything in the folder. The MIT license covers project code and instructions; [third-party notices](THIRD_PARTY_NOTICES.md) cover bundled fonts. This is a community template, not an official product integration. Grok Bot access and usage depend on your provider's plan; no free-service claim is made.
