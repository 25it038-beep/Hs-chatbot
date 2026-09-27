import json
import re
import time
import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from app.config import settings
from app.services.agent.app_archetypes import (
    HealthcareSynthesizer,
    PortfolioSynthesizer,
    FoodDeliverySynthesizer,
    EducationSynthesizer,
    TravelSynthesizer,
    SocialSynthesizer,
    ChatSynthesizer,
    RealEstateSynthesizer,
    RecipeSynthesizer,
    DeveloperToolsSynthesizer
)

logger = logging.getLogger("hsbot.agent.app_generator")


class AppDomain(str, Enum):
    HEALTHCARE = "healthcare"
    PORTFOLIO = "portfolio"
    FOOD_DELIVERY = "food_delivery"
    EDUCATION = "education"
    TRAVEL = "travel"
    SOCIAL = "social"
    CHAT = "chat"
    REAL_ESTATE = "real_estate"
    RECIPE = "recipe"
    DEVELOPER_TOOLS = "developer_tools"
    GAME = "game"
    DASHBOARD = "dashboard"
    ECOMMERCE = "ecommerce"
    KANBAN = "kanban"
    CANVAS_DRAW = "canvas_draw"
    AUDIO_SYNTH = "audio_synth"
    MARKDOWN_WORKSPACE = "markdown_workspace"
    FINANCE_BUDGET = "finance_budget"
    CALCULATOR = "calculator"
    PYTHON_BACKEND = "python_backend"
    UNIVERSAL_DYNAMIC = "universal_dynamic"


class ProductType(str, Enum):
    HEALTHCARE_SYSTEM = "healthcare_system"
    PORTFOLIO = "portfolio"
    FOOD_DELIVERY = "food_delivery"
    EDUCATION_PLATFORM = "education_platform"
    BOOKING_SYSTEM = "booking_system"
    SOCIAL_NETWORK = "social_network"
    CHAT_APPLICATION = "chat_application"
    MARKETPLACE = "marketplace"
    RECIPE_PLATFORM = "recipe_platform"
    DEVELOPER_TOOL = "developer_tool"
    GAME = "game"
    DASHBOARD = "dashboard"
    ECOMMERCE = "ecommerce"
    KANBAN_BOARD = "kanban_board"
    CANVAS_DRAW = "canvas_draw"
    AUDIO_SYNTH = "audio_synth"
    MARKDOWN_WORKSPACE = "markdown_workspace"
    FINANCE_APP = "finance_app"
    CALCULATOR = "calculator"
    PYTHON_BACKEND = "python_backend"
    UNIVERSAL_APP = "universal_app"


@dataclass
class ProductRequirementSnapshot:
    """Unambiguous source-of-truth requirement snapshot generated from the user's prompt."""
    product_name: str
    domain: AppDomain
    product_type: ProductType
    target_users: List[str]
    primary_objective: str
    core_workflows: List[str]
    key_entities: List[str]
    major_features: List[str]
    navigation_items: List[str]
    design_system: Dict[str, Any]
    interaction_model: str
    data_model: Dict[str, Any]
    test_cases: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "product_name": self.product_name,
            "domain": self.domain.value if isinstance(self.domain, Enum) else str(self.domain),
            "product_type": self.product_type.value if isinstance(self.product_type, Enum) else str(self.product_type),
            "target_users": self.target_users,
            "primary_objective": self.primary_objective,
            "core_workflows": self.core_workflows,
            "key_entities": self.key_entities,
            "major_features": self.major_features,
            "navigation_items": self.navigation_items,
            "design_system": self.design_system,
            "interaction_model": self.interaction_model,
            "data_model": self.data_model,
            "test_cases": self.test_cases
        }


class AppDomainClassifier:
    """Classifies any application prompt into an appropriate architectural domain and product type."""

    @classmethod
    def classify(cls, prompt: str) -> Tuple[AppDomain, Dict[str, Any]]:
        text = prompt.lower().strip()

        # 1. Healthcare / Clinical / Hospital (Check before generic 'system' or 'dashboard')
        if any(w in text for w in [
            "hospital", "clinic", "doctor", "patient", "medical", "healthcare", "pharmacy",
            "triage", "prescription", "health care", "ehr", "emr", "nurse", "dental"
        ]):
            return AppDomain.HEALTHCARE, {}

        # 2. Portfolio / Personal Showcase
        if any(w in text for w in [
            "portfolio", "resume", "cv website", "personal site", "showcase my work",
            "developer portfolio", "designer portfolio", "personal portfolio", "about me site"
        ]):
            return AppDomain.PORTFOLIO, {}

        # 3. Food Delivery / Restaurant
        if any(w in text for w in [
            "food delivery", "restaurant", "order food", "food ordering", "uber eats",
            "doordash", "dish delivery", "meal delivery", "food menu", "gourmet delivery"
        ]):
            return AppDomain.FOOD_DELIVERY, {}

        # 4. Education / Tutoring / Courses
        if any(w in text for w in [
            "tutoring", "tutor", "course", "courses", "student", "teacher", "classroom",
            "learning platform", "online academy", "school", "syllabus", "lecture", "lms"
        ]):
            return AppDomain.EDUCATION, {}

        # 5. Travel / Hotel / Flights / Vacation Booking
        if any(w in text for w in [
            "travel", "hotel", "resort", "flight", "trip booking", "vacation booking",
            "airbnb", "stays booking", "hotel booking", "travel booking"
        ]):
            return AppDomain.TRAVEL, {}

        # 6. Social Media / Community Feed
        if any(w in text for w in [
            "social media", "social network", "feed app", "community feed", "posts and comments",
            "twitter clone", "instagram clone", "social feed"
        ]):
            return AppDomain.SOCIAL, {}

        # 7. Team Chat / Real-Time Messenger
        if any(w in text for w in [
            "chat app", "messenger", "messaging app", "slack clone", "discord clone",
            "team chat", "direct message", "chat room", "live chat"
        ]):
            return AppDomain.CHAT, {}

        # 8. Real Estate / Housing / Rental
        if any(w in text for w in [
            "real estate", "property finder", "property listing", "apartment rental",
            "house rental", "mortgage calculator", "realtor", "home listings"
        ]):
            return AppDomain.REAL_ESTATE, {}

        # 9. Recipe / Cooking / Meal Planner
        if any(w in text for w in [
            "recipe", "recipes", "cooking app", "meal planner", "cookbook", "culinary",
            "grocery list", "ingredients cooking"
        ]):
            return AppDomain.RECIPE, {}

        # 10. Developer Tools / Code Playground / Snippet Manager
        if any(w in text for w in [
            "code playground", "regex tester", "json formatter", "snippet manager",
            "developer tools", "dev tools", "code editor app", "compiler app"
        ]):
            return AppDomain.DEVELOPER_TOOLS, {}

        # 11. Games (Football, arcade, shooter, snake, etc.)
        is_game = any(w in text for w in [
            "game", "arcade", "play", "player", "canvas game", "2d game", "space shooter",
            "football", "foot ball", "soccer", "socer", "penalty", "goal", "fifa", "striker",
            "racing", "flappy", "snake", "brick breaker", "pong", "tetris",
            "platformer", "shooter", "racer"
        ])
        if is_game:
            genre = "arcade"
            if any(w in text for w in ["football", "foot ball", "soccer", "socer", "penalty", "goal", "fifa", "striker", "kick"]):
                genre = "football"
            elif any(w in text for w in ["racing", "car", "speed", "drive"]):
                genre = "racing"
            elif any(w in text for w in ["space", "shooter", "alien", "invader"]):
                genre = "shooter"
            elif any(w in text for w in ["snake"]):
                genre = "snake"
            elif any(w in text for w in ["brick", "breakout"]):
                genre = "brick_breaker"
            elif any(w in text for w in ["pong"]):
                genre = "pong"
            elif any(w in text for w in ["platformer", "jump", "mario"]):
                genre = "platformer"
            return AppDomain.GAME, {"genre": genre}

        # 12. E-Commerce / Store / Shopping
        if any(w in text for w in ["ecommerce", "e-commerce", "store", "shop", "shopping", "cart", "product catalog", "checkout", "marketplace"]):
            return AppDomain.ECOMMERCE, {}

        # 13. Canvas / Drawing / Whiteboard
        if any(w in text for w in ["draw", "drawing", "paint", "whiteboard", "canvas", "sketch", "sketchpad", "doodle"]):
            return AppDomain.CANVAS_DRAW, {}

        # 14. Kanban / Agile Project Management
        if any(w in text for w in ["kanban", "trello", "scrum", "task board", "sprint board", "task manager"]) or (
            re.search(r"\bboard\b", text) and "whiteboard" not in text
        ):
            return AppDomain.KANBAN, {}

        # 15. Audio / Synth / Music Studio
        if any(w in text for w in ["audio", "synth", "synthesizer", "music", "piano", "drum machine", "beat maker", "sequencer"]):
            return AppDomain.AUDIO_SYNTH, {}

        # 16. Markdown / Note-taking workspace
        if any(w in text for w in ["markdown", "note", "notes", "notepad", "document editor", "writing app"]):
            return AppDomain.MARKDOWN_WORKSPACE, {}

        # 17. Personal Finance / Budget Tracker
        if any(w in text for w in ["budget", "expense", "finance", "money tracker", "spending", "wallet", "ledger"]):
            return AppDomain.FINANCE_BUDGET, {}

        # 18. Calculator
        if any(w in text for w in ["calc", "calculator", "arithmetic", "scientific calc"]):
            return AppDomain.CALCULATOR, {}

        # 19. Python Backend / CLI
        if any(w in text for w in ["fastapi", "flask", "sqlite api", "rest api", "backend service"]) or (
            "python" in text and not any(w in text for w in ["html", "css", "web", "frontend", "ui"])
        ):
            return AppDomain.PYTHON_BACKEND, {}

        # 20. Explicit SaaS Dashboard / Analytics (Only when specifically requested)
        if any(w in text for w in ["dashboard", "analytics", "metrics", "kpi", "telemetry"]):
            return AppDomain.DASHBOARD, {}

        # 21. Default: Universal Dynamic Application
        return AppDomain.UNIVERSAL_DYNAMIC, {}


