# Maui Travel Advisor - Setup & Usage Guide

## Project Overview

This is a multi-agent travel recommendation system that demonstrates strict separation of concerns between business logic, tool layer, and orchestration layer.

### Architecture Verification

The core architectural rule is: **Core logic must not import Google ADK, MCP, or any orchestration framework.**

To verify:

```bash
# This should work WITHOUT internet access:
python3 -c "from core.models import UserProfile; print(UserProfile.example())"
```

If this fails or requires network access, the architecture is violated.

## Installation

### 1. Set up Python environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Set up Anthropic API key

```bash
# Get API key from https://console.anthropic.com/
export ANTHROPIC_API_KEY="your-api-key-here"
```

### 3. Verify core logic (no internet required)

```bash
# Test that core can be imported without network
python tests/test_core.py
```

This should output:
```
✓ UserProfile creation works
✓ Weather scoring works
✓ Flight scoring works
✓ Hotel scoring works
✓ Weather ideal periods works
✓ Flight budget checking works
ALL TESTS PASSED ✓
```

## Running the System

### Option 1: Full Agent Flow

Run the complete Google ADK coordinator:

```bash
python agent/coordinator.py
```

This executes all 6 stages:
1. **Epistemic Reflection** - Recognizes missing information
2. **User Profile Retrieval** - Gets user preferences
3. **Weather Analysis** - Checks 30-day forecast
4. **Flight Search** - Finds flight options
5. **Hotel Evaluation** - Matches lodging to preferences
6. **Synthesis** - Generates final recommendation

### Option 2: MCP Server Only

Start just the MCP server for testing tools:

```bash
python tools/mcp_server.py
```

Then use MCP Inspector to test:

```bash
npx @modelcontextprotocol/inspector
```

### Option 3: Test Core Logic Only

```bash
# Import and use core logic directly
python3 << EOF
from core.models import UserProfile
from core.scoring import score_weather_compatibility

profile = UserProfile.example()
print(f"Profile: {profile.preferred_temp_min}-{profile.preferred_temp_max}°F")
EOF
```

## System Flow Example

```
User: "Is it a good time to go to Maui?"

┌─────────────────────────────────────────┐
│ Stage 1: Epistemic Reflection           │
├─────────────────────────────────────────┤
│ Agent recognizes missing:               │
│ • Weather preferences                    │
│ • Budget constraints                     │
│ • Trip duration                          │
│ • Flexibility                            │
└─────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────┐
│ Stage 2: User Profile Retrieval         │
├─────────────────────────────────────────┤
│ Tool: get_user_profile("default")       │
│ Returns structured preferences          │
└─────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────┐
│ Stage 3: Weather Analysis               │
├─────────────────────────────────────────┤
│ Tool: get_weather_forecast(30 days)     │
│ Flags storm periods                      │
│ Evaluates vs user temp preferences       │
└─────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────┐
│ Stage 4: Flight Search                  │
├─────────────────────────────────────────┤
│ Tool: search_flights(date_range)        │
│ Compares multiple options                │
│ Filters by budget & schedule prefs       │
└─────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────┐
│ Stage 5: Hotel Evaluation               │
├─────────────────────────────────────────┤
│ Tool: search_hotels(dates)               │
│ Matches loyalty programs                 │
│ Checks for storm discounts               │
└─────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────┐
│ Stage 6: Synthesis                       │
├─────────────────────────────────────────┤
│ Core: synthesize_recommendation()       │
│ • Scores all windows                     │
│ • Ranks options                          │
│ • Generates reasoning                    │
│ • Explains rejections                    │
└─────────────────────────────────────────┘
                ↓
        FINAL RECOMMENDATION
```

## MCP Tools Available

### 1. `get_user_profile`
```json
{
  "user_id": "default"
}
```
Returns structured user preferences.

### 2. `get_weather_forecast`
```json
{
  "destination": "Maui, Hawaii",
  "days_ahead": 30
}
```
Returns 30-day forecast with storm alerts.

### 3. `search_flights`
```json
{
  "origin": "SFO",
  "destination": "OGG",
  "departure_start": "2026-02-20",
  "departure_end": "2026-03-15",
  "trip_duration_days": 7
}
```
Returns multiple flight options with pricing and schedules.

