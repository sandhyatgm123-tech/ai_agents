# QUICKSTART - Run in 30 Seconds

## Simplest Way (No Installation!)

```bash
# Just run the demo - it has ZERO dependencies!
python3 demo.py
```

That's it! The demo uses only Python standard library.

---

## With Tests

```bash
# Run tests - also zero dependencies
python3 tests/test_core.py
```

---

## Web UI (Ask & Get Recommendations)

```bash
# Install (use the same command you use for Python: pip, pip3, or python3 -m pip)
python3 -m pip install streamlit

# Run the UI (this avoids "command not found: streamlit")
python3 -m streamlit run app.py
# Or from the project folder:
python3 run_ui.py
```

- **Demo mode**: Uses mock data; no API key needed.
- **Live mode**: Set `ANTHROPIC_API_KEY` for real weather + full agent.

---

## Real flight data (free, optional)

Flight search can use **Amadeus for Developers** (free tier) instead of mock data:

1. Register: [developers.amadeus.com/register](https://developers.amadeus.com/register)
2. Create an app and copy **Client ID** and **Client Secret**
3. Set environment variables:
   ```bash
   export AMADEUS_CLIENT_ID="your-client-id"
   export AMADEUS_CLIENT_SECRET="your-client-secret"
   ```
4. Install the SDK: `python3 -m pip install amadeus`

When both env vars are set, the app uses real flight offers from Amadeus; otherwise it falls back to mock data.

---

## With Claude API (Optional)

Only needed if you want the agent to use Claude for reasoning:

```bash
# 1. Install only what's needed
pip install anthropic

# 2. Set your API key
export ANTHROPIC_API_KEY="sk-ant-your-key-here"

# 3. Run the agent
python agent/coordinator.py
```

---

## What Each File Does

- **`app.py`** - Web UI: ask a question, get recommendation (needs `streamlit`)
- **`demo.py`** - Full demo with mock data (NO dependencies needed)
- **`tests/test_core.py`** - Unit tests (NO dependencies needed)
- **`agent/coordinator.py`** - Uses Claude API (needs `anthropic` package)
- **`tools/mcp_server.py`** - MCP server (optional, for production)

---

## Installation Options

### Option 1: No Installation (Recommended for Demo)
```bash
python3 demo.py
```

### Option 2: Minimal (Just for Claude API)
```bash
pip install -r requirements-minimal.txt
```

### Option 3: Full (Including MCP server)
```bash
pip install -r requirements.txt
# Then uncomment the MCP lines in requirements.txt
```

---

## Troubleshooting

**"ImportError: cannot import name 'FastMCP'"**
- You don't need FastMCP to run the demo!
- Just run: `python3 demo.py`
- FastMCP is only for production MCP server deployment

**Want to run the full agent with Claude?**
```bash
pip install anthropic
export ANTHROPIC_API_KEY="your-key"
python agent/coordinator.py
```

---

**Start here**: `python3 demo.py` 🚀
