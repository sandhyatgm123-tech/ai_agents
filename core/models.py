"""
Core data models for travel recommendation system.

This module contains pure Python dataclasses with no external dependencies.
Can be imported in a Python REPL without internet access.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Optional, Tuple
from enum import Enum


class TripLength(Enum):
    """Preferred trip duration"""
    SHORT = "3-5 days"
    MEDIUM = "6-9 days"
    LONG = "10-14 days"
    EXTENDED = "15+ days"


class LoyaltyProgram(Enum):
    """Hotel loyalty programs"""
    MARRIOTT = "marriott_bonvoy"
    HILTON = "hilton_honors"
    IHG = "ihg_rewards"
    HYATT = "world_of_hyatt"
    NONE = "none"


@dataclass
class UserProfile:
    """User travel preferences and constraints"""
    
    # Weather preferences
    preferred_temp_min: int  # Fahrenheit
    preferred_temp_max: int  # Fahrenheit
    rain_tolerance: str  # "low", "medium", "high"
    
    # Budget constraints
    flight_budget_soft: int  # USD - preferred max
    flight_budget_hard: int  # USD - absolute max
    hotel_budget_min: int  # USD per night
    hotel_budget_max: int  # USD per night
    
    # Trip preferences
    trip_length: TripLength
    flexibility_days: int  # How many days can shift travel dates
    
    # Loyalty and comfort
    hotel_loyalty: LoyaltyProgram
    safety_priority: int  # 1-5 scale, 5 = highest
    comfort_priority: int  # 1-5 scale, 5 = highest
    
    # Travel constraints
    can_take_red_eye: bool
    prefers_weekday_departure: bool
    
    @classmethod
    def example(cls) -> "UserProfile":
        """Create an example profile for testing"""
        return cls(
            preferred_temp_min=72,
            preferred_temp_max=85,
            rain_tolerance="medium",
            flight_budget_soft=500,
            flight_budget_hard=750,
            hotel_budget_min=150,
            hotel_budget_max=300,
            trip_length=TripLength.MEDIUM,
            flexibility_days=3,
            hotel_loyalty=LoyaltyProgram.MARRIOTT,
            safety_priority=4,
            comfort_priority=4,
            can_take_red_eye=False,
            prefers_weekday_departure=True
        )


@dataclass
class WeatherDay:
    """Single day weather forecast"""
    date: date
    temp_high: int
    temp_low: int
    precipitation_chance: int  # 0-100
    storm_risk: bool
    conditions: str  # "sunny", "cloudy", "rainy", "stormy"


@dataclass
class WeatherForecast:
    """30-day weather forecast for destination"""
    location: str
    forecast_days: List[WeatherDay]
    storm_periods: List[Tuple[date, date]]  # List of (start, end) tuples
    
    def get_ideal_periods(self, profile: UserProfile, min_days: int = 5) -> List[Tuple[date, date]]:
        """
        Find periods matching user weather preferences.
        
        Args:
            profile: User preferences
            min_days: Minimum consecutive days needed
            
        Returns:
            List of (start_date, end_date) tuples for ideal periods
        """
        ideal_periods = []
        current_start = None
        consecutive_days = 0
        
        for day in self.forecast_days:
            # Check if day meets criteria
            temp_ok = profile.preferred_temp_min <= day.temp_high <= profile.preferred_temp_max
            
            rain_ok = True
            if profile.rain_tolerance == "low":
                rain_ok = day.precipitation_chance < 20
            elif profile.rain_tolerance == "medium":
                rain_ok = day.precipitation_chance < 40
            # high tolerance accepts any precipitation
            
            storm_ok = not day.storm_risk
            
            if temp_ok and rain_ok and storm_ok:
                if current_start is None:
                    current_start = day.date
                consecutive_days += 1
            else:
                if current_start and consecutive_days >= min_days:
                    end_date = self.forecast_days[self.forecast_days.index(day) - 1].date
                    ideal_periods.append((current_start, end_date))
                current_start = None
                consecutive_days = 0
        
        # Check final period
        if current_start and consecutive_days >= min_days:
            ideal_periods.append((current_start, self.forecast_days[-1].date))
        
        return ideal_periods


@dataclass
class FlightOption:
    """Single flight itinerary option"""
    departure_date: date
    return_date: date
    departure_time: str
    return_time: str
    price: int  # USD
    airline: str
    stops: int
    duration_hours: float
    is_red_eye_outbound: bool
    is_red_eye_return: bool
    departure_day_of_week: str
    
    def is_within_budget(self, soft: int, hard: int) -> Tuple[bool, str]:
        """
        Check if flight is within budget.
        
        Returns:
            (is_affordable, tier) where tier is "great", "acceptable", or "too_expensive"
        """
        if self.price <= soft:
            return (True, "great")
        elif self.price <= hard:
            return (True, "acceptable")
        else:
            return (False, "too_expensive")


@dataclass
class FlightSearchResult:
    """Collection of flight options"""
    origin: str
    destination: str
    search_date: date
    options: List[FlightOption]
    
    def filter_by_profile(self, profile: UserProfile) -> List[FlightOption]:
        """Filter flights based on user preferences"""
        filtered = []
        
        for flight in self.options:
            # Budget check
            affordable, _ = flight.is_within_budget(
                profile.flight_budget_soft,
                profile.flight_budget_hard
            )
            if not affordable:
                continue
            
            # Red-eye preference
            if not profile.can_take_red_eye:
                if flight.is_red_eye_outbound or flight.is_red_eye_return:
                    continue
            
            # Weekday preference (allow some flexibility)
            if profile.prefers_weekday_departure:
                if flight.departure_day_of_week in ["Saturday", "Sunday"]:
                    # Still include but will rank lower
                    pass
            
            filtered.append(flight)
        
        return filtered


@dataclass
class HotelOption:
    """Single hotel option"""
    name: str
    brand: str
    nightly_rate: int  # USD
    total_nights: int
    total_cost: int
    loyalty_program: Optional[LoyaltyProgram]
    star_rating: float
    guest_rating: float  # Out of 5
    amenities: List[str]
    distance_to_beach: float  # miles
    cancellation_policy: str
    is_storm_discount: bool  # Flag if price is low due to storm period
    
    def matches_budget(self, min_rate: int, max_rate: int) -> bool:
        """Check if hotel is within nightly budget"""
        return min_rate <= self.nightly_rate <= max_rate
    
    def has_loyalty_match(self, program: LoyaltyProgram) -> bool:
        """Check if hotel matches user's loyalty program"""
        return self.loyalty_program == program


