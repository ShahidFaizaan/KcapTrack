from dotenv import load_dotenv
import streamlit as st
from PIL import Image
import os
import google.generativeai as genai
import re

# Load environment variables
load_dotenv()

# Configure the Google Gemini API with the API key
# Note that the API key is set directly in the code for demonstration purposes
# In production, you should use environment variables: os.getenv("GEMINI_API_KEY")
genai.configure(api_key="add your api key")#be with good amountf tokens to get faster ans accurate result


# Function to load Google Gemini Pro Vision API and get response
def get_gemini_response(input_prompt, image_data, nutrition_prompt):
    # The newest Anthropic model is "claude-3-5-sonnet-20241022" which was released October 22, 2024
    model = genai.GenerativeModel('gemini-1.5-pro-latest')
    response = model.generate_content(
        [input_prompt, image_data[0], nutrition_prompt])
    return response.text


# Function to handle the image and prepare it for the API
def input_image_setup(image_file):
    if image_file is not None:
        bytes_data = image_file.getvalue()
        image_parts = [{"mime_type": image_file.type, "data": bytes_data}]
        return image_parts
    else:
        raise FileNotFoundError("No image provided")


# Function to parse nutritional information from Gemini response
def parse_nutrition_info(response_text):
    food_items = []
    health_tips = []
    portion_info = {}

    # Split response into sections
    sections = response_text.split("---")

    # First section should be the nutritional info
    if len(sections) >= 1:
        nutrition_section = sections[0].strip()
        lines = nutrition_section.split('\n')

        # Enhanced pattern to include portion size
        food_pattern = r'^\d+\.\s+(.*?)\s+-\s+Calories:\s+(\d+)\s+kcal,\s+Protein:\s+(\d+)g,\s+Fat:\s+(\d+)g,\s+Carbs:\s+(\d+)g(?:,\s+Portion:\s+(.*?))?$'

        # Pattern to match total
        total_pattern = r'^Total\s+-\s+Calories:\s+(\d+)\s+kcal,\s+Protein:\s+(\d+)g,\s+Fat:\s+(\d+)g,\s+Carbs:\s+(\d+)g'

        for line in lines:
            # Try to match food item pattern
            food_match = re.match(food_pattern, line)
            if food_match:
                portion_size = food_match.group(6) if food_match.group(
                    6) else 'Standard serving'
                food_items.append({
                    'name': food_match.group(1).strip(),
                    'calories': int(food_match.group(2)),
                    'protein': int(food_match.group(3)),
                    'fat': int(food_match.group(4)),
                    'carbs': int(food_match.group(5)),
                    'portion_size': portion_size,
                    'sugars': 0,  # Default values for extended nutrition
                    'fiber': 0,
                    'sodium': 0
                })
                continue

            # Try to match total pattern
            total_match = re.match(total_pattern, line)
            if total_match:
                food_items.append({
                    'name': 'Total',
                    'calories': int(total_match.group(1)),
                    'protein': int(total_match.group(2)),
                    'fat': int(total_match.group(3)),
                    'carbs': int(total_match.group(4)),
                    'portion_size': 'Combined total'
                })

    # Second section should be the portion estimation
    if len(sections) >= 2:
        portion_section = sections[1].strip()
        for line in portion_section.split('\n'):
            if ':' in line and not line.startswith('#'):
                food, portion = line.split(':', 1)
                food = food.strip()
                portion = portion.strip()
                portion_info[food] = portion

                # Update food items with portion info
                for item in food_items:
                    if item['name'].lower() == food.lower():
                        item['portion_size'] = portion

    # Third section should be health tips
    if len(sections) >= 3:
        health_section = sections[2].strip()
        for line in health_section.split('\n'):
            if line.strip() and not line.startswith('#'):
                health_tips.append(line.strip())

    # Return structured data
    return {
        'food_items': food_items,
        'portion_info': portion_info,
        'health_tips': health_tips
    }


# Function to get personalized health warnings based on user profile
def get_health_warnings(food_data, user_profile=None, health_metrics=None):
    warnings = []

    if not user_profile or not health_metrics:
        return warnings

    # Get total nutritional values
    total_item = None
    for item in food_data['food_items']:
        if item['name'] == 'Total':
            total_item = item
            break

    if not total_item:
        return warnings

    # Check for high calorie content relative to user's goals
    if health_metrics.get('target_calories') and total_item['calories'] > (
            health_metrics['target_calories'] * 0.4):
        warnings.append(
            f"⚠️ This meal contains {total_item['calories']} calories, which is over 40% of your daily target ({health_metrics['target_calories']} calories)."
        )

    # Check if meal is low in protein relative to user's goals
    if health_metrics.get('protein_target') and total_item['protein'] < (
            health_metrics['protein_target'] * 0.15):
        warnings.append(
            f"⚠️ This meal is relatively low in protein. Consider adding protein-rich foods to meet your daily target of {health_metrics['protein_target']}g."
        )

    # Check for high-fat content for users with cutting goals
    if user_profile.get('goal') == 'Cutting' and total_item['fat'] > (
            health_metrics.get('fat_target', 65) * 0.4):
        warnings.append(
            "⚠️ This meal is high in fat, which may affect your cutting goals. Consider lower-fat alternatives."
        )

    # Check for low-carb content for users with bulking goals
    if user_profile.get('goal') == 'Bulking' and total_item['carbs'] < (
            health_metrics.get('carbs_target', 300) * 0.2):
        warnings.append(
            "⚠️ This meal is relatively low in carbohydrates, which may not support your bulking goals effectively."
        )

    return warnings


# Function to analyze food image with portion size estimation and health tips
def analyze_food_image(image_source,
                       description="Food items in the image",
                       user_profile=None,
                       health_metrics=None):
    nutrition_prompt = """
    You are a nutrition expert analyzing food in images. Provide detailed, structured output in three sections separated by "---".
    
    SECTION 1: NUTRITIONAL INFORMATION
    List each identified food item with its nutritional content in this format:
    1. Food Name - Calories: X kcal, Protein: Xg, Fat: Xg, Carbs: Xg, Portion: X grams/cups/etc
    ...
    Total - Calories: X kcal, Protein: Xg, Fat: Xg, Carbs: Xg
    
    SECTION 2: PORTION SIZE ESTIMATION
    Estimate portion sizes using reference objects if visible (hand, spoon, plate):
    * Look for hands, utensils, or standard dishes in the image
    * Use these as references to estimate sizes
    * Provide measurements in grams or standard units (cups, tablespoons)
    
    Format each item as:
    Food Name: Estimated X grams (about the size of Y)
    
    SECTION 3: HEALTH TIPS
    Provide 3-5 specific, actionable health tips based on the meal:
    * Comment on nutritional balance
    * Suggest improvements or compliment healthy choices
    * Offer meal timing advice
    * Note any potential allergens or sensitivities
    
    Be precise and specific in your analysis.

    dont give other text except the three sections .   """

    try:
        # Prepare the image for the API call
        image_data = input_image_setup(image_source)

        # Call the Gemini API with the prompts and image data
        response = get_gemini_response(description, image_data,
                                       nutrition_prompt)

        # Parse the nutritional information
        parsed_data = parse_nutrition_info(response)

        # Get personalized warnings based on user profile if available
        warnings = get_health_warnings(parsed_data, user_profile,
                                       health_metrics)

        return {
            'success': True,
            'raw_response': response,
            'food_items': parsed_data['food_items'],
            'portion_info': parsed_data['portion_info'],
            'health_tips': parsed_data['health_tips'],
            'warnings': warnings
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}
