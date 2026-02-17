"""
Synthesis logic for generating final travel recommendations.

Pure Python with no external dependencies.
"""

from typing import List, Tuple
from datetime import date, timedelta

from .models import (
    UserProfile,
    WeatherForecast,
    FlightSearchResult,
    HotelSearchResult,
    TravelWindow,
    TravelRecommendation,
    TripLength,
)
from .scoring import (
    score_weather_compatibility,
    score_flight_option,
    score_hotel_option,
    rank_travel_windows,
    find_best_match,
)


def get_trip_duration_days(trip_length: TripLength) -> int:
    """Convert trip length enum to number of days"""
    mapping = {
        TripLength.SHORT: 4,
        TripLength.MEDIUM: 7,
        TripLength.LONG: 12,
        TripLength.EXTENDED: 17,
    }
    return mapping.get(trip_length, 7)


def generate_candidate_windows(
    weather: WeatherForecast,
    profile: UserProfile
) -> List[Tuple[date, date]]:
    """
    Generate candidate travel windows based on weather and trip length.
    
    Returns:
        List of (start_date, end_date) tuples
    """
    trip_days = get_trip_duration_days(profile.trip_length)
    
    # Start with weather-ideal periods
    ideal_periods = weather.get_ideal_periods(profile, min_days=trip_days)
    
    # If no ideal periods, look at all weather and be more flexible
    if not ideal_periods:
        # Generate windows across the forecast
        candidates = []
        for i in range(0, len(weather.forecast_days) - trip_days, 3):  # Every 3 days
            start = weather.forecast_days[i].date
            end = weather.forecast_days[i + trip_days - 1].date
            candidates.append((start, end))
        return candidates
    
    # Expand ideal periods with flexibility buffer
    expanded = []
    for start, end in ideal_periods:
        # Add the main period
        expanded.append((start, end))
        
        # Add variations within flexibility window
        for offset in range(1, profile.flexibility_days + 1):
            # Earlier departure
            new_start = start - timedelta(days=offset)
            if new_start >= weather.forecast_days[0].date:
                expanded.append((new_start, new_start + timedelta(days=trip_days)))
            
            # Later departure
            new_start = start + timedelta(days=offset)
            new_end = new_start + timedelta(days=trip_days)
            if new_end <= weather.forecast_days[-1].date:
                expanded.append((new_start, new_end))
    
    return expanded


def create_travel_windows(
    candidates: List[Tuple[date, date]],
    weather: WeatherForecast,
    flights: FlightSearchResult,
    hotels: HotelSearchResult,
    profile: UserProfile
) -> List[TravelWindow]:
    """
    Score each candidate window and create TravelWindow objects.
    
    Args:
        candidates: List of (start, end) date tuples
        weather: Weather forecast data
        flights: Flight search results
        hotels: Hotel search results
        profile: User preferences
        
    Returns:
        List of TravelWindow objects with scores
    """
    windows = []
    
    for start_date, end_date in candidates:
        # Get weather for this period
        weather_days = [
            day for day in weather.forecast_days
            if start_date <= day.date <= end_date
        ]
        
        if not weather_days:
            continue
        
        # Score weather
        weather_score, weather_summary = score_weather_compatibility(weather_days, profile)
        
        # Find best flight for this departure date
        matching_flights = [
            f for f in flights.options
            if f.departure_date == start_date
        ]
        
        if not matching_flights:
            # Look for flights within flexibility window
            matching_flights = [
                f for f in flights.options
                if abs((f.departure_date - start_date).days) <= profile.flexibility_days
            ]
        
        # Only consider flights within the user's hard budget
        in_budget_flights = [
            f for f in matching_flights
            if f.price <= profile.flight_budget_hard
        ]
        best_flight = None
        flight_score = 0
        
        if in_budget_flights:
            scored = [(score_flight_option(f, profile)[0], f) for f in in_budget_flights]
            scored.sort(reverse=True, key=lambda x: x[0])
            flight_score, best_flight = scored[0]
        
        # Find best hotel for this period
        matching_hotels = hotels.filter_by_profile(profile)
        
        best_hotel = None
        hotel_score = 0
        
        if matching_hotels:
            scored = [(score_hotel_option(h, profile)[0], h) for h in matching_hotels]
            scored.sort(reverse=True, key=lambda x: x[0])
            hotel_score, best_hotel = scored[0]
        
        # Create window
        window = TravelWindow(
            start_date=start_date,
            end_date=end_date,
            weather_score=weather_score,
            flight_score=flight_score,
            hotel_score=hotel_score,
            overall_score=0,  # Will be calculated by rank_travel_windows
            flight_option=best_flight,
            hotel_option=best_hotel,
            weather_summary=weather_summary
        )
        
        windows.append(window)
    
    return windows


