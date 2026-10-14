def calculate_bmi(weight, height):
    """
    Calculate Body Mass Index (BMI)
    
    Parameters:
    weight (float): Weight in kilograms
    height (float): Height in centimeters
    
    Returns:
    float: BMI value
    """
    # Convert height from cm to meters
    height_m = height / 100
    
    # Calculate BMI: weight (kg) / height^2 (m)
    bmi = weight / (height_m * height_m)
    
    return round(bmi, 1)

def get_bmi_category(bmi):
    """Return the BMI category based on the BMI value."""
    if bmi < 18.5:
        return "Underweight"
    elif bmi < 25:
        return "Normal weight"
    elif bmi < 30:
        return "Overweight"
    else:
        return "Obese"

def calculate_bmr(weight, height, age, gender):
    """
    Calculate Basal Metabolic Rate (BMR) using the Mifflin-St Jeor Equation
    
    Parameters:
    weight (float): Weight in kilograms
    height (float): Height in centimeters
    age (int): Age in years
    gender (str): 'Male' or 'Female'
    
    Returns:
    float: BMR value in calories per day
    """
    if gender.lower() == 'male':
        bmr = (10 * weight) + (6.25 * height) - (5 * age) + 5
    else:  # female
        bmr = (10 * weight) + (6.25 * height) - (5 * age) - 161
    
    return round(bmr)

def calculate_tdee(bmr, activity_level):
    """
    Calculate Total Daily Energy Expenditure (TDEE)
    
    Parameters:
    bmr (float): Basal Metabolic Rate
    activity_level (str): Activity level of the user
    
    Returns:
    float: TDEE value in calories per day
    """
    activity_multipliers = {
        'sedentary': 1.2,
        'lightly_active': 1.375,
        'moderately_active': 1.55,
        'very_active': 1.725,
        'extra_active': 1.9
    }
    
    multiplier = activity_multipliers.get(activity_level, 1.2)
    tdee = bmr * multiplier
    
    return round(tdee)

def calculate_target_calories(tdee, goal):
    """
    Calculate target daily calories based on fitness goal
    
    Parameters:
    tdee (float): Total Daily Energy Expenditure
    goal (str): 'bulking', 'cutting', or 'maintaining'
    
    Returns:
    float: Target calories per day
    """
    if goal.lower() == 'bulking':
        # For bulking, add 15% to TDEE
        target = tdee * 1.15
    elif goal.lower() == 'cutting':
        # For cutting, subtract 20% from TDEE
        target = tdee * 0.8
    else:  # maintaining
        target = tdee
    
    return round(target)

def calculate_macronutrients(target_calories, goal):
    """
    Calculate recommended macronutrient distribution
    
    Parameters:
    target_calories (float): Target daily calorie intake
    goal (str): 'bulking', 'cutting', or 'maintaining'
    
    Returns:
    dict: Contains protein, fat, and carbs targets in grams
    """
    if goal.lower() == 'bulking':
        # Higher carbs for bulking
        protein_pct = 0.25  # 25% of calories from protein
        fat_pct = 0.25      # 25% of calories from fat
        carbs_pct = 0.5     # 50% of calories from carbs
    elif goal.lower() == 'cutting':
        # Higher protein for cutting
        protein_pct = 0.35  # 35% of calories from protein
        fat_pct = 0.3       # 30% of calories from fat
        carbs_pct = 0.35    # 35% of calories from carbs
    else:  # maintaining
        # Balanced distribution
        protein_pct = 0.3   # 30% of calories from protein
        fat_pct = 0.25      # 25% of calories from fat
        carbs_pct = 0.45    # 45% of calories from carbs
    
    # Convert percentages to grams
    # Protein: 4 calories per gram
    protein_target = (target_calories * protein_pct) / 4
    
    # Fat: 9 calories per gram
    fat_target = (target_calories * fat_pct) / 9
    
    # Carbs: 4 calories per gram
    carbs_target = (target_calories * carbs_pct) / 4
    
    return {
        'protein': round(protein_target),
        'fat': round(fat_target),
        'carbs': round(carbs_target)
    }
