#!/usr/bin/env python3
"""
Test script for the Maui Weather MCP Server

This tests the weather data fetching without running the full MCP server.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.weather_mcp_server import get_real_weather_data, get_mock_weather_data


def test_weather_api():
    """Test fetching real weather data"""
    print("=" * 80)
    print("TESTING MAUI WEATHER API")
    print("=" * 80)
    
    print("\n📡 Fetching 7-day forecast from Open-Meteo API...")
    
    try:
        weather = get_real_weather_data(days=7)
        
        print(f"✅ Successfully fetched weather data!")
        print(f"\n📍 Location: {weather['location']}")
        print(f"📅 Period: {weather['forecast_start']} to {weather['forecast_end']}")
        print(f"🌡️  Temperature Range: {weather['summary']['temp_range']}")
        print(f"☀️  Sunny Days: {weather['summary']['sunny_days']}")
        print(f"⚠️  Storm Days: {weather['summary']['storm_days']}")
        
        if weather['storm_periods']:
            print(f"\n⚠️  STORM WARNINGS:")
            for period in weather['storm_periods']:
                print(f"   • {period['warning']}")
        else:
            print(f"\n✅ No storm warnings - good weather expected!")
        
        print(f"\n📊 Daily Breakdown:")
        for day in weather['forecast'][:7]:  # Show first 7 days
            storm_flag = " ⚠️ STORM" if day['storm_risk'] else ""
            print(f"   {day['date']}: {day['temp_high']}°F ({day['conditions']}){storm_flag}")
        
        print(f"\n📡 Data source: {weather['data_source']}")
        print(f"🕐 Retrieved at: {weather['timestamp']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error fetching real data: {e}")
        print(f"\n💡 Falling back to mock data...")
        
        weather = get_mock_weather_data(days=7)
        print(f"✅ Mock data generated")
        print(f"📍 Location: {weather['location']}")
        print(f"⚠️  Storm Days: {weather['summary']['storm_days']}")
        
        return False


def test_extended_forecast():
    """Test 14-day extended forecast"""
    print("\n" + "=" * 80)
    print("TESTING EXTENDED 14-DAY FORECAST")
    print("=" * 80)
    
    print("\n📡 Fetching 14-day forecast...")
    
    try:
        weather = get_real_weather_data(days=14)
        
        print(f"✅ Successfully fetched 14-day forecast!")
        print(f"📅 Period: {weather['forecast_start']} to {weather['forecast_end']}")
        print(f"☀️  Sunny Days: {weather['summary']['sunny_days']}/14")
        print(f"⚠️  Storm Days: {weather['summary']['storm_days']}/14")
        
        # Find best 7-day window
        best_window_start = 0
        min_storm_days = float('inf')
        
        for i in range(len(weather['forecast']) - 6):
            window = weather['forecast'][i:i+7]
            storm_count = sum(1 for d in window if d['storm_risk'])
            if storm_count < min_storm_days:
                min_storm_days = storm_count
                best_window_start = i
        
        best_window = weather['forecast'][best_window_start:best_window_start+7]
        
        print(f"\n🎯 BEST 7-DAY WINDOW FOR TRAVEL:")
        print(f"   {best_window[0]['date']} to {best_window[-1]['date']}")
        print(f"   Storm days in window: {min_storm_days}")
        print(f"   Conditions: {', '.join(set(d['conditions'] for d in best_window))}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Run all tests"""
    print("\n🌴 MAUI WEATHER MCP SERVER TEST SUITE 🌴\n")
    
    # Test 1: Basic 7-day forecast
    result1 = test_weather_api()
    
    # Test 2: Extended 14-day forecast
    result2 = test_extended_forecast()
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"7-day forecast: {'✅ PASS' if result1 else '⚠️  USING MOCK DATA'}")
    print(f"14-day forecast: {'✅ PASS' if result2 else '❌ FAIL'}")
    
    if result1 and result2:
        print("\n🎉 All tests passed! Weather MCP server is ready to use.")
        print("\nNext steps:")
        print("1. Configure Claude Desktop (see MCP_SERVER_GUIDE.md)")
        print("2. Or run: python tools/weather_mcp_server.py")
    else:
        print("\n⚠️  Some tests failed, but mock data fallback is working.")
        print("Check your internet connection for real weather data.")
    
    print()


if __name__ == "__main__":
    main()