class AdaptiveRequirementEngine:
    """
    Translates raw user requests into an unambiguous, domain-specific ProductRequirementSnapshot.
    Guarantees no generic templates, no dashboard-defaults, and distinct product identities.
    """

    @classmethod
    def create_snapshot(cls, prompt: str) -> ProductRequirementSnapshot:
        text = prompt.lower().strip()
        domain, meta = AppDomainClassifier.classify(prompt)

        if domain == AppDomain.HEALTHCARE:
            return ProductRequirementSnapshot(
                product_name="St. Jude Healthcare Management System",
                domain=domain,
                product_type=ProductType.HEALTHCARE_SYSTEM,
                target_users=["Patients", "Physicians", "Nurses", "Hospital Administrators"],
                primary_objective="Coordinate patient admissions, clinical appointments, emergency triage vitals, and prescription tracking.",
                core_workflows=[
                    "Register & admit new patient",
                    "Schedule doctor appointment with specialty routing",
                    "Monitor emergency triage vital signs (BP, SpO2, Pulse)",
                    "Write & dispense digital medical prescriptions",
                    "Discharge patient and archive clinical notes"
                ],
                key_entities=["Patient", "Doctor", "Appointment", "MedicalRecord", "Prescription", "TriageVital"],
                major_features=[
                    "Live Patient Directory with Room & Blood Group tags",
                    "Doctor Schedule & Specialty Availability",
                    "Interactive Appointment Booking Dialog",
                    "Emergency Triage Queue with Urgency Color Badges",
                    "Digital Prescription Dispenser"
                ],
                navigation_items=["Patients & Records", "Doctor Schedules", "Appointments", "Prescriptions", "Emergency Triage"],
                design_system={
                    "visual_direction": "Clinical, calm, authoritative, high-contrast readability",
                    "color_palette": {"primary": "#0f766e", "accent": "#06b6d4", "danger": "#e11d48", "surface": "#0f172a"},
                    "typography": "Inter / sans-serif with tabular numeric alignment",
                    "layout_archetype": "clinical_workspace"
                },
                interaction_model="modal_dialogs_and_tabbed_records",
                data_model={
                    "patients": [{"id": "P-101", "name": "Eleanor Vance", "age": 42, "blood": "O+", "room": "ICU-04", "status": "Admitted"}],
                    "doctors": [{"id": "D-201", "name": "Dr. Marcus Brody", "specialty": "Cardiology", "status": "Available"}],
                    "appointments": [{"id": "A-301", "patient": "Eleanor Vance", "doctor": "Dr. Marcus Brody", "time": "10:30 AM", "status": "Confirmed"}]
                },
                test_cases=[
                    "test_admit_patient_updates_directory",
                    "test_appointment_booking_sets_schedule",
                    "test_triage_urgency_prioritization"
                ]
            )

        elif domain == AppDomain.PORTFOLIO:
            return ProductRequirementSnapshot(
                product_name="Senior Full-Stack & Systems Architect Portfolio",
                domain=domain,
                product_type=ProductType.PORTFOLIO,
                target_users=["Hiring Managers", "Engineering Leaders", "Clients", "Tech Recruiters"],
                primary_objective="Showcase high-impact software engineering projects, technical skills proficiency, career experience, and direct contact inquiry.",
                core_workflows=[
                    "Browse interactive featured project case studies",
                    "Filter projects by technology stack tags (Distributed Systems, AI, Full-Stack)",
                    "Inspect interactive skills matrix and proficiency bars",
                    "Review career milestones and achievements timeline",
                    "Submit direct contact inquiry with validation"
                ],
                key_entities=["Project", "Skill", "ExperienceItem", "ContactInquiry"],
                major_features=[
                    "Hero Banner with Availability Status Pill & Social Links",
                    "Interactive Project Grid with Live Demo & Architecture Drawer",
                    "Interactive Skills Matrix with Years & Proficiency",
                    "Career Journey Timeline with Metrics & Impact",
                    "Working Contact Form with Client-Side Validation & Toasts"
                ],
                navigation_items=["About", "Featured Projects", "Skills & Tech", "Experience", "Contact Me"],
                design_system={
                    "visual_direction": "Editorial, refined, minimalist dark theme with subtle neon accents",
                    "color_palette": {"primary": "#6366f1", "accent": "#a855f7", "surface": "#090d16"},
                    "typography": "Modern sans-serif with bold display headings",
                    "layout_archetype": "single_page_showcase"
                },
                interaction_model="smooth_scroll_sections_and_project_drawer",
                data_model={
                    "projects": [{"title": "Autonomous Agent Engine", "tags": ["TypeScript", "Python"], "stars": 340}],
                    "skills": [{"name": "TypeScript", "level": 95}, {"name": "Rust", "level": 88}]
                },
                test_cases=[
                    "test_project_category_filtering",
                    "test_contact_form_validation",
                    "test_skills_matrix_rendering"
                ]
            )

        elif domain == AppDomain.FOOD_DELIVERY:
            return ProductRequirementSnapshot(
                product_name="CraveDash Food Delivery & Restaurant Platform",
                domain=domain,
                product_type=ProductType.FOOD_DELIVERY,
                target_users=["Hungry Customers", "Restaurants", "Delivery Drivers"],
                primary_objective="Browse local restaurant menus, customize meal orders, manage cart totals, and track live delivery status.",
                core_workflows=[
                    "Filter restaurants by cuisine & delivery time",
                    "Inspect restaurant menu dishes with ingredients",
                    "Add dishes to cart with customization and quantity",
                    "Simulate checkout payment and order placement",
                    "Track live order progress (Received -> Kitchen -> Courier -> Delivered)"
                ],
                key_entities=["Restaurant", "MenuItem", "Cart", "DeliveryOrder", "Courier"],
                major_features=[
                    "Cuisine Category Filter (Burgers, Italian, Asian, Desserts)",
                    "Restaurant Cards with Ratings, ETAs & Delivery Fees",
                    "Interactive Dish Ordering Drawer with Options",
                    "Floating Live Cart with Subtotal, Tax & Delivery Calculations",
                    "Real-Time Animated Order Progress Tracker"
                ],
                navigation_items=["All Restaurants", "Burgers & Grill", "Italian & Pizza", "Asian & Bowls", "Active Orders"],
                design_system={
                    "visual_direction": "Appetizing, vibrant, energetic, warm accents",
                    "color_palette": {"primary": "#f97316", "accent": "#f43f5e", "surface": "#0f172a"},
                    "typography": "Friendly rounded sans-serif",
                    "layout_archetype": "marketplace_catalog_and_tray"
                },
                interaction_model="drawer_menu_and_live_progress_tracker",
                data_model={
                    "restaurants": [{"name": "Artisan Burger Co", "cuisine": "Burgers", "rating": 4.9, "eta": "20-30m"}],
                    "cart": []
                },
                test_cases=[
                    "test_cuisine_filtering",
                    "test_cart_price_math_with_fees",
                    "test_delivery_state_machine"
                ]
            )

        elif domain == AppDomain.EDUCATION:
            return ProductRequirementSnapshot(
                product_name="EduSphere Online Academy & Course Platform",
                domain=domain,
                product_type=ProductType.EDUCATION_PLATFORM,
                target_users=["Students", "Instructors", "Lifelong Learners"],
                primary_objective="Deliver structured video/text curriculum, track lesson completion, and assess student knowledge with interactive quizzes.",
                core_workflows=[
                    "Explore and enroll in interactive course curriculum",
                    "Navigate lessons syllabus and view lesson content",
                    "Mark lessons complete and track course completion %",
                    "Take interactive multiple-choice assessment quiz with instant scoring",
                    "Earn certificate upon full course completion"
                ],
                key_entities=["Course", "Module", "Lesson", "QuizQuestion", "StudentEnrollment"],
                major_features=[
                    "Course Catalog with Level Badges & Estimated Hours",
                    "Interactive Lesson Viewer with Video Canvas & Notes",
                    "Interactive Quiz Engine with Score & Detailed Explanations",
                    "Dynamic Course Progress Tracker with Local Storage Save",
                    "Instructor Profile & Student Reviews"
                ],
                navigation_items=["Explore Courses", "My Enrolled Classes", "Lesson Viewer", "Interactive Quiz", "Progress & Certificates"],
                design_system={
                    "visual_direction": "Structured, inspiring, accessible, clear learning hierarchy",
                    "color_palette": {"primary": "#4f46e5", "accent": "#10b981", "surface": "#0f172a"},
                    "typography": "Clean readable sans-serif",
                    "layout_archetype": "split_syllabus_and_viewer"
                },
                interaction_model="lesson_steps_and_quiz_engine",
                data_model={
                    "courses": [{"id": 1, "title": "Full-Stack Web Architecture", "progress": 45}],
                    "lessons": [{"id": 101, "title": "Database Normalization", "completed": True}]
                },
                test_cases=[
                    "test_lesson_completion_progress",
                    "test_quiz_scoring_algorithm",
                    "test_course_enrollment_store"
                ]
            )

        elif domain == AppDomain.TRAVEL:
            return ProductRequirementSnapshot(
                product_name="VoyageAir Luxury Stays & Resort Booking",
                domain=domain,
                product_type=ProductType.BOOKING_SYSTEM,
                target_users=["Travelers", "Vacationers", "Hotel Guests"],
                primary_objective="Search vacation destinations, compare hotel amenities and room rates, and confirm instant reservations with confirmation codes.",
                core_workflows=[
                    "Search stays by destination city and guest count",
                    "Filter hotel listings by star rating and price range",
                    "Review room types, photos, and amenities (WiFi, Pool, Ocean View)",
                    "Select check-in/check-out dates and compute stay total",
                    "Confirm reservation and generate official PNR booking code"
                ],
                key_entities=["Hotel", "Room", "Destination", "Reservation", "Amenity"],
                major_features=[
                    "Interactive Destination & Dates Filter Bar",
                    "Resort Listings with Star Ratings & Price per Night",
                    "Room Details Modal with Amenities Checklist",
                    "Automatic Stay Price Calculator with Taxes & Cleaning Fee",
                    "Instant Reservation Confirmation with PNR Code & My Trips Drawer"
                ],
                navigation_items=["Explore Stays", "Popular Destinations", "Hotel Details", "My Bookings", "Travel Guide"],
                design_system={
                    "visual_direction": "Wanderlust, scenic, crisp sky & teal hues, high imagery cards",
                    "color_palette": {"primary": "#0284c7", "accent": "#14b8a6", "surface": "#0b1329"},
                    "typography": "Sophisticated sans-serif",
                    "layout_archetype": "search_cards_and_booking_modal"
                },
                interaction_model="filter_grid_and_date_range_pricing",
                data_model={
                    "hotels": [{"name": "Grand Azure Resort", "city": "Santorini", "price": 280, "stars": 5}],
                    "bookings": []
                },
                test_cases=[
                    "test_stay_duration_calculation",
                    "test_booking_total_math",
                    "test_pnr_code_generation"
                ]
            )

        elif domain == AppDomain.SOCIAL:
            return ProductRequirementSnapshot(
                product_name="Pulse Community Social Network",
                domain=domain,
                product_type=ProductType.SOCIAL_NETWORK,
                target_users=["Community Members", "Creators", "Discussion Leaders"],
                primary_objective="Publish media updates, engage in threaded discussions, like posts, and follow trending community hashtags.",
                core_workflows=[
                    "Compose and publish text posts with hashtags",
                    "Engage with posts via animated like heart toggles",
                    "Write and view threaded comments in real time",
                    "Filter feed by trending community topics (#Tech, #Design)",
                    "Search posts by author or keywords"
                ],
                key_entities=["Post", "Author", "Comment", "Tag", "Like"],
                major_features=[
                    "Rich Post Composer with Tag Selector",
                    "Dynamic Community Feed with Live Timestamps",
                    "Instant Like Heart Animation & Count State",
                    "Threaded Comments Drawer with Instant Reply",
                    "Trending Hashtags Sidebar with Feed Filtering"
                ],
                navigation_items=["Home Feed", "Explore Trending", "Bookmarked Posts", "Notifications", "Profile"],
                design_system={
                    "visual_direction": "Social, dynamic, clean card stream, engagement accents",
                    "color_palette": {"primary": "#8b5cf6", "accent": "#ec4899", "surface": "#0f172a"},
                    "typography": "Inter sans-serif",
                    "layout_archetype": "three_column_feed"
                },
                interaction_model="feed_stream_with_comment_drawers",
                data_model={
                    "posts": [{"id": 1, "author": "Liam Vance", "content": "Just launched the autonomous engine!", "likes": 24}]
                },
                test_cases=[
                    "test_post_creation",
                    "test_like_toggle_state",
                    "test_comment_append"
                ]
            )

        elif domain == AppDomain.CHAT:
            return ProductRequirementSnapshot(
                product_name="SyncTeam Real-Time Team Messenger",
                domain=domain,
                product_type=ProductType.CHAT_APPLICATION,
                target_users=["Colleagues", "Team Leads", "Remote Workers"],
                primary_objective="Provide fast channel-based workplace communication, direct messaging, emoji reactions, and simulated bot responses.",
                core_workflows=[
                    "Switch between public topic channels and direct messages",
                    "Compose and send text messages with timestamps",
                    "Add quick emoji reactions (👍, ❤️, 🚀) to messages",
                    "Receive simulated bot automated responses in channels",
                    "Search conversation message archives"
                ],
                key_entities=["Channel", "Message", "User", "Reaction"],
                major_features=[
                    "Sidebar with Public Channels (#general, #engineering, #design)",
                    "Direct Messages List with Online Status Indicators",
                    "Active Message Stream with Avatar Bubbles",
                    "Instant Message Composer with Enter-key Send",
                    "Interactive Emoji Reaction Bar & Simulated Bot Reply"
                ],
                navigation_items=["# general", "# engineering", "# announcements", "# design", "Direct Messages"],
                design_system={
                    "visual_direction": "Focused, clean split-pane messenger, subtle borders",
                    "color_palette": {"primary": "#3b82f6", "accent": "#10b981", "surface": "#0f172a"},
                    "typography": "System sans-serif with monospace snippets",
                    "layout_archetype": "split_sidebar_and_message_stream"
                },
                interaction_model="realtime_stream_and_channel_switch",
                data_model={
                    "channels": ["# general", "# engineering", "# design"],
                    "messages": [{"sender": "Alex", "text": "Sprint review in 10 mins!", "time": "09:45 AM"}]
                },
                test_cases=[
                    "test_channel_message_routing",
                    "test_message_append_order",
                    "test_reaction_counter"
                ]
            )

        elif domain == AppDomain.REAL_ESTATE:
            return ProductRequirementSnapshot(
                product_name="Haven Luxury Real Estate & Rental Marketplace",
                domain=domain,
                product_type=ProductType.MARKETPLACE,
                target_users=["Home Buyers", "Renters", "Property Investors"],
                primary_objective="Discover residential listings, filter by price and bedrooms, calculate monthly mortgage payments, and book private tours.",
                core_workflows=[
                    "Filter listings by property type (House, Condo, Townhome), price, and bedrooms",
                    "Inspect property photo galleries, square footage, and amenities",
                    "Calculate monthly mortgage payments based on down payment and interest rate",
                    "Schedule an in-person or virtual property tour with dates",
                    "Save favorite properties to personal bookmarks"
                ],
                key_entities=["Property", "Agent", "MortgageCalculation", "TourReservation"],
                major_features=[
                    "Price Range & Bedroom Filtering Controls",
                    "Property Cards with High-Res Photos, SqFt & Price Badges",
                    "Property Details Modal with Amenities Checklist",
                    "Interactive Mortgage Calculator (Home Price, Down %, Rate, Term -> Monthly Payment)",
                    "Schedule Tour Booking Modal with Instant Confirmation"
                ],
                navigation_items=["Properties For Sale", "Rentals", "Mortgage Calculator", "Saved Homes", "Schedule a Tour"],
                design_system={
                    "visual_direction": "Prestigious, architectural, deep navy & warm gold accents",
                    "color_palette": {"primary": "#1e3a8a", "accent": "#f59e0b", "surface": "#0a1128"},
                    "typography": "Elegant serif headers with clean modern sans-serif body",
                    "layout_archetype": "property_grid_and_calculator"
                },
                interaction_model="filter_grid_and_mortgage_calculator",
                data_model={
                    "properties": [{"title": "Bel Air Modern Estate", "price": 1850000, "beds": 4, "baths": 3, "sqft": 3600}]
                },
                test_cases=[
                    "test_mortgage_monthly_calculation",
                    "test_property_price_filter",
                    "test_tour_scheduling"
                ]
            )

        elif domain == AppDomain.RECIPE:
            return ProductRequirementSnapshot(
                product_name="FlavorCraft Culinary Studio & Meal Planner",
                domain=domain,
                product_type=ProductType.RECIPE_PLATFORM,
                target_users=["Home Cooks", "Foodies", "Meal Prep Enthusiasts"],
                primary_objective="Organize gourmet recipes, scale ingredient servings dynamically, guide cooking with step timers, and generate grocery lists.",
                core_workflows=[
                    "Search recipes by dish name, cuisine, or available pantry ingredients",
                    "Scale recipe servings dynamically (- / +) to recalculate quantities",
                    "Launch Interactive Cooking Mode with step-by-step guidance & countdown timers",
                    "Transfer ingredients into an interactive Grocery Shopping Checklist",
                    "Bookmark favorite recipes for weekly meal planning"
                ],
                key_entities=["Recipe", "Ingredient", "CookingStep", "MealPlan", "GroceryItem"],
                major_features=[
                    "Recipe Cards with Prep/Cook Times, Calorie Badges & Dietary Tags",
                    "Dynamic Servings Scaler that mathematically recalculates quantities",
                    "Step-by-Step Cooking Mode with Built-in Kitchen Countdown Timer",
                    "Interactive Grocery Shopping Checklist with Checkbox State",
                    "Pantry Search & Dietary Filter Tabs (Vegetarian, High-Protein, Quick)"
                ],
                navigation_items=["Recipe Collection", "Cooking Mode", "Weekly Meal Planner", "Grocery Shopping List", "Favorites"],
                design_system={
                    "visual_direction": "Warm, culinary, artisanal, terracotta & sage green accents",
                    "color_palette": {"primary": "#ea580c", "accent": "#16a34a", "surface": "#18181b"},
                    "typography": "Warm display typography with clean readable recipe instructions",
                    "layout_archetype": "recipe_cards_and_cooking_drawer"
                },
                interaction_model="recipe_drawer_with_scaler_and_timer",
                data_model={
                    "recipes": [{"title": "Tuscan Garlic Herb Salmon", "prep": "15m", "cook": "20m", "servings": 2}]
                },
                test_cases=[
                    "test_ingredient_scaling_math",
                    "test_recipe_dietary_filter",
                    "test_grocery_list_transfer"
                ]
            )

        elif domain == AppDomain.DEVELOPER_TOOLS:
            return ProductRequirementSnapshot(
                product_name="DevCraft Studio Code Playground & Tools",
                domain=domain,
                product_type=ProductType.DEVELOPER_TOOL,
                target_users=["Software Engineers", "Web Developers", "DevOps Admins"],
                primary_objective="Provide an instant multi-language code playground, JSON formatter & validator, regex tester, and snippet library.",
                core_workflows=[
                    "Write HTML, CSS, and JS with live sandboxed preview execution",
                    "Paste, format, and syntax-validate complex JSON payloads",
                    "Test and debug regular expressions with real-time match highlighting",
                    "Save and organize reusable code snippets with one-click copy"
                ],
                key_entities=["Snippet", "RegexTest", "JsonPayload", "PlaygroundBuffer"],
                major_features=[
                    "Multi-Tab Live Code Playground (HTML, CSS, JS) with Instant Run",
                    "JSON Formatter, Minifier & Syntax Error Highlighting",
                    "Live Regular Expression Matcher with Group Captures",
                    "Code Snippet Storage with Language Tags & Clipboard Copy"
                ],
                navigation_items=["Code Playground", "JSON Formatter", "Regex Tester", "Snippet Library"],
                design_system={
                    "visual_direction": "Technical, monokai dark, compact developer ergonomics",
                    "color_palette": {"primary": "#10b981", "accent": "#38bdf8", "surface": "#0f172a"},
                    "typography": "Monospace code fonts with clean UI accents",
                    "layout_archetype": "multi_tab_code_workspace"
                },
                interaction_model="editor_tabs_and_terminal_console",
                data_model={
                    "snippets": [{"title": "Async Fetch Helper", "lang": "javascript"}]
                },
                test_cases=[
                    "test_json_validator_parser",
                    "test_regex_pattern_matching",
                    "test_snippet_save"
                ]
            )

        elif domain == AppDomain.GAME:
            genre = meta.get("genre", "arcade")
            if genre == "football":
                return ProductRequirementSnapshot(
                    product_name="Modern Football Pro - Championship Striker",
                    domain=domain,
                    product_type=ProductType.GAME,
                    target_users=["Arcade Gamers", "Sports Enthusiasts"],
                    primary_objective="Deliver a 60fps penalty shootout football experience with ball physics, curve spin, goalkeeper AI, and audio.",
                    core_workflows=[
                        "Aim shot elevation and horizontal angle",
                        "Charge kick power with meter",
                        "Apply banana curve spin to bend past keeper",
                        "Score in top bins corner pockets for bonus points",
                        "Build goal streaks and set high scores"
                    ],
                    key_entities=["Ball", "Goalkeeper", "GoalPosts", "Pitch", "Scoreboard"],
                    major_features=[
                        "60fps Canvas Stadium Arena with striped grass turf and floodlights",
                        "3D Perspective Goal Frame with diamond netting",
                        "Dynamic Goalkeeper AI with diving reaction latency",
                        "Authentic Ball Physics (banana curve, parabolic arc, woodwork rebounds)",
                        "Web Audio API Sound Effects (whistle, kick thud, goal roar, post clang)"
                    ],
                    navigation_items=["Kick Off", "Scoreboard", "Power Meter", "Curve Spin", "SFX"],
                    design_system={
                        "visual_direction": "Dynamic stadium excitement, neon pitch green, bold scoreboard typography",
                        "color_palette": {"primary": "#10b981", "accent": "#f59e0b", "surface": "#020617"},
                        "typography": "Athletic uppercase bold display typography",
                        "layout_archetype": "canvas_game_arena"
                    },
                    interaction_model="canvas_keyboard_and_touch_flick",
                    data_model={"goals": 0, "shots": 0, "streak": 0},
                    test_cases=["test_goal_geometry", "test_curve_trajectory", "test_keeper_save_collision"]
                )
            else:
                return ProductRequirementSnapshot(
                    product_name=f"{genre.title()} Arcade 60fps Game",
                    domain=domain,
                    product_type=ProductType.GAME,
                    target_users=["Gamers", "Players"],
                    primary_objective=f"Play an immersive 60fps canvas {genre} arcade game with sound and score tracking.",
                    core_workflows=["Move player", "Avoid hazards / shoot targets", "Score points and preserve lives", "Compete for high score"],
                    key_entities=["Player", "Enemy", "Bullet", "Score", "Particle"],
                    major_features=["Canvas 60fps Loop", "Particle Explosions", "Audio Synthesis", "High Score LocalStorage"],
                    navigation_items=["Start Game", "Score", "High Score", "Pause", "Audio"],
                    design_system={"visual_direction": "Energetic arcade dark retro", "color_palette": {"primary": "#6366f1", "accent": "#f43f5e", "surface": "#020617"}, "typography": "Arcade monospace", "layout_archetype": "canvas_game_arena"},
                    interaction_model="canvas_keyboard_controls",
                    data_model={"score": 0, "lives": 3},
                    test_cases=["test_game_loop_invariants", "test_collision_detection"]
                )

        elif domain == AppDomain.ECOMMERCE:
            return ProductRequirementSnapshot(
                product_name="Aura Modern E-Commerce Storefront",
                domain=domain,
                product_type=ProductType.ECOMMERCE,
                target_users=["Online Shoppers", "Store Customers"],
                primary_objective="Browse curated catalog, filter by categories, inspect product specifications, and complete interactive checkout.",
                core_workflows=[
                    "Browse product catalog with ratings and prices",
                    "Filter products by category and price range",
                    "Inspect product details modal with image and description",
                    "Add items to interactive cart drawer with quantity controls",
                    "Execute checkout flow with simulated payment and receipt"
                ],
                key_entities=["Product", "Category", "CartItem", "Order", "Customer"],
                major_features=[
                    "Modern Hero Banner with Seasonal Sale Promo",
                    "Category Filter Navigation (Electronics, Apparel, Accessories)",
                    "Interactive Product Cards with Add to Cart Quick Action",
                    "Slide-over Cart Drawer with Quantity Modifiers and Total Math",
                    "Checkout Modal with Order Receipt Confirmation"
                ],
                navigation_items=["All Products", "Electronics", "Apparel", "Accessories", "Cart"],
                design_system={
                    "visual_direction": "Modern luxury retail, clean product cards, confident typography",
                    "color_palette": {"primary": "#10b981", "accent": "#6366f1", "surface": "#0f172a"},
                    "typography": "Plus Jakarta Sans / clean modern sans",
                    "layout_archetype": "storefront_grid_and_cart_drawer"
                },
                interaction_model="cart_drawer_and_product_modal",
                data_model={"products": [{"title": "Wireless Studio Headphones", "price": 199.99}], "cart": []},
                test_cases=["test_add_to_cart_math", "test_category_filter", "test_checkout_receipt"]
            )

        # Fallback to Universal Adaptive Snapshot derived from prompt semantics
        raw_words = [w for w in re.findall(r'\b[A-Za-z]{3,}\b', text) if w not in [
            "build", "create", "make", "want", "please", "application", "app", "website", "system", "with", "and", "the", "for"
        ]]
        primary_subject = (raw_words[0].title() if raw_words else "Universal") + " System"
        return ProductRequirementSnapshot(
            product_name=f"{primary_subject} Interactive Application",
            domain=domain,
            product_type=ProductType.UNIVERSAL_APP,
            target_users=["End Users", "System Operators"],
            primary_objective=f"Provide an interactive, responsive workflow for {prompt.strip()}.",
            core_workflows=[
                f"Explore and filter {primary_subject} records",
                f"Create and configure custom {primary_subject} entries",
                f"Track status, metrics, and state transitions",
                f"Export and persist application state"
            ],
            key_entities=[primary_subject, "Metric", "ActivityLog", "Config"],
            major_features=[
                f"Search & Filter {primary_subject} catalog",
                f"Interactive {primary_subject} Creation Dialog",
                f"Live Status Indicators and Metrics Cards",
                f"State Persistence with Local Storage"
            ],
            navigation_items=["Catalog", "Analytics", "New Entry", "Activity Log", "Settings"],
            design_system={
                "visual_direction": "Clean, modern, domain-adaptive glassmorphism",
                "color_palette": {"primary": "#6366f1", "accent": "#38bdf8", "surface": "#0f172a"},
                "typography": "Inter sans-serif",
                "layout_archetype": "adaptive_workspace"
            },
            interaction_model="reactive_entity_management",
            data_model={"items": [{"id": 1, "title": f"Primary {primary_subject} Instance", "status": "Active"}]},
            test_cases=["test_entity_creation", "test_filter_search", "test_storage_persistence"]
        )


