     1|---
     2|name: findmy
     3|description: Track Apple devices and AirTags via FindMy.app on macOS using AppleScript and screen capture.
     4|version: 1.0.0
     5|author: Hermes Agent
     6|license: MIT
     7|platforms: [macos]
     8|metadata:
     9|  hermes:
    10|    tags: [FindMy, AirTag, location, tracking, macOS, Apple]
    11|---
    12|
    13|# Find My (Apple)
    14|
    15|Track Apple devices and AirTags via the FindMy.app on macOS. Since Apple doesn't
    16|provide a CLI for FindMy, this skill uses AppleScript to open the app and
    17|screen capture to read device locations.
    18|
    19|## Prerequisites
    20|
    21|- **macOS** with Find My app and iCloud signed in
    22|- Devices/AirTags already registered in Find My
    23|- Screen Recording permission for terminal (System Settings → Privacy → Screen Recording)
    24|- **Optional but recommended**: Install `peekaboo` for better UI automation:
    25|  `brew install steipete/tap/peekaboo`
    26|
    27|## When to Use
    28|
    29|- User asks "where is my [device/cat/keys/bag]?"
    30|- Tracking AirTag locations
    31|- Checking device locations (iPhone, iPad, Mac, AirPods)
    32|- Monitoring pet or item movement over time (AirTag patrol routes)
    33|
    34|## Method 1: AppleScript + Screenshot (Basic)
    35|
    36|### Open FindMy and Navigate
    37|
    38|```bash
    39|# Open Find My app
    40|osascript -e 'tell application "FindMy" to activate'
    41|
    42|# Wait for it to load
    43|sleep 3
    44|
    45|# Take a screenshot of the Find My window
    46|screencapture -w -o /tmp/findmy.png
    47|```
    48|
    49|Then use `vision_analyze` to read the screenshot:
    50|```
    51|vision_analyze(image_url="/tmp/findmy.png", question="What devices/items are shown and what are their locations?")
    52|```
    53|
    54|### Switch Between Tabs
    55|
    56|```bash
    57|# Switch to Devices tab
    58|osascript -e '
    59|tell application "System Events"
    60|    tell process "FindMy"
    61|        click button "Devices" of toolbar 1 of window 1
    62|    end tell
    63|end tell'
    64|
    65|# Switch to Items tab (AirTags)
    66|osascript -e '
    67|tell application "System Events"
    68|    tell process "FindMy"
    69|        click button "Items" of toolbar 1 of window 1
    70|    end tell
    71|end tell'
    72|```
    73|
    74|## Method 2: Peekaboo UI Automation (Recommended)
    75|
    76|If `peekaboo` is installed, use it for more reliable UI interaction:
    77|
    78|```bash
    79|# Open Find My
    80|osascript -e 'tell application "FindMy" to activate'
    81|sleep 3
    82|
    83|# Capture and annotate the UI
    84|peekaboo see --app "FindMy" --annotate --path /tmp/findmy-ui.png
    85|
    86|# Click on a specific device/item by element ID
    87|peekaboo click --on B3 --app "FindMy"
    88|
    89|# Capture the detail view
    90|peekaboo image --app "FindMy" --path /tmp/findmy-detail.png
    91|```
    92|
    93|Then analyze with vision:
    94|```
    95|vision_analyze(image_url="/tmp/findmy-detail.png", question="What is the location shown for this device/item? Include address and coordinates if visible.")
    96|```
    97|
    98|## Workflow: Track AirTag Location Over Time
    99|
   100|For monitoring an AirTag (e.g., tracking a cat's patrol route):
   101|
   102|```bash
   103|# 1. Open FindMy to Items tab
   104|osascript -e 'tell application "FindMy" to activate'
   105|sleep 3
   106|
   107|# 2. Click on the AirTag item (stay on page — AirTag only updates when page is open)
   108|
   109|# 3. Periodically capture location
   110|while true; do
   111|    screencapture -w -o /tmp/findmy-$(date +%H%M%S).png
   112|    sleep 300  # Every 5 minutes
   113|done
   114|```
   115|
   116|Analyze each screenshot with vision to extract coordinates, then compile a route.
   117|
   118|## Limitations
   119|
   120|- FindMy has **no CLI or API** — must use UI automation
   121|- AirTags only update location while the FindMy page is actively displayed
   122|- Location accuracy depends on nearby Apple devices in the FindMy network
   123|- Screen Recording permission required for screenshots
   124|- AppleScript UI automation may break across macOS versions
   125|
   126|## Rules
   127|
   128|1. Keep FindMy app in the foreground when tracking AirTags (updates stop when minimized)
   129|2. Use `vision_analyze` to read screenshot content — don't try to parse pixels
   130|3. For ongoing tracking, use a cronjob to periodically capture and log locations
   131|4. Respect privacy — only track devices/items the user owns
   132|