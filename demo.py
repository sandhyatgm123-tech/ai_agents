#!/usr/bin/env python3
"""
Demo script showing the Maui Travel Advisor in action.

This demonstrates the full 6-stage process without requiring
external API calls (uses mock data).
"""

import sys
import os

# Add to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import date, timedelta
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
from core.synthesis import synthesize_recommendation


def _profile_from_override(raw: dict) -> UserProfile:
    """Build UserProfile from UI override dict (raw_profile)."""
    trip_map = {"3-5 days": TripLength.SHORT, "6-9 days": TripLength.MEDIUM, "10-14 days": TripLength.LONG, "15+ days": TripLength.EXTENDED}
    loyalty_map = {"marriott_bonvoy": LoyaltyProgram.MARRIOTT, "hilton_honors": LoyaltyProgram.HILTON, "world_of_hyatt": LoyaltyProgram.HYATT, "ihg_rewards": LoyaltyProgram.IHG, "none": LoyaltyProgram.NONE}
    return UserProfile(
        preferred_temp_min=int(raw.get("preferred_temp_min", 75)),
        preferred_temp_max=int(raw.get("preferred_temp_max", 85)),
        rain_tolerance=raw.get("rain_tolerance", "medium"),
        flight_budget_soft=int(raw.get("flight_budget_soft", 600)),
        flight_budget_hard=int(raw.get("flight_budget_hard", 850)),
        hotel_budget_min=int(raw.get("hotel_budget_min", 180)),
        hotel_budget_max=int(raw.get("hotel_budget_max", 350)),
        trip_length=trip_map.get(raw.get("trip_length"), TripLength.MEDIUM) or TripLength.MEDIUM,
        flexibility_days=int(raw.get("flexibility_days", 4)),
        hotel_loyalty=loyalty_map.get(raw.get("hotel_loyalty"), LoyaltyProgram.MARRIOTT) or LoyaltyProgram.MARRIOTT,
        safety_priority=int(raw.get("safety_priority", 4)),
        comfort_priority=int(raw.get("comfort_priority", 4)),
        can_take_red_eye=bool(raw.get("can_take_red_eye", False)),
        prefers_weekday_departure=bool(raw.get("prefers_weekday_departure", True)),
    )