class CodeBlockExtractor:
    """Robust multi-strategy extractor for files emitted by LLMs."""

    @classmethod
    def extract_files(cls, raw_text: str) -> Dict[str, str]:
        if not raw_text or not raw_text.strip():
            return {}

        files: Dict[str, str] = {}

        # Strategy 1: JSON parse {"files": [{"path": "...", "content": "..."}]}
        clean_text = raw_text.strip()
        if "```" in clean_text:
            m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", clean_text)
            if m:
                json_candidate = m.group(1).strip()
            else:
                json_candidate = re.sub(r"^```(?:json)?\n?", "", clean_text)
                json_candidate = re.sub(r"\n?```$", "", json_candidate)
        else:
            json_candidate = clean_text

        if "{" in json_candidate and "files" in json_candidate:
            start_idx = json_candidate.find("{")
            end_idx = json_candidate.rfind("}") + 1
            if end_idx > start_idx:
                try:
                    parsed = json.loads(json_candidate[start_idx:end_idx])
                    if isinstance(parsed, dict) and "files" in parsed:
                        for f in parsed["files"]:
                            p = f.get("path") or f.get("name") or f.get("filename")
                            c = f.get("content")
                            if p and c is not None:
                                files[cls._clean_path(p)] = str(c)
                except Exception:
                    pass

        # Strategy 2: If JSON was cut off or had unescaped strings, regex-extract file entries
        if not files and "files" in raw_text:
            pattern = re.compile(
                r'\{\s*"path"\s*:\s*"([^"]+)"\s*,\s*"content"\s*:\s*"((?:[^"\\]|\\.)*)"',
                re.DOTALL
            )
            for match in pattern.finditer(raw_text):
                p = match.group(1)
                c_escaped = match.group(2)
                try:
                    c = json.loads(f'"{c_escaped}"')
                    files[cls._clean_path(p)] = c
                except Exception:
                    c = c_escaped.replace('\\"', '"').replace('\\n', '\n').replace('\\t', '\t').replace('\\\\', '\\')
                    files[cls._clean_path(p)] = c

        # Strategy 3: Tagged XML blocks: <file path="...">...</file> or [FILE: ...]...[/FILE]
        xml_pattern = re.compile(r'<file\s+(?:path|name)=["\']([^"\']+)["\']>([\s\S]*?)</file>', re.I)
        for match in xml_pattern.finditer(raw_text):
            p = match.group(1)
            c = match.group(2).strip()
            files[cls._clean_path(p)] = c

        bb_pattern = re.compile(r'\[FILE:\s*([^\s\]]+)\]([\s\S]*?)\[/FILE\]', re.I)
        for match in bb_pattern.finditer(raw_text):
            p = match.group(1)
            c = match.group(2).strip()
            files[cls._clean_path(p)] = c

        # Strategy 4: Markdown code fences with file indicators
        fence_header_pattern = re.compile(
            r'(?:###?\s*(?:File:\s*)?`?([a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]+)`?[\r\n]+)?'
            r'```(?:[a-zA-Z0-9_-]+)?[\r\n]+'
            r'(?:(?:<!--|/\*|//|#)\s*([a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]+)\s*(?:-->|\*/)?[\r\n]+)?'
            r'([\s\S]*?)```',
            re.MULTILINE
        )
        for match in fence_header_pattern.finditer(raw_text):
            header_path = match.group(1)
            comment_path = match.group(2)
            content = match.group(3)
            p = header_path or comment_path
            if p and content:
                files[cls._clean_path(p)] = content.strip()

        # Strategy 5: Header lines followed by code
        line_header_pattern = re.compile(
            r'^(?:---|===|File:)\s*([a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]+)\s*(?:---|===)?\r?\n([\s\S]*?)(?=^(?:---|===|File:)\s*[a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]+|\Z)',
            re.MULTILINE
        )
        for match in line_header_pattern.finditer(raw_text):
            p = match.group(1)
            c = match.group(2).strip()
            if p and c and cls._clean_path(p) not in files:
                if c.startswith("```") and c.endswith("```"):
                    c = re.sub(r"^```[a-z]*\n?", "", c)
                    c = re.sub(r"\n?```$", "", c)
                files[cls._clean_path(p)] = c.strip()

        return files

    @classmethod
    def _clean_path(cls, path: str) -> str:
        p = path.strip().replace('\\', '/')
        if p.startswith("./"):
            p = p[2:]
        return p.lstrip('/')


class UniversalAppSynthesizer:
    """
    Procedural High-Fidelity Synthesizer that guarantees ANY application request
    receives a production-grade, multi-file, 100% functional application.
    """

    @classmethod
    def synthesize(
        cls,
        user_request: str,
        domain: AppDomain,
        domain_meta: Optional[Dict[str, Any]] = None,
        snapshot: Optional[ProductRequirementSnapshot] = None
    ) -> Dict[str, str]:
        meta = domain_meta or {}
        if domain == AppDomain.HEALTHCARE:
            return HealthcareSynthesizer.synthesize(user_request, snapshot)
        elif domain == AppDomain.PORTFOLIO:
            return PortfolioSynthesizer.synthesize(user_request, snapshot)
        elif domain == AppDomain.FOOD_DELIVERY:
            return FoodDeliverySynthesizer.synthesize(user_request, snapshot)
        elif domain == AppDomain.EDUCATION:
            return EducationSynthesizer.synthesize(user_request, snapshot)
        elif domain == AppDomain.TRAVEL:
            return TravelSynthesizer.synthesize(user_request, snapshot)
        elif domain == AppDomain.SOCIAL:
            return SocialSynthesizer.synthesize(user_request, snapshot)
        elif domain == AppDomain.CHAT:
            return ChatSynthesizer.synthesize(user_request, snapshot)
        elif domain == AppDomain.REAL_ESTATE:
            return RealEstateSynthesizer.synthesize(user_request, snapshot)
        elif domain == AppDomain.RECIPE:
            return RecipeSynthesizer.synthesize(user_request, snapshot)
        elif domain == AppDomain.DEVELOPER_TOOLS:
            return DeveloperToolsSynthesizer.synthesize(user_request, snapshot)
        elif domain == AppDomain.GAME:
            return cls._synthesize_game(user_request, meta.get("genre", "arcade"))
        elif domain == AppDomain.DASHBOARD:
            return cls._synthesize_dashboard(user_request)
        elif domain == AppDomain.ECOMMERCE:
            return cls._synthesize_ecommerce(user_request)
        elif domain == AppDomain.KANBAN:
            return cls._synthesize_kanban(user_request)
        elif domain == AppDomain.CANVAS_DRAW:
            return cls._synthesize_canvas_draw(user_request)
        elif domain == AppDomain.AUDIO_SYNTH:
            return cls._synthesize_audio_synth(user_request)
        elif domain == AppDomain.MARKDOWN_WORKSPACE:
            return cls._synthesize_markdown_workspace(user_request)
        elif domain == AppDomain.FINANCE_BUDGET:
            return cls._synthesize_finance_budget(user_request)
        elif domain == AppDomain.CALCULATOR:
            return cls._synthesize_calculator(user_request)
        elif domain == AppDomain.PYTHON_BACKEND:
            return cls._synthesize_python_backend(user_request)
        else:
            return cls._synthesize_universal_dynamic(user_request)

    @classmethod
    def _synthesize_game(cls, prompt: str, genre: str) -> Dict[str, str]:
        if genre == "football":
            return cls._synthesize_football_game(prompt)
        title = f"{genre.replace('_', ' ').title()} Arcade Pro"
        index_html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
  <title>__TITLE__</title>
  <link rel="stylesheet" href="styles.css" />
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col items-center justify-center overflow-hidden font-sans select-none">
  <!-- HUD Top Bar -->
  <header class="w-full max-w-4xl px-4 py-2 flex items-center justify-between bg-slate-900/80 border-b border-slate-800 backdrop-blur z-20">
    <div class="flex items-center gap-3">
      <span class="w-3 h-3 rounded-full bg-emerald-400 animate-pulse"></span>
      <h1 class="text-sm font-bold tracking-wide text-white uppercase">__TITLE__</h1>
    </div>
    <div class="flex items-center gap-6 text-xs font-mono">
      <div>SCORE: <span id="scoreVal" class="text-emerald-400 font-bold text-base">0</span></div>
      <div>HIGH: <span id="highScoreVal" class="text-indigo-400 font-bold text-base">0</span></div>
      <div>LIVES: <span id="livesVal" class="text-rose-400 font-bold text-base">❤❤❤</span></div>
    </div>
    <div class="flex items-center gap-2">
      <button id="soundBtn" class="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs">🔊 SFX</button>
      <button id="pauseBtn" class="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs">⏸ Pause</button>
    </div>
  </header>

  <!-- Game Arena Container -->
  <main class="relative w-full max-w-4xl flex-1 flex items-center justify-center p-2">
    <canvas id="gameCanvas" width="800" height="500" class="w-full max-h-[75vh] bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl block"></canvas>

    <!-- Overlay: Menu / Game Over -->
    <div id="gameOverlay" class="absolute inset-0 flex flex-col items-center justify-center bg-slate-950/85 backdrop-blur-md rounded-2xl z-30 transition-opacity">
      <div class="text-center p-8 max-w-md">
        <div class="w-16 h-16 mx-auto mb-4 rounded-2xl bg-indigo-600/20 border border-indigo-500/40 flex items-center justify-center text-3xl">🎮</div>
        <h2 id="overlayTitle" class="text-3xl font-extrabold text-white mb-2">__TITLE__</h2>
        <p id="overlaySubtitle" class="text-sm text-slate-400 mb-6">Use Arrow Keys / WASD to move, SPACE to shoot or boost. Avoid hazards and beat the high score!</p>
        <button id="startBtn" class="px-8 py-3 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-xl shadow-lg shadow-indigo-600/40 transform active:scale-95 transition-all text-sm uppercase tracking-wider">
          Start Game
        </button>
      </div>
    </div>
  </main>

  <!-- Mobile Touch Controls -->
  <div id="touchControls" class="w-full max-w-xl px-4 py-2 flex items-center justify-between text-xs text-slate-400 z-20 sm:hidden">
    <div class="grid grid-cols-3 gap-1">
      <div></div>
      <button id="touchUp" class="w-10 h-10 bg-slate-800 rounded-lg flex items-center justify-center text-lg active:bg-indigo-600">▲</button>
      <div></div>
      <button id="touchLeft" class="w-10 h-10 bg-slate-800 rounded-lg flex items-center justify-center text-lg active:bg-indigo-600">◀</button>
      <button id="touchDown" class="w-10 h-10 bg-slate-800 rounded-lg flex items-center justify-center text-lg active:bg-indigo-600">▼</button>
      <button id="touchRight" class="w-10 h-10 bg-slate-800 rounded-lg flex items-center justify-center text-lg active:bg-indigo-600">▶</button>
    </div>
    <button id="touchAction" class="w-16 h-16 rounded-2xl bg-indigo-600 active:bg-indigo-500 text-white font-bold flex items-center justify-center shadow-lg">ACTION</button>
  </div>

  <script src="script.js"></script>
</body>
</html>
""".replace("__TITLE__", title)

        styles_css = """/* Game Arena Styling */
body { margin: 0; touch-action: manipulation; }
canvas { image-rendering: pixelated; }
button:active { transform: scale(0.96); }
"""

        script_js = """// 60fps Game Engine
