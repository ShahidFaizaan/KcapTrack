import streamlit as st
import os
from utils.authentication import login, register, check_authentication
from utils.database import initialize_database
from streamlit_lottie import st_lottie
import json
from streamlit_extras.colored_header import colored_header
from streamlit_extras.switch_page_button import switch_page
from streamlit_extras.card import card
import requests
from datetime import datetime

# Initialize the database when the app starts
initialize_database()

# Function to load lottie animations
def load_lottieurl(url):
    try:
        r = requests.get(url)
        if r.status_code != 200:
            return None
        return r.json()
    except:
        return None

def load_lottiefile(filepath):
    with open(filepath, "r") as f:
        return json.load(f)

# Page configuration
st.set_page_config(
    page_title="KcapTrack-(Capture.Track.Transform)",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state variables if they don't exist
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'username' not in st.session_state:
    st.session_state.username = None
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# Custom CSS with enhanced animations and colorful UI
st.markdown("""
<style>
    /* Global styles */
    .main-header {
        font-size: 2.5rem !important;
        font-weight: 800;
        margin-bottom: 1rem;
        background: linear-gradient(90deg, #00DBAD, #00ACFF, #FF5E78);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        animation: colorFlow 8s ease infinite;
    }
    
    @keyframes colorFlow {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    .sub-header {
        font-size: 1.5rem !important;
        font-weight: 600;
        margin-bottom: 1rem;
        color: #00DBAD;
    }
    
    /* Card styles with enhanced animations */
    .card-container {
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 20px;
        background: linear-gradient(145deg, #1c1c24, #262730);
        box-shadow: 5px 5px 15px rgba(0,0,0,0.2), 
                    -5px -5px 15px rgba(255,255,255,0.03);
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        border: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    .card-container:hover {
        transform: translateY(-8px) scale(1.02);
        box-shadow: 8px 8px 25px rgba(0,0,0,0.3), 
                    -8px -8px 25px rgba(255,255,255,0.05);
        border: 1px solid rgba(0, 219, 173, 0.3);
    }
    
    .card-title {
        font-weight: 700;
        font-size: 1.3rem;
        margin-bottom: 12px;
        background: linear-gradient(90deg, #00DBAD, #00C4FF);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: 0.5px;
    }
    
    .card-text {
        font-size: 0.95rem;
        color: #E0E0E0;
        line-height: 1.6;
    }
    
    /* Button styles with enhanced animations */
    .stButton>button {
        background: linear-gradient(90deg, #00DBAD, #00BADD);
        color: #0E1117;
        font-weight: 700;
        border: none;
        border-radius: 8px;
        padding: 12px 24px;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        box-shadow: 0 4px 10px rgba(0, 219, 173, 0.3);
        letter-spacing: 0.5px;
        position: relative;
        overflow: hidden;
    }
    
    .stButton>button:hover {
        background: linear-gradient(90deg, #00DBAD, #00ACFF);
        box-shadow: 0 8px 20px rgba(0, 219, 173, 0.5);
        transform: translateY(-3px) scale(1.02);
    }
    
    .stButton>button:active {
        transform: translateY(1px) scale(0.98);
    }
    
    .stButton>button::after {
        content: '';
        position: absolute;
        top: -50%;
        left: -60%;
        width: 20%;
        height: 200%;
        background: rgba(255, 255, 255, 0.2);
        transform: rotate(30deg);
        transition: all 0.5s ease;
    }
    
    .stButton>button:hover::after {
        left: 130%;
        transition: all 0.5s ease;
    }
    
    /* Input styles */
    .st-emotion-cache-79elbk input, .st-emotion-cache-183lzff input, div[data-baseweb="input"] input, div[data-baseweb="select"] div {
        border-radius: 10px;
        border: 1px solid #3a3f4b;
        padding: 12px;
        background-color: #1a1d24;
        color: #FAFAFA;
        transition: all 0.3s ease;
        box-shadow: inset 2px 2px 5px rgba(0,0,0,0.1), 
                    inset -2px -2px 5px rgba(255,255,255,0.05);
    }
    
    .st-emotion-cache-79elbk input:focus, .st-emotion-cache-183lzff input:focus, div[data-baseweb="input"] input:focus {
        border: 1px solid #00DBAD;
        box-shadow: 0 0 10px rgba(0, 219, 173, 0.3);
    }
    
    /* Animated background */
    .auth-background {
        background: linear-gradient(-45deg, #0E1117, #1c1c24, #262730, #1a1e2e);
        background-size: 400% 400%;
        animation: gradientAnimation 15s ease infinite;
        box-shadow: inset 0 0 50px rgba(0, 219, 173, 0.1);
        border-radius: 20px;
    }
    
    @keyframes gradientAnimation {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    /* Pulse animation for icons */
    .icon-pulse {
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.1); }
        100% { transform: scale(1); }
    }
    
    /* Floating animation for cards */
    .floating {
        animation: floating 4s ease-in-out infinite;
    }
    
    @keyframes floating {
        0% { transform: translateY(0px); }
        50% { transform: translateY(-10px); }
        100% { transform: translateY(0px); }
    }
    
    /* Shimmer effect */
    .shimmer {
        position: relative;
        overflow: hidden;
    }
    
    .shimmer::after {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 50%;
        height: 100%;
        background: linear-gradient(to right, transparent, rgba(255, 255, 255, 0.05), transparent);
        animation: shimmer 3s infinite;
    }
    
    @keyframes shimmer {
        0% { left: -100%; }
        100% { left: 200%; }
    }
    
    /* Selection color */
    ::selection {
        background-color: rgba(0, 219, 173, 0.3);
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# Load animations
health_animation = load_lottieurl("https://assets8.lottiefiles.com/packages/lf20_l5qvxwtf.json")
nutrition_animation = load_lottieurl("https://assets8.lottiefiles.com/packages/lf20_vPnn3K.json")
login_animation = load_lottieurl("https://assets9.lottiefiles.com/packages/lf20_wVaKqz.json")

# App header with mobile app style
st.markdown("""
<div style="display: flex; justify-content: center; margin-bottom: 1rem;">
    <div style="
        background-color: #00DBAD; 
        border-radius: 25px; 
        padding: 10px 20px;
        box-shadow: 0 4px 10px rgba(0.1,0.2,0.4,0.5);
        display: inline-block;
        ">
        <span style="font-size: 1.5rem; font-weight: 900; color: #0E1117;"><h3>KcapTrack</h3></span>
        <span style="font-size: 1rem; margin-left: 3px; color: #0E1117;">Capture.Track.Transform</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Display login form if user is not authenticated
if not st.session_state.authenticated:
    st.markdown("<div class='auth-background'>", unsafe_allow_html=True)
    
    # Display animation
    if login_animation:
        st_lottie(login_animation, height=200, key="login_anim")
    
    st.markdown("<h2 class='sub-header' style='text-align:center;'>Access Your Account</h2>", unsafe_allow_html=True)
    
    # Create tabs for login and registration
    tab1, tab2 = st.tabs(["🔑 Login", "📝 Register"])
    
    with tab1:
        # Login form with improved styling
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            login_username = st.text_input("Username", key="login_username")
            login_password = st.text_input("Password", type="password", key="login_password")
            login_button = st.button("Login", use_container_width=True)
            
            if login_button:
                if login(login_username, login_password):
                    st.success("Login successful!")
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Invalid username or password")
    
    with tab2:
        # Registration form with improved styling and user metrics collection
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("<h3 style='text-align:center; color:#00DBAD;'>Account Details</h3>", unsafe_allow_html=True)
            reg_username = st.text_input("Username", key="reg_username")
            reg_password = st.text_input("Password", type="password", key="reg_password")
            reg_confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm_password")
            
            st.markdown("<h3 style='text-align:center; color:#00DBAD; margin-top:20px;'>Physical Details</h3>", unsafe_allow_html=True)
            
            age = st.number_input("Age (years)", min_value=13, max_value=100, value=30)
            
            col_a, col_b = st.columns(2)
            with col_a:
                weight = st.number_input("Weight (kg)", min_value=30.0, max_value=300.0, value=70.0, step=0.1)
            with col_b:
                height = st.number_input("Height (cm)", min_value=120.0, max_value=250.0, value=170.0, step=0.1)
            
            gender = st.selectbox(
                "Gender", 
                options=["Male", "Female"],
                index=0
            )
            
            activity_level = st.select_slider(
                "Activity Level",
                options=["Sedentary", "Lightly Active", "Moderately Active", "Very Active", "Extremely Active"],
                value="Moderately Active"
            )
            
            goal = st.selectbox(
                "Fitness Goal", 
                options=["Bulking", "Cutting", "Maintaining"],
                index=2
            )
            
            reg_button = st.button("Register", use_container_width=True)
            
            if reg_button:
                if not reg_username or not reg_password:
                    st.error("Username and password are required")
                elif reg_password != reg_confirm_password:
                    st.error("Passwords do not match")
                else:
                    # Store user metrics in session state to use after registration
                    st.session_state.new_user_metrics = {
                        "age": age,
                        "weight": weight,
                        "height": height,
                        "gender": gender,
                        "activity_level": activity_level,
                        "goal": goal
                    }
                    
                    if register(reg_username, reg_password):
                        st.success("Registration successful! Please login.")
                        # Will save the metrics after login in the user profile page
                    else:
                        st.error("Username already exists or registration failed")
    
    st.markdown("</div>", unsafe_allow_html=True)

# Display navigation to other pages if user is authenticated
else:
    # Add mobile app-like style with enhanced animations and colors
    st.markdown("""
    <style>
    /* App Container */
    .mobile-container {
        max-width: 480px;
        margin: 0 auto;
        background: linear-gradient(135deg, #0a0c12 0%, #131722 100%);
        min-height: 100vh;
        padding: 15px;
        box-sizing: border-box;
        box-shadow: 0 0 30px rgba(0,0,0,0.5);
        border-radius: 20px;
        position: relative;
        overflow: hidden;
    }
    
    /* Animated stars background */
    .mobile-container::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-image: 
            radial-gradient(circle, rgba(255,255,255,0.1) 1px, transparent 1px),
            radial-gradient(circle, rgba(255,255,255,0.07) 2px, transparent 2px);
        background-size: 30px 30px, 80px 80px;
        background-position: 0 0, 40px 40px;
        animation: twinkle 8s ease-in-out infinite alternate;
        z-index: 0;
    }
    
    @keyframes twinkle {
        0%, 100% { opacity: 0.3; }
        50% { opacity: 0.7; }
    }
    
    /* Status bar with gradient */
    .status-bar {
        display: flex;
        justify-content: space-between;
        padding: 10px 20px;
        font-size: 12px;
        background: linear-gradient(90deg, #1c2130, #232a3b);
        border-radius: 15px;
        margin-bottom: 15px;
        border: 1px solid rgba(255, 255, 255, 0.05);
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        position: relative;
        z-index: 10;
        backdrop-filter: blur(10px);
    }
    
    /* Welcome card with glass morphism effect */
    .welcome-card {
        background: rgba(38, 39, 48, 0.7);
        border-radius: 20px;
        padding: 20px;
        margin-bottom: 25px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
        backdrop-filter: blur(8px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        position: relative;
        overflow: hidden;
        transition: all 0.4s ease;
        z-index: 1;
    }
    
    .welcome-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.3);
        border: 1px solid rgba(0, 219, 173, 0.2);
    }
    
    /* Animated gradient border effect */
    .welcome-card::before {
        content: '';
        position: absolute;
        top: -2px;
        left: -2px;
        right: -2px;
        bottom: -2px;
        z-index: -1;
        background: linear-gradient(45deg, #00DBAD, #00ACFF, #FF5E78, #00DBAD);
        background-size: 400% 400%;
        border-radius: 22px;
        animation: borderGradient 8s ease infinite;
        opacity: 0;
        transition: opacity 0.4s ease;
    }
    
    .welcome-card:hover::before {
        opacity: 1;
    }
    
    @keyframes borderGradient {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    /* Bottom navigation with advanced styling */
    .bottom-nav {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        background: rgba(30, 33, 41, 0.85);
        backdrop-filter: blur(10px);
        display: flex;
        justify-content: space-around;
        padding: 12px 0;
        box-shadow: 0 -5px 25px rgba(0, 0, 0, 0.3);
        z-index: 1000;
        border-top: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    .nav-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        position: relative;
        z-index: 2;
    }
    
    .nav-icon {
        background: linear-gradient(145deg, #1e2232, #262c40);
        border-radius: 50%;
        width: 55px;
        height: 55px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 6px;
        font-size: 24px;
        box-shadow: 5px 5px 15px rgba(0, 0, 0, 0.2),
                    -5px -5px 15px rgba(255, 255, 255, 0.03);
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        position: relative;
        overflow: hidden;
    }
    
    .nav-icon::after {
        content: '';
        position: absolute;
        width: 100%;
        height: 100%;
        background: radial-gradient(circle, rgba(255,255,255,0.15) 0%, transparent 70%);
        top: -50%;
        left: -50%;
        transition: all 0.5s ease;
    }
    
    .nav-icon:hover {
        transform: translateY(-8px);
        background: linear-gradient(135deg, #00dbad, #00c4ff);
        box-shadow: 0 10px 20px rgba(0, 219, 173, 0.4);
    }
    
    .nav-icon:hover::after {
        top: -20%;
        left: -20%;
    }
    
    .nav-text {
        font-size: 11px;
        font-weight: 500;
        color: #ADB5BD;
        transition: all 0.3s ease;
        opacity: 0.8;
    }
    
    .nav-item:hover .nav-text {
        color: #00DBAD;
        opacity: 1;
        transform: scale(1.1);
    }
    
    /* Active nav icon */
    .nav-active {
        background: linear-gradient(135deg, #00dbad, #00c4ff) !important;
        box-shadow: 0 8px 20px rgba(0, 219, 173, 0.4) !important;
    }
    
    /* Main content */
    .main-content {
        padding-bottom: 100px; /* Space for fixed bottom nav */
        position: relative;
        z-index: 5;
    }
    
    /* User greeting section */
    .user-greeting {
        display: flex;
        align-items: center;
        margin-bottom: 15px;
    }
    
    .user-avatar {
        width: 45px;
        height: 45px;
        background: linear-gradient(135deg, #00dbad, #00acff);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-right: 12px;
        font-weight: bold;
        color: #0E1117;
        box-shadow: 0 5px 15px rgba(0, 219, 173, 0.4);
        position: relative;
        overflow: hidden;
    }
    
    .user-avatar::after {
        content: '';
        position: absolute;
        width: 100%;
        height: 100%;
        background: radial-gradient(circle, rgba(255,255,255,0.3) 0%, transparent 70%);
        top: -50%;
        left: -50%;
    }
    
    /* Feature cards */
    .app-card {
        background: rgba(38, 39, 48, 0.7);
        border-radius: 22px;
        overflow: hidden;
        margin-bottom: 20px;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
        transition: all 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        backdrop-filter: blur(5px);
        border: 1px solid rgba(255, 255, 255, 0.05);
        transform: translateZ(0);
        position: relative;
    }
    
    .app-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: linear-gradient(135deg, rgba(0, 219, 173, 0.1) 0%, rgba(0, 172, 255, 0.1) 100%);
        opacity: 0;
        transition: opacity 0.3s ease;
    }
    
    .app-card:hover {
        transform: translateY(-8px) scale(1.02);
        box-shadow: 0 15px 35px rgba(0, 0, 0, 0.25);
        border: 1px solid rgba(0, 219, 173, 0.2);
    }
    
    .app-card:hover::before {
        opacity: 1;
    }
    
    .card-content {
        padding: 18px;
        position: relative;
        z-index: 2;
    }
    
    .card-image {
        height: 140px;
        background-size: cover;
        background-position: center;
        position: relative;
        transition: all 0.5s ease;
    }
    
    .card-image::after {
        content: '';
        position: absolute;
        bottom: 0;
        left: 0;
        width: 100%;
        height: 40%;
        background: linear-gradient(to top, rgba(38, 39, 48, 1), transparent);
    }
    
    .app-card:hover .card-image {
        transform: scale(1.05);
    }
    
    .card-title {
        font-weight: 700;
        font-size: 18px;
        margin-bottom: 8px;
        background: linear-gradient(90deg, #00DBAD, #00C4FF);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: 0.5px;
    }
    
    .card-text {
        font-size: 13px;
        color: #D0D0D0;
        margin-bottom: 15px;
        line-height: 1.5;
    }
    
    .card-button {
        background: linear-gradient(90deg, #00DBAD, #00BADD);
        color: #0E1117;
        border: none;
        border-radius: 8px;
        padding: 10px 15px;
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        width: 100%;
        text-align: center;
        box-shadow: 0 4px 10px rgba(0, 219, 173, 0.3);
        display: block;
        position: relative;
        overflow: hidden;
    }
    
    .card-button::after {
        content: '';
        position: absolute;
        width: 30%;
        height: 200%;
        background: rgba(255, 255, 255, 0.2);
        top: -50%;
        left: -100%;
        transform: rotate(30deg);
        transition: all 0.5s ease;
    }
    
    .card-button:hover {
        background: linear-gradient(90deg, #00DBAD, #00ACFF);
        box-shadow: 0 8px 20px rgba(0, 219, 173, 0.4);
        transform: translateY(-3px);
    }
    
    .card-button:hover::after {
        left: 200%;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Start mobile app container
    st.markdown("<div class='mobile-container'>", unsafe_allow_html=True)
    
    # Status bar
    st.markdown(f"""
    <div class="status-bar">
        <span>NutriTrack</span>
        <span>{datetime.now().strftime('%H:%M')}</span>
    </div>
    """, unsafe_allow_html=True)
    
    # Main content area with padding for bottom nav
    st.markdown("<div class='main-content'>", unsafe_allow_html=True)
    
    # Welcome card with user info
    username = st.session_state.username if st.session_state.username else "User"
    first_letter = username[0].upper() if username else "U"
    
    st.markdown(f"""
    <div class="welcome-card">
        <div class="user-greeting">
            <div class="user-avatar">{first_letter}</div>
            <div>
                <div style="font-weight: 600;">Welcome, {username}! 👋</div>
                <div style="font-size: 12px; color: #ADB5BD;">Let's track your nutrition today</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Display animations side by side
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if health_animation:
            st_lottie(health_animation, height=200, key="health")
            
    with col2:
        if nutrition_animation:
            st_lottie(nutrition_animation, height=200, key="nutrition")
    
    # Feature cards designed like mobile app cards
    st.markdown("<h3 style='font-size: 18px; margin-bottom: 15px;'>Features</h3>", unsafe_allow_html=True)
    
    # Feature cards with buttons
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="app-card">
            <div class="card-image" style="background-image: url('https://images.unsplash.com/photo-1551076805-e1869033e561?crop=entropy&cs=tinysrgb&fm=jpg&ixlib=rb-1.2.1&q=80&raw_url=true&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=1000');"></div>
            <div class="card-content">
                <div class="card-title">👤 Profile Setup</div>
                <div class="card-text">Update your physical measurements and fitness goals.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Go to Profile", key="profile_card", use_container_width=True):
            switch_page("1_User_Profile")
    
    with col2:
        st.markdown("""
        <div class="app-card">
            <div class="card-image" style="background-image: url('https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?crop=entropy&cs=tinysrgb&fm=jpg&ixlib=rb-1.2.1&q=80&raw_url=true&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=1000');"></div>
            <div class="card-content">
                <div class="card-title">📊 Health Metrics</div>
                <div class="card-text">View your BMI, metabolic rate, and calorie needs.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("View Metrics", key="metrics_card", use_container_width=True):
            switch_page("2_Health_Metrics")
    
    col3, col4 = st.columns(2)
    
    with col3:
        st.markdown("""
        <div class="app-card">
            <div class="card-image" style="background-image: url('https://images.unsplash.com/photo-1498837167922-ddd27525d352?crop=entropy&cs=tinysrgb&fm=jpg&ixlib=rb-1.2.1&q=80&raw_url=true&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=1000');"></div>
            <div class="card-content">
                <div class="card-title">🍽️ Food Analysis</div>
                <div class="card-text">Capture food images to analyze nutritional content.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Analyze Food", key="food_card", use_container_width=True):
            switch_page("3_Food_Analysis")
    
    with col4:
        st.markdown("""
        <div class="app-card">
            <div class="card-image" style="background-image: url('https://images.unsplash.com/photo-1526401485004-46910ecc8e51?crop=entropy&cs=tinysrgb&fm=jpg&ixlib=rb-1.2.1&q=80&raw_url=true&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=1000');"></div>
            <div class="card-content">
                <div class="card-title">📝 Daily Tracker</div>
                <div class="card-text">Log your meals and exercises to monitor nutrition.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Track Today", key="tracker_card", use_container_width=True):
            switch_page("4_Daily_Tracker")
    
    # Social Media Sharing section
    st.markdown("<h3 style='font-size: 18px; margin-bottom: 15px; margin-top: 20px;'>Share Your Achievements</h3>", unsafe_allow_html=True)
    
    st.markdown("""
    <div class="app-card" style="padding: 15px;">
        <div style="font-weight: 600; margin-bottom: 10px; color: #00DBAD;">Share Your Progress</div>
        <div style="font-size: 12px; color: #ADB5BD; margin-bottom: 15px;">
            Share your health achievements with friends and family on social media.
        </div>
        <div style="display: flex; justify-content: space-around; margin-top: 10px;">
            <div style="background-color: #1877F2; color: white; border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; cursor: pointer;">
                <span style="font-weight: bold;">f</span>
            </div>
            <div style="background-color: #1DA1F2; color: white; border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; cursor: pointer;">
                <span style="font-weight: bold;">t</span>
            </div>
            <div style="background-color: #E4405F; color: white; border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; cursor: pointer;">
                <span style="font-weight: bold;">i</span>
            </div>
            <div style="background-color: #0A66C2; color: white; border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; cursor: pointer;">
                <span style="font-weight: bold;">in</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Logout button
    if st.button("Logout", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.user_id = None
        st.session_state.username = None
        st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Bottom navigation bar with animated icons and gradients
    st.markdown("""
    <div class="bottom-nav">
        <a href="/User_Profile" target="_self" style="text-decoration: none; color: inherit;">
            <div class="nav-item">
                <div class="nav-icon">
                    <div class="icon-pulse">👤</div>
                </div>
                <div class="nav-text">Profile</div>
            </div>
        </a>
        <a href="/Health_Metrics" target="_self" style="text-decoration: none; color: inherit;">
            <div class="nav-item">
                <div class="nav-icon">
                    <div class="icon-pulse">📊</div>
                </div>
                <div class="nav-text">Metrics</div>
            </div>
        </a>
        <a href="/" target="_self" style="text-decoration: none; color: inherit;">
            <div class="nav-item">
                <div class="nav-icon nav-active">
                    <div class="icon-pulse">🏠</div>
                </div>
                <div class="nav-text" style="color: #00DBAD; font-weight: 600;">Home</div>
            </div>
        </a>
        <a href="/Food_Analysis" target="_self" style="text-decoration: none; color: inherit;">
            <div class="nav-item">
                <div class="nav-icon">
                    <div class="icon-pulse">🍽️</div>
                </div>
                <div class="nav-text">Food</div>
            </div>
        </a>
        <a href="/Daily_Tracker" target="_self" style="text-decoration: none; color: inherit;">
            <div class="nav-item">
                <div class="nav-icon">
                    <div class="icon-pulse">📝</div>
                </div>
                <div class="nav-text">Tracker</div>
            </div>
        </a>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)
