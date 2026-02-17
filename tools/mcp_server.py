"""
FastMCP server exposing travel recommendation tools.

This module wraps core business logic in MCP tools.
It depends on FastMCP but core logic remains independent.
"""

import sys
import os
from datetime import date, datetime, timedelta
from typing import Optional

# Add parent directory to path so we can import core
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    # Fallback for different fastmcp versions
    try:
        from fastmcp import FastMCP
    except ImportError:
        print("Error: FastMCP not installed properly")
        print("Try: pip install fastmcp")
        sys.exit(1)

# Import core logic
from core.models import (
    UserProfile,
    TripLength,
    LoyaltyProgram,
    WeatherForecast,
    WeatherDay,
    FlightSearchResult,
    FlightOption,
    HotelSearchResult,
    HotelOption,
)

# Initialize FastMCP server
mcp = FastMCP("maui-travel-advisor")


# ============================================================================
# TOOL 1: User Profile Retrieval
# ============================================================================

@mcp.tool()
def get_user_profile(user_id: str = "default") -> dict:
    """
    Retrieve user travel preferences and constraints.
    
    This tool returns a structured profile containing:
    - Weather preferences (temperature range, rain tolerance)
    - Budget constraints (flight and hotel budgets)
    - Trip preferences (duration, flexibility)
    - Loyalty programs and comfort priorities
    
    Args:
        user_id: User identifier (currently returns mock profile)
        
    Returns:
        Dictionary containing user profile with all preferences
    """
    # For this implementation, return a detailed mock profile
    # In production, this would query a database
    
    profile = UserProfile(
        preferred_temp_min=75,
        preferred_temp_max=85,
        rain_tolerance="medium",
        flight_budget_soft=600,
        flight_budget_hard=850,
        hotel_budget_min=180,
        hotel_budget_max=350,
        trip_length=TripLength.MEDIUM,
        flexibility_days=4,
        hotel_loyalty=LoyaltyProgram.MARRIOTT,
        safety_priority=4,
        comfort_priority=4,
        can_take_red_eye=False,
        prefers_weekday_departure=True
    )
    
    return {
        "user_id": user_id,
        "preferences": {
            "weather": {
                "temperature_range_f": f"{profile.preferred_temp_min}-{profile.preferred_temp_max}",
                "rain_tolerance": profile.rain_tolerance,
                "description": f"Prefers temperatures between {profile.preferred_temp_min}°F and {profile.preferred_temp_max}°F with {profile.rain_tolerance} tolerance for rain"
            },
            "budget": {
                "flight_soft_limit": profile.flight_budget_soft,
                "flight_hard_limit": profile.flight_budget_hard,
                "hotel_nightly_range": f"${profile.hotel_budget_min}-${profile.hotel_budget_max}",
                "description": f"Target flight budget ${profile.flight_budget_soft}, absolute max ${profile.flight_budget_hard}. Hotels ${profile.hotel_budget_min}-${profile.hotel_budget_max}/night"
            },
            "trip": {
                "preferred_duration": profile.trip_length.value,
                "flexibility_days": profile.flexibility_days,
                "description": f"Prefers {profile.trip_length.value} trips with {profile.flexibility_days} days flexibility on dates"
            },
            "loyalty": {
                "program": profile.hotel_loyalty.value,
                "description": f"Member of {profile.hotel_loyalty.value}"
            },
            "priorities": {
                "safety": profile.safety_priority,
                "comfort": profile.comfort_priority,
                "description": f"High priority on both safety ({profile.safety_priority}/5) and comfort ({profile.comfort_priority}/5)"
            },
            "schedule": {
                "red_eye_acceptable": profile.can_take_red_eye,
                "prefers_weekday": profile.prefers_weekday_departure,
                "description": f"{'Does not accept' if not profile.can_take_red_eye else 'Accepts'} red-eye flights, prefers weekday departures"
            }
        },
        "raw_profile": {
            "preferred_temp_min": profile.preferred_temp_min,
            "preferred_temp_max": profile.preferred_temp_max,
            "rain_tolerance": profile.rain_tolerance,
            "flight_budget_soft": profile.flight_budget_soft,
            "flight_budget_hard": profile.flight_budget_hard,
            "hotel_budget_min": profile.hotel_budget_min,
            "hotel_budget_max": profile.hotel_budget_max,
            "trip_length": profile.trip_length.value,
            "flexibility_days": profile.flexibility_days,
            "hotel_loyalty": profile.hotel_loyalty.value,
            "safety_priority": profile.safety_priority,
            "comfort_priority": profile.comfort_priority,
            "can_take_red_eye": profile.can_take_red_eye,
            "prefers_weekday_departure": profile.prefers_weekday_departure,
        }
    }


