# Harness capability contract

The setup agent maps these operations to available native tools. This repository provides configuration/compilation/journal helpers, not an API transport. Tool names differ by provider. Do not use undocumented endpoints. Tool receipts and human handoffs are observed evidence, not assertions generated to satisfy the journal.

| Operation | Needed result | Unsupported path |
|---|---|---|
| Create/select and inspect bots | 14 owned/explicitly selected IDs with stable role keys | Exact human UI handoff; inspect IDs afterward |
| Create/inspect groups | 3 group IDs, exact coordinator+4 members | Human creation/membership handoff then native readback |
| agent_messaging | Async lead/coordinator handoffs and receipts; SendToAgent priority false or actual equivalent | Full automatic workflow incomplete |
| group_messaging | Coordinator dispatch and team-only responses visible in the right group | Full automatic workflow incomplete |
| durable_instructions | Complete role/master/reference access survives future turns | Attach durable files/skill if supported; otherwise incomplete |
| files | User-specific bundle and local state readable/writable; role references accessible | Verified attachments can supply role files; local preparation needs a capable host |
| scheduling | Create/inspect/pause/enable routines and saved owner/time/zone/days | Exact human steps then inspect; never assume schedule saved |
| reply_detection | Reliably skip nudges/offers after a substantive reply | Leave them disabled; mark full automation incomplete |
| thumbnail_rendering | Existing Python renderer execution and actual JPEG delivery | Prepare tool on host or report missing full-install capability |
| Current web research | Dated source inspection for Phase 2 | Label current research unavailable and use evergreen ideas |

Required activation capabilities are the seven logical keys used by the journal: agent_messaging, group_messaging, durable_instructions, files, scheduling, reply_detection, thumbnail_rendering. Bot/group creation can be handed off before activation because they are installation operations; routine inspection and future runtime capabilities remain essential. Record only verified capabilities, including the exact inspected tool/UI or successful safe operation. Never mark a human-only step complete before readback.

For Grok Bot, inspect current official docs: [bots](https://docs.x.ai/grok-bot/bots), [groups](https://docs.x.ai/grok-bot/chat-and-collaboration), [skills/routines](https://docs.x.ai/grok-bot/skills-routines-and-automations). Personal bot durable instructions may be chat/memory/skills; do not depend on the old description editor. Bot-to-bot groups and routines are supported concepts, but their actual tool schema must be discovered in the running account. No public provisioning REST contract is assumed. Other harnesses must prove equivalent behavior; no complete installer is claimed for them.
