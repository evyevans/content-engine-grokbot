# Deployment quick path

1. Make the repository available to the user's Grok Bot on its shared computer, or attach the setup skill and files. Run `python3 scripts/verify.py --mode template`.
2. Invoke [setup-content-engine](skills/setup-content-engine/SKILL.md). It asks for missing essentials and validates the profile before remote creation.
3. Use an isolated `.local/<instance>/` directory for the profile, setup journal, account IDs, logs and resolved bundle. Record the actual absolute repository path in `production.workspace_root`; place cover output inside this instance. One setup actor per instance.
4. Create or explicitly select the coordinator, twelve specialists, standalone thumbnail bot and three groups. Record IDs, reconcile uncertain actions, and never bind by name alone.
5. Compile the resolved bundle with the actual profile and bindings; install durable role instructions, master and references; verify receipt and membership. Create selected routines paused, inspect saved local schedules and test reply detection.
6. Run the [live acceptance checklist](skills/setup-content-engine/references/acceptance.md). Record actual evidence. Only a passing live run with no missing required capability permits activation; simulation is insufficient.
7. Enable the selected routines through native tools, inspect the saved enabled state and record it. If any partial activation fails, pause the deployment's routines and report incomplete.

The [full guide](02_DEPLOYMENT_GUIDE.md) includes commands, update/recovery behavior and portability. No API credentials or private cloud folder are bundled. No external resources are created by the local compiler or journal scripts.