# ============================================================================
# TOOL 2: Weather Forecast Analysis
# ============================================================================

@mcp.tool()
def get_weather_forecast(
    destination: str,
    days_ahead: int = 30
) -> dict:
    """
    Get 30-day weather forecast for destination with storm alerts.
    
    Provides forward-looking weather data including:
    - Daily temperature highs/lows
    - Precipitation chances
    - Storm risk periods
    - Condition summaries
    
    Args:
        destination: Location (e.g., "Maui, Hawaii")
        days_ahead: Number of days to forecast (default 30)
        
    Returns:
        Dictionary with daily forecasts and storm period warnings
    """
    # Generate mock forecast for demonstration
    # In production, this would call a weather API
    
    today = date.today()
    forecast_days = []
    storm_periods = []
    
    # Simulate varied weather conditions
    for i in range(days_ahead):
        day_date = today + timedelta(days=i)
        
        # Simulate storm period (March 10-13)
        is_storm_period = i >= 26 and i <= 29
        
        if is_storm_period:
            temp_high = 78
            temp_low = 70
            precip = 85
            storm_risk = True
            conditions = "stormy"
        elif i % 7 == 0:  # Some rainy days
            temp_high = 79
            temp_low = 72
            precip = 60
            storm_risk = False
            conditions = "rainy"
        elif i % 3 == 0:  # Some cloudy days
            temp_high = 82
            temp_low = 74
            precip = 30
            storm_risk = False
            conditions = "cloudy"
        else:  # Nice days
            temp_high = 83
            temp_low = 73
            precip = 15
            storm_risk = False
            conditions = "sunny"
        
        forecast_days.append({
            "date": day_date.isoformat(),
            "temp_high": temp_high,
            "temp_low": temp_low,
            "precipitation_chance": precip,
            "storm_risk": storm_risk,
            "conditions": conditions
        })
        
        # Track storm periods
        if storm_risk:
            if not storm_periods or storm_periods[-1][1] != (day_date - timedelta(days=1)):
                storm_periods.append([day_date, day_date])
            else:
                storm_periods[-1][1] = day_date
    
    # Format storm periods
    storm_periods_formatted = [
        {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "warning": f"Storm expected {start.strftime('%b %d')} - {end.strftime('%b %d')}"
        }
        for start, end in storm_periods
    ]
    
    return {
        "destination": destination,
        "forecast_start": today.isoformat(),
        "forecast_end": (today + timedelta(days=days_ahead-1)).isoformat(),
        "days_ahead": days_ahead,
        "forecast": forecast_days,
        "storm_periods": storm_periods_formatted,
        "summary": {
            "total_days": len(forecast_days),
            "storm_days": sum(1 for d in forecast_days if d["storm_risk"]),
            "sunny_days": sum(1 for d in forecast_days if d["conditions"] == "sunny"),
            "temp_range": f"{min(d['temp_low'] for d in forecast_days)}-{max(d['temp_high'] for d in forecast_days)}°F"
        }
    }


# ============================================================================
# TOOL 3: Flight Search
# ============================================================================

