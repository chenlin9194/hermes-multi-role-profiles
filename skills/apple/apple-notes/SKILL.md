     1|---
     2|name: apple-notes
     3|description: Manage Apple Notes via the memo CLI on macOS (create, view, search, edit).
     4|version: 1.0.0
     5|author: Hermes Agent
     6|license: MIT
     7|platforms: [macos]
     8|metadata:
     9|  hermes:
    10|    tags: [Notes, Apple, macOS, note-taking]
    11|    related_skills: [obsidian]
    12|prerequisites:
    13|  commands: [memo]
    14|---
    15|
    16|# Apple Notes
    17|
    18|Use `memo` to manage Apple Notes directly from the terminal. Notes sync across all Apple devices via iCloud.
    19|
    20|## Prerequisites
    21|
    22|- **macOS** with Notes.app
    23|- Install: `brew tap antoniorodr/memo && brew install antoniorodr/memo/memo`
    24|- Grant Automation access to Notes.app when prompted (System Settings → Privacy → Automation)
    25|
    26|## When to Use
    27|
    28|- User asks to create, view, or search Apple Notes
    29|- Saving information to Notes.app for cross-device access
    30|- Organizing notes into folders
    31|- Exporting notes to Markdown/HTML
    32|
    33|## When NOT to Use
    34|
    35|- Obsidian vault management → use the `obsidian` skill
    36|- Bear Notes → separate app (not supported here)
    37|- Quick agent-only notes → use the `memory` tool instead
    38|
    39|## Quick Reference
    40|
    41|### View Notes
    42|
    43|```bash
    44|memo notes                        # List all notes
    45|memo notes -f "Folder Name"       # Filter by folder
    46|memo notes -s "query"             # Search notes (fuzzy)
    47|```
    48|
    49|### Create Notes
    50|
    51|```bash
    52|memo notes -a                     # Interactive editor
    53|memo notes -a "Note Title"        # Quick add with title
    54|```
    55|
    56|### Edit Notes
    57|
    58|```bash
    59|memo notes -e                     # Interactive selection to edit
    60|```
    61|
    62|### Delete Notes
    63|
    64|```bash
    65|memo notes -d                     # Interactive selection to delete
    66|```
    67|
    68|### Move Notes
    69|
    70|```bash
    71|memo notes -m                     # Move note to folder (interactive)
    72|```
    73|
    74|### Export Notes
    75|
    76|```bash
    77|memo notes -ex                    # Export to HTML/Markdown
    78|```
    79|
    80|## Limitations
    81|
    82|- Cannot edit notes containing images or attachments
    83|- Interactive prompts require terminal access (use pty=true if needed)
    84|- macOS only — requires Apple Notes.app
    85|
    86|## Rules
    87|
    88|1. Prefer Apple Notes when user wants cross-device sync (iPhone/iPad/Mac)
    89|2. Use the `memory` tool for agent-internal notes that don't need to sync
    90|3. Use the `obsidian` skill for Markdown-native knowledge management
    91|