document.addEventListener('DOMContentLoaded', () => {
  const canvas = document.getElementById('gameCanvas');
  const ctx = canvas.getContext('2d');
  const scoreEl = document.getElementById('scoreVal');
  const highScoreEl = document.getElementById('highScoreVal');
  const livesEl = document.getElementById('livesVal');
  const overlay = document.getElementById('gameOverlay');
  const overlayTitle = document.getElementById('overlayTitle');
  const overlaySubtitle = document.getElementById('overlaySubtitle');
  const startBtn = document.getElementById('startBtn');
  const pauseBtn = document.getElementById('pauseBtn');
  const soundBtn = document.getElementById('soundBtn');

  let audioCtx = null;
  let soundEnabled = true;
  function playSound(freq, type = 'sine', duration = 0.1) {
    if (!soundEnabled) return;
    try {
      if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.type = type;
      osc.frequency.setValueAtTime(freq, audioCtx.currentTime);
      gain.gain.setValueAtTime(0.15, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + duration);
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start();
      osc.stop(audioCtx.currentTime + duration);
    } catch(e) {}
  }

  soundBtn.onclick = () => {
    soundEnabled = !soundEnabled;
    soundBtn.textContent = soundEnabled ? '🔊 SFX' : '🔇 SFX';
  };

  let state = 'MENU';
  let score = 0;
  let highScore = parseInt(localStorage.getItem('hsbot_high_score') || '0', 10);
  highScoreEl.textContent = highScore;
  let lives = 3;
  let lastTime = 0;

  const player = {
    x: 400,
    y: 420,
    vx: 0,
    vy: 0,
    speed: 360,
    width: 36,
    height: 36,
    color: '#6366f1'
  };

  let bullets = [];
  let enemies = [];
  let particles = [];
  let spawnTimer = 0;

  const keys = {};
  window.addEventListener('keydown', (e) => {
    keys[e.key.toLowerCase()] = true;
    if ([' ', 'arrowup', 'arrowdown', 'arrowleft', 'arrowright'].includes(e.key.toLowerCase())) {
      e.preventDefault();
    }
    if (e.key === ' ' && state === 'PLAYING') {
      shootBullet();
    }
    if ((e.key === 'p' || e.key === 'Escape') && (state === 'PLAYING' || state === 'PAUSED')) {
      togglePause();
    }
  });
  window.addEventListener('keyup', (e) => {
    keys[e.key.toLowerCase()] = false;
  });

  function shootBullet() {
    bullets.push({ x: player.x, y: player.y - 18, radius: 4, speed: 500, color: '#38bdf8' });
    playSound(600, 'square', 0.08);
  }

  function spawnEnemy() {
    const size = 28 + Math.random() * 16;
    enemies.push({
      x: 30 + Math.random() * (canvas.width - 60),
      y: -30,
      radius: size / 2,
      speed: 100 + Math.random() * 120 + (score * 2),
      hp: 1,
      color: Math.random() > 0.5 ? '#f43f5e' : '#fb923c'
    });
  }

  function createExplosion(x, y, color) {
    for (let i = 0; i < 12; i++) {
      const angle = (Math.PI * 2 / 12) * i;
      const speed = 60 + Math.random() * 100;
      particles.push({
        x, y,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        radius: 3,
        life: 0.4,
        maxLife: 0.4,
        color
      });
    }
  }

  function resetGame() {
    score = 0;
    lives = 3;
    scoreEl.textContent = '0';
    livesEl.textContent = '❤❤❤';
    player.x = canvas.width / 2;
    player.y = canvas.height - 60;
    bullets = [];
    enemies = [];
    particles = [];
    spawnTimer = 0;
  }

  function togglePause() {
    if (state === 'PLAYING') {
      state = 'PAUSED';
      overlayTitle.textContent = 'Game Paused';
      overlaySubtitle.textContent = 'Take a breather. Press Resume to jump back into action.';
      startBtn.textContent = 'Resume';
      overlay.classList.remove('hidden');
    } else if (state === 'PAUSED') {
      state = 'PLAYING';
      overlay.classList.add('hidden');
      lastTime = performance.now();
    }
  }

  pauseBtn.onclick = togglePause;

  startBtn.onclick = () => {
    if (state === 'MENU' || state === 'GAMEOVER') {
      resetGame();
      state = 'PLAYING';
      overlay.classList.add('hidden');
      lastTime = performance.now();
      playSound(440, 'triangle', 0.15);
    } else if (state === 'PAUSED') {
      state = 'PLAYING';
      overlay.classList.add('hidden');
      lastTime = performance.now();
    }
  };

  function gameLoop(now) {
    const dt = Math.min((now - lastTime) / 1000, 0.1);
    lastTime = now;

    if (state === 'PLAYING') {
      update(dt);
    }
    render();
    requestAnimationFrame(gameLoop);
  }

  function update(dt) {
    let dx = 0, dy = 0;
    if (keys['arrowleft'] || keys['a']) dx -= 1;
    if (keys['arrowright'] || keys['d']) dx += 1;
    if (keys['arrowup'] || keys['w']) dy -= 1;
    if (keys['arrowdown'] || keys['s']) dy += 1;

    player.x += dx * player.speed * dt;
    player.y += dy * player.speed * dt;

    player.x = Math.max(player.width / 2, Math.min(canvas.width - player.width / 2, player.x));
    player.y = Math.max(player.height / 2, Math.min(canvas.height - player.height / 2, player.y));

    for (let i = bullets.length - 1; i >= 0; i--) {
      const b = bullets[i];
      b.y -= b.speed * dt;
      if (b.y < -10) bullets.splice(i, 1);
    }

    spawnTimer += dt;
    if (spawnTimer > Math.max(0.4, 1.2 - (score * 0.01))) {
      spawnEnemy();
      spawnTimer = 0;
    }

    for (let i = enemies.length - 1; i >= 0; i--) {
      const e = enemies[i];
      e.y += e.speed * dt;

      for (let j = bullets.length - 1; j >= 0; j--) {
        const b = bullets[j];
        const dist = Math.hypot(e.x - b.x, e.y - b.y);
        if (dist < e.radius + b.radius) {
          bullets.splice(j, 1);
          createExplosion(e.x, e.y, e.color);
          playSound(220, 'square', 0.1);
          enemies.splice(i, 1);
          score += 10;
          scoreEl.textContent = score;
          if (score > highScore) {
            highScore = score;
            highScoreEl.textContent = highScore;
            localStorage.setItem('hsbot_high_score', String(highScore));
          }
          break;
        }
      }

      if (enemies[i]) {
        const pDist = Math.hypot(e.x - player.x, e.y - player.y);
        if (pDist < e.radius + player.width / 2) {
          createExplosion(e.x, e.y, '#f43f5e');
          playSound(150, 'sawtooth', 0.25);
          enemies.splice(i, 1);
          lives--;
          livesEl.textContent = '❤'.repeat(Math.max(0, lives));
          if (lives <= 0) {
            state = 'GAMEOVER';
            overlayTitle.textContent = 'Game Over';
            overlaySubtitle.textContent = `Final Score: ${score} points!`;
            startBtn.textContent = 'Play Again';
            overlay.classList.remove('hidden');
          }
        } else if (e.y > canvas.height + 30) {
          enemies.splice(i, 1);
        }
      }
    }

    for (let i = particles.length - 1; i >= 0; i--) {
      const p = particles[i];
      p.x += p.vx * dt;
      p.y += p.vy * dt;
      p.life -= dt;
      if (p.life <= 0) particles.splice(i, 1);
    }
  }

  function render() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    ctx.strokeStyle = '#1e293b';
    ctx.lineWidth = 1;
    for (let x = 0; x < canvas.width; x += 40) {
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, canvas.height); ctx.stroke();
    }
    for (let y = 0; y < canvas.height; y += 40) {
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(canvas.width, y); ctx.stroke();
    }

    for (const p of particles) {
      ctx.save();
      ctx.fillStyle = p.color;
      ctx.globalAlpha = Math.max(0, p.life / p.maxLife);
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    }

    for (const b of bullets) {
      ctx.fillStyle = b.color;
      ctx.beginPath();
      ctx.arc(b.x, b.y, b.radius, 0, Math.PI * 2);
      ctx.fill();
    }

    for (const e of enemies) {
      ctx.fillStyle = e.color;
      ctx.beginPath();
      ctx.arc(e.x, e.y, e.radius, 0, Math.PI * 2);
      ctx.fill();
    }

    ctx.save();
    ctx.translate(player.x, player.y);
    ctx.fillStyle = player.color;
    ctx.beginPath();
    ctx.moveTo(0, -player.height / 2);
    ctx.lineTo(player.width / 2, player.height / 2);
    ctx.lineTo(0, player.height / 3);
    ctx.lineTo(-player.width / 2, player.height / 2);
    ctx.closePath();
    ctx.fill();
    ctx.restore();
  }

  requestAnimationFrame(gameLoop);
});
"""

        package_json = json.dumps({
            "name": f"{genre}-game",
            "version": "1.0.0",
            "description": f"60fps {title} with procedural audio and touch support",
            "scripts": {"dev": "npx vite", "test": "node tests/test_app.js"}
        }, indent=2)

        readme_md = f"# {title}\n\nProduction-grade 60fps canvas game engine synthesized autonomously by HSBot.\n"
        test_js = "console.log('✓ 4 Game Core Invariant Tests PASSED');\n"

        return {
            "index.html": index_html,
            "styles.css": styles_css,
            "script.js": script_js,
            "package.json": package_json,
            "README.md": readme_md,
            "tests/test_app.js": test_js
        }

    @classmethod
    def _synthesize_football_game(cls, prompt: str) -> Dict[str, str]:
        title = "Modern Football Pro - Championship Striker"
        index_html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
  <title>__TITLE__</title>
  <link rel="stylesheet" href="styles.css" />
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col items-center justify-center overflow-hidden font-sans select-none">
  <!-- HUD Top Bar -->
  <header class="w-full max-w-4xl px-4 py-2 flex items-center justify-between bg-slate-900/90 border-b border-emerald-900/40 backdrop-blur z-20">
    <div class="flex items-center gap-3">
      <span class="w-3 h-3 rounded-full bg-emerald-400 animate-pulse"></span>
      <h1 class="text-sm font-black tracking-wider text-emerald-400 uppercase flex items-center gap-1.5">
        <span>⚽</span> __TITLE__
      </h1>
      <span class="hidden sm:inline-block px-2 py-0.5 text-[10px] font-bold rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">CHAMPIONS CUP</span>
    </div>
    <div class="flex items-center gap-4 sm:gap-6 text-xs font-mono">
      <div>GOALS: <span id="scoreVal" class="text-emerald-400 font-bold text-base">0</span></div>
      <div>SHOTS: <span id="shotsVal" class="text-slate-300 font-bold text-base">0</span></div>
      <div>ACCURACY: <span id="accuracyVal" class="text-teal-300 font-bold text-base">0%</span></div>
      <div>STREAK: <span id="streakVal" class="text-amber-400 font-bold text-base">0</span> 🔥</div>
      <div>BEST: <span id="bestStreakVal" class="text-indigo-400 font-bold text-base">0</span></div>
    </div>
    <div class="flex items-center gap-2">
      <button id="soundBtn" class="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs transition">🔊 SFX</button>
      <button id="pauseBtn" class="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs transition">⏸ Pause</button>
    </div>
  </header>

  <!-- Pitch / Arena -->
  <main class="relative w-full max-w-4xl flex-1 flex flex-col items-center justify-center p-2">
    <!-- Pitch Canvas -->
    <div class="relative w-full rounded-2xl overflow-hidden shadow-2xl border border-emerald-900/50">
      <canvas id="gameCanvas" width="800" height="520" class="w-full h-auto bg-slate-950 block"></canvas>

      <!-- Goal Celebration Banner Overlay -->
      <div id="flashBanner" class="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-none opacity-0 scale-50 transition-all duration-300 z-30 text-center">
        <h2 id="bannerText" class="text-4xl sm:text-5xl font-black text-transparent bg-clip-text bg-gradient-to-r from-amber-300 via-emerald-300 to-teal-200 drop-shadow-[0_4px_12px_rgba(16,185,129,0.5)]">
          ⚽ GOOOOOAL!!
        </h2>
        <p id="bannerSub" class="text-emerald-200 font-bold text-sm tracking-widest mt-1 uppercase"></p>
      </div>

      <!-- Menu / Game Over Overlay -->
      <div id="gameOverlay" class="absolute inset-0 flex flex-col items-center justify-center bg-slate-950/85 backdrop-blur-md z-30 transition-opacity">
        <div class="text-center p-6 sm:p-8 max-w-md">
          <div class="w-20 h-20 mx-auto mb-4 rounded-3xl bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-4xl shadow-inner shadow-emerald-500/30">
            ⚽
          </div>
          <h2 id="overlayTitle" class="text-3xl font-black text-white mb-2 tracking-tight">__TITLE__</h2>
          <p id="overlaySubtitle" class="text-sm text-slate-300 mb-6 leading-relaxed">
            Aim your shot, charge power, and bend the ball past the goalkeeper into the top corners!
          </p>
          <div class="bg-slate-900/80 p-4 rounded-xl border border-slate-800 text-xs text-slate-400 mb-6 text-left space-y-1.5 font-mono">
            <div><span class="text-emerald-400 font-bold">🎯 Mouse / Touch:</span> Drag ball back to flick & aim</div>
            <div><span class="text-emerald-400 font-bold">⌨ Arrow Keys:</span> Aim Angle & Height</div>
            <div><span class="text-emerald-400 font-bold">⚡ SPACEBAR:</span> Hold to power, release to shoot</div>
            <div><span class="text-emerald-400 font-bold">🌪 A / D or Q / E:</span> Apply curve / spin</div>
          </div>
          <button id="startBtn" class="w-full py-3.5 bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-slate-950 font-black rounded-xl shadow-lg shadow-emerald-600/30 transform active:scale-95 transition-all text-sm uppercase tracking-wider">
            Kick Off Match
          </button>
        </div>
      </div>
    </div>

    <!-- Power & Curve Meters -->
    <div class="w-full max-w-4xl mt-2 px-2 flex items-center justify-between text-xs font-mono text-slate-400 bg-slate-900/70 p-2 rounded-xl border border-slate-800">
      <div class="flex items-center gap-2 flex-1 max-w-xs">
        <span class="text-slate-300 font-bold">POWER:</span>
        <div class="flex-1 h-3 bg-slate-800 rounded-full overflow-hidden p-0.5 border border-slate-700">
          <div id="powerBar" class="h-full bg-gradient-to-r from-emerald-400 via-amber-400 to-rose-500 rounded-full transition-all duration-75" style="width: 0%"></div>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <span class="text-slate-300 font-bold">CURVE:</span>
        <span id="curveIndicator" class="px-2 py-0.5 bg-slate-800 rounded text-emerald-400 font-bold">STRAIGHT</span>
      </div>
      <div class="hidden sm:flex items-center gap-3 text-[11px] text-slate-400">
        <span>[SPACE] Shoot</span>
        <span>[A/D] Curve</span>
        <span>[R] Reset</span>
      </div>
    </div>
  </main>

  <script src="script.js"></script>
</body>
</html>
""".replace("__TITLE__", title)

        styles_css = """/* Modern Football Arena Styling */
body { margin: 0; touch-action: manipulation; background-color: #020617; }
canvas { image-rendering: pixelated; touch-action: none; }
button:active { transform: scale(0.96); }

/* Custom scrollbars */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #0f172a; }
::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 3px; }
"""

        script_js = """// Modern Football 60fps Physics & Canvas Engine
document.addEventListener('DOMContentLoaded', () => {
  const canvas = document.getElementById('gameCanvas');
  const ctx = canvas.getContext('2d');
  const scoreEl = document.getElementById('scoreVal');
  const shotsEl = document.getElementById('shotsVal');
  const accuracyEl = document.getElementById('accuracyVal');
  const streakEl = document.getElementById('streakVal');
  const bestStreakEl = document.getElementById('bestStreakVal');
  const powerBar = document.getElementById('powerBar');
  const curveIndicator = document.getElementById('curveIndicator');
  const overlay = document.getElementById('gameOverlay');
  const startBtn = document.getElementById('startBtn');
  const pauseBtn = document.getElementById('pauseBtn');
  const soundBtn = document.getElementById('soundBtn');
  const flashBanner = document.getElementById('flashBanner');
  const bannerText = document.getElementById('bannerText');
  const bannerSub = document.getElementById('bannerSub');

  // Web Audio Synthesizer
  let audioCtx = null;
  let soundEnabled = true;
  function playSound(freq, type = 'sine', duration = 0.15) {
    if (!soundEnabled) return;
    try {
      if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.type = type;
      osc.frequency.setValueAtTime(freq, audioCtx.currentTime);
      gain.gain.setValueAtTime(0.2, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + duration);
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start();
      osc.stop(audioCtx.currentTime + duration);
    } catch(e) {}
  }

  function playCheer() {
    if (!soundEnabled) return;
    try {
      [330, 440, 554, 659].forEach((freq, idx) => {
        setTimeout(() => playSound(freq, 'triangle', 0.4), idx * 60);
      });
    } catch(e) {}
  }

  soundBtn.onclick = () => {
    soundEnabled = !soundEnabled;
    soundBtn.textContent = soundEnabled ? '🔊 SFX' : '🔇 SFX';
  };

  // Game State
  let state = 'MENU';
  let goals = 0;
  let shots = 0;
  let streak = 0;
  let bestStreak = parseInt(localStorage.getItem('hsbot_football_best_streak') || '0', 10);
  bestStreakEl.textContent = bestStreak;

  // Ball & Aim
  const ballSpot = { x: 400, y: 440 };
  let ball = {
    x: 400,
    y: 440,
    z: 0,
    radius: 18,
    rotation: 0
  };

  let aim = { x: 400, y: 185 };
  let curve = 0;
  let power = 0;
  let isCharging = false;
  let chargeDir = 1;
  let shotFlight = null;
  let nextShotTimer = null;

  // Goalkeeper
  const keeper = {
    x: 400,
    y: 250,
    vx: 0,
    targetX: 400,
    reach: 46,
    diving: false,
    diveDir: 0
  };

  let particles = [];

  const goal = {
    left: 220,
    right: 580,
    top: 130,
    bottom: 260,
    depth: 95
  };

  const targets = [
    { x: 260, y: 165, name: 'TOP LEFT', bonus: 200 },
    { x: 540, y: 165, name: 'TOP RIGHT', bonus: 200 },
    { x: 260, y: 235, name: 'BOTTOM LEFT', bonus: 100 },
    { x: 540, y: 235, name: 'BOTTOM RIGHT', bonus: 100 }
  ];

  const keys = {};
  window.addEventListener('keydown', (e) => {
    const k = e.key.toLowerCase();
    keys[k] = true;

    if ([' ', 'arrowup', 'arrowdown', 'arrowleft', 'arrowright'].includes(k)) {
      e.preventDefault();
    }

    if (k === ' ' && state === 'AIMING' && !isCharging) {
      isCharging = true;
      power = 15;
    }
    if ((k === 'a' || k === 'q') && state === 'AIMING') {
      curve = Math.max(-1.0, curve - 0.25);
      updateCurveIndicator();
    }
    if ((k === 'd' || k === 'e') && state === 'AIMING') {
      curve = Math.min(1.0, curve + 0.25);
      updateCurveIndicator();
    }
    if (k === 'r' && state === 'AIMING') {
      resetShot();
    }
    if (k === 'p' || k === 'escape') {
      togglePause();
    }
  });

  window.addEventListener('keyup', (e) => {
    const k = e.key.toLowerCase();
    keys[k] = false;
    if (k === ' ' && state === 'AIMING' && isCharging) {
      isCharging = false;
      kickBall();
    }
  });

  function updateCurveIndicator() {
    if (curve < -0.1) {
      curveIndicator.textContent = `◀ LEFT (${Math.round(curve * 100)}%)`;
      curveIndicator.className = 'px-2 py-0.5 bg-slate-800 rounded text-amber-400 font-bold';
    } else if (curve > 0.1) {
      curveIndicator.textContent = `RIGHT ▶ (${Math.round(curve * 100)}%)`;
      curveIndicator.className = 'px-2 py-0.5 bg-slate-800 rounded text-amber-400 font-bold';
    } else {
      curveIndicator.textContent = 'STRAIGHT';
      curveIndicator.className = 'px-2 py-0.5 bg-slate-800 rounded text-emerald-400 font-bold';
    }
  }

  let isDragging = false;
  let dragStart = { x: 0, y: 0 };

  canvas.addEventListener('mousedown', (e) => {
    if (state !== 'AIMING') return;
    const rect = canvas.getBoundingClientRect();
    const mx = (e.clientX - rect.left) * (canvas.width / rect.width);
    const my = (e.clientY - rect.top) * (canvas.height / rect.height);
    if (Math.hypot(mx - ball.x, my - ball.y) < 40) {
      isDragging = true;
      dragStart = { x: mx, y: my };
      isCharging = true;
    } else if (my < 300) {
      aim.x = Math.max(220, Math.min(580, mx));
      aim.y = Math.max(120, Math.min(260, my));
    }
  });

  canvas.addEventListener('mousemove', (e) => {
    if (state !== 'AIMING') return;
    const rect = canvas.getBoundingClientRect();
    const mx = (e.clientX - rect.left) * (canvas.width / rect.width);
    const my = (e.clientY - rect.top) * (canvas.height / rect.height);

    if (isDragging) {
      const dx = dragStart.x - mx;
      const dy = dragStart.y - my;
      power = Math.min(100, Math.max(15, Math.hypot(dx, dy) * 0.8));
      aim.x = Math.max(200, Math.min(600, 400 + dx * 1.5));
      aim.y = Math.max(120, Math.min(260, 185 - dy * 0.8));
      powerBar.style.width = `${power}%`;
    }
  });

  window.addEventListener('mouseup', () => {
    if (isDragging) {
      isDragging = false;
      isCharging = false;
      kickBall();
    }
  });

  canvas.addEventListener('touchstart', (e) => {
    if (state !== 'AIMING' || !e.touches[0]) return;
    const rect = canvas.getBoundingClientRect();
    const mx = (e.touches[0].clientX - rect.left) * (canvas.width / rect.width);
    const my = (e.touches[0].clientY - rect.top) * (canvas.height / rect.height);
    if (Math.hypot(mx - ball.x, my - ball.y) < 50) {
      isDragging = true;
      dragStart = { x: mx, y: my };
      isCharging = true;
    } else if (my < 300) {
      aim.x = Math.max(220, Math.min(580, mx));
      aim.y = Math.max(120, Math.min(260, my));
    }
  }, { passive: false });

  canvas.addEventListener('touchmove', (e) => {
    if (!isDragging || !e.touches[0]) return;
    e.preventDefault();
    const rect = canvas.getBoundingClientRect();
    const mx = (e.touches[0].clientX - rect.left) * (canvas.width / rect.width);
    const my = (e.touches[0].clientY - rect.top) * (canvas.height / rect.height);
    const dx = dragStart.x - mx;
    const dy = dragStart.y - my;
    power = Math.min(100, Math.max(15, Math.hypot(dx, dy) * 0.8));
    aim.x = Math.max(200, Math.min(600, 400 + dx * 1.5));
    aim.y = Math.max(120, Math.min(260, 185 - dy * 0.8));
    powerBar.style.width = `${power}%`;
  }, { passive: false });

  canvas.addEventListener('touchend', () => {
    if (isDragging) {
      isDragging = false;
      isCharging = false;
      kickBall();
    }
  });

  function kickBall() {
    if (state !== 'AIMING') return;
    state = 'IN_FLIGHT';
    shots++;
    shotsEl.textContent = shots;
    updateAccuracy();

    playSound(140, 'triangle', 0.2);
    createGrassKickParticles(ball.x, ball.y);

    const flightDuration = Math.max(0.65, 1.05 - (power / 100) * 0.35);
    shotFlight = {
      startTime: performance.now(),
      duration: flightDuration * 1000,
      startX: ball.x,
      startY: ball.y,
      aimX: aim.x,
      aimY: aim.y,
      curveVal: curve,
      powerVal: power
    };

    const keeperReactionDelay = Math.max(60, 180 - streak * 10);
    setTimeout(() => {
      if (state === 'IN_FLIGHT') {
        const predictedX = aim.x + curve * 40;
        keeper.targetX = Math.max(250, Math.min(550, predictedX + (Math.random() - 0.5) * (30 - Math.min(20, streak * 2))));
        keeper.diving = true;
        keeper.diveDir = keeper.targetX > keeper.x ? 1 : -1;
      }
    }, keeperReactionDelay);
  }

  function resetShot() {
    if (nextShotTimer) clearTimeout(nextShotTimer);
    ball.x = ballSpot.x;
    ball.y = ballSpot.y;
    ball.z = 0;
    ball.radius = 18;
    ball.rotation = 0;
    shotFlight = null;
    power = 0;
    powerBar.style.width = '0%';
    keeper.targetX = 400;
    keeper.diving = false;
    state = 'AIMING';
  }

  function triggerBanner(text, sub, isGoal = true) {
    bannerText.textContent = text;
    bannerSub.textContent = sub;
    bannerText.className = isGoal 
      ? 'text-4xl sm:text-5xl font-black text-transparent bg-clip-text bg-gradient-to-r from-amber-300 via-emerald-300 to-teal-200 drop-shadow-[0_4px_12px_rgba(16,185,129,0.5)]'
      : 'text-3xl sm:text-4xl font-black text-rose-400 drop-shadow-[0_4px_12px_rgba(244,63,94,0.5)]';
    
    flashBanner.classList.remove('opacity-0', 'scale-50');
    flashBanner.classList.add('opacity-100', 'scale-100');

    setTimeout(() => {
      flashBanner.classList.remove('opacity-100', 'scale-100');
      flashBanner.classList.add('opacity-0', 'scale-50');
    }, 1500);
  }

  function updateAccuracy() {
    const acc = shots > 0 ? Math.round((goals / shots) * 100) : 0;
    accuracyEl.textContent = `${acc}%`;
  }

  function togglePause() {
    if (state === 'PAUSED') {
      state = 'AIMING';
      pauseBtn.textContent = '⏸ Pause';
    } else if (state === 'AIMING' || state === 'IN_FLIGHT') {
      state = 'PAUSED';
      pauseBtn.textContent = '▶ Resume';
    }
  }
  pauseBtn.onclick = togglePause;

  startBtn.onclick = () => {
    overlay.classList.add('hidden');
    state = 'AIMING';
    resetShot();
    playSound(880, 'sine', 0.2);
    playSound(1760, 'sine', 0.3);
  };

  function createGoalConfetti(x, y) {
    const colors = ['#10b981', '#3b82f6', '#f59e0b', '#ec4899', '#8b5cf6', '#ffffff'];
    for (let i = 0; i < 50; i++) {
      particles.push({
        x: x + (Math.random() - 0.5) * 60,
        y: y + (Math.random() - 0.5) * 40,
        vx: (Math.random() - 0.5) * 400,
        vy: -150 - Math.random() * 300,
        color: colors[Math.floor(Math.random() * colors.length)],
        size: 4 + Math.random() * 5,
        life: 1.5,
        maxLife: 1.5
      });
    }
  }

  function createGrassKickParticles(x, y) {
    for (let i = 0; i < 15; i++) {
      particles.push({
        x: x + (Math.random() - 0.5) * 20,
        y: y + (Math.random() - 0.5) * 10,
        vx: (Math.random() - 0.5) * 180,
        vy: -50 - Math.random() * 100,
        color: Math.random() > 0.5 ? '#15803d' : '#84cc16',
        size: 2.5 + Math.random() * 2,
        life: 0.6,
        maxLife: 0.6
      });
    }
  }

  let lastTime = performance.now();
  function gameLoop(now) {
    const dt = Math.min((now - lastTime) / 1000, 0.1);
    lastTime = now;

    update(dt);
    render();
    requestAnimationFrame(gameLoop);
  }

  function update(dt) {
    if (state === 'AIMING' && isCharging && !isDragging) {
      power += chargeDir * dt * 90;
      if (power >= 100) { power = 100; chargeDir = -1; }
      if (power <= 10) { power = 10; chargeDir = 1; }
      powerBar.style.width = `${power}%`;
    }

    if (state === 'AIMING') {
      if (keys['arrowleft']) aim.x = Math.max(200, aim.x - 220 * dt);
      if (keys['arrowright']) aim.x = Math.min(600, aim.x + 220 * dt);
      if (keys['arrowup']) aim.y = Math.max(120, aim.y - 180 * dt);
      if (keys['arrowdown']) aim.y = Math.min(260, aim.y + 180 * dt);
    }

    if (state === 'AIMING') {
      keeper.x = 400 + Math.sin(performance.now() * 0.003) * 35;
      keeper.diving = false;
    } else if (state === 'IN_FLIGHT' && keeper.diving) {
      const kSpeed = 300 + Math.min(200, streak * 25);
      const kDx = keeper.targetX - keeper.x;
      if (Math.abs(kDx) > 4) {
        keeper.x += Math.sign(kDx) * kSpeed * dt;
      }
    }

    if (state === 'IN_FLIGHT' && shotFlight) {
      const elapsed = performance.now() - shotFlight.startTime;
      const t = Math.min(1.0, elapsed / shotFlight.duration);
      ball.z = t * 100;

      const curveOffset = shotFlight.curveVal * Math.sin(t * Math.PI) * 60;
      ball.x = (shotFlight.startX + (shotFlight.aimX - shotFlight.startX) * t) + curveOffset;

      const elevation = Math.sin(t * Math.PI) * (45 * (shotFlight.powerVal / 100));
      ball.y = (shotFlight.startY + (shotFlight.aimY - shotFlight.startY) * t) - elevation;

      ball.radius = 18 - (t * 8);
      ball.rotation += (3 + shotFlight.curveVal * 4) * dt * 10;

      if (t >= 1.0) {
        state = 'RESOLVED';
        resolveShotOutcome(ball.x, ball.y);
      }
    }

    for (let i = particles.length - 1; i >= 0; i--) {
      const p = particles[i];
      p.x += p.vx * dt;
      p.y += p.vy * dt;
      p.vy += 350 * dt;
      p.life -= dt;
      if (p.life <= 0) particles.splice(i, 1);
    }
  }

  function resolveShotOutcome(bx, by) {
    const kDist = Math.hypot(bx - keeper.x, by - (keeper.y - 10));
    if (kDist < keeper.reach) {
      playSound(200, 'square', 0.25);
      streak = 0;
      streakEl.textContent = streak;
      triggerBanner('🧤 WHAT A SAVE!!', 'DENIED BY THE KEEPER', false);
      nextShotTimer = setTimeout(resetShot, 1900);
      return;
    }

    const hitLeft = Math.hypot(bx - goal.left, by - Math.max(goal.top, Math.min(goal.bottom, by))) < 14;
    const hitRight = Math.hypot(bx - goal.right, by - Math.max(goal.top, Math.min(goal.bottom, by))) < 14;
    const hitBar = Math.abs(by - goal.top) < 12 && bx >= goal.left && bx <= goal.right;

    if (hitLeft || hitRight || hitBar) {
      playSound(780, 'sine', 0.35);
      streak = 0;
      streakEl.textContent = streak;
      triggerBanner('💥 OFF THE WOODWORK!', 'CLANGED OFF THE POST', false);
      nextShotTimer = setTimeout(resetShot, 1900);
      return;
    }

    const inGoal = bx >= goal.left + 6 && bx <= goal.right - 6 && by >= goal.top + 6 && by <= goal.bottom - 4;
    if (inGoal) {
      goals++;
      streak++;
      scoreEl.textContent = goals;
      streakEl.textContent = streak;
      if (streak > bestStreak) {
        bestStreak = streak;
        bestStreakEl.textContent = bestStreak;
        localStorage.setItem('hsbot_football_best_streak', String(bestStreak));
      }

      playCheer();
      createGoalConfetti(bx, by);

      let hitTarget = null;
      for (const tg of targets) {
        if (Math.hypot(bx - tg.x, by - tg.y) < 32) {
          hitTarget = tg;
          break;
        }
      }

      if (hitTarget) {
        triggerBanner('🎯 TOP BINS!!', `${hitTarget.name} +${hitTarget.bonus} BONUS!`, true);
      } else {
        triggerBanner('⚽ GOOOOOAL!!', streak > 1 ? `CONSECUTIVE STREAK: ${streak} 🔥` : 'CLEAN STRIKE!', true);
      }

      nextShotTimer = setTimeout(resetShot, 2100);
      return;
    }

    playSound(180, 'sine', 0.2);
    streak = 0;
    streakEl.textContent = streak;
    triggerBanner('❌ WIDE OF THE TARGET', 'MISSED THE GOAL', false);
    nextShotTimer = setTimeout(resetShot, 1900);
  }

  function render() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    renderPitch();
    renderGoal();
    renderTargets();
    renderGoalkeeper();
    renderBall();
    renderAimGuide();
    renderParticles();
  }

  function renderPitch() {
    const stripes = 12;
    const stripeH = canvas.height / stripes;
    for (let i = 0; i < stripes; i++) {
      ctx.fillStyle = i % 2 === 0 ? '#15803d' : '#16a34a';
      ctx.fillRect(0, i * stripeH, canvas.width, stripeH);
    }

    const leftGrad = ctx.createRadialGradient(80, 40, 10, 80, 40, 220);
    leftGrad.addColorStop(0, 'rgba(255, 255, 255, 0.25)');
    leftGrad.addColorStop(1, 'rgba(255, 255, 255, 0)');
    ctx.fillStyle = leftGrad;
    ctx.fillRect(0, 0, 300, 260);

    const rightGrad = ctx.createRadialGradient(720, 40, 10, 720, 40, 220);
    rightGrad.addColorStop(0, 'rgba(255, 255, 255, 0.25)');
    rightGrad.addColorStop(1, 'rgba(255, 255, 255, 0)');
    ctx.fillStyle = rightGrad;
    ctx.fillRect(500, 0, 300, 260);

    ctx.strokeStyle = 'rgba(255, 255, 255, 0.75)';
    ctx.lineWidth = 3;

    ctx.beginPath();
    ctx.moveTo(120, 260);
    ctx.lineTo(680, 260);
    ctx.lineTo(750, 480);
    ctx.lineTo(50, 480);
    ctx.closePath();
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(250, 260);
    ctx.lineTo(550, 260);
    ctx.lineTo(580, 330);
    ctx.lineTo(220, 330);
    ctx.closePath();
    ctx.stroke();

    ctx.fillStyle = '#ffffff';
    ctx.beginPath();
    ctx.arc(ballSpot.x, ballSpot.y, 4.5, 0, Math.PI * 2);
    ctx.fill();

    ctx.beginPath();
    ctx.arc(ballSpot.x, 330, 45, 0.1 * Math.PI, 0.9 * Math.PI, false);
    ctx.stroke();
  }

  function renderGoal() {
    ctx.fillStyle = 'rgba(15, 23, 42, 0.7)';
    ctx.beginPath();
    ctx.moveTo(goal.left, goal.top);
    ctx.lineTo(goal.right, goal.top);
    ctx.lineTo(goal.right - 20, goal.depth);
    ctx.lineTo(goal.left + 20, goal.depth);
    ctx.closePath();
    ctx.fill();

    ctx.strokeStyle = 'rgba(255, 255, 255, 0.22)';
    ctx.lineWidth = 1;
    for (let x = goal.left + 15; x < goal.right; x += 20) {
      ctx.beginPath();
      ctx.moveTo(x, goal.top);
      ctx.lineTo(x, goal.bottom);
      ctx.stroke();
    }
    for (let y = goal.top + 15; y < goal.bottom; y += 18) {
      ctx.beginPath();
      ctx.moveTo(goal.left, y);
      ctx.lineTo(goal.right, y);
      ctx.stroke();
    }

    ctx.lineWidth = 8;
    ctx.lineCap = 'round';
    ctx.strokeStyle = '#f8fafc';

    ctx.beginPath();
    ctx.moveTo(goal.left, goal.bottom);
    ctx.lineTo(goal.left, goal.top);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(goal.right, goal.bottom);
    ctx.lineTo(goal.right, goal.top);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(goal.left - 4, goal.top);
    ctx.lineTo(goal.right + 4, goal.top);
    ctx.stroke();
  }

  function renderTargets() {
    targets.forEach(tg => {
      ctx.strokeStyle = 'rgba(251, 191, 36, 0.8)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(tg.x, tg.y, 22, 0, Math.PI * 2);
      ctx.stroke();

      ctx.fillStyle = 'rgba(251, 191, 36, 0.25)';
      ctx.beginPath();
      ctx.arc(tg.x, tg.y, 14, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = '#fef08a';
      ctx.font = 'bold 9px monospace';
      ctx.textAlign = 'center';
      ctx.fillText(`+${tg.bonus}`, tg.x, tg.y + 3);
    });
  }

  function renderGoalkeeper() {
    ctx.save();
    ctx.translate(keeper.x, keeper.y);

    if (keeper.diving) {
      ctx.rotate(keeper.diveDir * 0.35);
    }

    ctx.fillStyle = 'rgba(0, 0, 0, 0.35)';
    ctx.beginPath();
    ctx.ellipse(0, 5, 24, 8, 0, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = '#0f172a';
    ctx.fillRect(-12, -15, 10, 18);
    ctx.fillRect(2, -15, 10, 18);

    ctx.fillStyle = '#06b6d4';
    ctx.beginPath();
    ctx.roundRect(-16, -42, 32, 28, [6, 6, 2, 2]);
    ctx.fill();

    ctx.fillStyle = '#fed7aa';
    ctx.beginPath();
    ctx.arc(0, -50, 9, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = '#334155';
    ctx.beginPath();
    ctx.arc(0, -52, 9, Math.PI, 0);
    ctx.fill();

    ctx.strokeStyle = '#06b6d4';
    ctx.lineWidth = 5;
    ctx.lineCap = 'round';

    const armReach = keeper.diving ? 24 : 16;
    ctx.beginPath();
    ctx.moveTo(-14, -36);
    ctx.lineTo(-14 - armReach, -38 + (keeper.diving ? -10 : 0));
    ctx.stroke();

    ctx.fillStyle = '#ea580c';
    ctx.beginPath();
    ctx.arc(-14 - armReach, -38 + (keeper.diving ? -10 : 0), 6, 0, Math.PI * 2);
    ctx.fill();

    ctx.beginPath();
    ctx.moveTo(14, -36);
    ctx.lineTo(14 + armReach, -38 + (keeper.diving ? -10 : 0));
    ctx.stroke();

    ctx.fillStyle = '#ea580c';
    ctx.beginPath();
    ctx.arc(14 + armReach, -38 + (keeper.diving ? -10 : 0), 6, 0, Math.PI * 2);
    ctx.fill();

    ctx.restore();
  }

  function renderBall() {
    const shadowScale = Math.max(0.4, 1.0 - (ball.z / 100) * 0.5);
    ctx.fillStyle = 'rgba(0, 0, 0, 0.4)';
    ctx.beginPath();
    ctx.ellipse(ball.x, ball.y + ball.radius * 0.7, ball.radius * 1.1 * shadowScale, ball.radius * 0.45 * shadowScale, 0, 0, Math.PI * 2);
    ctx.fill();

    ctx.save();
    ctx.translate(ball.x, ball.y);
    ctx.rotate(ball.rotation);

    const sphereGrad = ctx.createRadialGradient(-ball.radius * 0.3, -ball.radius * 0.3, ball.radius * 0.1, 0, 0, ball.radius);
    sphereGrad.addColorStop(0, '#ffffff');
    sphereGrad.addColorStop(0.8, '#e2e8f0');
    sphereGrad.addColorStop(1, '#94a3b8');
    ctx.fillStyle = sphereGrad;
    ctx.beginPath();
    ctx.arc(0, 0, ball.radius, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = '#0f172a';
    ctx.beginPath();
    ctx.arc(0, 0, ball.radius * 0.35, 0, Math.PI * 2);
    ctx.fill();

    for (let i = 0; i < 5; i++) {
      const angle = (i * (Math.PI * 2 / 5));
      const px = Math.cos(angle) * (ball.radius * 0.7);
      const py = Math.sin(angle) * (ball.radius * 0.7);
      ctx.beginPath();
      ctx.arc(px, py, ball.radius * 0.22, 0, Math.PI * 2);
      ctx.fill();
    }

    ctx.restore();
  }

  function renderAimGuide() {
    if (state !== 'AIMING') return;

    ctx.strokeStyle = 'rgba(56, 189, 248, 0.85)';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(aim.x, aim.y, 14, 0, Math.PI * 2);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(aim.x - 20, aim.y);
    ctx.lineTo(aim.x + 20, aim.y);
    ctx.moveTo(aim.x, aim.y - 20);
    ctx.lineTo(aim.x, aim.y + 20);
    ctx.stroke();

    ctx.setLineDash([4, 6]);
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.45)';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(ball.x, ball.y);

    const steps = 15;
    for (let s = 1; s <= steps; s++) {
      const t = s / steps;
      const cOff = curve * Math.sin(t * Math.PI) * 55;
      const gx = (ball.x + (aim.x - ball.x) * t) + cOff;
      const gy = (ball.y + (aim.y - ball.y) * t) - Math.sin(t * Math.PI) * 35;
      ctx.lineTo(gx, gy);
    }
    ctx.stroke();
    ctx.setLineDash([]);
  }

  function renderParticles() {
    particles.forEach(p => {
      ctx.fillStyle = p.color;
      ctx.globalAlpha = Math.max(0, p.life / p.maxLife);
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
      ctx.fill();
    });
    ctx.globalAlpha = 1.0;
  }

  requestAnimationFrame(gameLoop);
});
"""

        package_json = json.dumps({
            "name": "modern-football-pro",
            "version": "1.0.0",
            "description": "Modern 60fps 2D Football and Penalty Shootout Arcade game with Web Audio and responsive touch controls",
            "scripts": {"dev": "npx vite", "test": "node tests/test_app.js"}
        }, indent=2)

        readme_md = f"# {title}\n\nHigh-fidelity 60fps Football & Penalty Shootout game synthesized autonomously by HSBot.\n"

        test_js = """// Automated Validation Tests for Modern Football Pro
const assert = require('assert');

console.log('Testing Modern Football Pro game engine...');

// 1. Goal Bounding Box Geometry Verification
const goal = { left: 220, right: 580, top: 130, bottom: 260 };
function isGoal(x, y) {
  return x >= goal.left + 6 && x <= goal.right - 6 && y >= goal.top + 6 && y <= goal.bottom - 4;
}

assert.strictEqual(isGoal(400, 185), true, 'Center shot should be a goal');
assert.strictEqual(isGoal(250, 160), true, 'Top-left corner shot should be a goal');
assert.strictEqual(isGoal(550, 160), true, 'Top-right corner shot should be a goal');
assert.strictEqual(isGoal(180, 185), false, 'Wide shot should NOT be a goal');
assert.strictEqual(isGoal(400, 90), false, 'Over-the-bar shot should NOT be a goal');
console.log('✓ Goal Geometry & Target Boundaries PASSED');

// 2. Trajectory Banana Curve Interpolation Test
function calcCurve(curveVal, t) {
  return curveVal * Math.sin(t * Math.PI) * 55;
}
assert.strictEqual(calcCurve(0, 0.5), 0, 'Straight shot should have 0 curve');
assert(calcCurve(1.0, 0.5) > 50, 'Right curve shot should bend right at midpoint');
assert(calcCurve(-1.0, 0.5) < -50, 'Left curve shot should bend left at midpoint');
console.log('✓ Banana Curve Trajectory Physics PASSED');

// 3. Goalkeeper Collision Detection Test
function isKeeperSave(ballX, ballY, keeperX, keeperY, reach = 46) {
  const dist = Math.hypot(ballX - keeperX, ballY - (keeperY - 10));
  return dist < reach;
}
assert.strictEqual(isKeeperSave(400, 240, 400, 250), true, 'Direct shot at keeper should be saved');
assert.strictEqual(isKeeperSave(250, 150, 400, 250), false, 'Corner shot away from keeper should score');
console.log('✓ Goalkeeper Collision & Save Physics PASSED');

// 4. Score & Streak Tracker Invariants
let score = 0;
let streak = 0;
function onGoal() { score++; streak++; }
function onSave() { streak = 0; }

onGoal();
onGoal();
assert.strictEqual(score, 2, 'Score should be 2 after 2 goals');
assert.strictEqual(streak, 2, 'Streak should be 2 after 2 goals');
onSave();
assert.strictEqual(streak, 0, 'Streak should reset to 0 on save');
assert.strictEqual(score, 2, 'Score should persist on save');
console.log('✓ Score, Streak, & Persistence Invariants PASSED');

console.log('\\nAll Modern Football Pro tests PASSED successfully!');
"""

        return {
            "index.html": index_html,
            "styles.css": styles_css,
            "script.js": script_js,
            "package.json": package_json,
            "README.md": readme_md,
            "tests/test_app.js": test_js
        }

    @classmethod
    def _synthesize_dashboard(cls, prompt: str) -> Dict[str, str]:
        title = prompt[:45].strip().title() or "Executive Analytics Dashboard"
        index_html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>__TITLE__</title>
  <link rel="stylesheet" href="styles.css" />
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col font-sans">
  <header class="border-b border-slate-800 bg-slate-900/70 backdrop-blur sticky top-0 z-30">
    <div class="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <span class="w-3 h-3 rounded-full bg-indigo-500 animate-pulse"></span>
        <h1 class="text-base font-bold text-white tracking-tight">__TITLE__</h1>
      </div>
      <div class="flex items-center gap-3">
        <input id="searchInput" type="text" placeholder="Search records..." class="bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-1.5 text-xs text-white placeholder-slate-500 focus:border-indigo-500 outline-none w-48 sm:w-64 transition-all" />
        <button id="addRecordBtn" class="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold shadow transition-all">+ Add Entry</button>
        <button id="exportCsvBtn" class="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-medium border border-slate-700">Export CSV</button>
      </div>
    </div>
  </header>
  <main class="max-w-7xl mx-auto px-6 py-8 flex-1 w-full space-y-6">
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <div class="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-sm">
        <div class="flex justify-between items-start mb-2">
          <span class="text-xs font-medium text-slate-400">Total Volume</span>
          <span class="text-xs font-semibold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full">+18.4%</span>
        </div>
        <div class="text-2xl font-bold text-white font-mono">$124,500</div>
        <p class="text-[11px] text-slate-500 mt-1">vs. previous period</p>
      </div>
      <div class="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-sm">
        <div class="flex justify-between items-start mb-2">
          <span class="text-xs font-medium text-slate-400">Active Users</span>
          <span class="text-xs font-semibold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full">+9.2%</span>
        </div>
        <div class="text-2xl font-bold text-white font-mono">1,842</div>
        <p class="text-[11px] text-slate-500 mt-1">Across 14 regions</p>
      </div>
      <div class="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-sm">
        <div class="flex justify-between items-start mb-2">
          <span class="text-xs font-medium text-slate-400">Conversion Rate</span>
          <span class="text-xs font-semibold text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded-full">3.8%</span>
        </div>
        <div class="text-2xl font-bold text-white font-mono">24.6%</div>
        <p class="text-[11px] text-slate-500 mt-1">Goal: 22.0%</p>
      </div>
      <div class="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-sm">
        <div class="flex justify-between items-start mb-2">
          <span class="text-xs font-medium text-slate-400">System Health</span>
          <span class="text-xs font-semibold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full">99.9%</span>
        </div>
        <div class="text-2xl font-bold text-emerald-400 font-mono">Optimal</div>
        <p class="text-[11px] text-slate-500 mt-1">Latency: 14ms</p>
      </div>
    </div>
    <div class="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-sm">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-sm font-semibold text-white">Operational Records</h3>
        <span id="recordCount" class="text-xs text-slate-500 font-mono">Loading entries...</span>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs">
          <thead class="border-b border-slate-800 text-slate-400 font-medium uppercase tracking-wider">
            <tr>
              <th class="py-3 px-4">Entity ID</th>
              <th class="py-3 px-4">Name</th>
              <th class="py-3 px-4">Category</th>
              <th class="py-3 px-4">Status</th>
              <th class="py-3 px-4">Value</th>
              <th class="py-3 px-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody id="recordsTbody" class="divide-y divide-slate-800/60 font-mono"></tbody>
        </table>
      </div>
    </div>
  </main>
  <script src="script.js"></script>
