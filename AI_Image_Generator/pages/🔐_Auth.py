import streamlit as st
from auth import login_signup

st.set_page_config(
    page_title="Login / Sign Up",
    page_icon="🔐",
    layout="wide"
)

def main():
    login_signup()
    
    # Add a "Back to Home" button
    if st.button("← Back to Home", key="back_home"):
        st.switch_page("🏠_Home.py")

if __name__ == "__main__":
    main() 