def synthesize_recommendation(
    weather: WeatherForecast,
    flights: FlightSearchResult,
    hotels: HotelSearchResult,
    profile: UserProfile
) -> TravelRecommendation:
    """
    Synthesize all data into a final recommendation.
    
    This is the main synthesis function that combines all analysis.
    """
    # Generate candidate windows
    candidates = generate_candidate_windows(weather, profile)
    
    # Create and score all windows
    windows = create_travel_windows(candidates, weather, flights, hotels, profile)
    
    # Rank by overall score
    ranked_windows = rank_travel_windows(windows)
    
    if not ranked_windows:
        raise ValueError("No viable travel windows found")
    
    # Select top recommendation and alternatives
    recommended = ranked_windows[0]
    alternatives = ranked_windows[1:4]  # Next 3 best options
    
    # Generate reasoning
    reasoning = _generate_reasoning(recommended, profile)
    
    # Generate "why not" explanation
    why_not = _generate_why_not_explanation(ranked_windows, weather, profile)
    
    return TravelRecommendation(
        recommended_window=recommended,
        alternatives=alternatives,
        reasoning=reasoning,
        why_not_rejected=why_not,
        profile_used=profile
    )


def _generate_reasoning(window: TravelWindow, profile: UserProfile) -> str:
    """Generate explanation for why this window is recommended"""
    reasons = []
    
    # Weather reasoning
    if window.weather_score >= 85:
        reasons.append(
            f"Weather is excellent during this period ({window.weather_summary}), "
            f"matching your preference for {profile.preferred_temp_min}-{profile.preferred_temp_max}°F"
        )
    elif window.weather_score >= 70:
        reasons.append(
            f"Weather is favorable ({window.weather_summary}), with most days "
            f"in your preferred temperature range"
        )
    else:
        reasons.append(
            f"Weather is acceptable ({window.weather_summary}), though some "
            f"compromise on conditions"
        )
    
    # Flight reasoning
    if window.flight_option:
        flight = window.flight_option
        affordable, tier = flight.is_within_budget(
            profile.flight_budget_soft,
            profile.flight_budget_hard
        )
        if tier == "great":
            reasons.append(
                f"Flight pricing is excellent at ${flight.price}, well within your "
                f"${profile.flight_budget_soft} target budget"
            )
        elif tier == "acceptable":
            reasons.append(
                f"Flight at ${flight.price} fits your ${profile.flight_budget_hard} "
                f"maximum budget"
            )
        if flight.stops == 0:
            reasons.append("with convenient nonstop service")
    else:
        reasons.append(
            f"No flights within your ${profile.flight_budget_hard} budget for this window; "
            f"consider another date or a higher budget"
        )
    
    # Hotel reasoning
    if window.hotel_option:
        hotel = window.hotel_option
        
        if hotel.has_loyalty_match(profile.hotel_loyalty):
            reasons.append(
                f"Lodging at {hotel.name} earns {profile.hotel_loyalty.value} points "
                f"and is within your ${profile.hotel_budget_min}-${profile.hotel_budget_max} "
                f"nightly budget"
            )
        else:
            reasons.append(
                f"Lodging at {hotel.name} (${hotel.nightly_rate}/night) provides "
                f"{hotel.star_rating}-star comfort within budget"
            )
    
    return ". ".join(reasons) + "."


def _generate_why_not_explanation(
    all_windows: List[TravelWindow],
    weather: WeatherForecast,
    profile: UserProfile
) -> str:
    """Generate explanation for why other periods were rejected"""
    explanations = []
    
    # Look at rejected windows
    rejected = all_windows[4:]  # Skip top 4
    
    # Identify common rejection reasons
    storm_affected = 0
    too_expensive = 0
    poor_weather = 0
    
    for window in rejected:
        if window.weather_score < 50:
            poor_weather += 1
        if window.flight_score < 60:
            too_expensive += 1
    
    # Check for storm periods in forecast
    if weather.storm_periods:
        storm_dates = [f"{s.strftime('%b %d')}-{e.strftime('%b %d')}" 
                      for s, e in weather.storm_periods]
        explanations.append(
            f"Storm periods ({', '.join(storm_dates)}) were avoided due to "
            f"safety and weather concerns"
        )
    
    if poor_weather > 3:
        explanations.append(
            f"Several periods had suboptimal weather (frequent rain or "
            f"temperatures outside your {profile.preferred_temp_min}-"
            f"{profile.preferred_temp_max}°F preference)"
        )
    
    if too_expensive > 3:
        explanations.append(
            f"Many departure dates had flights exceeding your "
            f"${profile.flight_budget_hard} maximum budget"
        )
    
    if not explanations:
        explanations.append(
            "Other periods were viable but scored lower on the combination "
            "of weather, pricing, and schedule convenience"
        )
    
    return ". ".join(explanations) + "."
