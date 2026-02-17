"""
Scoring heuristics for travel recommendations.

Pure Python business logic with no external dependencies.
"""

from typing import List, Tuple
from datetime import date

from .models import (
    UserProfile,
    WeatherDay,
    FlightOption,
    HotelOption,
    TravelWindow,
)


def score_weather_compatibility(
    weather_days: List[WeatherDay],
    profile: UserProfile
) -> Tuple[float, str]:
    """
    Score how well weather matches user preferences.
    
    Args:
        weather_days: List of weather forecasts for the period
        profile: User preferences
        
    Returns:
        (score, summary) tuple where score is 0-100
    """
    if not weather_days:
        return (0.0, "No weather data available")
    
    total_score = 0
    perfect_days = 0
    storm_days = 0
    rainy_days = 0
    
    for day in weather_days:
        day_score = 100
        
        # Temperature scoring
        if profile.preferred_temp_min <= day.temp_high <= profile.preferred_temp_max:
            # Perfect temp
            temp_score = 100
        else:
            # Penalize based on deviation
            if day.temp_high < profile.preferred_temp_min:
                deviation = profile.preferred_temp_min - day.temp_high
            else:
                deviation = day.temp_high - profile.preferred_temp_max
            
            temp_score = max(0, 100 - (deviation * 5))  # -5 points per degree
        
        day_score = min(day_score, temp_score)
        
        # Precipitation scoring
        if profile.rain_tolerance == "low":
            if day.precipitation_chance >= 40:
                day_score *= 0.3
            elif day.precipitation_chance >= 20:
                day_score *= 0.6
        elif profile.rain_tolerance == "medium":
            if day.precipitation_chance >= 60:
                day_score *= 0.5
            elif day.precipitation_chance >= 40:
                day_score *= 0.8
        # high tolerance doesn't penalize rain
        
        # Storm penalty (severe)
        if day.storm_risk:
            day_score *= 0.1  # Major penalty
            storm_days += 1
        
        if day.precipitation_chance > 50:
            rainy_days += 1
        
        if day_score >= 90:
            perfect_days += 1
        
        total_score += day_score
    
    avg_score = total_score / len(weather_days)
    
    # Generate summary
    summary_parts = []
    summary_parts.append(f"{perfect_days}/{len(weather_days)} ideal days")
    
    if storm_days > 0:
        summary_parts.append(f"{storm_days} storm day(s)")
    elif rainy_days > len(weather_days) / 2:
        summary_parts.append("frequent rain expected")
    else:
        summary_parts.append("generally favorable conditions")
    
    temp_range = f"{min(d.temp_high for d in weather_days)}-{max(d.temp_high for d in weather_days)}°F"
    summary_parts.append(temp_range)
    
    summary = ", ".join(summary_parts)
    
    return (avg_score, summary)


def score_flight_option(
    flight: FlightOption,
    profile: UserProfile
) -> Tuple[float, str]:
    """
    Score a flight option based on user preferences.
    
    Returns:
        (score, explanation) tuple where score is 0-100
    """
    score = 100
    factors = []
    
    # Price scoring (40% weight)
    affordable, tier = flight.is_within_budget(
        profile.flight_budget_soft,
        profile.flight_budget_hard
    )
    
    if tier == "great":
        price_score = 100
        factors.append(f"excellent price (${flight.price})")
    elif tier == "acceptable":
        price_score = 70
        factors.append(f"acceptable price (${flight.price})")
    else:
        price_score = 0
        factors.append(f"over budget (${flight.price})")
    
    score = price_score * 0.4
    
    # Duration/convenience scoring (30% weight)
    duration_score = 100
    if flight.stops == 0:
        duration_score = 100
        factors.append("nonstop")
    elif flight.stops == 1:
        duration_score = 75
        factors.append("1 stop")
    else:
        duration_score = 50
        factors.append(f"{flight.stops} stops")
    
    if flight.duration_hours > 12:
        duration_score *= 0.8
    
    score += duration_score * 0.3
    
    # Schedule preference scoring (30% weight)
    schedule_score = 100
    
    if not profile.can_take_red_eye:
        if flight.is_red_eye_outbound or flight.is_red_eye_return:
            schedule_score = 0
            factors.append("red-eye (disliked)")
    else:
        if flight.is_red_eye_outbound or flight.is_red_eye_return:
            factors.append("red-eye")
    
    if profile.prefers_weekday_departure:
        if flight.departure_day_of_week in ["Monday", "Tuesday", "Wednesday", "Thursday"]:
            factors.append(f"weekday departure")
        else:
            schedule_score *= 0.9
            factors.append(f"weekend departure")
    
    score += schedule_score * 0.3
    
    explanation = f"{flight.airline}: " + ", ".join(factors)
    
    return (score, explanation)


