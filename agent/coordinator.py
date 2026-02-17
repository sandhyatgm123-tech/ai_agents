"""
Anthropic Claude Coordinator Agent for Maui Travel Recommendations.
This agent orchestrates the multi-stage reasoning process without containing
business logic. It delegates to MCP tools and synthesizes results.
"""

import os
import sys
from datetime import date
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import anthropic
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
from agent.prompts import (
    SYSTEM_PROMPT,
    EPISTEMIC_REFLECTION_PROMPT
)


class MauiTravelCoordinator:
    """
    Coordinator agent using Anthropic Claude.
    
    Orchestrates the 6-stage recommendation process:
    1. Epistemic Reflection
    2. User Profile Retrieval
    3. Weather Analysis
    4. Flight Search
    5. Hotel Evaluation
    6. Synthesis & Recommendation
    """
    
    def __init__(self, api_key: str, model_name: str = "claude-sonnet-4-20250514"):
        """
        Initialize the coordinator.
        
        Args:
            api_key: Anthropic API key
            model_name: Claude model to use
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model_name = model_name
        
        # Track conversation state
        self.conversation_history = []
        self.collected_data = {}
        
    def process_query(self, user_query: str, profile_override: dict = None) -> str:
        """
        Process user query through the full recommendation pipeline.

        Args:
            user_query: User's travel question
            profile_override: Optional profile from UI (must have 'raw_profile' and optionally 'origin')

        Returns:
            Final recommendation text
        """
        self._profile_override = profile_override
        print("\n" + "="*80)
        print("MAUI TRAVEL ADVISOR")
        print("="*80)

        # Stage 1: Epistemic Reflection
        reflection = self._stage_1_reflect(user_query)
        #print(reflection)

        # Stage 2: User Profile Retrieval (from UI override or default)
        profile = self._stage_2_get_profile()
        print(f"Retrieved profile for user with preferences:")
        print(f"  • Temperature: {profile['raw_profile']['preferred_temp_min']}-{profile['raw_profile']['preferred_temp_max']}°F")
        print(f"  • Budget: Flights ${profile['raw_profile']['flight_budget_soft']}-${profile['raw_profile']['flight_budget_hard']}")
        print(f"  • Hotels: ${profile['raw_profile']['hotel_budget_min']}-${profile['raw_profile']['hotel_budget_max']}/night")
        print(f"  • Trip: {profile['raw_profile']['trip_length']}")
        print(f"  • Loyalty: {profile['raw_profile']['hotel_loyalty']}")
        
        # Stage 3: Weather Analysis
        print("\nSTAGE 3: Weather Analysis")
        weather = self._stage_3_get_weather()
        print(f"30-day forecast retrieved:")
        print(f"  • Storm periods: {len(weather['storm_periods'])}")
        print(f"  • Storm days: {weather['summary']['storm_days']}/{weather['summary']['total_days']}")
        print(f"  • Sunny days: {weather['summary']['sunny_days']}/{weather['summary']['total_days']}")
        print(f"  • Temp range: {weather['summary']['temp_range']}")
        if weather['storm_periods']:
            for period in weather['storm_periods']:
                print(f"{period['warning']}")
        
        # Stage 4: Flight Search
        print("\nSTAGE 4: Flight Search")
        flights = self._stage_4_search_flights(profile, weather)
        print(f"Flight search completed:")
        print(f"  • Options found: {flights['summary']['total_options']}")
        print(f"  • Price range: {flights['summary']['price_range']}")
        print(f"  • Nonstop available: {flights['summary']['nonstop_available']}")
        print(f"  • Average price: ${flights['summary']['average_price']:.0f}")
        
        # Stage 5: Hotel Evaluation
        print("\nSTAGE 5: Hotel Evaluation")
        print("-" * 80)
        hotels = self._stage_5_search_hotels(profile, weather, flights)
        print(f"Hotel search completed:")
        print(f"  • Options found: {hotels['summary']['total_options']}")
        print(f"  • Rate range: {hotels['summary']['nightly_rate_range']}")
        print(f"  • Avg rating: {hotels['summary']['avg_rating']:.1f}/5.0")
        print(f"  • Loyalty programs: {', '.join(hotels['summary']['loyalty_programs_available'])}")
        if hotels['storm_warning']['active']:
            print(f"{hotels['storm_warning']['message']}")
        
        # Stage 6: Synthesis
        print("\nSTAGE 6: Synthesis & Recommendation")
        print("-" * 80)
        recommendation = self._stage_6_synthesize(profile, weather, flights, hotels)
        
        print("\n" + "="*80)
        print("FINAL RECOMMENDATION")
        print("="*80)
        print(recommendation)
        
        return recommendation
    
    def _stage_1_reflect(self, query: str) -> str:
        """
        Stage 1: Recognize that the question is underspecified.
        
        The agent must explicitly identify missing information before
        consulting external data.
        """
        message = self.client.messages.create(
            model=self.model_name,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": EPISTEMIC_REFLECTION_PROMPT.format(user_query=query)
                }
            ]
        )
        
        reflection = message.content[0].text
        
        # The agent should recognize missing dimensions like:
        # - Weather preferences
        # - Budget constraints
        # - Travel flexibility
        # - Trip duration
        # etc.
        
        return reflection
    
    def _stage_2_get_profile(self) -> dict:
        """
        Stage 2: Retrieve user profile (from UI override or default).
        """
        if getattr(self, "_profile_override", None) is not None:
            profile = self._profile_override
        else:
            from tools.mcp_server import get_user_profile
            profile = get_user_profile("default")
        self.collected_data["profile"] = profile
        return profile
    
    def _stage_3_get_weather(self) -> dict:
        """
        Stage 3: Get weather forecast conditioned on user preferences.
        Checks 30-day forecast and flags storm periods.
        """
        # Simulate MCP tool call
        from tools.weather_mcp_server import get_real_weather_data
        weather = get_real_weather_data("Maui,Hawaii")
        
        self.collected_data['weather'] = weather
        return weather
    
    def _stage_4_search_flights(self, profile: dict, weather: dict) -> dict:
        from datetime import date, timedelta
        """
        Stage 4: Search flights based on profile and weather windows.
        
        Identifies viable travel windows and searches for flights.
        """
        # Determine search window based on weather and flexibility
        profile_raw = profile['raw_profile']
        
        # Get trip duration
        trip_mapping = {
            "3-5 days": 4,
            "6-9 days": 7,
            "10-14 days": 12,
            "15+ days": 17,
        }
        trip_days = trip_mapping.get(profile_raw['trip_length'], 7)
        
        # Search starting from today for 30 days
        today = date.today()
        end_date = today + timedelta(days=30)
        
        origin = profile.get("origin", "SFO")
        if not origin or len(origin) != 3:
            origin = "SFO"
        from tools.mcp_server import search_flights
        flights = search_flights(
            origin=origin,
            destination="OGG",
            departure_start=today.isoformat(),
            departure_end=end_date.isoformat(),
            trip_duration_days=trip_days,
            flight_budget_soft=profile_raw.get("flight_budget_soft"),
            flight_budget_hard=profile_raw.get("flight_budget_hard"),
        )
        
        self.collected_data['flights'] = flights
        return flights
    
    def _stage_5_search_hotels(self, profile: dict, weather: dict, flights: dict) -> dict:
        """
        Stage 5: Evaluate hotel options.
        
        Searches hotels for viable date ranges and evaluates against
        budget, loyalty, and quality preferences.
        """
        profile_raw = profile['raw_profile']
        
        # Use dates from best flight option
        if flights['options']:
            best_flight = flights['options'][0]  # Simplified
            check_in = best_flight['departure_date']
            check_out = best_flight['return_date']
        else:
            # Fallback
            today = date.today()
            check_in = today.isoformat()
            check_out = (today.replace(day=today.day + 7)).isoformat()
        
        # Simulate MCP tool call
        from tools.mcp_server import search_hotels
        hotels = search_hotels(
            destination="Maui, Hawaii",
            check_in=check_in,
            check_out=check_out,
            budget_min=profile_raw['hotel_budget_min'],
            budget_max=profile_raw['hotel_budget_max']
        )
        
        self.collected_data['hotels'] = hotels
        return hotels
    
    def _stage_6_synthesize(
        self,
        profile: dict,
        weather: dict,
        flights: dict,
        hotels: dict
    ) -> str:
        """
        Stage 6: Synthesize all data into final recommendation.
        Uses core business logic to generate personalized recommendation
        with reasoning.
        """
        # Convert tool outputs to core models
        profile_obj = self._dict_to_profile(profile['raw_profile'])
        weather_obj = self._dict_to_weather(weather)
        flights_obj = self._dict_to_flights(flights)
        hotels_obj = self._dict_to_hotels(hotels)
        
        # Use core synthesis logic
        recommendation = synthesize_recommendation(
            weather_obj,
            flights_obj,
            hotels_obj,
            profile_obj
        )
        
        # Format for user
        return recommendation.format_recommendation()
    
    # Helper methods to convert dicts to core models
    
    def _dict_to_profile(self, profile_dict: dict) -> UserProfile:
        """Convert dict to UserProfile"""
        return UserProfile(
            preferred_temp_min=profile_dict['preferred_temp_min'],
            preferred_temp_max=profile_dict['preferred_temp_max'],
            rain_tolerance=profile_dict['rain_tolerance'],
            flight_budget_soft=profile_dict['flight_budget_soft'],
            flight_budget_hard=profile_dict['flight_budget_hard'],
            hotel_budget_min=profile_dict['hotel_budget_min'],
            hotel_budget_max=profile_dict['hotel_budget_max'],
            trip_length=TripLength.MEDIUM,  # Parse from string
            flexibility_days=profile_dict['flexibility_days'],
            hotel_loyalty=LoyaltyProgram.MARRIOTT,  # Parse from string
            safety_priority=profile_dict['safety_priority'],
            comfort_priority=profile_dict['comfort_priority'],
            can_take_red_eye=profile_dict['can_take_red_eye'],
            prefers_weekday_departure=profile_dict['prefers_weekday_departure']
        )
    
    def _dict_to_weather(self, weather_dict: dict) -> WeatherForecast:
        """Convert dict to WeatherForecast"""
        forecast_days = []
        for day_dict in weather_dict['forecast']:
            day = WeatherDay(
                date=date.fromisoformat(day_dict['date']),
                temp_high=day_dict['temp_high'],
                temp_low=day_dict['temp_low'],
                precipitation_chance=day_dict['precipitation_chance'],
                storm_risk=day_dict['storm_risk'],
                conditions=day_dict['conditions']
            )
            forecast_days.append(day)
        
        storm_periods = []
        for period in weather_dict['storm_periods']:
            start = date.fromisoformat(period['start'])
            end = date.fromisoformat(period['end'])
            storm_periods.append((start, end))
        
        return WeatherForecast(
            location=weather_dict['location'],
            forecast_days=forecast_days,
            storm_periods=storm_periods
        )
    
    def _dict_to_flights(self, flights_dict: dict) -> FlightSearchResult:
        """Convert dict to FlightSearchResult"""
        options = []
        for opt_dict in flights_dict['options']:
            opt = FlightOption(
                departure_date=date.fromisoformat(opt_dict['departure_date']),
                return_date=date.fromisoformat(opt_dict['return_date']),
                departure_time=opt_dict['departure_time'],
                return_time=opt_dict['return_time'],
                price=opt_dict['price'],
                airline=opt_dict['airline'],
                stops=opt_dict['stops'],
                duration_hours=opt_dict['duration_hours'],
                is_red_eye_outbound=opt_dict['is_red_eye_outbound'],
                is_red_eye_return=opt_dict['is_red_eye_return'],
                departure_day_of_week=opt_dict['departure_day_of_week']
            )
            options.append(opt)
        
        return FlightSearchResult(
            origin=flights_dict['origin'],
            destination=flights_dict['destination'],
            search_date=date.today(),
            options=options
        )
    
    def _dict_to_hotels(self, hotels_dict: dict) -> HotelSearchResult:
        """Convert dict to HotelSearchResult"""
        options = []
        for opt_dict in hotels_dict['options']:
            loyalty = None
            if opt_dict.get('loyalty_program'):
                loyalty_map = {
                    'marriott_bonvoy': LoyaltyProgram.MARRIOTT,
                    'hilton_honors': LoyaltyProgram.HILTON,
                    'ihg_rewards': LoyaltyProgram.IHG,
                    'world_of_hyatt': LoyaltyProgram.HYATT,
                }
                loyalty = loyalty_map.get(opt_dict['loyalty_program'])
            
            opt = HotelOption(
                name=opt_dict['name'],
                brand=opt_dict['brand'],
                nightly_rate=opt_dict['nightly_rate'],
                total_nights=opt_dict['total_nights'],
                total_cost=opt_dict['total_cost'],
                loyalty_program=loyalty,
                star_rating=opt_dict['star_rating'],
                guest_rating=opt_dict['guest_rating'],
                amenities=opt_dict['amenities'],
                distance_to_beach=opt_dict['distance_to_beach'],
                cancellation_policy=opt_dict['cancellation_policy'],
                is_storm_discount=opt_dict['is_storm_discount']
            )
            options.append(opt)
        
        return HotelSearchResult(
            destination=hotels_dict['destination'],
            check_in=date.fromisoformat(hotels_dict['check_in']),
            check_out=date.fromisoformat(hotels_dict['check_out']),
            options=options
        )


def main():
    """Run the coordinator agent"""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        print("Get your API key from: https://console.anthropic.com/")
        return
    
    coordinator = MauiTravelCoordinator(api_key)
    
    # Process the canonical query
    user_query = "Is it a good time to go to Maui?"
    
    result = coordinator.process_query(user_query)


if __name__ == "__main__":
    main()