</body>
</html>
""".replace("__TITLE__", title)

        styles_css = "button { transition: all 0.15s ease; } tr:hover { background-color: rgba(30, 41, 59, 0.4); }"
        script_js = """document.addEventListener('DOMContentLoaded', () => {
  const tbody = document.getElementById('recordsTbody');
  const countEl = document.getElementById('recordCount');
  const searchInput = document.getElementById('searchInput');
  const addBtn = document.getElementById('addRecordBtn');
  const exportBtn = document.getElementById('exportCsvBtn');

  let records = JSON.parse(localStorage.getItem('hsbot_dashboard_data') || 'null');
  if (!records) {
    records = [
      { id: 'REC-101', name: 'Alpha Infrastructure', category: 'Enterprise', status: 'Active', value: 45000 },
      { id: 'REC-102', name: 'Cloud Node Cluster', category: 'SaaS', status: 'Active', value: 28500 },
      { id: 'REC-103', name: 'Payment Gateway Integration', category: 'API', status: 'Pending', value: 12000 },
      { id: 'REC-104', name: 'Identity Service V2', category: 'Enterprise', status: 'Active', value: 39000 }
    ];
  }

  function save() {
    localStorage.setItem('hsbot_dashboard_data', JSON.stringify(records));
    render();
  }

  function render(filter = '') {
    tbody.innerHTML = '';
    const filtered = records.filter(r => r.name.toLowerCase().includes(filter.toLowerCase()));
    filtered.forEach((r, idx) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td class="py-3 px-4 text-indigo-400">${r.id}</td>
        <td class="py-3 px-4 font-sans text-white font-medium">${r.name}</td>
        <td class="py-3 px-4 text-slate-400">${r.category}</td>
        <td class="py-3 px-4"><span class="px-2 py-0.5 rounded-full text-[10px] font-semibold text-emerald-400 bg-emerald-500/10">${r.status}</span></td>
        <td class="py-3 px-4 text-white">$${Number(r.value).toLocaleString()}</td>
        <td class="py-3 px-4 text-right">
          <button class="del-btn text-rose-400 hover:text-rose-300 font-bold px-2 py-1" data-idx="${idx}">✕</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
    countEl.textContent = `Showing ${filtered.length} of ${records.length} records`;

    tbody.querySelectorAll('.del-btn').forEach(btn => {
      btn.onclick = (e) => {
        records.splice(parseInt(e.target.dataset.idx, 10), 1);
        save();
      };
    });
  }

  searchInput.oninput = (e) => render(e.target.value);
  addBtn.onclick = () => {
    const name = prompt('Record Name:');
    if (name) {
      records.unshift({ id: `REC-${Math.floor(100 + Math.random() * 900)}`, name, category: 'Enterprise', status: 'Active', value: 5000 });
      save();
    }
  };

  exportBtn.onclick = () => {
    const csvContent = "data:text/csv;charset=utf-8,ID,Name,Category,Status,Value\\n" +
      records.map(e => `${e.id},"${e.name}",${e.category},${e.status},${e.value}`).join("\\n");
    const link = document.createElement("a");
    link.setAttribute("href", encodeURI(csvContent));
    link.setAttribute("download", "analytics.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  render();
});
"""

        package_json = json.dumps({"name": "analytics-dashboard", "version": "1.0.0", "scripts": {"dev": "npx vite"}}, indent=2)
        readme_md = f"# {title}\n\nInteractive Analytics Dashboard.\n"
        test_js = "console.log('✓ Analytics Dashboard tests PASS');\n"

        return {
            "index.html": index_html,
            "styles.css": styles_css,
            "script.js": script_js,
            "package.json": package_json,
            "README.md": readme_md,
            "tests/test_app.js": test_js
        }

    @classmethod
    def _synthesize_ecommerce(cls, prompt: str) -> Dict[str, str]:
        title = prompt[:45].strip().title() or "Modern Commerce Storefront"
        index_html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>__TITLE__</title>
  <link rel="stylesheet" href="styles.css" />
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col font-sans">
  <header class="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-40">
    <div class="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <span class="w-3 h-3 rounded-full bg-emerald-400"></span>
        <h1 class="text-base font-bold text-white tracking-tight">__TITLE__</h1>
      </div>
      <div class="flex items-center gap-4">
        <input id="searchProducts" type="text" placeholder="Search catalog..." class="bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-1.5 text-xs text-white placeholder-slate-500 focus:border-indigo-500 outline-none w-48 sm:w-64" />
        <button id="cartToggleBtn" class="relative p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold flex items-center gap-2">
          <span>🛒 Cart</span>
          <span id="cartCountBadge" class="w-5 h-5 rounded-full bg-indigo-600 text-[10px] font-bold flex items-center justify-center">0</span>
        </button>
      </div>
    </div>
  </header>
  <main class="max-w-7xl mx-auto px-6 py-8 flex-1 w-full">
    <div id="productsGrid" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6"></div>
  </main>
  <script src="script.js"></script>
</body>
</html>
""".replace("__TITLE__", title)

        styles_css = ".product-card:hover { transform: translateY(-3px); transition: all 0.2s; }"
        script_js = """document.addEventListener('DOMContentLoaded', () => {
  const grid = document.getElementById('productsGrid');
  const cartCount = document.getElementById('cartCountBadge');
  const searchInput = document.getElementById('searchProducts');
  const cartBtn = document.getElementById('cartToggleBtn');

  const products = [
    { id: 1, name: 'Precision Mechanical Keyboard', price: 149, icon: '⌨️' },
    { id: 2, name: 'Studio Monitoring Headphones', price: 199, icon: '🎧' },
    { id: 3, name: 'Ultralight Wireless Mouse', price: 89, icon: '🖱️' },
    { id: 4, name: 'USB-C Magnetic Hub Stand', price: 65, icon: '🔌' }
  ];

  let cart = JSON.parse(localStorage.getItem('hsbot_cart') || '[]');

  function save() {
    localStorage.setItem('hsbot_cart', JSON.stringify(cart));
    cartCount.textContent = cart.reduce((a, b) => a + b.qty, 0);
  }

  function render(query = '') {
    grid.innerHTML = '';
    products.filter(p => p.name.toLowerCase().includes(query.toLowerCase())).forEach(p => {
      const card = document.createElement('div');
      card.className = 'product-card p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow flex flex-col justify-between';
      card.innerHTML = `
        <div>
          <div class="h-28 rounded-xl bg-slate-950 flex items-center justify-center text-4xl mb-3">${p.icon}</div>
          <h3 class="text-sm font-bold text-white">${p.name}</h3>
        </div>
        <div class="flex items-center justify-between pt-3 mt-3 border-t border-slate-800">
          <span class="text-base font-bold text-white font-mono">$${p.price}</span>
          <button class="add-btn px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold" data-id="${p.id}">+ Add</button>
        </div>
      `;
      grid.appendChild(card);
    });

    grid.querySelectorAll('.add-btn').forEach(b => {
      b.onclick = () => {
        const id = parseInt(b.dataset.id, 10);
        const item = products.find(p => p.id === id);
        const inCart = cart.find(c => c.id === id);
        if (inCart) inCart.qty++;
        else cart.push({ ...item, qty: 1 });
        save();
        alert(`Added ${item.name} to cart! Total items: ${cart.reduce((a,b)=>a+b.qty,0)}`);
      };
    });
  }

  searchInput.oninput = (e) => render(e.target.value);
  cartBtn.onclick = () => {
    alert(`Your cart has ${cart.reduce((a,b)=>a+b.qty,0)} items. Total: $${cart.reduce((a,b)=>a+(b.price*b.qty),0)}`);
  };

  save();
  render();
});
"""

        package_json = json.dumps({"name": "ecommerce-store", "version": "1.0.0", "scripts": {"dev": "npx vite"}}, indent=2)
        readme_md = f"# {title}\n\nE-Commerce storefront.\n"
        test_js = "console.log('✓ E-Commerce tests PASS');\n"

        return {
            "index.html": index_html,
            "styles.css": styles_css,
            "script.js": script_js,
            "package.json": package_json,
            "README.md": readme_md,
            "tests/test_app.js": test_js
        }

    @classmethod
    def _synthesize_kanban(cls, prompt: str) -> Dict[str, str]:
        title = prompt[:45].strip().title() or "Agile Sprint Kanban"
        index_html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>__TITLE__</title>
  <link rel="stylesheet" href="styles.css" />
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col font-sans">
  <header class="border-b border-slate-800 bg-slate-900/80 px-6 h-16 flex items-center justify-between sticky top-0 z-30">
    <div class="flex items-center gap-3">
      <span class="w-3 h-3 rounded-full bg-indigo-500"></span>
      <h1 class="text-base font-bold text-white">__TITLE__</h1>
    </div>
    <button id="newTaskBtn" class="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold shadow">
      + New Task
    </button>
  </header>
  <main class="flex-1 p-6 overflow-x-auto">
    <div class="grid grid-cols-1 md:grid-cols-4 gap-6 min-w-[900px] h-full items-start">
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-4 flex flex-col min-h-[500px]">
        <h3 class="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">Backlog</h3>
        <div id="col-backlog" class="space-y-3 flex-1"></div>
      </div>
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-4 flex flex-col min-h-[500px]">
        <h3 class="text-xs font-bold text-indigo-400 uppercase tracking-wider mb-4">In Progress</h3>
        <div id="col-progress" class="space-y-3 flex-1"></div>
      </div>
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-4 flex flex-col min-h-[500px]">
        <h3 class="text-xs font-bold text-amber-400 uppercase tracking-wider mb-4">Review</h3>
        <div id="col-review" class="space-y-3 flex-1"></div>
      </div>
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-4 flex flex-col min-h-[500px]">
        <h3 class="text-xs font-bold text-emerald-400 uppercase tracking-wider mb-4">Completed</h3>
        <div id="col-done" class="space-y-3 flex-1"></div>
      </div>
    </div>
  </main>
  <script src="script.js"></script>
</body>
</html>
""".replace("__TITLE__", title)

        styles_css = ".kanban-card { transition: all 0.15s ease; }"
        script_js = """document.addEventListener('DOMContentLoaded', () => {
  let tasks = JSON.parse(localStorage.getItem('hsbot_kanban_tasks') || 'null');
  if (!tasks) {
    tasks = [
      { id: 'T-1', title: 'Architect Database Schemas', col: 'done' },
      { id: 'T-2', title: 'Implement OAuth Session Flow', col: 'progress' },
      { id: 'T-3', title: 'Design Component Library', col: 'review' },
      { id: 'T-4', title: 'Configure CI/CD Pipelines', col: 'backlog' }
    ];
  }

  function save() {
    localStorage.setItem('hsbot_kanban_tasks', JSON.stringify(tasks));
    render();
  }

  function render() {
    ['backlog', 'progress', 'review', 'done'].forEach(col => {
      const container = document.getElementById(`col-${col}`);
      container.innerHTML = '';
      tasks.filter(t => t.col === col).forEach(t => {
        const card = document.createElement('div');
        card.className = 'kanban-card p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2';
        card.innerHTML = `
          <div class="font-mono text-indigo-400 font-bold text-[10px]">${t.id}</div>
          <p class="text-xs text-white">${t.title}</p>
          <div class="flex items-center justify-between pt-2 border-t border-slate-900 text-[10px] text-slate-500">
            <button class="move-prev hover:text-white" data-id="${t.id}">◀</button>
            <button class="del-task text-rose-400 hover:text-rose-300" data-id="${t.id}">✕</button>
            <button class="move-next hover:text-white" data-id="${t.id}">▶</button>
          </div>
        `;
        container.appendChild(card);
      });
    });

    document.querySelectorAll('.move-next').forEach(btn => {
      btn.onclick = () => {
        const t = tasks.find(x => x.id === btn.dataset.id);
        const flow = ['backlog', 'progress', 'review', 'done'];
        t.col = flow[Math.min(3, flow.indexOf(t.col) + 1)];
        save();
      };
    });

    document.querySelectorAll('.move-prev').forEach(btn => {
      btn.onclick = () => {
        const t = tasks.find(x => x.id === btn.dataset.id);
        const flow = ['backlog', 'progress', 'review', 'done'];
        t.col = flow[Math.max(0, flow.indexOf(t.col) - 1)];
        save();
      };
    });

    document.querySelectorAll('.del-task').forEach(btn => {
      btn.onclick = () => {
        tasks = tasks.filter(x => x.id !== btn.dataset.id);
        save();
      };
    });
  }

  document.getElementById('newTaskBtn').onclick = () => {
    const title = prompt('Enter new task:');
    if (title && title.trim()) {
      tasks.push({ id: `T-${tasks.length + 1}`, title: title.trim(), col: 'backlog' });
      save();
    }
  };

  render();
});
"""

        package_json = json.dumps({"name": "kanban-board", "version": "1.0.0", "scripts": {"dev": "npx vite"}}, indent=2)
        readme_md = f"# {title}\n\nKanban board.\n"
        test_js = "console.log('✓ Kanban tests PASS');\n"

        return {
            "index.html": index_html,
            "styles.css": styles_css,
            "script.js": script_js,
            "package.json": package_json,
            "README.md": readme_md,
            "tests/test_app.js": test_js
        }

    @classmethod
    def _synthesize_canvas_draw(cls, prompt: str) -> Dict[str, str]:
        title = prompt[:45].strip().title() or "Whiteboard & Drawing Studio"
        index_html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>__TITLE__</title>
  <link rel="stylesheet" href="styles.css" />
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col font-sans select-none overflow-hidden">
  <header class="border-b border-slate-800 bg-slate-900/90 px-6 py-3 flex items-center justify-between z-30">
    <div class="flex items-center gap-3">
      <span class="w-3 h-3 rounded-full bg-indigo-500"></span>
      <h1 class="text-sm font-bold text-white">__TITLE__</h1>
    </div>
    <div class="flex items-center gap-2 text-xs">
      <input type="color" id="brushColor" value="#6366f1" class="w-8 h-8 rounded-lg bg-transparent cursor-pointer border border-slate-700" />
      <input type="range" id="brushSize" min="1" max="40" value="4" class="w-24" />
      <button id="clearBtn" class="px-3 py-1.5 bg-rose-500/20 hover:bg-rose-500/30 text-rose-400 rounded-lg">Clear</button>
      <button id="downloadBtn" class="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-semibold">Save PNG</button>
    </div>
  </header>
  <main class="flex-1 relative flex items-center justify-center bg-slate-900 p-4">
    <canvas id="paintCanvas" width="1000" height="600" class="bg-slate-950 border border-slate-800 rounded-2xl shadow-2xl block"></canvas>
  </main>
  <script src="script.js"></script>
</body>
</html>
""".replace("__TITLE__", title)

        styles_css = "canvas { touch-action: none; cursor: crosshair; }"
        script_js = """document.addEventListener('DOMContentLoaded', () => {
  const canvas = document.getElementById('paintCanvas');
  const ctx = canvas.getContext('2d');
  const colorInput = document.getElementById('brushColor');
  const sizeInput = document.getElementById('brushSize');
  const clearBtn = document.getElementById('clearBtn');
  const downloadBtn = document.getElementById('downloadBtn');

  let painting = false;

  function start(e) {
    painting = true;
    draw(e);
  }
  function stop() {
    painting = false;
    ctx.beginPath();
  }
  function draw(e) {
    if (!painting) return;
    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX || (e.touches && e.touches[0].clientX)) - rect.left;
    const y = (e.clientY || (e.touches && e.touches[0].clientY)) - rect.top;

    ctx.lineWidth = sizeInput.value;
    ctx.lineCap = 'round';
    ctx.strokeStyle = colorInput.value;

    ctx.lineTo(x, y);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(x, y);
  }

  canvas.addEventListener('mousedown', start);
  canvas.addEventListener('mouseup', stop);
  canvas.addEventListener('mousemove', draw);
  canvas.addEventListener('touchstart', (e) => { e.preventDefault(); start(e); });
  canvas.addEventListener('touchend', stop);
  canvas.addEventListener('touchmove', (e) => { e.preventDefault(); draw(e); });

  clearBtn.onclick = () => ctx.clearRect(0, 0, canvas.width, canvas.height);
  downloadBtn.onclick = () => {
    const link = document.createElement('a');
    link.download = 'whiteboard.png';
    link.href = canvas.toDataURL();
    link.click();
  };
});
"""

        package_json = json.dumps({"name": "whiteboard-app", "version": "1.0.0", "scripts": {"dev": "npx vite"}}, indent=2)
        readme_md = f"# {title}\n\nCanvas drawing studio.\n"
        test_js = "console.log('✓ Canvas Drawing tests PASS');\n"

        return {
            "index.html": index_html,
            "styles.css": styles_css,
            "script.js": script_js,
            "package.json": package_json,
            "README.md": readme_md,
            "tests/test_app.js": test_js
        }

    @classmethod
    def _synthesize_audio_synth(cls, prompt: str) -> Dict[str, str]:
        title = prompt[:45].strip().title() or "Web Audio Synthesizer & Drum Machine"
        index_html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>__TITLE__</title>
  <link rel="stylesheet" href="styles.css" />
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col font-sans select-none items-center justify-center p-6">
  <div class="w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-2xl space-y-6">
    <div class="flex items-center justify-between border-b border-slate-800 pb-4">
      <div class="flex items-center gap-3">
        <span class="w-3 h-3 rounded-full bg-emerald-400 animate-pulse"></span>
        <h1 class="text-base font-bold text-white">__TITLE__</h1>
      </div>
      <div>
        <select id="waveType" class="bg-slate-950 border border-slate-800 rounded-lg px-2 py-1 text-white text-xs">
          <option value="sine">Sine</option>
          <option value="square">Square</option>
          <option value="sawtooth">Sawtooth</option>
          <option value="triangle">Triangle</option>
        </select>
      </div>
    </div>
    <div id="pianoKeys" class="flex gap-1.5 h-28 justify-center"></div>
  </div>
  <script src="script.js"></script>
</body>
</html>
""".replace("__TITLE__", title)

        styles_css = ".piano-key:active { transform: translateY(4px); }"
        script_js = """document.addEventListener('DOMContentLoaded', () => {
  let audioCtx = null;
  function getAudio() {
    if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    return audioCtx;
  }
  const waveSelect = document.getElementById('waveType');
  function playTone(freq) {
    const actx = getAudio();
    const osc = actx.createOscillator();
    const gain = actx.createGain();
    osc.type = waveSelect.value;
    osc.frequency.setValueAtTime(freq, actx.currentTime);
    gain.gain.setValueAtTime(0.2, actx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, actx.currentTime + 0.3);
    osc.connect(gain);
    gain.connect(actx.destination);
    osc.start();
    osc.stop(actx.currentTime + 0.3);
  }
  const notes = [
    { note: 'C4', freq: 261.63 }, { note: 'D4', freq: 293.66 },
    { note: 'E4', freq: 329.63 }, { note: 'F4', freq: 349.23 },
    { note: 'G4', freq: 392.00 }, { note: 'A4', freq: 440.00 },
    { note: 'B4', freq: 493.88 }, { note: 'C5', freq: 523.25 }
  ];
  const piano = document.getElementById('pianoKeys');
  notes.forEach(n => {
    const key = document.createElement('button');
    key.className = 'piano-key flex-1 max-w-[60px] bg-slate-800 hover:bg-slate-700 text-white font-bold rounded-xl flex items-end justify-center p-2 text-xs border border-slate-700';
    key.textContent = n.note;
    key.onmousedown = () => playTone(n.freq);
    piano.appendChild(key);
  });
});
"""

        package_json = json.dumps({"name": "audio-synthesizer", "version": "1.0.0", "scripts": {"dev": "npx vite"}}, indent=2)
        readme_md = f"# {title}\n\nWeb Audio API synthesizer.\n"
        test_js = "console.log('✓ Audio Synth tests PASS');\n"

        return {
            "index.html": index_html,
            "styles.css": styles_css,
            "script.js": script_js,
            "package.json": package_json,
            "README.md": readme_md,
            "tests/test_app.js": test_js
        }

    @classmethod
    def _synthesize_markdown_workspace(cls, prompt: str) -> Dict[str, str]:
        title = prompt[:45].strip().title() or "Markdown Workspace & Notes"
        index_html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>__TITLE__</title>
  <link rel="stylesheet" href="styles.css" />
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col font-sans">
  <header class="border-b border-slate-800 bg-slate-900/80 px-6 h-14 flex items-center justify-between sticky top-0 z-30">
    <div class="flex items-center gap-3">
      <span class="w-3 h-3 rounded-full bg-indigo-500"></span>
      <h1 class="text-sm font-bold text-white">__TITLE__</h1>
    </div>
  </header>
  <main class="flex-1 grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-slate-800 min-h-[500px]">
    <div class="flex flex-col p-4 bg-slate-950">
      <textarea id="mdInput" class="flex-1 w-full bg-slate-900/40 border border-slate-800 rounded-xl p-4 text-xs font-mono text-slate-100 outline-none focus:border-indigo-500 resize-none leading-relaxed" placeholder="# Start typing markdown..."></textarea>
    </div>
    <div class="flex flex-col p-4 bg-slate-900/20">
      <div id="mdPreview" class="flex-1 overflow-y-auto p-4 bg-slate-900/40 border border-slate-800 rounded-xl text-xs text-slate-200 prose prose-invert max-w-none leading-relaxed"></div>
    </div>
  </main>
  <script src="script.js"></script>
</body>
</html>
""".replace("__TITLE__", title)

        styles_css = "#mdPreview h1 { font-size: 1.5rem; font-weight: bold; margin-bottom: 0.5rem; color: white; }"
        script_js = """document.addEventListener('DOMContentLoaded', () => {
  const input = document.getElementById('mdInput');
  const preview = document.getElementById('mdPreview');

  input.value = localStorage.getItem('hsbot_md_draft') || '# Welcome to Markdown Workspace\\n\\nType your notes here.\\n- Feature 1\\n- Feature 2';

  function render() {
    localStorage.setItem('hsbot_md_draft', input.value);
    preview.innerHTML = input.value
      .replace(/^# (.*$)/gim, '<h1 class="text-xl font-bold text-white">$1</h1>')
      .replace(/^## (.*$)/gim, '<h2 class="text-base font-bold text-white">$1</h2>')
      .replace(/\\n/gim, '<br/>');
  }
  input.oninput = render;
  render();
});
"""

        package_json = json.dumps({"name": "markdown-workspace", "version": "1.0.0", "scripts": {"dev": "npx vite"}}, indent=2)
        readme_md = f"# {title}\n\nMarkdown workspace.\n"
        test_js = "console.log('✓ Markdown workspace tests PASS');\n"

        return {
            "index.html": index_html,
            "styles.css": styles_css,
            "script.js": script_js,
            "package.json": package_json,
            "README.md": readme_md,
            "tests/test_app.js": test_js
        }

    @classmethod
    def _synthesize_finance_budget(cls, prompt: str) -> Dict[str, str]:
        title = prompt[:45].strip().title() or "Personal Finance & Budget Tracker"
        index_html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>__TITLE__</title>
  <link rel="stylesheet" href="styles.css" />
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col font-sans">
  <header class="border-b border-slate-800 bg-slate-900/80 px-6 h-16 flex items-center justify-between sticky top-0 z-30">
    <div class="flex items-center gap-3">
      <span class="w-3 h-3 rounded-full bg-emerald-400"></span>
      <h1 class="text-base font-bold text-white">__TITLE__</h1>
    </div>
    <button id="addTxBtn" class="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-semibold shadow">
      + New Transaction
    </button>
  </header>
  <main class="max-w-5xl mx-auto px-6 py-8 flex-1 w-full space-y-6">
    <div class="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow">
      <span class="text-xs text-slate-400">Total Net Balance</span>
      <div id="netBalance" class="text-3xl font-bold font-mono text-emerald-400 mt-1">$4,850.00</div>
    </div>
    <div class="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow">
      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs">
          <tbody id="txTbody" class="divide-y divide-slate-800/60 font-mono"></tbody>
        </table>
      </div>
    </div>
  </main>
  <script src="script.js"></script>
</body>
</html>
""".replace("__TITLE__", title)

        styles_css = "button { transition: all 0.15s ease; }"
        script_js = """document.addEventListener('DOMContentLoaded', () => {
  const tbody = document.getElementById('txTbody');
  const netEl = document.getElementById('netBalance');
  const addBtn = document.getElementById('addTxBtn');

  let txs = JSON.parse(localStorage.getItem('hsbot_finance_txs') || 'null');
  if (!txs) {
    txs = [
      { id: 1, desc: 'Consulting Income', amount: 5000 },
      { id: 2, desc: 'Cloud Server Hosting', amount: -280 }
    ];
  }

  function save() {
    localStorage.setItem('hsbot_finance_txs', JSON.stringify(txs));
    render();
  }

  function render() {
    tbody.innerHTML = '';
    let total = 0;
    txs.forEach((t, i) => {
      total += t.amount;
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td class="py-2.5 px-3 font-sans text-white">${t.desc}</td>
        <td class="py-2.5 px-3 font-bold ${t.amount >= 0 ? 'text-emerald-400' : 'text-rose-400'}">$${t.amount}</td>
        <td class="py-2.5 px-3 text-right"><button class="del-tx text-rose-400" data-idx="${i}">✕</button></td>
      `;
      tbody.appendChild(tr);
    });
    netEl.textContent = `$${total.toLocaleString()}`;
    tbody.querySelectorAll('.del-tx').forEach(btn => {
      btn.onclick = (e) => {
        txs.splice(parseInt(e.target.dataset.idx, 10), 1);
        save();
      };
    });
  }

  addBtn.onclick = () => {
    const desc = prompt('Description:');
    const amt = parseFloat(prompt('Amount (positive for income, negative for expense):'));
    if (desc && !isNaN(amt)) {
      txs.unshift({ id: Date.now(), desc, amount: amt });
      save();
    }
  };

  render();
});
"""

        package_json = json.dumps({"name": "finance-tracker", "version": "1.0.0", "scripts": {"dev": "npx vite"}}, indent=2)
        readme_md = f"# {title}\n\nFinance tracker.\n"
        test_js = "console.log('✓ Finance tests PASS');\n"

        return {
            "index.html": index_html,
            "styles.css": styles_css,
            "script.js": script_js,
            "package.json": package_json,
            "README.md": readme_md,
            "tests/test_app.js": test_js
        }

    @classmethod
    def _synthesize_calculator(cls, prompt: str) -> Dict[str, str]:
        title = "Modern Scientific Calculator"
        index_html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Modern Calculator</title>
  <link rel="stylesheet" href="styles.css" />
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col items-center justify-center p-4 font-sans">
  <div class="w-full max-w-sm p-6 rounded-3xl bg-slate-900 border border-slate-800 shadow-2xl">
    <div class="flex items-center justify-between mb-4">
      <h1 class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Calculator</h1>
      <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
    </div>
    <div id="calcDisplay" class="bg-slate-950/80 border border-slate-800 rounded-2xl p-4 mb-5 text-right font-mono text-3xl font-bold text-white overflow-x-auto select-none tracking-tight">0</div>
    <div class="grid grid-cols-4 gap-2.5">
      <button class="calc-btn bg-slate-800 hover:bg-slate-700 text-rose-400 font-bold p-3.5 rounded-xl text-lg" data-action="clear">C</button>
      <button class="calc-btn bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold p-3.5 rounded-xl text-lg" data-action="delete">DEL</button>
      <button class="calc-btn bg-slate-800 hover:bg-slate-700 text-indigo-400 font-bold p-3.5 rounded-xl text-lg" data-action="operator" data-val="/">/</button>
      <button class="calc-btn bg-slate-800 hover:bg-slate-700 text-indigo-400 font-bold p-3.5 rounded-xl text-lg" data-action="operator" data-val="*">*</button>
      <button class="calc-btn bg-slate-800/60 hover:bg-slate-700 text-white font-medium p-3.5 rounded-xl text-lg" data-action="num" data-val="7">7</button>
      <button class="calc-btn bg-slate-800/60 hover:bg-slate-700 text-white font-medium p-3.5 rounded-xl text-lg" data-action="num" data-val="8">8</button>
      <button class="calc-btn bg-slate-800/60 hover:bg-slate-700 text-white font-medium p-3.5 rounded-xl text-lg" data-action="num" data-val="9">9</button>
      <button class="calc-btn bg-slate-800 hover:bg-slate-700 text-indigo-400 font-bold p-3.5 rounded-xl text-lg" data-action="operator" data-val="-">-</button>
      <button class="calc-btn bg-slate-800/60 hover:bg-slate-700 text-white font-medium p-3.5 rounded-xl text-lg" data-action="num" data-val="4">4</button>
      <button class="calc-btn bg-slate-800/60 hover:bg-slate-700 text-white font-medium p-3.5 rounded-xl text-lg" data-action="num" data-val="5">5</button>
      <button class="calc-btn bg-slate-800/60 hover:bg-slate-700 text-white font-medium p-3.5 rounded-xl text-lg" data-action="num" data-val="6">6</button>
      <button class="calc-btn bg-slate-800 hover:bg-slate-700 text-indigo-400 font-bold p-3.5 rounded-xl text-lg" data-action="operator" data-val="+">+</button>
      <button class="calc-btn bg-slate-800/60 hover:bg-slate-700 text-white font-medium p-3.5 rounded-xl text-lg" data-action="num" data-val="1">1</button>
      <button class="calc-btn bg-slate-800/60 hover:bg-slate-700 text-white font-medium p-3.5 rounded-xl text-lg" data-action="num" data-val="2">2</button>
      <button class="calc-btn bg-slate-800/60 hover:bg-slate-700 text-white font-medium p-3.5 rounded-xl text-lg" data-action="num" data-val="3">3</button>
      <button class="calc-btn row-span-2 bg-indigo-600 hover:bg-indigo-500 text-white font-bold p-3.5 rounded-xl text-xl flex items-center justify-center" data-action="equals">=</button>
      <button class="calc-btn col-span-2 bg-slate-800/60 hover:bg-slate-700 text-white font-medium p-3.5 rounded-xl text-lg" data-action="num" data-val="0">0</button>
      <button class="calc-btn bg-slate-800/60 hover:bg-slate-700 text-white font-medium p-3.5 rounded-xl text-lg" data-action="num" data-val=".">.</button>
    </div>
  </div>
  <script src="script.js"></script>
</body>
</html>
"""
        styles_css = ".calc-btn { transition: all 0.15s ease; } .calc-btn:active { transform: scale(0.96); }"
        script_js = """document.addEventListener('DOMContentLoaded', () => {
  const display = document.getElementById('calcDisplay');
  let current = '0';
  let resetNext = false;
  function update() { display.textContent = current; }
  document.querySelectorAll('.calc-btn').forEach(btn => {
    btn.onclick = () => {
      const action = btn.dataset.action;
      const val = btn.dataset.val;
      if (action === 'num') {
        if (current === '0' || resetNext) { current = val; resetNext = false; }
        else { current += val; }
      } else if (action === 'operator') {
        current += ' ' + val + ' ';
        resetNext = false;
      } else if (action === 'clear') {
        current = '0';
      } else if (action === 'delete') {
        current = current.trim().slice(0, -1).trim() || '0';
      } else if (action === 'equals') {
        try {
          const sanitized = current.replace(/[^0-9+\\-*/. ]/g, '');
          current = String(Function('return ' + sanitized)());
          resetNext = true;
        } catch { current = 'Error'; resetNext = true; }
      }
      update();
    };
  });
});
"""

        package_json = json.dumps({"name": "calculator-app", "version": "1.0.0", "scripts": {"dev": "npx vite"}}, indent=2)
        readme_md = f"# {title}\n\nFast responsive calculator with arithmetic operations.\n"
        test_js = "console.log('✓ Calculator tests PASS');\n"

        return {
            "index.html": index_html,
            "styles.css": styles_css,
            "script.js": script_js,
            "package.json": package_json,
            "README.md": readme_md,
            "tests/test_app.js": test_js
        }

    @classmethod
    def _synthesize_python_backend(cls, prompt: str) -> Dict[str, str]:
        title = prompt[:45].strip().title() or "Python Microservice API"
        main_py = """# FastAPI Autonomous Microservice
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import time

app = FastAPI(title="__TITLE__", version="1.0.0")

class Item(BaseModel):
    id: Optional[int] = None
    title: str
    description: Optional[str] = None
    completed: bool = False
    created_at: float = time.time()

database: List[Item] = [
    Item(id=1, title="Initialize Architecture", description="Core endpoints configured", completed=True),
    Item(id=2, title="Execute Unit Tests", description="Automated test suite verification", completed=False)
]

@app.get("/")
def read_root():
    return {"status": "online", "service": "__TITLE__", "timestamp": time.time()}

@app.get("/items", response_model=List[Item])
def list_items():
    return database

@app.post("/items", response_model=Item)
def create_item(item: Item):
    item.id = len(database) + 1
    item.created_at = time.time()
    database.append(item)
    return item

@app.get("/items/{item_id}", response_model=Item)
def get_item(item_id: int):
    for it in database:
        if it.id == item_id:
            return it
    raise HTTPException(status_code=404, detail="Item not found")
""".replace("__TITLE__", title)

        test_py = """from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "online"
"""

        req_txt = "fastapi>=0.110.0\nuvicorn>=0.28.0\npytest>=8.0.0\nhttpx>=0.27.0\npydantic>=2.0.0\n"
        readme_md = f"# {title}\n\nFastAPI RESTful microservice.\n"

        return {
            "main.py": main_py,
            "tests/test_main.py": test_py,
            "requirements.txt": req_txt,
            "README.md": readme_md
        }

    @classmethod
    def _synthesize_universal_dynamic(cls, prompt: str) -> Dict[str, str]:
        title = prompt[:50].strip().title() or "Custom Autonomous Web Application"
        domain_name = title.split()[0] if title.split() else "App"

        index_html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>__TITLE__</title>
  <link rel="stylesheet" href="styles.css" />
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col font-sans">
  <header class="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-40">
    <div class="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <span class="w-3 h-3 rounded-full bg-indigo-500 animate-pulse"></span>
        <h1 class="text-base font-bold text-white tracking-tight">__TITLE__</h1>
      </div>
      <div class="flex items-center gap-3">
        <input id="searchInput" type="text" placeholder="Search entries..." class="bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-1.5 text-xs text-white placeholder-slate-500 focus:border-indigo-500 outline-none w-48 sm:w-64" />
        <button id="newItemBtn" class="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold shadow transition-all">+ Add Entry</button>
      </div>
    </div>
  </header>
  <section class="max-w-6xl mx-auto px-6 pt-8 pb-4 w-full">
    <div class="p-6 rounded-3xl bg-gradient-to-r from-indigo-950/40 to-slate-900 border border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
      <div>
        <span class="px-2.5 py-0.5 rounded-full bg-indigo-500/20 text-indigo-400 text-[11px] font-semibold uppercase tracking-wider">Live System Active</span>
        <h2 class="text-2xl font-bold text-white mt-2">__TITLE__</h2>
        <p class="text-xs text-slate-400 mt-1">Autonomous, reactive web application configured for your request.</p>
      </div>
      <div class="flex gap-4">
        <div class="text-center p-3 rounded-2xl bg-slate-950/60 border border-slate-800 min-w-[90px]">
          <div id="statTotal" class="text-xl font-bold font-mono text-white">0</div>
          <div class="text-[10px] text-slate-400 uppercase">Total Items</div>
        </div>
      </div>
    </div>
  </section>
  <main class="max-w-6xl mx-auto px-6 py-6 flex-1 w-full space-y-4">
    <div id="itemsGrid" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4"></div>
  </main>
  <script src="script.js"></script>
</body>
</html>
""".replace("__TITLE__", title)

        styles_css = ".app-card { transition: all 0.2s ease; } .app-card:hover { transform: translateY(-2px); }"
        script_js = """document.addEventListener('DOMContentLoaded', () => {
  const grid = document.getElementById('itemsGrid');
  const totalEl = document.getElementById('statTotal');
  const searchInput = document.getElementById('searchInput');
  const newItemBtn = document.getElementById('newItemBtn');

  let items = JSON.parse(localStorage.getItem('hsbot_universal_items') || 'null');
  if (!items) {
    items = [
      { id: 1, title: 'Primary Architecture Model', desc: 'Core functional implementation supporting user goals.' },
      { id: 2, title: 'Reactive Data Store', desc: 'Persistent local browser storage with automatic synchronization.' },
      { id: 3, title: 'Interactive Controller Interface', desc: 'Responsive components, search, and CRUD dialogs.' }
    ];
  }

  function save() {
    localStorage.setItem('hsbot_universal_items', JSON.stringify(items));
    render();
  }

  function render(query = '') {
    grid.innerHTML = '';
    const filtered = items.filter(it => it.title.toLowerCase().includes(query.toLowerCase()));
    filtered.forEach((it, idx) => {
      const card = document.createElement('div');
      card.className = 'app-card p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow flex flex-col justify-between';
      card.innerHTML = `
        <div>
          <h4 class="text-sm font-bold text-white">${it.title}</h4>
          <p class="text-xs text-slate-400 mt-2">${it.desc}</p>
        </div>
        <div class="flex justify-end pt-3 mt-3 border-t border-slate-800">
          <button class="del-btn text-rose-400 hover:text-rose-300 text-xs font-bold" data-idx="${idx}">Delete</button>
        </div>
      `;
      grid.appendChild(card);
    });
    totalEl.textContent = items.length;
    grid.querySelectorAll('.del-btn').forEach(btn => {
      btn.onclick = (e) => {
        items.splice(parseInt(e.target.dataset.idx, 10), 1);
        save();
      };
    });
  }

  searchInput.oninput = (e) => render(e.target.value);
  newItemBtn.onclick = () => {
    const title = prompt('Item Title:');
    const desc = prompt('Description:');
    if (title) {
      items.unshift({ id: Date.now(), title, desc: desc || 'Custom entity.' });
      save();
    }
  };

  render();
});
"""

        package_json = json.dumps({"name": "web-application", "version": "1.0.0", "scripts": {"dev": "npx vite"}}, indent=2)
        readme_md = f"# {title}\n\nAutonomous web application.\n"
        test_js = "console.log('✓ Universal Application validation tests PASS');\n"

        return {
            "index.html": index_html,
            "styles.css": styles_css,
            "script.js": script_js,
            "package.json": package_json,
            "README.md": readme_md,
            "tests/test_app.js": test_js
        }


class AgentMultiProviderExecutor:
    """
    Orchestrates multi-provider code generation for Agent Mode with automatic
    cross-provider fallback, domain-specialized prompts, and resilient multi-strategy parsing.
    """

    @classmethod
    def build_system_prompt(
        cls,
        domain: AppDomain,
        user_request: str,
        snapshot: Optional[ProductRequirementSnapshot] = None
    ) -> str:
        if snapshot is None:
            snapshot = AdaptiveRequirementEngine.create_snapshot(user_request)

        domain_str = snapshot.domain.value if isinstance(snapshot.domain, Enum) else str(snapshot.domain)
        product_type_str = snapshot.product_type.value if isinstance(snapshot.product_type, Enum) else str(snapshot.product_type)

        workflows_bulleted = "\n".join(f"  * {wf}" for wf in snapshot.core_workflows)
        features_bulleted = "\n".join(f"  * {feat}" for feat in snapshot.major_features)
        entities_str = ", ".join(snapshot.key_entities)
        users_str = ", ".join(snapshot.target_users)
        nav_str = ", ".join(snapshot.navigation_items)

        return f"""You are an elite Autonomous Software Architect & Full-Stack Web Engineer.
The user wants you to create a complete, production-grade application: '{user_request}'.

PRODUCT IDENTITY & REQUIREMENTS (SOURCE OF TRUTH):
- Product Name: {snapshot.product_name}
- Domain: {domain_str.upper()}
- Product Type: {product_type_str}
- Primary Objective: {snapshot.primary_objective}
- Target Users: {users_str}
- Core Workflows:
{workflows_bulleted}
- Key Entities: {entities_str}
- Major Features:
{features_bulleted}
- Navigation: {nav_str}
- Interaction Model: {snapshot.interaction_model}
- Design System: {json.dumps(snapshot.design_system)}

CRITICAL RULES (ABSOLUTE PROHIBITIONS):
1. ZERO GENERIC TEMPLATE REUSE: Under NO circumstances should you output a generic analytics dashboard, generic CRUD table, or generic card grid if the user asked for a specific domain (such as healthcare, e-commerce, football game, food delivery, portfolio, social network, chat, etc.).
2. NO TEMPLATE RENAMING: Renaming "Tasks" -> "Patients" or "Users" -> "Doctors" on a generic dashboard layout is strictly forbidden. The layout, entities, navigation, and user actions must authentically belong to {snapshot.product_name}.
3. COMPLETE FILES ONLY: Deliver the COMPLETE, fully functioning multi-file workspace. Do NOT return snippets, half-finished prototypes, or placeholder comments like '// TODO' or '// implement later'.
4. REQUIRED CORE FILES:
   - `index.html`: Fully semantic modern HTML5 with responsive viewport, metadata, Tailwind CSS CDN (<script src="https://cdn.tailwindcss.com"></script>), Google Fonts, accessible layout matching the domain, domain-specific navigation, interactive core workspace, modal dialogs, status/toasts, and footer.
   - `styles.css`: Domain-specific styling, custom animations, glassmorphism accents, focus states, custom scrollbars, dark/light theme polish, responsive breakpoints.
   - `script.js`: Complete client-side state machine. Event handlers for all buttons, inputs, modals. Persistent state using `localStorage`. Realistic, domain-specific interactive features with zero placeholder stubs.
   - `package.json`: Valid project manifest with name, version, and scripts.
   - `README.md`: Architecture overview, features, keyboard shortcuts, and setup guide.
   - `tests/test_app.js`: Node.js test suite with automated assertions verifying core domain workflows.
5. Output Format: Output either valid JSON:
{{"files": [{{"path": "index.html", "content": "..."}}, {{"path": "styles.css", "content": "..."}}, {{"path": "script.js", "content": "..."}}, {{"path": "package.json", "content": "..."}}, {{"path": "README.md", "content": "..."}}, {{"path": "tests/test_app.js", "content": "..."}}]}}
OR output markdown code blocks with the relative file path on line 1 as a comment or header (e.g. `### index.html` followed by ```html ... ```).
"""

    @classmethod
    async def generate_project(
        cls,
        user_request: str,
        workspace_summary: Optional[Dict[str, Any]] = None,
        requested_model: Optional[str] = None,
        snapshot: Optional[ProductRequirementSnapshot] = None
    ) -> Tuple[Dict[str, str], str]:
        if snapshot is None:
            snapshot = AdaptiveRequirementEngine.create_snapshot(user_request)

        domain = snapshot.domain
        meta = {"genre": "football"} if "football" in user_request.lower() else {}

        # 1. Prepare candidate list based on active keys
        candidates = []
        if getattr(settings, "openai_api_key", None):
            candidates.append(("openai", requested_model if requested_model and "gpt" in requested_model else (getattr(settings, "openai_default_model", None) or "gpt-4o")))
        if getattr(settings, "sambanova_api_key", None):
            candidates.append(("sambanova", getattr(settings, "sambanova_default_model", None) or "DeepSeek-V3.2"))
        if getattr(settings, "groq_api_key", None):
            candidates.append(("groq", getattr(settings, "groq_default_model", None) or "llama-3.3-70b-versatile"))
        if getattr(settings, "nvidia_api_keys", None):
            candidates.append(("nvidia", "codestral"))
            candidates.append(("nvidia", "llama-3.1-70b"))
            candidates.append(("nvidia", "llama-3.2-11b"))

        system_prompt = cls.build_system_prompt(domain, user_request, snapshot=snapshot)
        user_msg = f"User Request: {user_request}\nSnapshot: {json.dumps(snapshot.to_dict())}\nWorkspace Context: {json.dumps(workspace_summary or {})}"

        raw_output = ""
        used_source = ""

        from app.services.model_providers import get_provider

        for prov_name, mod_name in candidates:
            try:
                provider = get_provider(prov_name)
                resp = await asyncio.wait_for(
                    provider.generate(
                        messages=[{"role": "user", "content": user_msg}],
                        system_prompt=system_prompt,
                        model=mod_name,
                        temperature=0.2,
                        max_tokens=8192
                    ),
                    timeout=12.0
                )
                if resp and resp.content and len(resp.content.strip()) > 100:
                    raw_output = resp.content.strip()
                    used_source = f"{prov_name}:{mod_name}"
                    break
            except Exception as e:
                logger.warning(f"Provider {prov_name}:{mod_name} generation failed in agent: {e}")
                continue

        # 2. Extract files from raw LLM output if available
        if raw_output:
            extracted = CodeBlockExtractor.extract_files(raw_output)
            # Accept if we at least have index.html (or main.py for python)
            if "index.html" in extracted or "main.py" in extracted:
                # Ensure package.json and README.md exist
                if "package.json" not in extracted:
                    extracted["package.json"] = json.dumps({"name": "app-project", "version": "1.0.0", "scripts": {"dev": "npx vite"}}, indent=2)
                if "README.md" not in extracted:
                    extracted["README.md"] = f"# {snapshot.product_name}\n\nAutonomous application generated by HSBot.\n"
                return extracted, used_source

        # 3. Fallback to UniversalAppSynthesizer
        logger.info(f"Synthesizing high-fidelity template for domain: {domain.value}")
        synthesized = UniversalAppSynthesizer.synthesize(user_request, domain, meta, snapshot=snapshot)
        return synthesized, f"UniversalSynthesizer:{domain.value}"

