"""Survey configuration for manufactured housing property surveys."""

from pydantic import BaseModel, Field
from typing import Optional


class PropertySurveyData(BaseModel):
    """Data collected from a manufactured housing property survey."""

    property_name: Optional[str] = None
    contact_name: Optional[str] = None
    contact_title: Optional[str] = None

    # Lot information
    total_lots: Optional[int] = None
    occupied_lots: Optional[int] = None
    occupancy_rate: Optional[float] = None

    # Rent information
    lot_rent_min: Optional[float] = None
    lot_rent_max: Optional[float] = None
    lot_rent_average: Optional[float] = None

    # Utilities & fees
    utilities_included: Optional[str] = None
    additional_fees: Optional[str] = None
    water_sewer_cost: Optional[str] = None
    trash_cost: Optional[str] = None

    # Community details
    pet_policy: Optional[str] = None
    age_restriction: Optional[str] = None
    home_sales_on_site: Optional[bool] = None
    rent_increase_history: Optional[str] = None

    # Market info
    waitlist: Optional[bool] = None
    recent_rent_increase: Optional[str] = None

    # Notes
    notes: Optional[str] = None


SYSTEM_PROMPT = """You are a professional property surveyor conducting a phone survey \
of manufactured housing communities (mobile home parks). Your name is Sarah and you \
work for a real estate research firm.

Your goal is to collect the following information through natural conversation:

1. **Lot rent** - What is the current monthly lot rent? Is there a range?
2. **Occupancy** - How many total lots? How many are occupied?
3. **Utilities** - What utilities are included in lot rent? What do residents pay separately?
4. **Additional fees** - Any admin fees, pet fees, or other charges?
5. **Pet policy** - Are pets allowed? Any restrictions?
6. **Age restrictions** - Is this an all-ages or 55+ community?
7. **Home sales** - Does the community sell homes on-site?
8. **Rent increases** - Any recent or planned rent increases?
9. **Waitlist** - Is there a waitlist for lots?

Guidelines:
- Be polite, professional, and conversational
- Ask one or two questions at a time, don't overwhelm
- If they seem busy, offer to call back
- Thank them for their time
- If they ask why you're calling, explain you're conducting market research on \
manufactured housing communities in the area
- Confirm information if it seems unusual
- Keep responses concise - this is a phone call, not an email

Start by introducing yourself and asking to speak with the community manager or \
someone who can help with general community information."""


SURVEY_QUESTIONS = [
    {
        "topic": "introduction",
        "question": "Hi, this is Sarah calling from a real estate research firm. "
        "I'm conducting a brief survey of manufactured housing communities in your area. "
        "Could I speak with the community manager or someone who handles leasing?",
        "required_data": [],
    },
    {
        "topic": "lot_rent",
        "question": "Could you tell me what the current monthly lot rent is?",
        "required_data": ["lot_rent_min", "lot_rent_max"],
    },
    {
        "topic": "occupancy",
        "question": "How many lots does the community have, and roughly how many are occupied?",
        "required_data": ["total_lots", "occupied_lots"],
    },
    {
        "topic": "utilities",
        "question": "What utilities are included in the lot rent?",
        "required_data": ["utilities_included"],
    },
    {
        "topic": "fees",
        "question": "Are there any additional monthly fees beyond lot rent?",
        "required_data": ["additional_fees"],
    },
    {
        "topic": "pet_policy",
        "question": "What is the community's pet policy?",
        "required_data": ["pet_policy"],
    },
    {
        "topic": "age_restriction",
        "question": "Is this an all-ages community or is there an age restriction?",
        "required_data": ["age_restriction"],
    },
    {
        "topic": "home_sales",
        "question": "Does the community sell manufactured homes on-site?",
        "required_data": ["home_sales_on_site"],
    },
    {
        "topic": "rent_increases",
        "question": "Have there been any recent rent increases, or are any planned?",
        "required_data": ["recent_rent_increase"],
    },
    {
        "topic": "waitlist",
        "question": "Is there currently a waitlist for available lots?",
        "required_data": ["waitlist"],
    },
    {
        "topic": "closing",
        "question": "Thank you so much for your time. This information is really helpful.",
        "required_data": [],
    },
]
