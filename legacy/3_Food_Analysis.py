import streamlit as st
from PIL import Image
import os
from utils.authentication import check_authentication
from utils.food_analysis import analyze_food_image
from utils.database import log_food, get_health_metrics
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
    page_title="Food Analysis - NutriTrack",
    page_icon="🍽️",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem !important;
        font-weight: 600;
        margin-bottom: 1rem;
        color: #00DBAD;
    }
    .sub-header {
        font-size: 1.5rem !important;
        font-weight: 500;
        margin-bottom: 1rem;
    }
    .food-analysis-container {
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
    .food-item-row {
        background-color: #262730;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    .food-item-row:hover {
        transform: translateY(-3px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
    }
    .food-item-name {
        font-weight: 600;
        color: #00DBAD;
        font-size: 1.1rem;
    }
    .food-stat {
        display: inline-block;
        background-color: #1E2129;
        padding: 5px 10px;
        border-radius: 5px;
        margin-right: 5px;
        font-size: 0.9rem;
    }
    .analyze-btn {
        position: relative;
        overflow: hidden;
    }
    .analyze-btn:after {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
        animation: shine 2s infinite;
    }
    @keyframes shine {
        0% {left: -100%;}
        20% {left: 100%;}
        100% {left: 100%;}
    }
    
    /* Bottom navigation styling */
    .bottom-nav {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        background-color: #1E2129;
        display: flex;
        justify-content: space-around;
        padding: 10px 0;
        box-shadow: 0 -2px 10px rgba(0,0,0,0.2);
        z-index: 1000;
    }
    .nav-item {
        display: flex;
        flex-direction: column;
        align-items: center;
    }
    .nav-icon {
        background-color: #262730;
        border-radius: 50%;
        width: 50px;
        height: 50px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 5px;
        font-size: 24px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        transition: all 0.3s ease;
    }
    .nav-icon:hover {
        transform: translateY(-5px);
        background-color: #00DBAD;
    }
    .nav-text {
        font-size: 10px;
        color: #ADB5BD;
    }
    .main-content {
        padding-bottom: 100px; /* Space for fixed bottom nav */
    }
</style>
""", unsafe_allow_html=True)

# Add padding at the bottom for the fixed navigation bar
st.markdown("<div class='main-content'>", unsafe_allow_html=True)

# Load food analysis animation
food_animation = load_lottieurl("https://assets9.lottiefiles.com/packages/lf20_ysas4vcp.json")

# Custom header with animation
colored_header(
    label="Food Analysis",
    description="Capture or upload food images to analyze nutritional content",
    color_name="green-70",
)

# Display animation
if food_animation:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st_lottie(food_animation, height=200, key="food")

# Function to display nutritional information with enhanced features
def display_nutritional_info(analysis_results):
    # Get food items from analysis results
    food_items = analysis_results.get('food_items', [])
    portion_info = analysis_results.get('portion_info', {})
    health_tips = analysis_results.get('health_tips', [])
    warnings = analysis_results.get('warnings', [])
    
    if not food_items:
        st.warning("No food items were detected. Try another image or provide more details.")
        return
    
    # Get user's health metrics for comparison
    user_metrics = get_health_metrics(st.session_state.user_id)
    
    # Display any personalized warnings at the top
    if warnings:
        warning_container = st.container()
        with warning_container:
            for warning in warnings:
                st.warning(warning)
    
    # Display health tips in a card at the top
    if health_tips:
        st.markdown("""
        <div style="background-color: #262730; border-radius: 10px; padding: 15px; margin-bottom: 20px; border-left: 5px solid #00DBAD;">
            <h3 style="color: #00DBAD; font-size: 18px; margin-bottom: 10px;">Health Tips</h3>
        """, unsafe_allow_html=True)
        
        for tip in health_tips:
            st.markdown(f"""
            <div style="margin-bottom: 8px; font-size: 14px; color: #FFFFFF;">• {tip}</div>
            """, unsafe_allow_html=True)
            
        st.markdown("</div>", unsafe_allow_html=True)
    
    st.subheader("Detected Food Items")
    
    # Create a table for food items with portion size information
    col1, col2, col3, col4, col5, col6, col7 = st.columns([3, 1, 1, 1, 1, 2, 2])
    col1.write("**Food Item**")
    col2.write("**Calories**")
    col3.write("**Protein**")
    col4.write("**Fat**")
    col5.write("**Carbs**")
    col6.write("**Portion**")
    col7.write("**Actions**")
    
    st.markdown("---")
    
    # Total values for summary
    total_calories = 0
    total_protein = 0
    total_fat = 0
    total_carbs = 0
    
    # Display each food item
    for i, item in enumerate(food_items):
        if item['name'] == 'Total':  # Skip the total in the item list
            continue
            
        col1, col2, col3, col4, col5, col6, col7 = st.columns([3, 1, 1, 1, 1, 2, 2])
        
        col1.markdown(f"<div class='food-item-name'>{item['name']}</div>", unsafe_allow_html=True)
        col2.write(f"{item['calories']} kcal")
        col3.write(f"{item['protein']}g")
        col4.write(f"{item['fat']}g")
        col5.write(f"{item['carbs']}g")
        col6.write(f"{item['portion_size']}")
        
        # Log food button
        with col7:
            # Meal type selection
            meal_type = st.selectbox(
                "Meal",
                options=["Breakfast", "Lunch", "Dinner", "Snack"],
                key=f"meal_{i}"
            )
            
            # Log button
            if st.button("Log", key=f"log_{i}"):
                if log_food(
                    st.session_state.user_id, 
                    item['name'], 
                    item['calories'], 
                    item['protein'], 
                    item['fat'], 
                    item['carbs'], 
                    item.get('portion_size', 'Standard serving'),
                    meal_type
                ):
                    st.success(f"Logged {item['name']}")
                else:
                    st.error("Failed to log food")
        
        # Keep track of totals
        total_calories += item['calories']
        total_protein += item['protein']
        total_fat += item['fat']
        total_carbs += item['carbs']
        
        st.markdown("---")
    
    # Display portion estimation details
    if portion_info and len(portion_info) > 0:
        with st.expander("📏 Portion Size Estimation Details", expanded=True):
            st.markdown("<div style='font-size: 16px; color: #00DBAD; margin-bottom: 10px;'>How portions were estimated:</div>", unsafe_allow_html=True)
            
            for food_name, portion_detail in portion_info.items():
                st.markdown(f"""
                <div style="background-color: #1E2129; border-radius: 8px; padding: 10px; margin-bottom: 8px;">
                    <span style="font-weight: 600; color: #FFFFFF;">{food_name}:</span> {portion_detail}
                </div>
                """, unsafe_allow_html=True)
    
    # Display nutritional summary
    st.subheader("Meal Summary")
    
    # Create columns for the summary
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Calories", f"{total_calories} kcal")
        if user_metrics:
            percentage = (total_calories / user_metrics['target_calories']) * 100
            st.caption(f"{percentage:.1f}% of daily target ({user_metrics['target_calories']} kcal)")
    
    with col2:
        st.metric("Total Protein", f"{total_protein}g")
        if user_metrics:
            percentage = (total_protein / user_metrics['protein_target']) * 100
            st.caption(f"{percentage:.1f}% of daily target ({user_metrics['protein_target']}g)")
    
    with col3:
        st.metric("Total Fat", f"{total_fat}g")
        if user_metrics:
            percentage = (total_fat / user_metrics['fat_target']) * 100
            st.caption(f"{percentage:.1f}% of daily target ({user_metrics['fat_target']}g)")
    
    with col4:
        st.metric("Total Carbs", f"{total_carbs}g")
        if user_metrics:
            percentage = (total_carbs / user_metrics['carbs_target']) * 100
            st.caption(f"{percentage:.1f}% of daily target ({user_metrics['carbs_target']}g)")
            
    # Social sharing option for meal
    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
    with st.expander("Share This Meal Analysis", expanded=False):
        st.markdown("""
        <div style="background-color: #262730; border-radius: 10px; padding: 15px; margin-top: 10px;">
            <div style="font-weight: 600; margin-bottom: 10px; color: #00DBAD;">Share your meal with friends</div>
            <div style="font-size: 12px; color: #ADB5BD; margin-bottom: 15px;">
                Let others know about your healthy eating habits!
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
                <div style="background-color: #25D366; color: white; border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; cursor: pointer;">
                    <span style="font-weight: bold;">w</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# Streamlit camera input widget to capture an image
st.subheader("Take a Photo of Your Food")
captured_image = st.camera_input("Take a picture")

# File uploader for uploading an image
st.subheader("Or Upload a Food Image")
uploaded_image = st.file_uploader("Upload an image", type=["jpg", "jpeg", "png"])

# Determine which image to use
image_source = None
if captured_image is not None:
    image_source = captured_image
    st.image(captured_image, caption="Captured Image", use_column_width=True)
elif uploaded_image is not None:
    image_source = uploaded_image
    st.image(uploaded_image, caption="Uploaded Image", use_column_width=True)

# Input prompt for the API
input_prompt = st.text_input("Describe the food items (optional):", value="Food items in the image", key="input")

# Button to trigger the analysis
analyze_button = st.button("Analyze Food", disabled=image_source is None)

# Store analysis results in session state to persist between reruns
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None

if analyze_button and image_source is not None:
    with st.spinner("Analyzing food image..."):
        # Get the user's profile and health metrics for personalized analysis
        from utils.database import get_user_profile, get_health_metrics
        
        user_profile = get_user_profile(st.session_state.user_id)
        health_metrics = get_health_metrics(st.session_state.user_id)
        
        # Analyze the image with user context for personalized feedback
        analysis_results = analyze_food_image(
            image_source, 
            description=input_prompt,
            user_profile=user_profile,
            health_metrics=health_metrics
        )
        
        if analysis_results['success']:
            st.session_state.analysis_results = analysis_results
            st.success("Analysis complete!")
        else:
            st.error(f"Analysis failed: {analysis_results['error']}")

# Display results if available
if st.session_state.analysis_results:
    display_nutritional_info(st.session_state.analysis_results)
    
    # Option to view raw API response
    with st.expander("View Raw Analysis"):
        st.write(st.session_state.analysis_results['raw_response'])

# Manual food entry option
st.subheader("Manual Food Entry")
st.write("If image analysis isn't working or you prefer to enter food details manually, use this form:")

with st.form("manual_food_entry"):
    # Create columns for form fields
    col1, col2 = st.columns(2)
    
    with col1:
        food_name = st.text_input("Food Name")
        calories = st.number_input("Calories (kcal)", min_value=0)
        portion = st.text_input("Portion Size", value="Standard serving")
    
    with col2:
        protein = st.number_input("Protein (g)", min_value=0)
        fat = st.number_input("Fat (g)", min_value=0)
        carbs = st.number_input("Carbohydrates (g)", min_value=0)
        
        meal_type = st.selectbox(
            "Meal Type",
            options=["Breakfast", "Lunch", "Dinner", "Snack"]
        )
    
    # Submit button
    submitted = st.form_submit_button("Log Food Item")
    
    if submitted:
        if not food_name:
            st.error("Food name is required")
        else:
            if log_food(
                st.session_state.user_id,
                food_name,
                calories,
                protein,
                fat,
                carbs,
                portion,
                meal_type
            ):
                st.success(f"Successfully logged {food_name}")
            else:
                st.error("Failed to log food item")

# Close the main content div
st.markdown("</div>", unsafe_allow_html=True)

# Add bottom navigation bar
from streamlit_extras.switch_page_button import switch_page

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
            <div class="nav-icon">
                <div class="icon-pulse">🏠</div>
            </div>
            <div class="nav-text">Home</div>
        </div>
    </a>
    <a href="/Food_Analysis" target="_self" style="text-decoration: none; color: inherit;">
        <div class="nav-item">
            <div class="nav-icon nav-active">
                <div class="icon-pulse">🍽️</div>
            </div>
            <div class="nav-text" style="color: #00DBAD; font-weight: 600;">Food</div>
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
