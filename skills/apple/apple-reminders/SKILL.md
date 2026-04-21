     1|---
     2|name: apple-reminders
     3|description: Manage Apple Reminders via remindctl CLI (list, add, complete, delete).
     4|version: 1.0.0
     5|author: Hermes Agent
     6|license: MIT
     7|platforms: [macos]
     8|metadata:
     9|  hermes:
    10|    tags: [Reminders, tasks, todo, macOS, Apple]
    11|prerequisites:
    12|  commands: [remindctl]
    13|---
    14|
    15|# Apple Reminders
    16|
    17|Use `remindctl` to manage Apple Reminders directly from the terminal. Tasks sync across all Apple devices via iCloud.
    18|
    19|## Prerequisites
    20|
    21|- **macOS** with Reminders.app
    22|- Install: `brew install steipete/tap/remindctl`
    23|- Grant Reminders permission when prompted
    24|- Check: `remindctl status` / Request: `remindctl authorize`
    25|
    26|## When to Use
    27|
    28|- User mentions "reminder" or "Reminders app"
    29|- Creating personal to-dos with due dates that sync to iOS
    30|- Managing Apple Reminders lists
    31|- User wants tasks to appear on their iPhone/iPad
    32|
    33|## When NOT to Use
    34|
    35|- Scheduling agent alerts → use the cronjob tool instead
    36|- Calendar events → use Apple Calendar or Google Calendar
    37|- Project task management → use GitHub Issues, Notion, etc.
    38|- If user says "remind me" but means an agent alert → clarify first
    39|
    40|## Quick Reference
    41|
    42|### View Reminders
    43|
    44|```bash
    45|remindctl                    # Today's reminders
    46|remindctl today              # Today
    47|remindctl tomorrow           # Tomorrow
    48|remindctl week               # This week
    49|remindctl overdue            # Past due
    50|remindctl all                # Everything
    51|remindctl 2026-01-04         # Specific date
    52|```
    53|
    54|### Manage Lists
    55|
    56|```bash
    57|remindctl list               # List all lists
    58|remindctl list Work          # Show specific list
    59|remindctl list Projects --create    # Create list
    60|remindctl list Work --delete        # Delete list
    61|```
    62|
    63|### Create Reminders
    64|
    65|```bash
    66|remindctl add "Buy milk"
    67|remindctl add --title "Call mom" --list Personal --due tomorrow
    68|remindctl add --title "Meeting prep" --due "2026-02-15 09:00"
    69|```
    70|
    71|### Complete / Delete
    72|
    73|```bash
    74|remindctl complete 1 2 3          # Complete by ID
    75|remindctl delete 4A83 --force     # Delete by ID
    76|```
    77|
    78|### Output Formats
    79|
    80|```bash
    81|remindctl today --json       # JSON for scripting
    82|remindctl today --plain      # TSV format
    83|remindctl today --quiet      # Counts only
    84|```
    85|
    86|## Date Formats
    87|
    88|Accepted by `--due` and date filters:
    89|- `today`, `tomorrow`, `yesterday`
    90|- `YYYY-MM-DD`
    91|- `YYYY-MM-DD HH:mm`
    92|- ISO 8601 (`2026-01-04T12:34:56Z`)
    93|
    94|## Rules
    95|
    96|1. When user says "remind me", clarify: Apple Reminders (syncs to phone) vs agent cronjob alert
    97|2. Always confirm reminder content and due date before creating
    98|3. Use `--json` for programmatic parsing
    99|