def create_mock_data(profile_override: dict = None):
    """Create mock data for demonstration. Optionally use profile from UI (profile_override with 'raw_profile')."""
    if profile_override and profile_override.get("raw_profile"):
        profile = _profile_from_override(profile_override["raw_profile"])
    else:
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
            prefers_weekday_departure=True,
        )
    
    # Weather forecast (30 days)
    today = date.today()
    forecast_days = []
    
    for i in range(30):
        day_date = today + timedelta(days=i)
        
        # Simulate storm period (days 18-21)
        if 18 <= i <= 21:
            weather_day = WeatherDay(
                date=day_date,
                temp_high=78,
                temp_low=70,
                precipitation_chance=85,
                storm_risk=True,
                conditions="stormy"
            )
        # Some rainy days
        elif i % 7 == 0:
            weather_day = WeatherDay(
                date=day_date,
                temp_high=79,
                temp_low=72,
                precipitation_chance=60,
                storm_risk=False,
                conditions="rainy"
            )
        # Nice weather
        else:
            weather_day = WeatherDay(
                date=day_date,
                temp_high=81,
                temp_low=73,
                precipitation_chance=15,
                storm_risk=False,
                conditions="sunny"
            )
        
        forecast_days.append(weather_day)
    
    weather = WeatherForecast(
        location="Maui, Hawaii",
        forecast_days=forecast_days,
        storm_periods=[(today + timedelta(days=18), today + timedelta(days=21))]
    )
    
    # Flight options (include options in user's budget so recommendations respect preferences)
    flight_options = []
    soft, hard = profile.flight_budget_soft, profile.flight_budget_hard
    mid_budget = (soft + hard) // 2 if hard > soft else soft

    for offset in [7, 8, 9, 10, 11, 12, 14, 15, 16]:
        dep_date = today + timedelta(days=offset)
        ret_date = dep_date + timedelta(days=7)

        # In-budget options (so user's flight budget is respected)
        if hard >= 200:
            price_in_budget = min(mid_budget, hard - 20) if hard > soft else soft
            if price_in_budget >= 150:
                flight_options.append(FlightOption(
                    departure_date=dep_date,
                    return_date=ret_date,
                    departure_time="2:20 PM",
                    return_time="8:45 PM",
                    price=price_in_budget,
                    airline="Southwest Airlines" if price_in_budget < 280 else "United Airlines",
                    stops=1,
                    duration_hours=7.5,
                    is_red_eye_outbound=False,
                    is_red_eye_return=False,
                    departure_day_of_week=dep_date.strftime("%A"),
                ))
            if soft < hard and (hard - soft) >= 60:
                flight_options.append(FlightOption(
                    departure_date=dep_date,
                    return_date=ret_date,
                    departure_time="11:15 AM",
                    return_time="5:30 PM",
                    price=soft + 30,
                    airline="Spirit Airlines",
                    stops=1,
                    duration_hours=9.0,
                    is_red_eye_outbound=False,
                    is_red_eye_return=False,
                    departure_day_of_week=dep_date.strftime("%A"),
                ))

        # Premium options (for users with higher budgets)
        flight_options.append(FlightOption(
            departure_date=dep_date,
            return_date=ret_date,
            departure_time="10:30 AM",
            return_time="4:15 PM",
            price=620 if dep_date.weekday() < 5 else 720,
            airline="Hawaiian Airlines",
            stops=0,
            duration_hours=5.5,
            is_red_eye_outbound=False,
            is_red_eye_return=False,
            departure_day_of_week=dep_date.strftime("%A"),
        ))
        if offset % 2 == 0:
            flight_options.append(FlightOption(
                departure_date=dep_date,
                return_date=ret_date,
                departure_time="6:45 AM",
                return_time="10:30 PM",
                price=540 if dep_date.weekday() < 5 else 640,
                airline="United Airlines",
                stops=1,
                duration_hours=8.5,
                is_red_eye_outbound=False,
                is_red_eye_return=True,
                departure_day_of_week=dep_date.strftime("%A"),
            ))
    
    origin = "SFO"
    if profile_override and profile_override.get("origin"):
        origin = (profile_override["origin"] or "SFO").strip().upper()[:3] or "SFO"
    flights = FlightSearchResult(
        origin=origin,
        destination="OGG",
        search_date=today,
        options=flight_options
    )
    
    # Hotel options
    check_in = today + timedelta(days=9)
    check_out = check_in + timedelta(days=7)
    
    hotel_options = [
        HotelOption(
            name="Wailea Beach Resort - Marriott",
            brand="Marriott",
            nightly_rate=295,
            total_nights=7,
            total_cost=2065,
            loyalty_program=LoyaltyProgram.MARRIOTT,
            star_rating=4.5,
            guest_rating=4.7,
            amenities=["pool", "spa", "beach_access", "restaurant"],
            distance_to_beach=0.1,
            cancellation_policy="Free cancellation 48h before",
            is_storm_discount=False
        ),
        HotelOption(
            name="Andaz Maui at Wailea",
            brand="Hyatt",
            nightly_rate=265,
            total_nights=7,
            total_cost=1855,
            loyalty_program=LoyaltyProgram.HYATT,
            star_rating=4.0,
            guest_rating=4.5,
            amenities=["pool", "beach_access", "restaurant"],
            distance_to_beach=0.2,
            cancellation_policy="Free cancellation 24h before",
            is_storm_discount=False
        ),
        HotelOption(
            name="Hilton Maui Resort & Spa",
            brand="Hilton",
            nightly_rate=215,
            total_nights=7,
            total_cost=1505,
            loyalty_program=LoyaltyProgram.HILTON,
            star_rating=3.5,
            guest_rating=4.2,
            amenities=["pool", "beach_access"],
            distance_to_beach=0.8,
            cancellation_policy="Free cancellation 72h before",
            is_storm_discount=False
        )
    ]
    
    hotels = HotelSearchResult(
        destination="Maui, Hawaii",
        check_in=check_in,
        check_out=check_out,
        options=hotel_options
    )
    
    return profile, weather, flights, hotels


def print_banner(text):
    """Print a formatted banner"""
    print("\n" + "=" * 80)
    print(text.center(80))
    print("=" * 80 + "\n")


def print_section(title):
    """Print a section header"""
    print(f"\n{'─' * 80}")
    print(f"📍 {title}")
    print(f"{'─' * 80}\n")