def score_hotel_option(
    hotel: HotelOption,
    profile: UserProfile
) -> Tuple[float, str]:
    """
    Score a hotel option based on user preferences.
    
    Returns:
        (score, explanation) tuple where score is 0-100
    """
    score = 100
    factors = []
    
    # Budget alignment (40% weight)
    if hotel.nightly_rate <= profile.hotel_budget_max * 0.7:
        budget_score = 100
        factors.append(f"great value (${hotel.nightly_rate}/nt)")
    elif hotel.nightly_rate <= profile.hotel_budget_max * 0.85:
        budget_score = 85
        factors.append(f"good rate (${hotel.nightly_rate}/nt)")
    elif hotel.nightly_rate <= profile.hotel_budget_max:
        budget_score = 70
        factors.append(f"at budget max (${hotel.nightly_rate}/nt)")
    else:
        budget_score = 0
        factors.append(f"over budget (${hotel.nightly_rate}/nt)")
    
    score = budget_score * 0.4
    
    # Quality scoring (35% weight)
    quality_score = (hotel.star_rating / 5.0) * 50 + (hotel.guest_rating / 5.0) * 50
    
    if hotel.star_rating >= 4.0 and hotel.guest_rating >= 4.5:
        factors.append("highly rated")
    elif hotel.star_rating >= 3.5 and hotel.guest_rating >= 4.0:
        factors.append("well rated")
    elif hotel.star_rating < 3.0 or hotel.guest_rating < 3.5:
        factors.append("lower ratings")
    
    score += quality_score * 0.35
    
    # Loyalty bonus (15% weight)
    loyalty_score = 50  # baseline
    if hotel.has_loyalty_match(profile.hotel_loyalty):
        loyalty_score = 100
        factors.append(f"{profile.hotel_loyalty.value} member")
    
    score += loyalty_score * 0.15
    
    # Location/amenities (10% weight)
    location_score = max(0, 100 - (hotel.distance_to_beach * 20))  # penalize distance
    score += location_score * 0.1
    
    if hotel.distance_to_beach <= 0.5:
        factors.append("beachfront")
    elif hotel.distance_to_beach <= 1.5:
        factors.append("near beach")
    
    # Storm discount warning
    if hotel.is_storm_discount:
        score *= 0.7  # Major penalty for storm risk
        factors.append("⚠️ storm-period pricing")
    
    explanation = f"{hotel.name}: " + ", ".join(factors)
    
    return (score, explanation)


def rank_travel_windows(
    windows: List[TravelWindow]
) -> List[TravelWindow]:
    """
    Rank travel windows by overall score.
    
    The overall score is a weighted combination of weather, flight, and hotel scores.
    """
    # Calculate overall scores
    for window in windows:
        # Weights: weather 40%, flight 35%, hotel 25%
        window.overall_score = (
            window.weather_score * 0.40 +
            window.flight_score * 0.35 +
            window.hotel_score * 0.25
        )
    
    # Sort by overall score descending
    return sorted(windows, key=lambda w: w.overall_score, reverse=True)


def find_best_match(
    start_date: date,
    end_date: date,
    flights: List[FlightOption],
    hotels: List[HotelOption],
    profile: UserProfile
) -> Tuple[FlightOption, HotelOption]:
    """
    Find the best flight and hotel combination for a date range.
    
    Returns:
        (best_flight, best_hotel) tuple
    """
    # Filter flights for this date range
    valid_flights = [
        f for f in flights
        if f.departure_date >= start_date and f.departure_date <= start_date
    ]
    
    # Score and rank flights
    scored_flights = []
    for flight in valid_flights:
        score, _ = score_flight_option(flight, profile)
        scored_flights.append((score, flight))
    
    scored_flights.sort(reverse=True, key=lambda x: x[0])
    best_flight = scored_flights[0][1] if scored_flights else valid_flights[0] if valid_flights else None
    
    # Filter hotels for this date range
    valid_hotels = [
        h for h in hotels
        # Simple filter - could be more sophisticated
    ]
    
    # Score and rank hotels
    scored_hotels = []
    for hotel in valid_hotels:
        score, _ = score_hotel_option(hotel, profile)
        scored_hotels.append((score, hotel))
    
    scored_hotels.sort(reverse=True, key=lambda x: x[0])
    best_hotel = scored_hotels[0][1] if scored_hotels else valid_hotels[0] if valid_hotels else None
    
    return (best_flight, best_hotel)
