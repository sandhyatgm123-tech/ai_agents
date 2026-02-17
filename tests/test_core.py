"""
Unit tests for core business logic.

These tests verify that core logic works without any framework dependencies.
They can run in a Python REPL without internet access.
"""

import sys
import os
from datetime import date, timedelta

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.models import (
    UserProfile,
    TripLength,
    LoyaltyProgram,
    WeatherDay,
    WeatherForecast,
    FlightOption,
    HotelOption,
)
from core.scoring import (
    score_weather_compatibility,
    score_flight_option,
    score_hotel_option,
)


def test_user_profile_creation():
    """Test that UserProfile can be created without dependencies"""
    profile = UserProfile.example()
    
    assert profile.preferred_temp_min == 72
    assert profile.preferred_temp_max == 85
    assert profile.trip_length == TripLength.MEDIUM
    assert profile.hotel_loyalty == LoyaltyProgram.MARRIOTT
    
    print("✓ UserProfile creation works")


def test_weather_scoring():
    """Test weather compatibility scoring"""
    profile = UserProfile.example()
    
    # Create ideal weather
    weather_days = [
        WeatherDay(
            date=date.today() + timedelta(days=i),
            temp_high=78,
            temp_low=70,
            precipitation_chance=10,
            storm_risk=False,
            conditions="sunny"
        )
        for i in range(7)
    ]
    
    score, summary = score_weather_compatibility(weather_days, profile)
    
    assert score > 90, f"Expected high score for ideal weather, got {score}"
    assert "ideal" in summary.lower()
    
    print(f"✓ Weather scoring works: {score:.1f}/100 - {summary}")


def test_flight_scoring():
    """Test flight option scoring"""
    profile = UserProfile.example()
    
    # Good flight within budget
    good_flight = FlightOption(
        departure_date=date.today() + timedelta(days=7),
        return_date=date.today() + timedelta(days=14),
        departure_time="10:00 AM",
        return_time="4:00 PM",
        price=550,  # Within soft budget
        airline="Hawaiian Airlines",
        stops=0,
        duration_hours=5.5,
        is_red_eye_outbound=False,
        is_red_eye_return=False,
        departure_day_of_week="Tuesday"
    )
    
    score, explanation = score_flight_option(good_flight, profile)
    
    assert score > 80, f"Expected high score for good flight, got {score}"
    assert "nonstop" in explanation.lower()
    
    print(f"✓ Flight scoring works: {score:.1f}/100 - {explanation}")


def test_hotel_scoring():
    """Test hotel option scoring"""
    profile = UserProfile.example()
    
    # Good hotel with loyalty match
    good_hotel = HotelOption(
        name="Wailea Beach Resort",
        brand="Marriott",
        nightly_rate=280,  # Within budget
        total_nights=7,
        total_cost=1960,
        loyalty_program=LoyaltyProgram.MARRIOTT,  # Matches profile
        star_rating=4.5,
        guest_rating=4.7,
        amenities=["pool", "spa", "beach"],
        distance_to_beach=0.1,
        cancellation_policy="Free cancellation",
        is_storm_discount=False
    )
    
    score, explanation = score_hotel_option(good_hotel, profile)
    
    assert score > 80, f"Expected high score for good hotel, got {score}"
    assert "marriott" in explanation.lower()
    
    print(f"✓ Hotel scoring works: {score:.1f}/100 - {explanation}")


def test_weather_ideal_periods():
    """Test finding ideal weather periods"""
    profile = UserProfile.example()
    
    # Create forecast with mixed conditions
    forecast_days = []
    today = date.today()
    
    # First 5 days: not ideal (too hot)
    for i in range(5):
        forecast_days.append(
            WeatherDay(
                date=today + timedelta(days=i),
                temp_high=90,  # Too hot
                temp_low=75,
                precipitation_chance=10,
                storm_risk=False,
                conditions="sunny"
            )
        )
    
    # Next 10 days: ideal
    for i in range(5, 15):
        forecast_days.append(
            WeatherDay(
                date=today + timedelta(days=i),
                temp_high=80,  # Perfect
                temp_low=72,
                precipitation_chance=10,
                storm_risk=False,
                conditions="sunny"
            )
        )
    
    # Last 5 days: stormy
    for i in range(15, 20):
        forecast_days.append(
            WeatherDay(
                date=today + timedelta(days=i),
                temp_high=78,
                temp_low=70,
                precipitation_chance=80,
                storm_risk=True,
                conditions="stormy"
            )
        )
    
    forecast = WeatherForecast(
        location="Maui",
        forecast_days=forecast_days,
        storm_periods=[(today + timedelta(days=15), today + timedelta(days=19))]
    )
    
    ideal_periods = forecast.get_ideal_periods(profile, min_days=5)
    
    assert len(ideal_periods) > 0, "Should find at least one ideal period"
    
    # First ideal period should be days 5-14
    start, end = ideal_periods[0]
    assert (start - today).days >= 5, "Ideal period should start after hot days"
    assert (end - today).days <= 15, "Ideal period should end before storm"
    
    print(f"✓ Weather ideal periods works: Found {len(ideal_periods)} period(s)")
    for start, end in ideal_periods:
        print(f"  • {start} to {end}")


def test_flight_budget_check():
    """Test flight budget checking"""
    profile = UserProfile.example()
    
    # Flight within soft budget
    cheap_flight = FlightOption(
        departure_date=date.today(),
        return_date=date.today() + timedelta(days=7),
        departure_time="10:00 AM",
        return_time="4:00 PM",
        price=450,
        airline="Test",
        stops=0,
        duration_hours=5.5,
        is_red_eye_outbound=False,
        is_red_eye_return=False,
        departure_day_of_week="Monday"
    )
    
    affordable, tier = cheap_flight.is_within_budget(
        profile.flight_budget_soft,
        profile.flight_budget_hard
    )
    
    assert affordable
    assert tier == "great"
    
    # Flight over hard budget
    expensive_flight = FlightOption(
        departure_date=date.today(),
        return_date=date.today() + timedelta(days=7),
        departure_time="10:00 AM",
        return_time="4:00 PM",
        price=900,  # Over hard budget (750)
        airline="Test",
        stops=0,
        duration_hours=5.5,
        is_red_eye_outbound=False,
        is_red_eye_return=False,
        departure_day_of_week="Monday"
    )
    
    affordable, tier = expensive_flight.is_within_budget(
        profile.flight_budget_soft,
        profile.flight_budget_hard
    )
    
    assert not affordable
    assert tier == "too_expensive"
    
    print("✓ Flight budget checking works")


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("RUNNING CORE LOGIC TESTS (No Internet Required)")
    print("="*60 + "\n")
    
    test_user_profile_creation()
    test_weather_scoring()
    test_flight_scoring()
    test_hotel_scoring()
    test_weather_ideal_periods()
    test_flight_budget_check()
    
    print("\n" + "="*60)
    print("ALL TESTS PASSED ✓")
    print("="*60 + "\n")


if __name__ == "__main__":
    run_all_tests()