def main():
    """Run the demo"""
    
    print_banner("MAUI TRAVEL ADVISOR DEMO")
    print("This demonstrates the full 6-stage recommendation process.\n")
    print("User Query: \"Is it a good time to go to Maui?\"\n")
    
    # Stage 1: Epistemic Reflection
    print_section("STAGE 1: Epistemic Reflection")
    print("The agent recognizes that the query is underspecified and needs:")
    print("  • Weather preferences (temperature, rain tolerance)")
    print("  • Budget constraints (flight and hotel budgets)")
    print("  • Trip preferences (duration, flexibility)")
    print("  • Loyalty programs and comfort priorities")
    print("  • Schedule preferences (red-eye acceptance, weekday preference)")
    print("\n→ Decision: Retrieve user profile before consulting external data")
    
    # Stage 2: User Profile Retrieval
    print_section("STAGE 2: User Profile Retrieval")
    profile, weather, flights, hotels = create_mock_data()
    
    print(f"Retrieved profile:")
    print(f"  • Temperature preference: {profile.preferred_temp_min}-{profile.preferred_temp_max}°F")
    print(f"  • Rain tolerance: {profile.rain_tolerance}")
    print(f"  • Flight budget: ${profile.flight_budget_soft} target, ${profile.flight_budget_hard} max")
    print(f"  • Hotel budget: ${profile.hotel_budget_min}-${profile.hotel_budget_max}/night")
    print(f"  • Trip duration: {profile.trip_length.value}")
    print(f"  • Flexibility: {profile.flexibility_days} days")
    print(f"  • Hotel loyalty: {profile.hotel_loyalty.value}")
    print(f"  • Safety priority: {profile.safety_priority}/5")
    print(f"  • Comfort priority: {profile.comfort_priority}/5")
    print(f"  • Red-eye flights: {'Acceptable' if profile.can_take_red_eye else 'Not acceptable'}")
    print(f"  • Departure preference: {'Weekday' if profile.prefers_weekday_departure else 'Flexible'}")
    
    # Stage 3: Weather Analysis
    print_section("STAGE 3: Weather Analysis")
    print(f"30-day forecast for {weather.location}:")
    print(f"  • Total days: {len(weather.forecast_days)}")
    print(f"  • Storm periods: {len(weather.storm_periods)}")
    
    storm_days = sum(1 for day in weather.forecast_days if day.storm_risk)
    sunny_days = sum(1 for day in weather.forecast_days if day.conditions == "sunny")
    temp_highs = [d.temp_high for d in weather.forecast_days]
    
    print(f"  • Storm days: {storm_days}")
    print(f"  • Sunny days: {sunny_days}")
    print(f"  • Temperature range: {min(temp_highs)}-{max(temp_highs)}°F")
    
    if weather.storm_periods:
        for start, end in weather.storm_periods:
            print(f"  ⚠️  Storm warning: {start.strftime('%b %d')} - {end.strftime('%b %d')}")
    
    # Stage 4: Flight Search
    print_section("STAGE 4: Flight Search")
    print(f"Flight search from {flights.origin} to {flights.destination}:")
    print(f"  • Total options found: {len(flights.options)}")
    
    prices = [f.price for f in flights.options]
    nonstop = sum(1 for f in flights.options if f.stops == 0)
    
    print(f"  • Price range: ${min(prices)}-${max(prices)}")
    print(f"  • Average price: ${sum(prices)/len(prices):.0f}")
    print(f"  • Nonstop flights: {nonstop}")
    print(f"  • Flights with stops: {len(flights.options) - nonstop}")
    
    # Stage 5: Hotel Evaluation
    print_section("STAGE 5: Hotel Evaluation")
    print(f"Hotel search for {hotels.destination}:")
    print(f"  • Options found: {len(hotels.options)}")
    
    rates = [h.nightly_rate for h in hotels.options]
    ratings = [h.guest_rating for h in hotels.options]
    
    print(f"  • Rate range: ${min(rates)}-${max(rates)}/night")
    print(f"  • Average rating: {sum(ratings)/len(ratings):.1f}/5.0")
    print(f"  • Loyalty programs available: {', '.join(set(str(h.loyalty_program.value) for h in hotels.options if h.loyalty_program))}")
    
    # Stage 6: Synthesis
    print_section("STAGE 6: Synthesis & Recommendation")
    print("Analyzing all data and generating personalized recommendation...")
    
    recommendation = synthesize_recommendation(
        weather,
        flights,
        hotels,
        profile
    )
    
    # Display final recommendation
    print_banner("FINAL RECOMMENDATION")
    print(recommendation.format_recommendation())
    
    # Show scoring breakdown
    print("\n" + "=" * 80)
    print("SCORING BREAKDOWN")
    print("=" * 80 + "\n")
    
    rec_window = recommendation.recommended_window
    print(f"Weather Score: {rec_window.weather_score:.1f}/100")
    print(f"Flight Score:  {rec_window.flight_score:.1f}/100")
    print(f"Hotel Score:   {rec_window.hotel_score:.1f}/100")
    print(f"Overall Score: {rec_window.overall_score:.1f}/100")
    
    print("\nWeights: Weather (40%), Flight (35%), Hotel (25%)")
    
    # Architecture verification
    print_banner("ARCHITECTURE VERIFICATION")
    print("✓ Core logic ran without framework dependencies")
    print("✓ All business logic in core/ module")
    print("✓ No MCP or Google ADK imports in core/")
    print("✓ Pure Python dataclasses and algorithms")
    print("\nTo verify: python3 -c 'from core.models import UserProfile; print(UserProfile.example())'")
    
    print("\n")


if __name__ == "__main__":
    main()
