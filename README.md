# Maui Travel Advisor

A multi-agent system that provides personalized travel recommendations for Maui trips using Anthropic Claude and FastMCP.

## Architecture

This system follows strict separation of concerns:

```
maui-travel-advisor/
├── core/           # Pure Python business logic (no framework dependencies)
├── tools/          # FastMCP tool wrappers
├── agent/          # Anthropic Claude orchestration layer
└── tests/          # Unit and integration tests
```

### Design Principle

**Core logic MUST NOT import Anthropic SDK, MCP, or any orchestration framework.**

The `core/` module contains pure Python that can be imported in a REPL without internet access.

## System Flow

1. **Epistemic Reflection**: Agent recognizes question is underspecified
2. **User Profile Retrieval**: Fetch structured user preferences
3. **Weather Analysis**: Check 30-day forecast against preferences
4. **Flight Search**: Find and rank flight options
5. **Hotel Evaluation**: Match lodging to budget and preferences
6. **Synthesis**: Generate personalized recommendation

## Installation

```bash
# Install dependencies
pip install anthropic fastmcp

# For development
pip install pytest black mypy
```

## Running the Agent

```bash
# Set your Anthropic API key
export ANTHROPIC_API_KEY="your-api-key-here"

# Start the MCP server
python tools/mcp_server.py

# In another terminal, run the agent
python agent/coordinator.py
```

## Testing

```bash
# Test core logic (no internet required)
python -c "from core.models import UserProfile; print(UserProfile.example())"

# Run unit tests
pytest tests/

# Test with MCP Inspector
npx @modelcontextprotocol/inspector
```

## Key Components

### Core (`core/`)
- `models.py`: Data models (UserProfile, WeatherForecast, Flight, Hotel)
- `scoring.py`: Recommendation heuristics and scoring logic
- `synthesis.py`: Final recommendation generation

### Tools (`tools/`)
- `mcp_server.py`: FastMCP server exposing all tools
- `profile_tool.py`: User profile retrieval
- `weather_tool.py`: Weather forecast analysis
- `flight_tool.py`: Flight search and comparison
- `hotel_tool.py`: Hotel evaluation

### Agent (`agent/`)
- `coordinator.py`: Anthropic Claude agent with reasoning loop
- `prompts.py`: System prompts and templates