@dataclass
class HotelSearchResult:
    """Collection of hotel options"""
    destination: str
    check_in: date
    check_out: date
    options: List[HotelOption]
    
    def filter_by_profile(self, profile: UserProfile) -> List[HotelOption]:
        """Filter hotels based on user preferences"""
        filtered = []
        
        for hotel in self.options:
            # Budget check
            if not hotel.matches_budget(
                profile.hotel_budget_min,
                profile.hotel_budget_max
            ):
                continue
            
            # Safety check (assuming higher star rating = safer)
            if profile.safety_priority >= 4:
                if hotel.star_rating < 3.5:
                    continue
            
            # Comfort check
            if profile.comfort_priority >= 4:
                if hotel.guest_rating < 4.0:
                    continue
            
            filtered.append(hotel)
        
        return filtered


@dataclass
class TravelWindow:
    """Represents a potential travel window with scores"""
    start_date: date
    end_date: date
    weather_score: float  # 0-100
    flight_score: float  # 0-100
    hotel_score: float  # 0-100
    overall_score: float  # 0-100
    
    flight_option: Optional[FlightOption] = None
    hotel_option: Optional[HotelOption] = None
    weather_summary: str = ""
    
    def duration_days(self) -> int:
        """Calculate trip duration in days"""
        return (self.end_date - self.start_date).days


@dataclass
class TravelRecommendation:
    """Final personalized travel recommendation"""
    recommended_window: TravelWindow
    alternatives: List[TravelWindow]
    
    reasoning: str
    why_not_rejected: str
    
    profile_used: UserProfile
    generated_at: datetime = field(default_factory=datetime.now)
    
    def format_recommendation(self) -> str:
        """Format recommendation as human-readable text"""
        rec = self.recommended_window
        
        output = f"""
🌴 PERSONALIZED MAUI TRAVEL RECOMMENDATION 🌴

RECOMMENDED TRAVEL WINDOW:
{rec.start_date.strftime('%B %d')} - {rec.end_date.strftime('%B %d, %Y')} ({rec.duration_days()} days)
Overall Score: {rec.overall_score:.1f}/100

WEATHER:
{rec.weather_summary}

FLIGHT:
{rec.flight_option.airline + ' $' + str(rec.flight_option.price) + ' - ' + rec.flight_option.departure_time + ' ' + str(rec.flight_option.stops) + ' stop(s)' if rec.flight_option else 'No flights within your budget for this window'}

LODGING:
{rec.hotel_option.name if rec.hotel_option else 'TBD'}
${rec.hotel_option.nightly_rate if rec.hotel_option else 'TBD'}/night - {rec.hotel_option.star_rating if rec.hotel_option else 'N/A'} stars

WHY THIS WINDOW:
{self.reasoning}

ALTERNATIVES CONSIDERED:
"""
        
        for alt in self.alternatives[:2]:
            output += f"\n• {alt.start_date.strftime('%b %d')} - {alt.end_date.strftime('%b %d')}: "
            output += f"Score {alt.overall_score:.1f}/100 - {alt.weather_summary[:100]}"
        
        output += f"\n\nWHY NOT OTHER PERIODS:\n{self.why_not_rejected}"
        
        return output
