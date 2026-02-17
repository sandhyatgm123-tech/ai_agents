"""
Core business logic package for Maui travel recommendations.

This package contains pure Python with no external framework dependencies.
All modules can be imported in a Python REPL without internet access.
"""

from .models import (
    UserProfile,
    WeatherDay,
    WeatherForecast,
    FlightOption,
    FlightSearchResult,
    HotelOption,
    HotelSearchResult,
    TravelWindow,
    TravelRecommendation,
    TripLength,
    LoyaltyProgram,
)

__all__ = [
    "UserProfile",
    "WeatherDay",
    "WeatherForecast",
    "FlightOption",
    "FlightSearchResult",
    "HotelOption",
    "HotelSearchResult",
    "TravelWindow",
    "TravelRecommendation",
    "TripLength",
    "LoyaltyProgram",
]
