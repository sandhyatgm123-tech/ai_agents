# Running the Maui Weather MCP Server

This guide shows you how to run the standalone MCP weather server that connects to real weather APIs.

## What This Server Does

The **Maui Weather MCP Server** provides:
- ✅ Real-time 7-14 day weather forecasts for Maui
- ✅ Storm risk detection (heavy rain >0.5" or wind gusts >35mph)
- ✅ Temperature, precipitation, and wind data
- ✅ Automatic storm period identification
- ✅ No API key required (uses free Open-Meteo API)

## Option 1: Use with Claude Desktop

### Step 1: Install MCP SDK

```bash
pip install mcp
```

### Step 2: Configure Claude Desktop

Edit your Claude Desktop config file:

**Mac**: `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

Add this configuration:

```json
{
  "mcpServers": {
    "maui-weather": {
      "command": "python3",
      "args": [
        "/full/path/to/maui-travel-advisor/tools/weather_mcp_server.py"
      ]
    }
  }
}
```

**Replace `/full/path/to/` with your actual path!**

### Step 3: Restart Claude Desktop

Close and reopen Claude Desktop. You should see the MCP server connected.

### Step 4: Use the Tools

In Claude Desktop, you can now ask:

- "What's the weather forecast for Maui for the next 7 days?"
- "Are there any storms expected in Maui?"
- "Get me the extended 14-day Maui weather forecast"
- "When is the best time to visit Maui this month based on weather?"

Claude will automatically use the `get_maui_weather` or `get_extended_maui_weather` tools!

---

## Option 2: Test Standalone

You can also run and test the server directly:

### Using MCP Inspector

```bash
# Install inspector
npm install -g @modelcontextprotocol/inspector

# Run inspector
npx @modelcontextprotocol/inspector python3 tools/weather_mcp_server.py
```

This opens a web UI where you can test the tools.

### Manual Testing

```bash
# Run the server
python3 tools/weather_mcp_server.py

# It will wait for JSON-RPC input on stdin
# Send this to test (then Ctrl+D):
{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
```

---

## Option 3: Use in Your Own Code

You can also call the weather functions directly in Python:

```python
import sys
sys.path.append('/path/to/maui-travel-advisor')

from tools.weather_mcp_server import get_real_weather_data

# Get 7-day forecast
weather = get_real_weather_data(days=7)

print(f"Storm days: {weather['summary']['storm_days']}")
print(f"Temperature range: {weather['summary']['temp_range']}")

for day in weather['forecast']:
    if day['storm_risk']:
        print(f"⚠️ Storm risk on {day['date']}")
```

---

## Available Tools

### 1. `get_maui_weather`

**Parameters**:
- `days` (optional): Number of forecast days (1-16, default: 7)

**Returns**: 
- 7-day detailed forecast
- Storm period warnings
- Temperature, precipitation, wind data
- Daily conditions (sunny/cloudy/rainy/stormy)

**Use for**: Standard trip planning

### 2. `get_extended_maui_weather`

**Parameters**: None (always returns 14 days)

**Returns**:
- 14-day forecast overview
- Storm periods to avoid
- Condensed daily summaries

**Use for**: Finding the best 7-10 day window in a 2-week period

---

## How Storm Detection Works

A day is flagged as **storm risk** if:
- Precipitation > 0.5 inches, OR
- Wind gusts > 35 mph

This helps identify days that could be dangerous for:
- Beach activities
- Hiking
- Outdoor excursions
- Flight delays

---

## Data Source

**Open-Meteo API** (https://open-meteo.com/)
- ✅ Free, no API key required
- ✅ Reliable weather data
- ✅ Updated multiple times per day
- ✅ Professional-grade forecasts

If the API is unavailable, the server automatically falls back to mock data (clearly labeled).

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'mcp'"

```bash
pip install mcp
```

### "Server not showing in Claude Desktop"

1. Check the config file path is correct
2. Make sure the Python path in config points to the actual file
3. Restart Claude Desktop completely
4. Check Claude Desktop logs for errors

### "No internet connection"

The server will fall back to mock data if it can't reach the weather API.

---

## Example Queries for Claude Desktop

Once configured, try these in Claude:

1. **Basic forecast**: "What's the weather like in Maui for the next week?"

2. **Storm planning**: "Are there any storms expected in Maui in the next 2 weeks?"

3. **Trip planning**: "I want to visit Maui for 7 days. When's the best time in the next 2 weeks based on weather?"

4. **Detailed analysis**: "Give me a detailed breakdown of Maui weather including storm risks and temperatures"

---

## Architecture

```
Claude Desktop
      ↓
  (MCP Protocol - JSON-RPC over stdio)
      ↓
weather_mcp_server.py
      ↓
  (HTTP request)
      ↓
Open-Meteo Weather API
      ↓
  (JSON response with forecast data)
      ↓
Storm Risk Analysis
      ↓
  (Formatted response back to Claude)
```

---

## Next Steps

Want to add more tools? You can extend this server with:

- **Flight search** - Connect to flight APIs
- **Hotel search** - Connect to booking APIs
- **Activities** - Beach conditions, surf reports
- **Historical data** - Past weather patterns

All following the same MCP pattern!
