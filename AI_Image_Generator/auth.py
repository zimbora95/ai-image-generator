import streamlit as st
from firebase_admin import auth
import firebase_admin
from firebase_admin import credentials
import pyrebase
from pathlib import Path
import json
import datetime

# Initialize Firebase Admin SDK if not already initialized
if not firebase_admin._apps:
    current_dir = Path(__file__).parent
    service_account_path = current_dir / 'serviceAccountKey.json'
    
    try:
        cred = credentials.Certificate(str(service_account_path))
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Error initializing Firebase: {str(e)}")
        st.stop()

# Configure Pyrebase
firebaseConfig = {
    "apiKey": "AIzaSyCgf0yCLtLjPJdjJ1TpAXaP6AS3NWgKnUA",
    "authDomain": "toonzon-a2c50.firebaseapp.com",
    "projectId": "toonzon-a2c50",
    "storageBucket": "toonzon-a2c50.appspot.com",
    "messagingSenderId": "997161691599",
    "databaseURL": "https://toonzon-a2c50-default-rtdb.firebaseio.com",
    "appId": "1:997161691599:web:c2e4c0c2838a3ff2ba67e"
}

# Initialize Pyrebase
firebase = pyrebase.initialize_app(firebaseConfig)
auth_firebase = firebase.auth()

def check_token():
    """Check if the user's token is still valid"""
    if 'user' in st.session_state:
        try:
            # Get a new ID token if the current one is about to expire
            user = auth_firebase.refresh(st.session_state.user['refreshToken'])
            st.session_state.user = user
            return True
        except Exception as e:
            if "Token expired" in str(e):
                try:
                    # Try to refresh the token
                    new_token = auth_firebase.refresh(st.session_state.user['refreshToken'])
                    st.session_state.user = new_token
                    return True
                except:
                    st.session_state.user = None
                    return False
            st.session_state.user = None
            return False
    return False