@mcp.tool()
def search_flights(
    origin: str,
    destination: str,
    departure_start: str,
    departure_end: str,
    trip_duration_days: int = 7,
    flight_budget_soft: Optional[int] = None,
    flight_budget_hard: Optional[int] = None,
) -> dict:
    """
    Search for flights within a date range and compare options.
    When flight_budget_soft/hard are provided, mock results include options in that range.

    Args:
        origin: Departure airport code (e.g., "SFO")
        destination: Arrival airport code (e.g., "OGG")
        departure_start: Earliest departure date (YYYY-MM-DD)
        departure_end: Latest departure date (YYYY-MM-DD)
        trip_duration_days: Length of trip in days
        flight_budget_soft: Optional user target flight budget (USD)
        flight_budget_hard: Optional user max flight budget (USD)

    Returns:
        Dictionary with multiple flight options and comparison data
    """
    from tools.flight_provider import fetch_flights_amadeus

    # Try free Amadeus API first (set AMADEUS_CLIENT_ID + AMADEUS_CLIENT_SECRET)
    options = fetch_flights_amadeus(
        origin=origin,
        destination=destination,
        departure_start=departure_start,
        departure_end=departure_end,
        trip_duration_days=trip_duration_days,
    )

    if not options:
        # Fallback: mock flight options
        start = datetime.fromisoformat(departure_start).date()
        end = datetime.fromisoformat(departure_end).date()
        soft = flight_budget_soft if flight_budget_soft is not None else 600
        hard = flight_budget_hard if flight_budget_hard is not None else 850
        mid_budget = (soft + hard) // 2 if hard > soft else soft
        options = []
        current = start
        while current <= end:
            # In-budget options when user has a budget (so recommendations respect preferences)
            if hard >= 200:
                price_in_budget = min(mid_budget, hard - 20) if hard > soft else soft
                if price_in_budget >= 150:
                    options.append({
                        "departure_date": current.isoformat(),
                        "return_date": (current + timedelta(days=trip_duration_days)).isoformat(),
                        "departure_time": "2:20 PM",
                        "return_time": "8:45 PM",
                        "price": price_in_budget,
                        "airline": "Southwest Airlines" if price_in_budget < 280 else "United Airlines",
                        "stops": 1,
                        "duration_hours": 7.5,
                        "is_red_eye_outbound": False,
                        "is_red_eye_return": False,
                        "departure_day_of_week": current.strftime("%A"),
                    })
                if soft < hard and (hard - soft) >= 60:
                    options.append({
                        "departure_date": current.isoformat(),
                        "return_date": (current + timedelta(days=trip_duration_days)).isoformat(),
                        "departure_time": "11:15 AM",
                        "return_time": "5:30 PM",
                        "price": soft + 30,
                        "airline": "Spirit Airlines",
                        "stops": 1,
                        "duration_hours": 9.0,
                        "is_red_eye_outbound": False,
                        "is_red_eye_return": False,
                        "departure_day_of_week": current.strftime("%A"),
                    })

            # Premium options
            base_price = 520 if current.weekday() < 5 else 680
            options.append({
                "departure_date": current.isoformat(),
                "return_date": (current + timedelta(days=trip_duration_days)).isoformat(),
                "departure_time": "10:30 AM",
                "return_time": "4:15 PM",
                "price": base_price + 150,
                "airline": "Hawaiian Airlines",
                "stops": 0,
                "duration_hours": 5.5,
                "is_red_eye_outbound": False,
                "is_red_eye_return": False,
                "departure_day_of_week": current.strftime("%A"),
            })
            if current.weekday() in [1, 3, 5]:
                options.append({
                    "departure_date": current.isoformat(),
                    "return_date": (current + timedelta(days=trip_duration_days)).isoformat(),
                    "departure_time": "6:45 AM",
                    "return_time": "10:30 PM",
                    "price": base_price - 80,
                    "airline": "United Airlines",
                    "stops": 1,
                    "duration_hours": 8.5,
                    "is_red_eye_outbound": False,
                    "is_red_eye_return": True,
                    "departure_day_of_week": current.strftime("%A"),
                })
            if current.weekday() == 6:
                options.append({
                    "departure_date": current.isoformat(),
                    "return_date": (current + timedelta(days=trip_duration_days)).isoformat(),
                    "departure_time": "11:45 PM",
                    "return_time": "2:00 PM",
                    "price": base_price - 120,
                    "airline": "Alaska Airlines",
                    "stops": 1,
                    "duration_hours": 7.0,
                    "is_red_eye_outbound": True,
                    "is_red_eye_return": False,
                    "departure_day_of_week": current.strftime("%A"),
                })

            current += timedelta(days=2)

    return {
        "origin": origin,
        "destination": destination,
        "search_window": {
            "start": departure_start,
            "end": departure_end
        },
        "trip_duration_days": trip_duration_days,
        "options": options,
        "summary": {
            "total_options": len(options),
            "price_range": f"${min(o['price'] for o in options)}-${max(o['price'] for o in options)}",
            "nonstop_available": any(o["stops"] == 0 for o in options),
            "cheapest_price": min(o['price'] for o in options),
            "average_price": sum(o['price'] for o in options) / len(options)
        }
    }


# ============================================================================
# TOOL 4: Hotel Evaluation
# ============================================================================