### 4. `search_hotels`
```json
{
  "destination": "Maui, Hawaii",
  "check_in": "2026-02-25",
  "check_out": "2026-03-04",
  "budget_min": 150,
  "budget_max": 400
}
```
Returns hotel options with loyalty program info.

## Core Business Logic

The `core/` package contains pure Python with zero external dependencies:

### Models (`core/models.py`)
- `UserProfile` - User preferences and constraints
- `WeatherForecast` - Weather data with analysis methods
- `FlightOption` - Flight details and budget checking
- `HotelOption` - Hotel details and matching logic
- `TravelWindow` - Scored travel period
- `TravelRecommendation` - Final output

### Scoring (`core/scoring.py`)
- `score_weather_compatibility()` - Weather vs preferences
- `score_flight_option()` - Flight quality scoring
- `score_hotel_option()` - Hotel quality scoring
- `rank_travel_windows()` - Overall ranking

### Synthesis (`core/synthesis.py`)
- `generate_candidate_windows()` - Create travel windows
- `create_travel_windows()` - Score all candidates
- `synthesize_recommendation()` - Final synthesis

## Testing

### Unit Tests (No Internet)
```bash
python tests/test_core.py
```

### Integration Tests (Requires API Key)
```bash
python agent/coordinator.py
```

### Architecture Verification
```bash
# Must work without network:
python3 << EOF
import sys
sys.path.insert(0, '.')
from core.models import UserProfile
from core.scoring import score_weather_compatibility
from core.synthesis import synthesize_recommendation
print("✓ Core imports work without internet")
EOF
```

## Key Design Principles

1. **Separation of Concerns**
   - `core/` = Pure Python business logic
   - `tools/` = FastMCP wrappers
   - `agent/` = Google ADK orchestration

2. **Core Independence**
   - Core logic has ZERO dependencies
   - Can be imported in Python REPL
   - Works offline

3. **Epistemic Reflection**
   - Agent must recognize underspecification
   - Profile retrieval before external data
   - Explicit reasoning about missing info

4. **Multi-Stage Processing**
   - Each stage builds on previous
   - Tool outputs feed synthesis
   - Clear decision points

5. **Nuanced Recommendations**
   - Not just one answer
   - Alternatives provided
   - Rejection reasons explained
   - Trade-offs made explicit

## Common Issues

### "ModuleNotFoundError: No module named 'mcp'"

Install FastMCP:
```bash
pip install fastmcp mcp
```

### "ModuleNotFoundError: No module named 'anthropic'"

Install Anthropic SDK:
```bash
pip install anthropic
```

### "Core logic imports fail"

This is a critical error - the architecture is violated. Core should have no external dependencies.

Check:
```bash
grep -r "import anthropic" core/
grep -r "import mcp" core/
grep -r "from fastmcp" core/
```

These should return nothing.

## Production Considerations

### Mock Data vs Real APIs

Current implementation uses mock data for demonstration. In production:

1. **Weather**: Replace with real weather API (OpenWeatherMap, WeatherAPI, etc.)
2. **Flights**: Integrate flight search APIs (Amadeus, Skyscanner, etc.)
3. **Hotels**: Connect to hotel APIs (Booking.com, Expedia, etc.)
4. **User Profile**: Connect to database or user management system

### MCP Server Deployment

For production MCP server:

```python
# Use streamable HTTP instead of stdio
from mcp import FastMCP

mcp = FastMCP("maui-travel-advisor", transport="http")

if __name__ == "__main__":
    mcp.run(host="0.0.0.0", port=8000)
```

### Caching and Performance

Add caching for:
- Weather forecasts (cache for 6 hours)
- Flight searches (cache for 1 hour)
- Hotel availability (cache for 30 minutes)

### Error Handling

Production should add:
- Retry logic for API failures
- Fallback data sources
- Graceful degradation
- User-friendly error messages

## Further Development

### Additional Tools

Consider adding:
- `get_activities` - Local activities and tours
- `get_car_rentals` - Vehicle options
- `get_restaurant_recommendations` - Dining options
- `check_special_events` - Festivals, concerts, etc.

### Enhanced Reasoning

- Multi-day itinerary planning
- Group travel coordination
- Budget optimization algorithms
- Real-time price alerts

### User Interface

- Web interface for recommendations
- Mobile app integration
- Email/SMS notifications
- Interactive date picker

## License

See LICENSE.txt for terms.