def initialize_firebase_db():
    """Initialize Firebase database with root structure"""
    try:
        db = firebase.database()
        root_ref = db.child("/")
        
        # Initialize root structure if it doesn't exist
        current_data = root_ref.get().val()
        if not current_data or 'users' not in current_data:
            root_ref.update({
                "users": {
                    "_config": {
                        "created_at": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                }
            })
        return True
    except Exception as e:
        st.error(f"Failed to initialize Firebase database: {str(e)}")
        return False

def login_signup():
    # Check token validity at the start
    check_token()
    
    st.markdown("""
        <style>
        .auth-container {
            max-width: 400px;
            margin: auto;
            padding: 20px;
        }
        .google-btn {
            background-color: white;
            color: #757575;
            border: 1px solid #ddd;
            padding: 10px;
            border-radius: 4px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            margin: 10px 0;
            text-decoration: none;
        }
        .google-btn:hover {
            background-color: #f5f5f5;
        }
        .google-icon {
            margin-right: 10px;
            width: 18px;
            height: 18px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    with st.container():
        st.markdown("<div class='auth-container'>", unsafe_allow_html=True)
        
        # Google Sign In button
        google_icon = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxOCIgaGVpZ2h0PSIxOCIgdmlld0JveD0iMCAwIDQ4IDQ4Ij48cGF0aCBmaWxsPSIjRkZDMTA3IiBkPSJNNDMuNjExLDIwLjA4M0g0MlYyMEgyNHY4aDExLjMwM2MtMS42NDksNC42NTctNi4wOCw4LTExLjMwMyw4Yy02LjYyNywwLTEyLTUuMzczLTEyLTEyYzAtNi42MjcsNS4zNzMtMTIsMTItMTJjMy4wNTksMCw1Ljg0MiwxLjE1NCw3Ljk2MSwzLjAzOWw1LjY1Ny01LjY1N0MzNC4wNDYsNi4wNTMsMjkuMjY4LDQsMjQsNEMxMi45NTUsNCw0LDEyLjk1NSw0LDI0YzAsMTEuMDQ1LDguOTU1LDIwLDIwLDIwYzExLjA0NSwwLDIwLTguOTU1LDIwLTIwQzQ0LDIyLjY1OSw0My44NjIsMjEuMzUsNDMuNjExLDIwLjA4M3oiLz48cGF0aCBmaWxsPSIjRkYzRDAwIiBkPSJNNi4zMDYsMTQuNjkxbDYuNTcxLDQuODE5QzE0LjY1NSwxNS4xMDgsMTguOTYxLDEyLDI0LDEyYzMuMDU5LDAsNS44NDIsMS4xNTQsNy45NjEsMy4wMzlsNS42NTctNS42NTdDMzQuMDQ2LDYuMDUzLDI5LjI2OCw0LDI0LDRDMTYuMzE4LDQsOS42NTYsOC4zMzcsNi4zMDYsMTQuNjkxeiIvPjxwYXRoIGZpbGw9IiM0Q0FGNTAiIGQ9Ik0yNCw0NGM1LjE2NiwwLDkuODYtMS45NzcsMTMuNDA5LTUuMTkybC02LjE5LTUuMjM4QzI5LjIxMSwzNS4wOTEsMjYuNzE1LDM2LDI0LDM2Yy01LjIwMiwwLTkuNjE5LTMuMzE3LTExLjI4My03Ljk0NmwtNi41MjIsNS4wMjVDOS41MDUsMzkuNTU2LDE2LjIyNyw0NCwyNCw0NHoiLz48cGF0aCBmaWxsPSIjMTk3NkQyIiBkPSJNNDMuNjExLDIwLjA4M0g0MlYyMEgyNHY4aDExLjMwM2MtMC43OTIsMi4yMzctMi4yMzEsNC4xNjYtNC4wODcsNS41NzFjMC4wMDEtMC4wMDEsMC4wMDItMC4wMDEsMC4wMDMtMC4wMDJsNi4xOSw1LjIzOEMzNi45NzEsMzkuMjA1LDQ0LDM0LDQ0LDI0QzQ0LDIyLjY1OSw0My44NjIsMjEuMzUsNDMuNjExLDIwLjA4M3oiLz48L3N2Zz4="
        
        st.markdown(f"""
            <a href="https://toonzon-a2c50.firebaseapp.com/__/auth/handler?provider=google" target="_blank" class="google-btn">
                <img src="{google_icon}" class="google-icon" />
                Continue with Google
            </a>
        """, unsafe_allow_html=True)
        
        st.markdown("<p style='text-align: center; color: #666;'>- or -</p>", unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["Login", "Sign Up"])
        
        with tab1:
            st.header("Login")
            login_email = st.text_input("Email", key="login_email")
            login_password = st.text_input("Password", type="password", key="login_password")
            
            if st.button("Login", use_container_width=True):
                try:
                    user = auth_firebase.sign_in_with_email_and_password(login_email, login_password)
                    st.session_state.user = user
                    st.success("Logged in successfully!")
                    st.switch_page("🏠_Home.py")
                except Exception as e:
                    st.error("Invalid email or password")
        
        with tab2:
            st.header("Sign Up")
            signup_email = st.text_input("Email", key="signup_email")
            signup_password = st.text_input("Password", type="password", key="signup_password")
            signup_password_confirm = st.text_input("Confirm Password", type="password", key="signup_password_confirm")
            
            if st.button("Sign Up", use_container_width=True):
                if signup_password != signup_password_confirm:
                    st.error("Passwords do not match!")
                elif len(signup_password) < 6:
                    st.error("Password must be at least 6 characters long")
                else:
                    try:
                        user = auth_firebase.create_user_with_email_and_password(signup_email, signup_password)
                        st.success("Account created successfully! Please login.")
                        st.session_state.active_tab = "Login"
                        st.rerun()
                    except Exception as e:
                        if "EMAIL_EXISTS" in str(e):
                            st.error("Email already exists. Please login instead.")
                        else:
                            st.error("Sign up failed. Please try again.")
        
        st.markdown("</div>", unsafe_allow_html=True)

def show_auth_sidebar():
    """Show authentication options in sidebar"""
    # Check token validity
    is_valid = check_token()
    
    with st.sidebar:
        if not is_valid:
            st.info("Sign in to save your generated images to your account!")
            if st.button("Login / Sign Up"):
                st.switch_page("pages/🔐_Auth.py")
        else:
            # Get email from the correct location in the user object
            user_email = None
            if 'user' in st.session_state:
                if 'email' in st.session_state.user:
                    user_email = st.session_state.user['email']
                elif 'email' in st.session_state.user.get('users', [{}])[0]:
                    user_email = st.session_state.user['users'][0]['email']
                else:
                    # Fallback to displaying user ID if email not found
                    user_email = st.session_state.user.get('localId', 'User')
            
            st.write(f"Welcome, {user_email}")
            if st.button("Logout", key="logout"):
                st.session_state.user = None
                st.rerun()

def handle_auth():
    """Handle authentication flow"""
    show_auth_sidebar()
    return False  # Always show main content since auth is on a separate page 