@mcp.tool()
def search_hotels(
    destination: str,
    check_in: str,
    check_out: str,
    budget_min: int = 150,
    budget_max: int = 400
) -> dict:
    """
    Search for hotels and evaluate options against preferences.
    
    Returns hotels with:
    - Nightly rates and total costs
    - Star and guest ratings
    - Loyalty program information
    - Amenities and location details
    - Storm discount warnings
    
    Args:
        destination: Location (e.g., "Maui, Hawaii")
        check_in: Check-in date (YYYY-MM-DD)
        check_out: Check-out date (YYYY-MM-DD)
        budget_min: Minimum nightly rate
        budget_max: Maximum nightly rate
        
    Returns:
        Dictionary with hotel options and comparison data
    """
    # Generate mock hotel options
    # In production, this would call hotel search APIs
    
    check_in_date = datetime.fromisoformat(check_in).date()
    check_out_date = datetime.fromisoformat(check_out).date()
    nights = (check_out_date - check_in_date).days
    
    # Check if dates fall in storm period (simulated as March 10-13)
    storm_period_start = date(2026, 3, 10)
    storm_period_end = date(2026, 3, 13)
    is_storm_period = (check_in_date <= storm_period_end and check_out_date >= storm_period_start)
    
    options = []
    
    # Option 1: Luxury Marriott
    base_rate = 320 if not is_storm_period else 220
    options.append({
        "name": "Wailea Beach Resort - Marriott",
        "brand": "Marriott",
        "nightly_rate": base_rate,
        "total_nights": nights,
        "total_cost": base_rate * nights,
        "loyalty_program": "marriott_bonvoy",
        "star_rating": 4.5,
        "guest_rating": 4.7,
        "amenities": ["pool", "spa", "beach_access", "restaurant", "fitness_center"],
        "distance_to_beach": 0.1,
        "cancellation_policy": "Free cancellation until 48h before",
        "is_storm_discount": is_storm_period
    })
    
    # Option 2: Mid-range Hyatt
    base_rate = 245 if not is_storm_period else 180
    options.append({
        "name": "Andaz Maui at Wailea Resort",
        "brand": "Hyatt",
        "nightly_rate": base_rate,
        "total_nights": nights,
        "total_cost": base_rate * nights,
        "loyalty_program": "world_of_hyatt",
        "star_rating": 4.0,
        "guest_rating": 4.5,
        "amenities": ["pool", "beach_access", "restaurant", "bar"],
        "distance_to_beach": 0.2,
        "cancellation_policy": "Free cancellation until 24h before",
        "is_storm_discount": is_storm_period
    })
    
    # Option 3: Budget Hilton
    base_rate = 195 if not is_storm_period else 145
    options.append({
        "name": "Hilton Maui Resort & Spa",
        "brand": "Hilton",
        "nightly_rate": base_rate,
        "total_nights": nights,
        "total_cost": base_rate * nights,
        "loyalty_program": "hilton_honors",
        "star_rating": 3.5,
        "guest_rating": 4.2,
        "amenities": ["pool", "beach_access", "restaurant"],
        "distance_to_beach": 0.8,
        "cancellation_policy": "Free cancellation until 72h before",
        "is_storm_discount": is_storm_period
    })
    
    # Option 4: Independent boutique
    base_rate = 280 if not is_storm_period else 205
    options.append({
        "name": "Paia Bay Resort",
        "brand": "Independent",
        "nightly_rate": base_rate,
        "total_nights": nights,
        "total_cost": base_rate * nights,
        "loyalty_program": None,
        "star_rating": 4.0,
        "guest_rating": 4.8,
        "amenities": ["pool", "beach_access", "kitchenette", "parking"],
        "distance_to_beach": 0.3,
        "cancellation_policy": "Free cancellation until 7 days before",
        "is_storm_discount": is_storm_period
    })
    
    return {
        "destination": destination,
        "check_in": check_in,
        "check_out": check_out,
        "nights": nights,
        "budget_range": f"${budget_min}-${budget_max}",
        "options": options,
        "storm_warning": {
            "active": is_storm_period,
            "message": "⚠️ Rates may reflect storm-period discounts. Weather conditions should be carefully evaluated." if is_storm_period else None
        },
        "summary": {
            "total_options": len(options),
            "nightly_rate_range": f"${min(o['nightly_rate'] for o in options)}-${max(o['nightly_rate'] for o in options)}",
            "avg_rating": sum(o['guest_rating'] for o in options) / len(options),
            "loyalty_programs_available": list(set(o.get('loyalty_program') for o in options if o.get('loyalty_program')))
        }
    }


# ============================================================================
# Run Server
# ============================================================================

if __name__ == "__main__":
    mcp.run()
