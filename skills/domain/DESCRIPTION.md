     1|---
     2|name: domain-intel
     3|description: Passive domain reconnaissance using Python stdlib. Use this skill for subdomain discovery, SSL certificate inspection, WHOIS lookups, DNS records, domain availability checks, and bulk multi-domain analysis. No API keys required. Triggers on requests like "find subdomains", "check ssl cert", "whois lookup", "is this domain available", "bulk check these domains".
     4|license: MIT
     5|---
     6|
     7|Passive domain intelligence using only Python stdlib and public data sources.
     8|Zero dependencies. Zero API keys. Works out of the box.
     9|
    10|## Capabilities
    11|
    12|- Subdomain discovery via crt.sh certificate transparency logs
    13|- Live SSL/TLS certificate inspection (expiry, cipher, SANs, TLS version)
    14|- WHOIS lookup — supports 100+ TLDs via direct TCP queries
    15|- DNS records: A, AAAA, MX, NS, TXT, CNAME
    16|- Domain availability check (DNS + WHOIS + SSL signals)
    17|- Bulk multi-domain analysis in parallel (up to 20 domains)
    18|
    19|## Data Sources
    20|
    21|- crt.sh — Certificate Transparency logs
    22|- WHOIS servers — Direct TCP to 100+ authoritative TLD servers  
    23|- Google DNS-over-HTTPS — MX/NS/TXT/CNAME resolution
    24|- System DNS — A/AAAA records
    25|