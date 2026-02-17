#!/usr/bin/env python3
"""
Standalone MCP Server for Maui Weather Data

This server provides real-time weather data for Maui with storm risk detection.
Uses the MCP (Model Context Protocol) Python SDK.

"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from typing import Any

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# MCP SDK imports
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio

import urllib.request
import json
import requests


# Initialize MCP server
server = Server("maui-weather-server")

def geocode_location(location: str):
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": location,
        "format": "json"
    }

    response = requests.get(
        url,
        params=params,
        headers={"User-Agent": "my-app"}  # required by OSM
    )

    data = response.json()

    if not data:
        return None

    lat = float(data[0]["lat"])
    lon = float(data[0]["lon"])

    return {"lat": lat, "lon": lon}


def get_real_weather_data(location:str, days: int = 7) -> dict:
    """
    Fetch real weather data from Open-Meteo API (free, no API key needed)
    
    Args:
        lat: Latitude (default: Maui)
        lon: Longitude (default: Maui)
        days: Number of forecast days
        
    Returns:
        Weather data with storm risk analysis
    """

    coords = geocode_location(location)
    lat = coords["lat"]
    lon = coords["lon"]

    # Open-Meteo API - free weather API, no key required
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,"
        f"precipitation_probability_max,windspeed_10m_max,windgusts_10m_max"
        f"&temperature_unit=fahrenheit"
        f"&windspeed_unit=mph"
        f"&precipitation_unit=inch"
        f"&timezone=Pacific/Honolulu"
        f"&forecast_days={days}"
    )
    
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())
        
        # Process the data
        daily = data.get("daily", {})
        dates = daily.get("time", [])
        temp_max = daily.get("temperature_2m_max", [])
        temp_min = daily.get("temperature_2m_min", [])
        precip = daily.get("precipitation_sum", [])
        precip_prob = daily.get("precipitation_probability_max", [])
        wind_speed = daily.get("windspeed_10m_max", [])
        wind_gusts = daily.get("windgusts_10m_max", [])
        
        forecast_days = []
        storm_periods = []
        
        for i in range(len(dates)):
            # Detect storm conditions
            is_storm = (
                (precip[i] if i < len(precip) else 0) > 0.5 or  # Heavy rain
                (wind_gusts[i] if i < len(wind_gusts) else 0) > 35  # High winds
            )
            
            if is_storm:
                if precip_prob[i] > 80:
                    conditions = "stormy"
                else:
                    conditions = "rainy"
            elif (precip_prob[i] if i < len(precip_prob) else 0) > 40:
                conditions = "rainy"
            elif (precip_prob[i] if i < len(precip_prob) else 0) > 20:
                conditions = "cloudy"
            else:
                conditions = "sunny"
            
            day_data = {
                "date": dates[i],
                "temp_high": int(temp_max[i]) if i < len(temp_max) else 80,
                "temp_low": int(temp_min[i]) if i < len(temp_min) else 70,
                "precipitation_chance": int(precip_prob[i]) if i < len(precip_prob) else 0,
                "precipitation_amount": round(precip[i], 2) if i < len(precip) else 0,
                "wind_speed": int(wind_speed[i]) if i < len(wind_speed) else 10,
                "wind_gusts": int(wind_gusts[i]) if i < len(wind_gusts) else 15,
                "storm_risk": is_storm,
                "conditions": conditions
            }
            
            forecast_days.append(day_data)
            
            # Track storm periods
            if is_storm:
                if not storm_periods or storm_periods[-1]["end"] != dates[i-1] if i > 0 else True:
                    storm_periods.append({
                        "start": dates[i],
                        "end": dates[i],
                        "warning": f"Storm risk on {dates[i]}"
                    })
                else:
                    storm_periods[-1]["end"] = dates[i]
                    storm_periods[-1]["warning"] = f"Storm period {storm_periods[-1]['start']} to {dates[i]}"
        
        return {
            "location": location,
            "coordinates": {"latitude": lat, "longitude": lon},
            "forecast_start": dates[0] if dates else None,
            "forecast_end": dates[-1] if dates else None,
            "days_ahead": len(dates),
            "forecast": forecast_days,
            "storm_periods": storm_periods,
            "summary": {
                "total_days": len(forecast_days),
                "storm_days": sum(1 for d in forecast_days if d["storm_risk"]),
                "sunny_days": sum(1 for d in forecast_days if d["conditions"] == "sunny"),
                "temp_range": f"{min(d['temp_low'] for d in forecast_days)}-{max(d['temp_high'] for d in forecast_days)}°F" if forecast_days else "N/A",
                "max_wind_gust": max(d['wind_gusts'] for d in forecast_days) if forecast_days else 0
            },
            "data_source": "Open-Meteo API",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        # Fallback to mock data if API fails
        return get_mock_weather_data(days)


def get_mock_weather_data(days: int = 7) -> dict:
    """Fallback mock data if real API fails"""
    today = datetime.now().date()
    forecast_days = []
    
    for i in range(days):
        day_date = today + timedelta(days=i)
        
        # Simulate varied conditions
        is_storm = i % 8 == 0
        
        if is_storm:
            temp_high = 78
            temp_low = 70
            precip = 85
            conditions = "stormy"
            wind_gusts = 40
        elif i % 3 == 0:
            temp_high = 79
            temp_low = 72
            precip = 60
            conditions = "rainy"
            wind_gusts = 20
        else:
            temp_high = 82
            temp_low = 73
            precip = 15
            conditions = "sunny"
            wind_gusts = 15
        
        forecast_days.append({
            "date": day_date.isoformat(),
            "temp_high": temp_high,
            "temp_low": temp_low,
            "precipitation_chance": precip,
            "precipitation_amount": 0.5 if is_storm else 0.1,
            "wind_speed": 15 if is_storm else 10,
            "wind_gusts": wind_gusts,
            "storm_risk": is_storm,
            "conditions": conditions
        })
    
    storm_periods = [
        {
            "start": day["date"],
            "end": day["date"],
            "warning": f"Storm risk on {day['date']}"
        }
        for day in forecast_days if day["storm_risk"]
    ]
    
    return {
        "location": "Maui, Hawaii",
        "coordinates": {"latitude": 20.7984, "longitude": -156.3319},
        "forecast_start": forecast_days[0]["date"],
        "forecast_end": forecast_days[-1]["date"],
        "days_ahead": days,
        "forecast": forecast_days,
        "storm_periods": storm_periods,
        "summary": {
            "total_days": len(forecast_days),
            "storm_days": sum(1 for d in forecast_days if d["storm_risk"]),
            "sunny_days": sum(1 for d in forecast_days if d["conditions"] == "sunny"),
            "temp_range": f"{min(d['temp_low'] for d in forecast_days)}-{max(d['temp_high'] for d in forecast_days)}°F",
            "max_wind_gust": max(d['wind_gusts'] for d in forecast_days)
        },
        "data_source": "Mock Data (API unavailable)",
        "timestamp": datetime.now().isoformat()
    }


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools"""
    return [
        types.Tool(
            name="get_maui_weather",
            description="""Get current weather forecast for Maui, Hawaii with storm risk detection.
            
Returns a 7-day forecast including:
- Daily high/low temperatures (Fahrenheit)
- Precipitation probability and amounts
- Wind speeds and gusts
- Storm risk flags (based on heavy rain >0.5" or wind gusts >35mph)
- Weather conditions (sunny/cloudy/rainy/stormy)

The tool automatically detects storm periods and provides warnings.
Data source: Open-Meteo free weather API (no API key required).

Perfect for travel planning - helps identify safe travel windows and periods to avoid.
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "days": {
                        "type": "number",
                        "description": "Number of forecast days (1-16, default: 7)",
                        "default": 7
                    }
                },
                "required": []
            },
        ),
        types.Tool(
            name="get_extended_maui_weather",
            description="""Get extended 14-day weather forecast for Maui with detailed storm analysis.
            
Same as get_maui_weather but provides 14 days of data for longer-term trip planning.
Useful for identifying the best 7-10 day travel windows within a 2-week period.
""",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool calls"""
    
    if name == "get_maui_weather":
        days = arguments.get("days", 7) if arguments else 7
        days = min(max(int(days), 1), 16)  # Clamp to 1-16 days
        
        weather_data = get_real_weather_data(days=days)
        
        # Format as readable text
        response = f"""# Maui Weather Forecast - {days} Days

**Location**: {weather_data['location']}  
**Forecast Period**: {weather_data['forecast_start']} to {weather_data['forecast_end']}

## Summary
- **Total Days**: {weather_data['summary']['total_days']}
- **Storm Days**: {weather_data['summary']['storm_days']}
- **Sunny Days**: {weather_data['summary']['sunny_days']}
- **Temperature Range**: {weather_data['summary']['temp_range']}
- **Max Wind Gust**: {weather_data['summary']['max_wind_gust']} mph

"""
        
        # Storm warnings
        if weather_data['storm_periods']:
            response += "## ⚠️ STORM WARNINGS\n"
            for period in weather_data['storm_periods']:
                response += f"- **{period['warning']}**\n"
            response += "\n"
        else:
            response += "## ✅ No Storm Warnings\nNo significant storm activity expected during this period.\n\n"
        
        # Daily forecast
        response += "## Daily Forecast\n\n"
        for day in weather_data['forecast']:
            storm_icon = "⚠️ " if day['storm_risk'] else ""
            response += f"""**{day['date']}** {storm_icon}({day['conditions'].title()})
- High: {day['temp_high']}°F, Low: {day['temp_low']}°F
- Precipitation: {day['precipitation_chance']}% chance, {day['precipitation_amount']}" expected
- Wind: {day['wind_speed']} mph, gusts to {day['wind_gusts']} mph
{"- **STORM RISK**: Heavy rain or high winds expected" if day['storm_risk'] else ""}

"""
        
        response += f"\n*Data source: {weather_data['data_source']}*  \n"
        response += f"*Retrieved: {weather_data['timestamp']}*\n"
        
        return [
            types.TextContent(
                type="text",
                text=response
            )
        ]
    
    elif name == "get_extended_maui_weather":
        weather_data = get_real_weather_data(days=14)
        
        # Similar formatting but more concise for 14 days
        response = f"""# Extended Maui Weather Forecast - 14 Days

**Location**: {weather_data['location']}  
**Period**: {weather_data['forecast_start']} to {weather_data['forecast_end']}

## Summary
- Storm Days: {weather_data['summary']['storm_days']}/14
- Sunny Days: {weather_data['summary']['sunny_days']}/14
- Temp Range: {weather_data['summary']['temp_range']}

"""
        
        if weather_data['storm_periods']:
            response += "## Storm Periods to Avoid:\n"
            for period in weather_data['storm_periods']:
                response += f"- {period['start']} to {period['end']}\n"
            response += "\n"
        
        # Condensed daily view
        response += "## Daily Overview\n"
        for day in weather_data['forecast']:
            storm = " ⚠️" if day['storm_risk'] else ""
            response += f"{day['date']}: {day['temp_high']}°F, {day['conditions']}{storm}\n"
        
        return [
            types.TextContent(
                type="text",
                text=response
            )
        ]
    
    raise ValueError(f"Unknown tool: {name}")


async def main():
    """Run the MCP server"""
    # Run the server using stdin/stdout streams
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="maui-weather-server",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
