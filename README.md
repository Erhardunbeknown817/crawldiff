<p align="center">
  <h1 align="center">crawldiff</h1>
  <p align="center">
    <strong><code>git log</code> for any website.</strong>
  </p>
  <p align="center">
    Track what changed on any website. Get git-style diffs with AI-powered summaries.<br/>
    Powered by Cloudflare's <a href="https://developers.cloudflare.com/browser-rendering/rest-api/crawl-endpoint/">/crawl</a> endpoint.
  </p>
  <p align="center">
    <a href="https://github.com/GeoRouv/crawldiff/actions/workflows/ci.yml"><img src="https://github.com/GeoRouv/crawldiff/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
    <a href="https://pypi.org/project/crawldiff/"><img src="https://img.shields.io/pypi/v/crawldiff?color=blue" alt="PyPI"></a>
    <a href="https://github.com/GeoRouv/crawldiff/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="License"></a>
    <a href="https://python.org"><img src="https://img.shields.io/badge/python-3.12+-blue" alt="Python"></a>
  </p>
</p>

---

<p align="center">
  <img src="assets/demo.svg" alt="crawldiff demo" width="750">
</p>

```bash
pip install crawldiff
```

```bash
# Snapshot a site
crawldiff crawl https://stripe.com/pricing

# Come back later. See what changed.
crawldiff diff https://stripe.com/pricing --since 7d
```

## Why

Every website monitoring tool is a SaaS dashboard built for marketing teams.

**crawldiff** is for developers. It's a CLI. It diffs like git. It summarizes with AI. It stores everything locally. And it's powered by Cloudflare's brand new [`/crawl` endpoint](https://blog.cloudflare.com/crawl-entire-websites-with-a-single-api-call-using-browser-rendering/) — the same infrastructure that powers the internet.

No accounts. No subscriptions. No GUI. Just `crawldiff diff`.

## Setup (30 seconds)

You need a free [Cloudflare account](https://dash.cloudflare.com/sign-up). That's it.

```bash
# Install
pip install crawldiff

# Set your Cloudflare credentials (free tier: 5 jobs/day, 100 pages/job)
export CLOUDFLARE_ACCOUNT_ID="your-account-id"
export CLOUDFLARE_API_TOKEN="your-api-token"

# Or save to config
crawldiff config set cloudflare.account_id your-id
crawldiff config set cloudflare.api_token your-token
```

## Usage

### Track changes on any website

```bash
# Take a snapshot
crawldiff crawl https://competitor.com

# Later, see what changed
crawldiff diff https://competitor.com --since 7d

# Output as JSON (pipe to jq, Slack, wherever)
crawldiff diff https://competitor.com --since 7d --format json

# Save a markdown report
crawldiff diff https://competitor.com --since 30d --output report.md
```

### Watch a site continuously

```bash
# Check every hour, get notified when something changes
crawldiff watch https://stripe.com/pricing --every 1h

# Check every 6 hours, skip AI summary
crawldiff watch https://competitor.com --every 6h --no-summary
```

### View history

```bash
crawldiff history https://stripe.com/pricing
```

```
       Crawl History — https://stripe.com/pricing
┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Job ID         ┃ Date                ┃ Pages ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ cf-job-abc-123 │ 2026-03-13 09:00:00 │    12 │
│ cf-job-def-456 │ 2026-03-06 09:00:00 │    11 │
│ cf-job-ghi-789 │ 2026-02-27 09:00:00 │    11 │
└────────────────┴─────────────────────┴───────┘
```

### Crawl options

```bash
# Deeper crawl
crawldiff crawl https://docs.react.dev --depth 3 --max-pages 100

# Static sites (faster, no browser rendering)
crawldiff crawl https://blog.example.com --no-render

# Ignore whitespace noise
crawldiff diff https://example.com --since 7d --ignore-whitespace
```

## AI Summaries (optional)

Raw diffs are useful. AI summaries make them *actionable*. crawldiff supports three providers:

```bash
# Cloudflare Workers AI (free, uses your existing CF account)
crawldiff config set ai.provider cloudflare

# Anthropic Claude
pip install crawldiff[ai]
crawldiff config set ai.provider anthropic
export ANTHROPIC_API_KEY="sk-..."

# OpenAI
pip install crawldiff[ai]
crawldiff config set ai.provider openai
export OPENAI_API_KEY="sk-..."
```

Don't want AI? Just use `--no-summary`. Diffs work perfectly without it.

## How it works

```
1. crawldiff crawl <url>
   └─→ Cloudflare /crawl API (headless browser, respects robots.txt)
   └─→ Store Markdown snapshots in local SQLite (~/.crawldiff/)

2. crawldiff diff <url> --since 7d
   └─→ Cloudflare /crawl with modifiedSince (only fetches changed pages)
   └─→ Diff against stored snapshot (unified diff via difflib)
   └─→ AI summary (optional)
   └─→ Beautiful terminal output via rich
```

The key insight: Cloudflare's `modifiedSince` parameter means **incremental crawling is built-in**. On repeat diffs, only changed pages are fetched. Fast and cheap.

## Why Cloudflare /crawl?

| | crawldiff (Cloudflare) | Firecrawl | Crawl4AI |
|---|---|---|---|
| **Free tier** | 5 jobs/day, 100 pages | 500 credits | Self-host |
| **Incremental crawling** | Built-in (`modifiedSince`) | No | No |
| **Browser rendering** | Headless Chrome at the edge | Yes | Yes |
| **Respects robots.txt** | By default | Opt-in | No |
| **Pricing** | $5/mo (Workers Paid) | From $16/mo | Free (self-host) |
| **Infrastructure** | Cloudflare's global network | Their servers | Your servers |

## vs. other monitoring tools

| Feature | crawldiff | Visualping | changedetection.io | Firecrawl |
|---------|-----------|------------|-------------------|-----------|
| Open source | **Yes** | No | Yes | Yes |
| CLI-native | **Yes** | No | No | No |
| AI summaries | **Yes** | No | No | No |
| Incremental crawling | **Yes** | No | No | No |
| Local storage | **Yes** | No | No | No |
| JSON/pipe output | **Yes** | No | Yes | Yes |
| Free | **Yes** | Limited | Yes | Limited |

## All commands

```
crawldiff crawl <url>      Snapshot a website
crawldiff diff <url>       Show what changed (the main command)
crawldiff watch <url>      Monitor continuously
crawldiff history <url>    View past snapshots
crawldiff config set|get|show   Manage settings
```

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for setup and guidelines.

## License

MIT
