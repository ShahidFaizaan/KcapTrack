import streamlit as st
import plotly.graph_objects as go
from utils.authentication import check_authentication
from utils.database import get_user_profile, save_health_metrics, get_health_metrics
from utils.health_calculations import (
    calculate_bmi, get_bmi_category, calculate_bmr, 
    calculate_tdee, calculate_target_calories, calculate_macronutrients
)
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
    page_title="Health Metrics - NutriTrack",
    page_icon="📊",
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
    .metrics-container {
        animation: slideIn 0.8s ease-in-out;
    }
    @keyframes slideIn {
        0% {opacity: 0; transform: translateX(-20px);}
        100% {opacity: 1; transform: translateX(0);}
    }
    .card {
        background-color: #262730;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    .card:hover {
        transform: translateY(-5px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
    }
    .gauge-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #00DBAD;
        text-align: center;
        margin-bottom: 10px;
    }
    .expander-header {
        font-weight: 600;
        color: #00DBAD;
    }
</style>
""", unsafe_allow_html=True)

# Load metrics animation
metrics_animation = load_lottieurl("https://assets9.lottiefiles.com/packages/lf20_KvK0ZJBQzu.json")

# Custom header
colored_header(
    label="Health Metrics",
    description="Your personalized health calculations and nutritional recommendations",
    color_name="green-70",
)

# Display animation
if metrics_animation:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st_lottie(metrics_animation, height=200, key="metrics")

# Get user profile
profile = get_user_profile(st.session_state.user_id)

if not profile:
    st.warning("Please complete your profile first before viewing health metrics.")
    st.info("Go to the User Profile page to enter your information.")
    st.stop()

# Calculate health metrics
bmi = calculate_bmi(profile['weight'], profile['height'])
bmi_category = get_bmi_category(bmi)
bmr = calculate_bmr(profile['weight'], profile['height'], profile['age'], profile['gender'])
tdee = calculate_tdee(bmr, profile['activity_level'])
target_calories = calculate_target_calories(tdee, profile['goal'])
macros = calculate_macronutrients(target_calories, profile['goal'])

# Save calculated metrics to database
save_health_metrics(
    st.session_state.user_id,
    bmi,
    bmr,
    tdee,
    target_calories,
    macros['protein'],
    macros['fat'],
    macros['carbs']
)

# Display main metrics with enhanced styling
colored_header(
    label="Key Health Indicators",
    description="Your personalized health metrics",
    color_name="green-70",
)

st.markdown("<div class='metrics-container'>", unsafe_allow_html=True)

# Create columns for metrics
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"""
    <div class="card">
        <div class="gauge-title">Body Mass Index (BMI)</div>
        <div style="font-size: 1.8rem; text-align: center; font-weight: 600;">{bmi}</div>
        <div style="text-align: center; color: #ADB5BD;">Category: {bmi_category}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Create BMI gauge with improved styling
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = bmi,
        domain = {'x': [0, 1], 'y': [0, 1]},
        number = {'font': {'color': '#FAFAFA'}},
        gauge = {
            'axis': {'range': [None, 40], 'tickwidth': 1, 'tickcolor': '#FAFAFA'},
            'bar': {'color': "#00DBAD"},
            'bgcolor': 'rgba(0,0,0,0)',
            'borderwidth': 0,
            'steps': [
                {'range': [0, 18.5], 'color': "#00DBAD"},
                {'range': [18.5, 25], 'color': "#00DBAD"},
                {'range': [25, 30], 'color': "#FFA15A"},
                {'range': [30, 40], 'color': "#FF4B4B"}
            ],
            'threshold': {
                'line': {'color': "#FAFAFA", 'width': 4},
                'thickness': 0.75,
                'value': bmi
            }
        },
        title = {'text': "BMI Scale", 'font': {'color': '#FAFAFA'}}
    ))
    
    fig.update_layout(
        paper_bgcolor = 'rgba(0,0,0,0)',
        plot_bgcolor = 'rgba(0,0,0,0)',
        font = {'color': "#FAFAFA"},
    )
    
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.markdown(f"""
    <div class="card">
        <div class="gauge-title">Basal Metabolic Rate (BMR)</div>
        <div style="font-size: 1.8rem; text-align: center; font-weight: 600;">{bmr} calories/day</div>
        <div style="text-align: center; color: #ADB5BD;">Calories needed at complete rest</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="card">
        <div class="gauge-title">Total Daily Energy Expenditure (TDEE)</div>
        <div style="font-size: 1.8rem; text-align: center; font-weight: 600;">{tdee} calories/day</div>
        <div style="text-align: center; color: #ADB5BD;">Calories needed with your activity level</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="card">
        <div class="gauge-title">Target Daily Calories</div>
        <div style="font-size: 1.8rem; text-align: center; font-weight: 600;">{target_calories} calories/day</div>
        <div style="text-align: center; color: #ADB5BD;">Based on your goal: {profile['goal']}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Daily calorie comparison with improved styling
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=['Target', 'TDEE', 'BMR'],
        x=[target_calories, tdee, bmr],
        orientation='h',
        marker=dict(
            color=['#00DBAD', '#636EFA', '#FFA15A']
        )
    ))
    fig.update_layout(
        title={
            'text': "Daily Calorie Comparison",
            'font': {'color': '#FAFAFA'}
        },
        xaxis_title="Calories",
        xaxis={'color': '#FAFAFA'},
        yaxis={'color': '#FAFAFA'},
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)

st.markdown("</div>", unsafe_allow_html=True)

# Display macronutrient recommendations
st.subheader("Recommended Macronutrient Distribution")

# Create columns for macros
col1, col2 = st.columns([3, 1])

with col1:
    # Create macronutrient distribution pie chart
    protein_cals = macros['protein'] * 4
    fat_cals = macros['fat'] * 9
    carbs_cals = macros['carbs'] * 4
    
    fig = go.Figure(data=[go.Pie(
        labels=['Protein', 'Fat', 'Carbohydrates'],
        values=[protein_cals, fat_cals, carbs_cals],
        hole=.4,
        marker_colors=['#FFA15A', '#00CC96', '#636EFA']
    )])
    fig.update_layout(title_text=f"Calorie Distribution ({target_calories} total)")
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.metric("Protein", f"{macros['protein']} g")
    st.metric("Fat", f"{macros['fat']} g")
    st.metric("Carbohydrates", f"{macros['carbs']} g")

# Explanations section
st.subheader("What do these metrics mean?")

with st.expander("Body Mass Index (BMI)"):
    st.write("""
    **BMI** is a measurement of a person's weight with respect to their height. It's a screening tool 
    that can indicate whether a person has a healthy weight for their height.
    
    - **Below 18.5**: Underweight
    - **18.5 - 24.9**: Normal weight
    - **25 - 29.9**: Overweight
    - **30 and above**: Obese
    
    Note that BMI is a general indicator and doesn't account for factors like muscle mass, bone density, 
    or body composition.
    """)

with st.expander("Basal Metabolic Rate (BMR)"):
    st.write("""
    **BMR** represents the minimum number of calories your body needs at complete rest to maintain 
    basic physiological functions like breathing, circulation, and cell production.
    
    Your BMR is calculated using the Mifflin-St Jeor Equation, which takes into account your weight, 
    height, age, and gender.
    """)

with st.expander("Total Daily Energy Expenditure (TDEE)"):
    st.write("""
    **TDEE** estimates the total calories you burn in a day, including your BMR plus additional calories 
    burned through physical activity and digestion.
    
    Your TDEE is calculated by multiplying your BMR by an activity factor based on your reported 
    activity level.
    """)

with st.expander("Target Calories"):
    st.write(f"""
    **Target Calories** is the recommended daily caloric intake to achieve your fitness goal of {profile['goal'].lower()}.
    
    - **Maintaining**: Equal to your TDEE
    - **Bulking**: TDEE + 15% (caloric surplus to gain muscle)
    - **Cutting**: TDEE - 20% (caloric deficit to lose fat)
    """)

with st.expander("Macronutrients"):
    st.write("""
    **Macronutrients** are the nutrients your body needs in large amounts: protein, fat, and carbohydrates.
    
    - **Protein**: Essential for muscle growth and repair (4 calories per gram)
    - **Fat**: Important for hormone production and nutrient absorption (9 calories per gram)
    - **Carbohydrates**: The body's primary energy source (4 calories per gram)
    
    The recommended distribution varies based on your fitness goal, ensuring you get the right balance 
    to support your objectives.
    """)
