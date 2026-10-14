import os
import psycopg2
import streamlit as st
from psycopg2 import sql
from datetime import datetime

def get_connection():
    """Create and return a database connection."""##u can make use of any databse which convinent to you
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("PGDATABASE"),
            user=os.getenv("PGUSER"),
            password=os.getenv("PGPASSWORD"),
            host=os.getenv("PGHOST"),
            port=os.getenv("PGPORT")
        )
        return conn
    except psycopg2.Error as e:
        st.error(f"Unable to connect to the database: {e}")
        raise e

def initialize_database():
    """Create necessary tables if they don't exist."""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Create users table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password VARCHAR(256) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Create user_profiles table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            weight FLOAT,
            height FLOAT,
            age INTEGER,
            gender VARCHAR(10),
            goal VARCHAR(20),
            activity_level VARCHAR(20),
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Create health_metrics table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS health_metrics (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            bmi FLOAT,
            bmr FLOAT,
            tdee FLOAT,
            target_calories FLOAT,
            protein_target FLOAT,
            fat_target FLOAT,
            carbs_target FLOAT,
            calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Create food_logs table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS food_logs (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            food_name VARCHAR(100),
            calories FLOAT,
            protein FLOAT,
            fat FLOAT,
            carbs FLOAT,
            portion_size VARCHAR(50),
            meal_type VARCHAR(20),
            consumed_at DATE DEFAULT CURRENT_DATE
        )
        """)
        
        # Create exercise_logs table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS exercise_logs (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            exercise_name VARCHAR(100),
            duration INTEGER,
            calories_burned FLOAT,
            performed_at DATE DEFAULT CURRENT_DATE
        )
        """)
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        st.error(f"Error initializing database: {e}")
    finally:
        cur.close()
        conn.close()

def save_user_profile(user_id, weight, height, age, gender, goal, activity_level):
    """Save or update user profile information."""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Check if profile already exists
        cur.execute("SELECT id FROM user_profiles WHERE user_id = %s", (user_id,))
        profile = cur.fetchone()
        
        if profile:
            # Update existing profile
            cur.execute("""
            UPDATE user_profiles 
            SET weight = %s, height = %s, age = %s, gender = %s, goal = %s, activity_level = %s, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s
            """, (weight, height, age, gender, goal, activity_level, user_id))
        else:
            # Insert new profile
            cur.execute("""
            INSERT INTO user_profiles (user_id, weight, height, age, gender, goal, activity_level)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (user_id, weight, height, age, gender, goal, activity_level))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"Error saving user profile: {e}")
        return False
    finally:
        cur.close()
        conn.close()

def get_user_profile(user_id):
    """Retrieve user profile information."""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
        SELECT weight, height, age, gender, goal, activity_level
        FROM user_profiles
        WHERE user_id = %s
        """, (user_id,))
        profile = cur.fetchone()
        conn.close()
        
        if profile:
            return {
                'weight': profile[0],
                'height': profile[1],
                'age': profile[2],
                'gender': profile[3],
                'goal': profile[4],
                'activity_level': profile[5]
            }
        return None
    except Exception as e:
        st.error(f"Error retrieving user profile: {e}")
        return None

def save_health_metrics(user_id, bmi, bmr, tdee, target_calories, protein_target, fat_target, carbs_target):
    """Save or update user health metrics."""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Check if metrics already exist
        cur.execute("SELECT id FROM health_metrics WHERE user_id = %s", (user_id,))
        metrics = cur.fetchone()
        
        if metrics:
            # Update existing metrics
            cur.execute("""
            UPDATE health_metrics 
            SET bmi = %s, bmr = %s, tdee = %s, target_calories = %s, 
                protein_target = %s, fat_target = %s, carbs_target = %s,
                calculated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s
            """, (bmi, bmr, tdee, target_calories, protein_target, fat_target, carbs_target, user_id))
        else:
            # Insert new metrics
            cur.execute("""
            INSERT INTO health_metrics 
            (user_id, bmi, bmr, tdee, target_calories, protein_target, fat_target, carbs_target)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (user_id, bmi, bmr, tdee, target_calories, protein_target, fat_target, carbs_target))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"Error saving health metrics: {e}")
        return False
    finally:
        cur.close()
        conn.close()

def get_health_metrics(user_id):
    """Retrieve user health metrics."""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
        SELECT bmi, bmr, tdee, target_calories, protein_target, fat_target, carbs_target
        FROM health_metrics
        WHERE user_id = %s
        """, (user_id,))
        metrics = cur.fetchone()
        conn.close()
        
        if metrics:
            return {
                'bmi': metrics[0],
                'bmr': metrics[1],
                'tdee': metrics[2],
                'target_calories': metrics[3],
                'protein_target': metrics[4],
                'fat_target': metrics[5],
                'carbs_target': metrics[6]
            }
        return None
    except Exception as e:
        st.error(f"Error retrieving health metrics: {e}")
        return None

