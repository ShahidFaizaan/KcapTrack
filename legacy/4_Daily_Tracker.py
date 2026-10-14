import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from utils.authentication import check_authentication
from utils.database import (
    get_daily_food_logs, get_daily_exercise_logs, 
    get_daily_summary, get_health_metrics, log_exercise
)
from streamlit_lottie import st_lottie  ## i have used stremlit but not shown visually to the user.
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
    page_title="Daily Tracker - NutriTrack",
    page_icon="📝",
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
    .tracker-container {
        animation: slideInRight 0.8s ease-in-out;
    }
    @keyframes slideInRight {
        0% {opacity: 0; transform: translateX(20px);}
        100% {opacity: 1; transform: translateX(0);}
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
    .tracker-card {
        background-color: #262730;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    .tracker-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
    }
    .date-header {
        font-size: 1.2rem;
        font-weight: 600;
        color: #00DBAD;
        margin-bottom: 15px;
        text-align: center;
    }
    .food-item {
        margin-bottom: 10px;
        padding: 10px;
        border-radius: 5px;
        background-color: #1E2129;
    }
    .food-name {
        font-weight: 600;
        color: #00DBAD;
    }
    .food-calories {
        color: #FFA15A;
        font-weight: 500;
    }
    .exercise-item {
        margin-bottom: 10px;
        padding: 10px;
        border-radius: 5px;
        background-color: #1E2129;
    }
    .exercise-name {
        font-weight: 600;
        color: #636EFA;
    }
    .exercise-calories {
        color: #00CC96;
        font-weight: 500;
    }
    /* Styling for the date input */
    .stDateInput>div>div>input {
        background-color: #1E2129 !important;
        color: #FAFAFA !important;
        border: 1px solid #434956 !important;
        border-radius: 5px !important;
    }
    .stTab {
        background-color: #262730;
        border-radius: 5px 5px 0 0;
        padding: 10px 15px;
        font-weight: 600;
    }
    .stTab:hover {
        background-color: #2e3441;
    }
    .stTab[aria-selected="true"] {
        background-color: #00DBAD;
        color: #0E1117;
    }
</style>
""", unsafe_allow_html=True)

# Load tracker animation
tracker_animation = load_lottieurl("https://assets5.lottiefiles.com/packages/lf20_g7gfccst.json")

# Custom header
colored_header(
    label="Daily Tracker",
    description="Monitor your nutrition and exercise progress",
    color_name="green-70",
)

# Display animation
if tracker_animation:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st_lottie(tracker_animation, height=200, key="tracker")

# Date selector with better styling
st.markdown("<div class='date-header'>Select a date to view your tracking data</div>", unsafe_allow_html=True)
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    selected_date = st.date_input(
        "",  # Remove label as we're using the custom header above
        value=datetime.now().date(),
        max_value=datetime.now().date()
    )

# Get user data for the selected date
food_logs = get_daily_food_logs(st.session_state.user_id, selected_date)
exercise_logs = get_daily_exercise_logs(st.session_state.user_id, selected_date)
daily_summary = get_daily_summary(st.session_state.user_id, selected_date)
health_metrics = get_health_metrics(st.session_state.user_id)

# Calculate daily progress
calories_consumed = daily_summary['total_calories']
calories_burned = daily_summary['total_calories_burned']
net_calories = calories_consumed - calories_burned

# Create tabs for different sections
tab1, tab2, tab3 = st.tabs(["Daily Summary", "Food Log", "Exercise Log"])

with tab1:
    st.markdown("<div class='tracker-container'>", unsafe_allow_html=True)
    colored_header(
        label="Daily Nutrition Summary",
        description="Your nutrition overview for the day",
        color_name="green-70",
    )
    
    # Progress towards daily targets
    if health_metrics:
        # Create columns for key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            calories_percentage = min(100, int((calories_consumed / health_metrics['target_calories']) * 100)) if health_metrics['target_calories'] else 0
            st.metric(
                "Calories Consumed", 
                f"{calories_consumed} kcal", 
                f"{calories_percentage}% of target"
            )
            
            # Calories gauge with improved styling
            fig = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = calories_consumed,
                domain = {'x': [0, 1], 'y': [0, 1]},
                number = {'suffix': " kcal", 'font': {'color': '#FAFAFA'}},
                gauge = {
                    'axis': {'range': [None, health_metrics['target_calories']], 'tickwidth': 1, 'tickcolor': '#FAFAFA'},
                    'bar': {'color': "#00DBAD"},
                    'bgcolor': 'rgba(0,0,0,0)',
                    'borderwidth': 0,
                    'steps': [
                        {'range': [0, health_metrics['target_calories']*0.5], 'color': "#1E2129"},
                        {'range': [health_metrics['target_calories']*0.5, health_metrics['target_calories']*0.8], 'color': "#262730"},
                        {'range': [health_metrics['target_calories']*0.8, health_metrics['target_calories']], 'color': "#2e3441"}
                    ],
                    'threshold': {
                        'line': {'color': "#FAFAFA", 'width': 4},
                        'thickness': 0.75,
                        'value': health_metrics['target_calories']
                    }
                },
                title = {'text': "Daily Calories", 'font': {'color': '#FAFAFA'}}
            ))
            
            fig.update_layout(
                paper_bgcolor = 'rgba(0,0,0,0)',
                plot_bgcolor = 'rgba(0,0,0,0)',
                font = {'color': "#FAFAFA"},
                height = 250
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            protein_percentage = min(100, int((daily_summary['total_protein'] / health_metrics['protein_target']) * 100)) if health_metrics['protein_target'] else 0
            st.metric(
                "Protein", 
                f"{daily_summary['total_protein']}g", 
                f"{protein_percentage}% of target"
            )
            
            # Protein gauge
            fig = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = daily_summary['total_protein'],
                domain = {'x': [0, 1], 'y': [0, 1]},
                number = {'suffix': "g"},
                gauge = {
                    'axis': {'range': [None, health_metrics['protein_target']]},
                    'bar': {'color': "#FFA15A"},
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': health_metrics['protein_target']
                    }
                },
                title = {'text': "Protein"}
            ))
            st.plotly_chart(fig, use_container_width=True)
        
        with col3:
            fat_percentage = min(100, int((daily_summary['total_fat'] / health_metrics['fat_target']) * 100)) if health_metrics['fat_target'] else 0
            st.metric(
                "Fat", 
                f"{daily_summary['total_fat']}g", 
                f"{fat_percentage}% of target"
            )
            
            # Fat gauge
            fig = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = daily_summary['total_fat'],
                domain = {'x': [0, 1], 'y': [0, 1]},
                number = {'suffix': "g"},
                gauge = {
                    'axis': {'range': [None, health_metrics['fat_target']]},
                    'bar': {'color': "#00CC96"},
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': health_metrics['fat_target']
                    }
                },
                title = {'text': "Fat"}
            ))
            st.plotly_chart(fig, use_container_width=True)
        
        with col4:
            carbs_percentage = min(100, int((daily_summary['total_carbs'] / health_metrics['carbs_target']) * 100)) if health_metrics['carbs_target'] else 0
            st.metric(
                "Carbohydrates", 
                f"{daily_summary['total_carbs']}g", 
                f"{carbs_percentage}% of target"
            )
            
            # Carbs gauge
            fig = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = daily_summary['total_carbs'],
                domain = {'x': [0, 1], 'y': [0, 1]},
                number = {'suffix': "g"},
                gauge = {
                    'axis': {'range': [None, health_metrics['carbs_target']]},
                    'bar': {'color': "#636EFA"},
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': health_metrics['carbs_target']
                    }
                },
                title = {'text': "Carbs"}
            ))
            st.plotly_chart(fig, use_container_width=True)
    
    # Calorie balance with better styling
    colored_header(
        label="Calorie Balance",
        description="Your energy balance for the day",
        color_name="green-70",
    )
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Calories Consumed", f"{calories_consumed} kcal")
    
    with col2:
        st.metric("Calories Burned", f"{calories_burned} kcal")
    
    with col3:
        if health_metrics:
            net_target = health_metrics['target_calories'] - calories_burned
            delta = net_calories - net_target
            st.metric(
                "Net Calories", 
                f"{net_calories} kcal", 
                f"{delta:+.0f} kcal from target",
                delta_color="inverse"
            )
        else:
            st.metric("Net Calories", f"{net_calories} kcal")
    
    # Visual representation of calorie balance
    if health_metrics:
        # Create a calorie balance chart
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=['Goal', 'Consumed', 'Burned', 'Net'],
            y=[health_metrics['target_calories'], calories_consumed, calories_burned, net_calories],
            marker=dict(
                color=['#636EFA', '#FFA15A', '#00CC96', '#EF553B']
            )
        ))
        
        fig.update_layout(
            title="Calorie Balance",
            yaxis_title="Calories (kcal)",
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Macronutrient distribution with better styling
    if daily_summary['total_calories'] > 0:
        colored_header(
            label="Macronutrient Distribution",
            description="Breakdown of your daily nutrient intake",
            color_name="green-70",
        )
        
        # Calculate percentages
        protein_cals = daily_summary['total_protein'] * 4
        fat_cals = daily_summary['total_fat'] * 9
        carbs_cals = daily_summary['total_carbs'] * 4
        
        # Create pie chart
        fig = go.Figure(data=[go.Pie(
            labels=['Protein', 'Fat', 'Carbohydrates'],
            values=[protein_cals, fat_cals, carbs_cals],
            hole=.4,
            marker_colors=['#FFA15A', '#00CC96', '#636EFA']
        )])
        
        fig.update_layout(
            title_text=f"Macronutrient Distribution ({calories_consumed} kcal)"
        )
        
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.markdown("<div class='tracker-container'>", unsafe_allow_html=True)
    colored_header(
        label="Food Log",
        description="Your meal entries for the day",
        color_name="green-70",
    )
    
    if food_logs:
        # Create a dataframe for the food logs
        food_df = pd.DataFrame(food_logs)
        
        # Group by meal type
        meal_groups = food_df.groupby('meal_type')
        
        for meal_type in sorted(meal_groups.groups.keys()):
            st.markdown(f"<div class='tracker-card'><h3 style='color: #00DBAD; margin-bottom: 15px;'>{meal_type}</h3>", unsafe_allow_html=True)
            
            meal_data = meal_groups.get_group(meal_type)
            
            # Create a table for food items with better styling
            for i, row in meal_data.iterrows():
                st.markdown(f"""
                <div class="food-item">
                    <div class="food-name">{row['food_name']}</div>
                    <div style="margin-top: 5px;">
                        <span class="food-calories">{row['calories']} kcal</span> | 
                        <span style="color: #FFA15A;">{row['protein']}g protein</span> | 
                        <span style="color: #00CC96;">{row['fat']}g fat</span> | 
                        <span style="color: #636EFA;">{row['carbs']}g carbs</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            # Calculate meal totals
            meal_calories = meal_data['calories'].sum()
            meal_protein = meal_data['protein'].sum()
            meal_fat = meal_data['fat'].sum()
            meal_carbs = meal_data['carbs'].sum()
            
            # Display meal totals with better styling
            st.markdown(f"""
            <div style="background-color: #1E2129; padding: 10px; border-radius: 5px; margin-top: 10px;">
                <div style="font-weight: 600; color: #00DBAD;">Meal Totals</div>
                <div style="display: flex; justify-content: space-between; margin-top: 5px;">
                    <span><b>{meal_calories}</b> kcal</span>
                    <span><b>{meal_protein}g</b> protein</span>
                    <span><b>{meal_fat}g</b> fat</span>
                    <span><b>{meal_carbs}g</b> carbs</span>
                </div>
            </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="tracker-card" style="text-align: center; padding: 30px;">
            <i class="fas fa-utensils" style="font-size: 40px; color: #ADB5BD; margin-bottom: 15px;"></i>
            <div style="color: #ADB5BD; font-size: 1.1rem;">No food logged for this date.</div>
            <div style="margin-top: 10px;">Go to the Food Analysis page to log your meals.</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)

with tab3:
    st.markdown("<div class='tracker-container'>", unsafe_allow_html=True)
    colored_header(
        label="Exercise Log",
        description="Your physical activities for the day",
        color_name="green-70",
    )
    
    # Form for adding exercise with improved styling
    st.markdown("<div class='tracker-card'>", unsafe_allow_html=True)
    st.markdown("<h3 style='color: #00DBAD; margin-bottom: 15px;'>Add New Exercise</h3>", unsafe_allow_html=True)
    
    with st.form("log_exercise"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            exercise_name = st.text_input("Exercise Name")
        
        with col2:
            duration = st.number_input("Duration (minutes)", min_value=1, value=30)
        
        with col3:
            calories_burned = st.number_input("Calories Burned", min_value=0, value=100)
        
        submitted = st.form_submit_button("Log Exercise", use_container_width=True)
        
        if submitted:
            if not exercise_name:
                st.error("Exercise name is required")
            else:
                if log_exercise(st.session_state.user_id, exercise_name, duration, calories_burned):
                    st.success(f"Successfully logged {exercise_name}")
                    st.rerun()
                else:
                    st.error("Failed to log exercise")
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Display exercise logs with improved styling
    if exercise_logs:
        # Create a dataframe for the exercise logs
        exercise_df = pd.DataFrame(exercise_logs)
        
        st.markdown("<div class='tracker-card'>", unsafe_allow_html=True)
        st.markdown("<h3 style='color: #00DBAD; margin-bottom: 15px;'>Exercise Activities</h3>", unsafe_allow_html=True)
        
        # Display each exercise with better styling
        for i, row in exercise_df.iterrows():
            st.markdown(f"""
            <div class="exercise-item">
                <div class="exercise-name">{row['exercise_name']}</div>
                <div style="margin-top: 5px; display: flex; justify-content: space-between;">
                    <span style="color: #ADB5BD;"><i class="fas fa-clock"></i> {row['duration']} minutes</span>
                    <span class="exercise-calories"><i class="fas fa-fire"></i> {row['calories_burned']} kcal burned</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # Calculate total
        total_duration = exercise_df['duration'].sum()
        total_burned = exercise_df['calories_burned'].sum()
        
        # Display exercise totals with better styling
        st.markdown(f"""
        <div style="background-color: #1E2129; padding: 10px; border-radius: 5px; margin-top: 15px;">
            <div style="font-weight: 600; color: #00DBAD;">Exercise Totals</div>
            <div style="display: flex; justify-content: space-between; margin-top: 5px;">
                <span><b>{total_duration}</b> minutes</span>
                <span><b>{total_burned}</b> calories burned</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="tracker-card" style="text-align: center; padding: 30px;">
            <i class="fas fa-running" style="font-size: 40px; color: #ADB5BD; margin-bottom: 15px;"></i>
            <div style="color: #ADB5BD; font-size: 1.1rem;">No exercises logged for this date.</div>
            <div style="margin-top: 10px;">Use the form above to log your activities.</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("</div>", unsafe_allow_html=True)
