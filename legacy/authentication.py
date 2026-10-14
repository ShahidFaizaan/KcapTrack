import streamlit as st
import hashlib
import os
import psycopg2
from utils.database import get_connection

def hash_password(password):
    """Hash a password for storing."""
    return hashlib.sha256(password.encode()).hexdigest()

def register(username, password):
    """Register a new user in the database."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # Check if username already exists
        cur.execute("SELECT id FROM users WHERE username = %s", (username,))
        if cur.fetchone() is not None:
            conn.close()
            return False
        
        # Insert new user
        hashed_password = hash_password(password)
        cur.execute(
            "INSERT INTO users (username, password) VALUES (%s, %s) RETURNING id",
            (username, hashed_password)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"An error occurred during registration: {e}")
        return False

def login(username, password):
    """Authenticate a user and set session state if successful."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # Get user by username
        cur.execute("SELECT id, username, password FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        conn.close()
        
        if user and user[2] == hash_password(password):
            # Set session state
            st.session_state.user_id = user[0]
            st.session_state.username = user[1]
            st.session_state.authenticated = True
            return True
        return False
    except Exception as e:
        st.error(f"An error occurred during login: {e}")
        return False

def check_authentication():
    """Check if user is authenticated, redirect to home if not."""
    if not st.session_state.get('authenticated', False):
        st.error("You need to login to access this page")
        st.stop()