def log_food(user_id, food_name, calories, protein, fat, carbs, portion_size, meal_type):
    """Log food consumption."""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
        INSERT INTO food_logs 
        (user_id, food_name, calories, protein, fat, carbs, portion_size, meal_type)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (user_id, food_name, calories, protein, fat, carbs, portion_size, meal_type))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"Error logging food: {e}")
        return False
    finally:
        cur.close()
        conn.close()

def log_exercise(user_id, exercise_name, duration, calories_burned):
    """Log exercise activity."""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
        INSERT INTO exercise_logs 
        (user_id, exercise_name, duration, calories_burned)
        VALUES (%s, %s, %s, %s)
        """, (user_id, exercise_name, duration, calories_burned))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"Error logging exercise: {e}")
        return False
    finally:
        cur.close()
        conn.close()

def get_daily_food_logs(user_id, date=None):
    """Get food logs for a specific day."""
    if date is None:
        date = datetime.now().date()
        
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
        SELECT food_name, calories, protein, fat, carbs, portion_size, meal_type
        FROM food_logs
        WHERE user_id = %s AND consumed_at = %s
        ORDER BY id DESC
        """, (user_id, date))
        logs = cur.fetchall()
        conn.close()
        
        result = []
        for log in logs:
            result.append({
                'food_name': log[0],
                'calories': log[1],
                'protein': log[2],
                'fat': log[3],
                'carbs': log[4],
                'portion_size': log[5],
                'meal_type': log[6]
            })
        return result
    except Exception as e:
        st.error(f"Error retrieving food logs: {e}")
        return []

def get_daily_exercise_logs(user_id, date=None):
    """Get exercise logs for a specific day."""
    if date is None:
        date = datetime.now().date()
        
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
        SELECT exercise_name, duration, calories_burned
        FROM exercise_logs
        WHERE user_id = %s AND performed_at = %s
        ORDER BY id DESC
        """, (user_id, date))
        logs = cur.fetchall()
        conn.close()
        
        result = []
        for log in logs:
            result.append({
                'exercise_name': log[0],
                'duration': log[1],
                'calories_burned': log[2]
            })
        return result
    except Exception as e:
        st.error(f"Error retrieving exercise logs: {e}")
        return []

def get_daily_summary(user_id, date=None):
    """Get nutritional summary for a specific day."""
    if date is None:
        date = datetime.now().date()
        
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Get total nutritional values
        cur.execute("""
        SELECT SUM(calories), SUM(protein), SUM(fat), SUM(carbs)
        FROM food_logs
        WHERE user_id = %s AND consumed_at = %s
        """, (user_id, date))
        food_totals = cur.fetchone()
        
        # Get total calories burned
        cur.execute("""
        SELECT SUM(calories_burned)
        FROM exercise_logs
        WHERE user_id = %s AND performed_at = %s
        """, (user_id, date))
        exercise_total = cur.fetchone()
        
        conn.close()
        
        return {
            'total_calories': food_totals[0] if food_totals[0] else 0,
            'total_protein': food_totals[1] if food_totals[1] else 0,
            'total_fat': food_totals[2] if food_totals[2] else 0,
            'total_carbs': food_totals[3] if food_totals[3] else 0,
            'total_calories_burned': exercise_total[0] if exercise_total and exercise_total[0] else 0
        }
    except Exception as e:
        st.error(f"Error retrieving daily summary: {e}")
        return {
            'total_calories': 0,
            'total_protein': 0,
            'total_fat': 0,
            'total_carbs': 0,
            'total_calories_burned': 0
        }
