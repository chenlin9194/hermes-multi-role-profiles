     1|---
     2|name: imessage
     3|description: Send and receive iMessages/SMS via the imsg CLI on macOS.
     4|version: 1.0.0
     5|author: Hermes Agent
     6|license: MIT
     7|platforms: [macos]
     8|metadata:
     9|  hermes:
    10|    tags: [iMessage, SMS, messaging, macOS, Apple]
    11|prerequisites:
    12|  commands: [imsg]
    13|---
    14|
    15|# iMessage
    16|
    17|Use `imsg` to read and send iMessage/SMS via macOS Messages.app.
    18|
    19|## Prerequisites
    20|
    21|- **macOS** with Messages.app signed in
    22|- Install: `brew install steipete/tap/imsg`
    23|- Grant Full Disk Access for terminal (System Settings → Privacy → Full Disk Access)
    24|- Grant Automation permission for Messages.app when prompted
    25|
    26|## When to Use
    27|
    28|- User asks to send an iMessage or text message
    29|- Reading iMessage conversation history
    30|- Checking recent Messages.app chats
    31|- Sending to phone numbers or Apple IDs
    32|
    33|## When NOT to Use
    34|
    35|- Telegram/Discord/Slack/WhatsApp messages → use the appropriate gateway channel
    36|- Group chat management (adding/removing members) → not supported
    37|- Bulk/mass messaging → always confirm with user first
    38|
    39|## Quick Reference
    40|
    41|### List Chats
    42|
    43|```bash
    44|imsg chats --limit 10 --json
    45|```
    46|
    47|### View History
    48|
    49|```bash
    50|# By chat ID
    51|imsg history --chat-id 1 --limit 20 --json
    52|
    53|# With attachments info
    54|imsg history --chat-id 1 --limit 20 --attachments --json
    55|```
    56|
    57|### Send Messages
    58|
    59|```bash
    60|# Text only
    61|imsg send --to "+141****1212" --text "Hello!"
    62|
    63|# With attachment
    64|imsg send --to "+141****1212" --text "Check this out" --file /path/to/image.jpg
    65|
    66|# Force iMessage or SMS
    67|imsg send --to "+141****1212" --text "Hi" --service imessage
    68|imsg send --to "+141****1212" --text "Hi" --service sms
    69|```
    70|
    71|### Watch for New Messages
    72|
    73|```bash
    74|imsg watch --chat-id 1 --attachments
    75|```
    76|
    77|## Service Options
    78|
    79|- `--service imessage` — Force iMessage (requires recipient has iMessage)
    80|- `--service sms` — Force SMS (green bubble)
    81|- `--service auto` — Let Messages.app decide (default)
    82|
    83|## Rules
    84|
    85|1. **Always confirm recipient and message content** before sending
    86|2. **Never send to unknown numbers** without explicit user approval
    87|3. **Verify file paths** exist before attaching
    88|4. **Don't spam** — rate-limit yourself
    89|
    90|## Example Workflow
    91|
    92|User: "Text mom that I'll be late"
    93|
    94|```bash
    95|# 1. Find mom's chat
    96|imsg chats --limit 20 --json | jq '.[] | select(.displayName | contains("Mom"))'
    97|
    98|# 2. Confirm with user: "Found Mom at +155****3456. Send 'I'll be late' via iMessage?"
    99|
   100|# 3. Send after confirmation
   101|imsg send --to "+155****3456" --text "I'll be late"
   102|```
   103|