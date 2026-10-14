import streamlit as st #can be alterd according to the user needs
from utils.authentication import check_authentication
from utils.database import save_user_profile, get_user_profile
from streamlit_lottie import st_lottie
import requests
from streamlit_extras.colored_header import colored_header

# Function to load lottie animations
def load_lottieurl(url):
    try:
        r = requests.get(url)
        if r.status_code != 200:
            return None
        return r.json()
    except:
        return None

# Check if the user is authenticated
check_authentication()

# Page configuration
st.set_page_config(
    page_title="User Profile - NutriTrack",
    page_icon="👤",
    layout="wide"
)

#as user can chnage the interface on that project
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem !important;
        font-weight: 600;
        margin-bottom: 1rem;
        color: #00DBAD;
    }
    .profile-container {
        animation: fadeIn 0.8s ease-in-out;
    }
    @keyframes fadeIn {
        0% {opacity: 0; transform: translateY(20px);}
        100% {opacity: 1; transform: translateY(0);}
    }
    .stButton>button {
        background-color: #00DBAD !important;
        color: #0E1117 !important;
        font-weight: 600 !important;
        border: none !important;
        border-radius: 5px !important;
        padding: 10px 20px !important;
        transition: all 0.3s ease !important;
    }
    .stButton>button:hover {
        background-color: #00B894 !important;
        box-shadow: 0 5px 15px rgba(0,0,0,0.2) !important;
        transform: translateY(-2px) !important;
    }
    .metric-card {
        background-color: #262730;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
    }
    .metric-label {
        font-weight: 600;
        color: #00DBAD;
    }
    .metric-value {
        font-size: 1.2rem;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)

# Load profile animation
profile_animation = load_lottieurl("https://assets3.lottiefiles.com/packages/lf20_jAljUv.json")

# Custom header
colored_header(
    label="User Profile",
    description="Setup your personal information for customized recommendations",
    color_name="green-70",
)

# Display animation
if profile_animation:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st_lottie(profile_animation, height=200, key="profile")

# Get existing profile if available
profile = get_user_profile(st.session_state.user_id)

# Create a form for user profile information
with st.form("profile_form"):
    # Two columns for layout
    col1, col2 = st.columns(2)
    
    with col1:
        # Physical measurements
        weight = st.number_input(
            "Weight (kg)", 
            min_value=30.0, 
            max_value=250.0, 
            value=float(profile['weight']) if profile and profile['weight'] else 70.0,
            step=0.1,
            help="Enter your weight in kilograms"
        )
        
        height = st.number_input(
            "Height (cm)", 
            min_value=100.0, 
            max_value=250.0, 
            value=float(profile['height']) if profile and profile['height'] else 170.0,
            step=0.1,
            help="Enter your height in centimeters"
        )
        
        age = st.number_input(
            "Age", 
            min_value=18, 
            max_value=100, 
            value=int(profile['age']) if profile and profile['age'] else 30,
            help="Enter your age in years"
        )
        
        gender = st.selectbox(
            "Gender",
            options=["Male", "Female"],
            index=0 if not profile or profile['gender'] == "Male" else 1,
            help="Select your gender for accurate calculations"
        )
    
    with col2:
        # Fitness goals and activity level
        goal = st.selectbox(
            "What is your fitness goal?",
            options=["Maintaining", "Bulking", "Cutting"],
            index=0 if not profile else ["Maintaining", "Bulking", "Cutting"].index(profile['goal']) if profile['goal'] else 0,
            help="Select your fitness goal"
        )
        
        activity_level = st.selectbox(
            "Activity Level",
            options=[
                "Sedentary (little or no exercise)",
                "Lightly active (light exercise/sports 1-3 days/week)",
                "Moderately active (moderate exercise/sports 3-5 days/week)",
                "Very active (hard exercise/sports 6-7 days/week)",
                "Extra active (very hard exercise & physical job or training twice a day)"
            ],
            index=0 if not profile else ["sedentary", "lightly_active", "moderately_active", "very_active", "extra_active"].index(profile['activity_level']) if profile['activity_level'] else 0,
            help="Select your typical activity level"
        )
        
        # Map activity level selection to database values
        activity_mapping = {
            "Sedentary (little or no exercise)": "sedentary",
            "Lightly active (light exercise/sports 1-3 days/week)": "lightly_active",
            "Moderately active (moderate exercise/sports 3-5 days/week)": "moderately_active",
            "Very active (hard exercise/sports 6-7 days/week)": "very_active",
            "Extra active (very hard exercise & physical job or training twice a day)": "extra_active"
        }
    
    # Submit button
    submitted = st.form_submit_button("Save Profile")
    
    if submitted:
        # Save profile to database
        if save_user_profile(
            st.session_state.user_id,
            weight,
            height,
            age,
            gender,
            goal,
            activity_mapping[activity_level]
        ):
            st.success("Profile updated successfully!")
            st.info("Head to the Health Metrics page to see your calculated metrics.")
        else:
            st.error("Failed to update profile. Please try again.")

# Display profile summary if available
if profile:
    st.markdown("<div class='profile-container'>", unsafe_allow_html=True)
    st.subheader("Current Profile")
    
    # Create metrics display with improved styling
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-label">Weight</div>
            <div class="metric-value">%s kg</div>
        </div>
        """ % profile['weight'], unsafe_allow_html=True)
        
    with col2:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-label">Height</div>
            <div class="metric-value">%s cm</div>
        </div>
        """ % profile['height'], unsafe_allow_html=True)
        
    with col3:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-label">Age</div>
            <div class="metric-value">%s years</div>
        </div>
        """ % profile['age'], unsafe_allow_html=True)
        
    with col4:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-label">Goal</div>
            <div class="metric-value">%s</div>
        </div>
        """ % profile['goal'], unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)
