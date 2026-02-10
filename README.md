# Phantom Trace

Advanced OSINT people search engine with multi-agent orchestration. Uses both local (Ollama) and cloud AI models for intelligent analysis, chain-of-thought reasoning, and automated investigation planning.

## Features

### Core OSINT
- **42+ platform scanning** with async engine (80 concurrent requests)
- **Multi-vector search**: username, email, phone, real name
- **Alias generation**: leet speak, separators, name patterns, affixes
- **Metadata extraction**: bio, location, followers, join dates
- **Cross-platform correlation**: social graph building
- **Breach checking**: Have I Been Pwned integration
- **Confidence scoring**: Evidence-based reliability assessment

### AI Intelligence
- **Local-first model routing**: Ollama → Groq → OpenAI → Anthropic
- **Profile analysis**: AI-powered identity assessment
- **Chain-of-thought reasoning**: Multi-hypothesis evaluation
- **Investigation planning**: Automated next-step generation
- **Alias correlation**: AI determines if profiles match

### Agent Orchestration
- **Pipeline modes**: quick, standard, deep, stealth
- **Specialized agents**: ReconAgent, EnrichmentAgent, AnalysisAgent, ReasoningAgent, DeepReconAgent, ReportAgent
- **Conditional execution**: Stages run based on findings
- **Parallel execution**: Independent agents run concurrently
- **Fault tolerance**: Pipeline continues if non-critical agents fail

## Quick Start

```bash
pip install -r requirements.txt

# Quick scan (no AI)
python phantom.py username johndoe --mode quick

# Standard with AI analysis
python phantom.py username johndoe --mode standard

# Deep investigation (aliases + reasoning)
python phantom.py username johndoe --mode deep

# Stealth mode (slow + local AI only)
python phantom.py username johndoe --mode stealth

# Search by email
python phantom.py email johndoe@gmail.com

# Search by name
python phantom.py name John Doe --birth-year 1995

# Check AI providers
python phantom.py providers
```

## Pipeline Modes

| Mode | Agents | AI | Speed | Depth |
|------|--------|----|----- -|-------|
| quick | Recon → Enrich → Report | No | Fast | Surface |
| standard | Recon → Enrich → Analysis → Report | Yes | Medium | Moderate |
| deep | Recon → Enrich → DeepRecon → Reasoning → Analysis → Report | Yes (CoT) | Slow | Maximum |
| stealth | Recon(slow) → Enrich → Reasoning(local) → Report(JSON) | Local only | Slowest | Moderate |

## Architecture

```
phantom-trace/
├── phantom.py                         # CLI entry point
├── src/
│   ├── models.py                      # Data models
│   ├── config.py                      # YAML configuration
│   ├── engines/
│   │   ├── scanner.py                 # Sync scanner (legacy)
│   │   └── async_scanner.py           # Async engine + rate limiting
│   ├── modules/
│   │   ├── alias_generator.py         # Username permutation engine
│   │   ├── email_recon.py             # Email OSINT
│   │   ├── phone_recon.py             # Phone number intelligence
│   │   ├── breach_check.py            # HIBP integration
│   │   ├── social_graph.py            # Cross-platform graph
│   │   └── metadata_extractor.py      # Profile correlation
│   ├── ai/
│   │   ├── base.py                    # Provider abstractions
│   │   ├── ollama_provider.py         # Local Ollama models
│   │   ├── api_provider.py            # OpenAI / Anthropic / Groq
│   │   ├── router.py                  # Intelligent model routing
│   │   └── analyzer.py               # AI profile analysis
│   ├── agents/
│   │   ├── base.py                    # Agent framework + task system
│   │   ├── orchestrator.py            # Pipeline orchestration engine
│   │   ├── pipelines.py              # Pre-built pipeline configs
│   │   ├── recon_agent.py            # Platform scanning agent
│   │   ├── enrichment_agent.py       # Metadata enrichment agent
│   │   ├── analysis_agent.py         # AI analysis agent
│   │   ├── reasoning_agent.py        # Chain-of-thought reasoning
│   │   ├── deep_recon_agent.py       # Alias follow-up agent
│   │   └── report_agent.py           # Report compilation agent
│   └── exporters/
│       ├── json_export.py            # JSON reports
│       └── html_export.py            # Interactive HTML dashboard
├── data/sites.json                    # 42+ platform configurations
├── config/settings.yaml               # Runtime configuration
├── tests/                             # Test suite
├── .env.example                       # API key template
└── requirements.txt
```

## AI Provider Priority

| # | Provider | Model | Cost | Privacy | Use Case |
|---|----------|-------|------|---------|----------|
| 1 | Ollama | llama3.2 | Free | Full | Default for all analysis |
| 2 | Groq | llama-3.1-70b | $0 (free tier) | Moderate | Fast fallback |
| 3 | OpenAI | gpt-4o-mini | ~$0.15/1M | Low | Complex reasoning |
| 4 | Anthropic | claude-sonnet | ~$3/1M | Low | Deep analysis |

## Disclaimer

**For authorized security research, penetration testing, and OSINT investigations only.**
Do not use to stalk, harass, or invade anyone's privacy.
Comply with all applicable laws and platform terms of service.

## License

MIT
