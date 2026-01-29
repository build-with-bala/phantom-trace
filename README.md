# Phantom Trace

Advanced OSINT people search engine with AI-powered analysis. Goes beyond basic username enumeration with multi-vector intelligence, cross-platform correlation, and intelligent agent orchestration using both local (Ollama) and cloud AI models.

## What Makes It Different

| Feature | Sherlock | Phantom Trace |
|---------|---------|---------------|
| Username search | ✓ | ✓ (42+ sites) |
| Email OSINT | ✗ | ✓ |
| Phone OSINT | ✗ | ✓ |
| Real name search | ✗ | ✓ |
| Alias generation | ✗ | ✓ (leet, affixes, name patterns) |
| Cross-platform correlation | ✗ | ✓ |
| Metadata extraction | ✗ | ✓ (bio, location, followers) |
| Social graph building | ✗ | ✓ |
| Breach checking | ✗ | ✓ (HIBP) |
| AI profile analysis | ✗ | ✓ (local + cloud models) |
| Agent orchestration | ✗ | ✓ (multi-agent pipeline) |
| Confidence scoring | ✗ | ✓ |
| HTML reports | ✗ | ✓ (interactive dashboard) |
| Async engine | ✗ | ✓ (80 concurrent) |
| Rate limiting | ✗ | ✓ (per-domain token bucket) |

## Disclaimer

**For authorized security research and OSINT investigations only.** Do not use to stalk, harass, or invade privacy. Comply with applicable laws.

## Quick Start

```bash
pip install -r requirements.txt

# Basic username search
python phantom.py username johndoe

# With AI analysis (requires Ollama or API key)
python phantom.py username johndoe --ai

# Email search
python phantom.py email johndoe@gmail.com

# Phone search
python phantom.py phone "+1234567890"

# Name search
python phantom.py name John Doe --birth-year 1995
```

## AI Providers

Phantom Trace uses a local-first model routing strategy:

| Priority | Provider | Model | Cost | Privacy |
|----------|----------|-------|------|---------|
| 1 | Ollama (local) | llama3.2 | Free | Full |
| 2 | Groq | llama-3.1-70b | Low | Moderate |
| 3 | OpenAI | gpt-4o-mini | Medium | Low |
| 4 | Anthropic | claude-sonnet | Medium | Low |

```bash
# Install Ollama for free local AI
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull llama3.2

# Or set API keys
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
export GROQ_API_KEY=gsk_...
```

## Architecture

```
phantom-trace/
├── phantom.py                     # CLI entry point
├── src/
│   ├── models.py                  # Data models
│   ├── config.py                  # Configuration
│   ├── engines/
│   │   ├── scanner.py             # Sync scanner (legacy)
│   │   └── async_scanner.py       # Async engine with rate limiting
│   ├── modules/
│   │   ├── alias_generator.py     # Username permutations
│   │   ├── email_recon.py         # Email OSINT
│   │   ├── phone_recon.py         # Phone OSINT
│   │   ├── breach_check.py        # HIBP integration
│   │   ├── social_graph.py        # Graph builder
│   │   └── metadata_extractor.py  # Cross-platform correlation
│   ├── ai/
│   │   ├── base.py                # Provider abstractions
│   │   ├── ollama_provider.py     # Local Ollama models
│   │   ├── api_provider.py        # OpenAI/Anthropic/Groq
│   │   ├── router.py              # Model routing + fallback
│   │   └── analyzer.py            # Profile analysis
│   └── exporters/
│       ├── json_export.py         # JSON reports
│       └── html_export.py         # HTML dashboard
├── data/sites.json                # 42+ platform configs
├── config/settings.yaml           # Runtime config
├── tests/                         # Test suite
└── .env.example                   # Environment template
```
