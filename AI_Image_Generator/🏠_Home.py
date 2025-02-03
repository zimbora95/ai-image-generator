import streamlit as st
try:
    import fal_client
except ImportError as e:
    st.error("""
    Error importing fal-serverless package. 
    Please check your installation and make sure you're using version 0.6.41.
    Error details: {}
    """.format(str(e)))
    st.stop()
import os
import tempfile
import random
import datetime
from pathlib import Path
import pandas as pd
from logo import LOGO_BASE64
import base64
from firebase_admin import auth
import firebase_admin
from firebase_admin import credentials
import pyrebase
import json
from firebase_admin import firestore
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# Import the auth module
from auth import firebase, auth_firebase, handle_auth, initialize_firebase_db

# Must be the first Streamlit command
st.set_page_config(
    page_title="Portrait AI Generator",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Set up FAL API key
os.environ['FAL_KEY'] = st.secrets["fal"]["api_key"]

# Modify the Firebase initialization section
try:
    # Configure Firebase
    firebaseConfig = {
        "apiKey": st.secrets["firebase"]["api_key"],
        "authDomain": st.secrets["firebase"]["auth_domain"],
        "projectId": st.secrets["firebase"]["project_id"],
        "storageBucket": st.secrets["firebase"]["storage_bucket"],
        "messagingSenderId": st.secrets["firebase"]["messaging_sender_id"],
        "databaseURL": st.secrets["firebase"]["database_url"],
        "appId": st.secrets["firebase"]["app_id"]
    }

    # Initialize Firebase Admin SDK if not already initialized
    if not firebase_admin._apps:
        current_dir = Path(__file__).parent
        service_account_path = current_dir / 'serviceAccountKey.json'
        
        if not service_account_path.exists():
            st.error("serviceAccountKey.json not found. Please make sure it's in the same directory as this script.")
            st.stop()
            
        cred = credentials.Certificate(str(service_account_path))
        firebase_admin.initialize_app(cred)

    # Get Firestore database instance
    db = firebase_admin.firestore.client()

    # Initialize Pyrebase using the same config
    firebase = pyrebase.initialize_app(firebaseConfig)
    auth_firebase = firebase.auth()

except Exception as e:
    st.error(f"Error initializing Firebase: {str(e)}")
    logging.error(f"Firebase initialization error: {str(e)}", exc_info=True)
    st.stop()

# Initialize session state for storing generated images if it doesn't exist
if 'generated_images' not in st.session_state:
    st.session_state.generated_images = []
if 'favorite_images' not in st.session_state:
    st.session_state.favorite_images = set()

# Initialize session state for input method if not exists
if 'input_method' not in st.session_state:
    st.session_state.input_method = "Upload Image"
if 'clear_upload' not in st.session_state:
    st.session_state.clear_upload = False
if 'selected_category' not in st.session_state:
    st.session_state.selected_category = 'Man'
if 'selected_style' not in st.session_state:
    st.session_state.selected_style = None

# Initialize default prompts
if 'default_prompt' not in st.session_state:
    st.session_state.default_prompt = "Portrait, "
if 'default_negative_prompt' not in st.session_state:
    st.session_state.default_negative_prompt = "bad quality, worst quality, text, signature, watermark, extra limbs"

# At the top with other session state initializations
if 'current_prompt' not in st.session_state:
    st.session_state.current_prompt = "Portrait, man, "

def add_logo():
    st.markdown(
        """
        <style>
            /* Color Variables */
            :root {
                --toonzon-purple: #7B2CBF;
                --toonzon-blue: #4361EE;
                --toonzon-orange: #FF6B35;
                --toonzon-yellow: #FFB800;
                --toonzon-green: #38B000;
                --toonzon-text: #31333F;
                --toonzon-background: #FFFFFF;
            }

            /* Global Styles */
            .stApp {
                background-color: var(--toonzon-background);
                font-family: 'Poppins', sans-serif;
            }

            /* Header Styles */
            .main-header {
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 2rem 0 3rem 0;
                padding: 1rem;
                background: linear-gradient(135deg, var(--toonzon-purple) 0%, var(--toonzon-blue) 100%);
                border-radius: 15px;
            }

            .logo-title-container {
                text-align: center;
            }

            .logo-img {
                width: 180px;
                margin-bottom: 1rem;
            }

            .title-text {
                color: white;
                font-size: 2.8rem;
                font-weight: 700;
                margin-top: 0;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
            }
        </style>
        """,
        unsafe_allow_html=True
    )

def load_styles(category):
    try:
        file_path = Path(__file__).parent / 'static' / 'styles' / f'styles-{category.lower()}.csv'
        # Add error handling for CSV reading
        df = pd.read_csv(file_path, on_bad_lines='skip', encoding='utf-8')
        
        # Ensure the DataFrame has the required columns
        required_columns = ['name', 'Prompt', 'negative_prompt']
        if not all(col in df.columns for col in required_columns):
            # If columns are missing, create a default DataFrame
            df = pd.DataFrame(columns=required_columns)
            st.warning(f"The styles file for {category} is missing required columns. Using default settings.")
        
        # Clean the DataFrame
        df = df.dropna(subset=['name'])  # Remove rows with missing names
        df = df.fillna({'Prompt': '', 'negative_prompt': ''})  # Fill missing values
        
        return df
    except FileNotFoundError:
        st.warning(f"Styles file for {category} not found. Using default settings.")
        return pd.DataFrame(columns=['name', 'Prompt', 'negative_prompt'])
    except Exception as e:
        st.warning(f"Error loading styles for {category}: {str(e)}. Using default settings.")
        return pd.DataFrame(columns=['name', 'Prompt', 'negative_prompt'])

def update_prompt_from_style(style_name, category):
    """Update prompt based on selected style and category"""
    if style_name != 'None':
        styles_df = load_styles(category)
        styles_df['display_name'] = styles_df['name'].apply(lambda x: x.replace('style_', '') if isinstance(x, str) else x)
        style_data = styles_df[styles_df['display_name'] == style_name].iloc[0]
        return style_data['Prompt'], style_data['negative_prompt']
    return f"Portrait, {category.lower()}, ", "bad quality, worst quality, text, signature, watermark, extra limbs"

def on_category_change():
    """Callback for when category changes"""
    category = st.session_state.category
    # Reset style
    st.session_state.style = 'None'
    # Update prompt
    st.session_state.current_prompt = f"Portrait, {category.lower()}, "

def on_style_change():
    """Callback for when style changes"""
    style = st.session_state.style
    category = st.session_state.category
    
    if style != 'None':
        styles_df = load_styles(category)
        styles_df['display_name'] = styles_df['name'].apply(lambda x: x.replace('style_', '') if isinstance(x, str) else x)
        style_data = styles_df[styles_df['display_name'] == style].iloc[0]
        st.session_state.current_prompt = style_data['Prompt']
        st.session_state.default_negative_prompt = style_data['negative_prompt']
    else:
        st.session_state.current_prompt = f"Portrait, {category.lower()}, "

def app_content():
    """Main application content after user is authenticated"""
    add_logo()
    
    # Input section - Required fields first
    st.markdown("## Input", unsafe_allow_html=True)
    
    # Create columns for the required fields
    col1, col2 = st.columns(2)
    
    with col1:
        prompt = st.text_input(
            "Prompt*:", 
            value=st.session_state.current_prompt,
            key="prompt_input"
        )
    
    # Reference Image Input
    with col2:
        input_method = st.radio(
            "Reference Image Input Method*:",
            ["Upload Image", "Camera"],
            key="input_method",
            horizontal=True
        )

        if input_method == "Upload Image":
            uploaded_file = st.file_uploader("Upload a reference image", type=["png", "jpg", "jpeg"])
            if uploaded_file is not None:
                # Create a container with fixed dimensions
                preview_container = st.container()
                with preview_container:
                    st.markdown(
                        """
                        <style>
                        .preview-img {
                            max-height: 250px;
                            width: auto;
                            display: block;
                            margin: auto;
                        }
                        </style>
                        """,
                        unsafe_allow_html=True
                    )
                    st.markdown(
                        f'<img src="data:image/png;base64,{base64.b64encode(uploaded_file.getvalue()).decode()}" class="preview-img">',
                        unsafe_allow_html=True
                    )
        elif input_method == "Camera":
            camera_image = st.camera_input("Take a picture")
            if camera_image is not None:
                # Create a container with fixed dimensions for camera preview
                preview_container = st.container()
                with preview_container:
                    st.markdown(
                        """
                        <style>
                        .preview-img {
                            max-height: 250px;
                            width: auto;
                            display: block;
                            margin: auto;
                        }
                        </style>
                        """,
                        unsafe_allow_html=True
                    )
                    st.markdown(
                        f'<img src="data:image/png;base64,{base64.b64encode(camera_image.getvalue()).decode()}" class="preview-img">',
                        unsafe_allow_html=True
                    )

    # Additional Settings in an expander
    with st.expander("Additional Settings", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            # Image Size selection with dimensions display
            size_options = {
                "Square HD": {"value": "square_hd", "dims": "1024 x 1024"},
                "Square": {"value": "square", "dims": "512 x 512"},
                "Portrait 3:4": {"value": "portrait_4_3", "dims": "768 x 1024"},
                "Portrait 9:16": {"value": "portrait_16_9", "dims": "576 x 1024"},
                "Landscape 4:3": {"value": "landscape_4_3", "dims": "1024 x 768"},
                "Landscape 16:9": {"value": "landscape_16_9", "dims": "1024 x 576"},
                "Custom": {"value": "custom", "dims": "custom"}
            }
            
            selected_size = st.selectbox(
                "Image Size",
                options=list(size_options.keys()),
                format_func=lambda x: f"{x} ({size_options[x]['dims']})"
            )
            
            if selected_size == "Custom":
                col3, col4 = st.columns(2)
                with col3:
                    width = st.number_input("Width", min_value=128, max_value=1024, value=512, step=64)
                with col4:
                    height = st.number_input("Height", min_value=128, max_value=1024, value=512, step=64)
                image_size = {"width": width, "height": height}
            else:
                image_size = size_options[selected_size]["value"]
            
            negative_prompt = st.text_input(
                "Negative Prompt:", 
                value=st.session_state.default_negative_prompt,
                help="Specify what you don't want in the image"
            )

        with col2:
            num_inference_steps = st.slider(
                "Num Inference Steps",
                min_value=1,
                max_value=50,
                value=20,
                step=1,
                help="Higher values = better quality but slower generation"
            )
            
            seed = st.number_input(
                "Seed",
                value=-1,
                help="Use -1 for random seed"
            )
            
            guidance_scale = st.slider(
                "Guidance Scale (CFG)",
                min_value=1.0,
                max_value=20.0,
                value=4.0,
                step=0.5,
                help="How closely to follow the prompt"
            )

    # Style Selection after the prompts
    st.markdown("## Style Selection", unsafe_allow_html=True)

    # Create three columns for the layout
    col1, col2, col3 = st.columns([1, 1, 2])  # Adjust ratios as needed

    with col1:
        category = st.selectbox(
            "Gender:",
            options=['Man', 'Woman'],
            key='category',
            on_change=on_category_change,
            index=0 if st.session_state.selected_category == 'Man' else 1
        )
        st.session_state.selected_category = category
        
        # Show gender preview image
        gender_preview_path = Path(__file__).parent / 'static' / 'styles' / category / 'preview.png'
        if gender_preview_path.exists():
            preview_container = st.container()
            with preview_container:
                st.markdown(
                    """
                    <style>
                    .gender-preview-img {
                        max-height: 300px;
                        width: auto;
                        display: block;
                        margin: auto;
                    }
                    </style>
                    """,
                    unsafe_allow_html=True
                )
                
                # Read and convert the image to base64
                with open(gender_preview_path, "rb") as f:
                    encoded_image = base64.b64encode(f.read()).decode()
                
                # Display the image with size control
                st.markdown(
                    f'<img src="data:image/png;base64,{encoded_image}" class="gender-preview-img">',
                    unsafe_allow_html=True
                )

    # Load styles for the selected category
    styles_df = load_styles(category)
    styles_df['display_name'] = styles_df['name'].apply(lambda x: x.replace('style_', '') if isinstance(x, str) else x)
    style_options = ['None'] + styles_df['display_name'].tolist()

    with col2:
        selected_style = st.selectbox(
            "Style:",
            options=style_options,
            key='style',
            on_change=on_style_change
        )
        st.session_state.selected_style = selected_style

    # Show style preview in the third column
    with col3:
        if selected_style != 'None':
            # Convert spaces to underscores and make lowercase
            file_name = selected_style.lower().replace(' ', '_')
            
            # Try different possible file name formats
            possible_paths = [
                Path(__file__).parent / 'static' / 'styles' / category / 'Output' / selected_style / f'{file_name}.png',
                Path(__file__).parent / 'static' / 'styles' / category / 'Output' / selected_style / f'{selected_style}.png',
                Path(__file__).parent / 'static' / 'styles' / category / 'Output' / selected_style / 'preview.png'
            ]
            
            # Try to find the image in any of the possible paths
            preview_path = next((path for path in possible_paths if path.exists()), None)
            
            if preview_path:
                # Create a container for the preview with controlled size
                preview_container = st.container()
                with preview_container:
                    st.markdown(
                        """
                        <style>
                        .style-preview-img {
                            max-height: 300px;
                            width: auto;
                            display: block;
                            margin: auto;
                        }
                        </style>
                        """,
                        unsafe_allow_html=True
                    )
                    
                    # Read and convert the image to base64
                    with open(preview_path, "rb") as f:
                        encoded_image = base64.b64encode(f.read()).decode()
                    
                    # Display the image with size control
                    st.markdown(
                        f'<img src="data:image/png;base64,{encoded_image}" class="style-preview-img">',
                        unsafe_allow_html=True
                    )
            else:
                st.info(f"No preview available for style: {selected_style}")

    # After style selection section

    # Image Gallery Section
    st.markdown("## Image Gallery", unsafe_allow_html=True)

    # Gallery filters
    col1, col2 = st.columns([2, 1])
    with col1:
        filter_option = st.radio(
            "Filter:",
            ["All Images", "Favorites Only"],
            horizontal=True
        )

    with col2:
        sort_option = st.selectbox(
            "Sort by:",
            ["Newest First", "Oldest First"]
        )

    # After the gallery filters and before the status container, add the display_gallery function
    def display_gallery():
        """Display the image gallery with generated images"""
        try:
            if 'generated_images' in st.session_state and st.session_state.generated_images:
                # Filter images based on selection
                filtered_images = st.session_state.generated_images
                if filter_option == "Favorites Only":
                    filtered_images = [img for img in filtered_images if img.get('id') in st.session_state.favorite_images]
                
                # Sort images
                filtered_images = sorted(
                    filtered_images,
                    key=lambda x: x['timestamp'],
                    reverse=(sort_option == "Newest First")
                )
                
                # Create columns for the gallery
                cols = st.columns(3)
                
                # Track which images to remove after iteration
                images_to_remove = []
                
                for idx, image_data in enumerate(filtered_images):
                    col = cols[idx % 3]
                    with col:
                        # Display the image
                        st.image(image_data['image_url'], use_container_width=True)
                        
                        # Add metadata, favorite and delete buttons in columns
                        meta_cols = st.columns([3, 0.5, 0.5])  # Changed ratios to bring icons closer
                        with meta_cols[0]:
                            # Show truncated prompt
                            prompt = image_data.get('prompt', 'N/A')
                            if len(prompt) > 50:
                                prompt = prompt[:47] + "..."
                            st.caption(f"Prompt: {prompt}")
                            
                            # Format timestamp
                            timestamp = image_data.get('timestamp', 'N/A')
                            if isinstance(timestamp, datetime.datetime):
                                timestamp = timestamp.strftime('%Y-%m-%d %H:%M')
                            st.caption(f"Generated: {timestamp}")
                        
                        with meta_cols[1]:
                            # Favorite button with custom styling
                            is_favorite = image_data.get('id') in st.session_state.favorite_images
                            if st.button("★" if is_favorite else "☆", 
                                       key=f"fav_{image_data.get('id')}", 
                                       help="Remove from favorites" if is_favorite else "Add to favorites"):
                                if is_favorite:
                                    st.session_state.favorite_images.remove(image_data['id'])
                                else:
                                    st.session_state.favorite_images.add(image_data['id'])
                                st.rerun()
                        
                        with meta_cols[2]:
                            # Delete button with custom styling
                            if st.button("🗑️", 
                                       key=f"delete_{idx}", 
                                       help="Delete image"):
                                if delete_image(image_data.get('id')):
                                    st.success("Image deleted successfully!")
                                    images_to_remove.append(image_data)
                                    st.rerun()
                        
                        # Add collapsible section for full details
                        with st.expander("Show Details"):
                            st.markdown(f"**Full Prompt:** {image_data['prompt']}")
                            if 'parameters' in image_data:
                                params = image_data['parameters']
                                st.markdown(f"**Negative Prompt:** {params.get('negative_prompt', 'N/A')}")
                                st.markdown(f"**Image Size:** {params.get('image_size', 'N/A')}")
                                st.markdown(f"**Steps:** {params.get('num_inference_steps', 'N/A')}")
                                st.markdown(f"**Guidance Scale:** {params.get('guidance_scale', 'N/A')}")
                                st.markdown(f"**Seed:** {params.get('seed', 'N/A')}")
                        
                        # Add download button
                        st.download_button(
                            "Download",
                            data=image_data['image_url'],
                            file_name=f"generated_image_{timestamp}.png",
                            mime="image/png",
                            key=f"download_{image_data.get('id')}"
                        )
                        
                        st.markdown("---")  # Separator line
                
                # Remove deleted images from session state
                for image in images_to_remove:
                    st.session_state.generated_images.remove(image)
                
            else:
                st.info("No images generated yet. Try generating some images first!")
                
        except Exception as e:
            st.error(f"Error displaying gallery: {str(e)}")

    # Add status container first
    status_container = st.empty()

    # Display initial gallery state after status container
    if not st.session_state.generated_images:
        st.info("No images generated yet. Generated images will appear here.")

    # Generate Image button
    if st.button("Generate Image", type="primary"):
        if not prompt:
            status_container.error("Please enter a prompt")
        elif input_method not in ["Upload Image", "Camera"]:
            status_container.error("Please select a reference image input method")
        elif (input_method == "Upload Image" and uploaded_file is None) or \
             (input_method == "Camera" and camera_image is None):
            status_container.error("Missing reference image. Please upload one and try again.")
        else:
            # Prepare the reference image
            reference_image_url = None
            if input_method == "Upload Image" and uploaded_file is not None:
                try:
                    # Create a temporary file
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
                        tmp_file.write(uploaded_file.getvalue())
                        tmp_file.flush()
                        
                    reference_image_url = fal_client.upload_file(tmp_file.name)
                    
                    try:
                        os.remove(tmp_file.name)
                    except:
                        pass
                except Exception as e:
                    status_container.error(f"Error processing uploaded file: {str(e)}")
                    
            elif input_method == "Camera" and camera_image is not None:
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
                        tmp_file.write(camera_image.getvalue())
                        tmp_file.flush()
                        
                    reference_image_url = fal_client.upload_file(tmp_file.name)
                    
                    try:
                        os.remove(tmp_file.name)
                    except:
                        pass
                except Exception as e:
                    status_container.error(f"Error processing camera image: {str(e)}")

            try:
                # Show generating status in the container
                with status_container:
                    with st.spinner('Generating image...'):
                        arguments = {
                            "prompt": prompt,
                            "negative_prompt": negative_prompt,
                            "image_size": image_size,
                            "num_inference_steps": num_inference_steps,
                            "guidance_scale": guidance_scale,
                            "true_cfg": 1,
                            "id_weight": 1,
                            "max_sequence_length": "128",
                            "enable_safety_checker": True
                        }
                        
                        if seed != -1:
                            arguments["seed"] = seed
                        if reference_image_url:
                            arguments["reference_image_url"] = reference_image_url

                        result = fal_client.subscribe(
                            "fal-ai/flux-pulid",
                            arguments=arguments,
                            on_queue_update=lambda update: print(f"Status: {update}") if hasattr(update, 'logs') else None
                        )

                        if result and "images" in result and len(result["images"]) > 0:
                            image_id = str(hash(f"{result['images'][0]['url']}_{datetime.datetime.now()}"))
                            
                            image_data = {
                                'id': image_id,
                                'image_url': result['images'][0]['url'],
                                'timestamp': datetime.datetime.now(),
                                'prompt': prompt,
                                'parameters': {
                                    'negative_prompt': negative_prompt,
                                    'image_size': image_size,
                                    'num_inference_steps': num_inference_steps,
                                    'guidance_scale': guidance_scale,
                                    'seed': seed
                                }
                            }
                            
                            # Store the image using our new function
                            store_image(image_data)
                            
                            status_container.success("Image generated successfully!")
                            st.rerun()
                        else:
                            status_container.error("Failed to generate image")
                
            except Exception as e:
                # Convert API error messages to user-friendly messages
                error_message = str(e)
                if "reference_image_url" in error_message and "field required" in error_message:
                    status_container.error("Missing reference image. Please upload one and try again.")
                else:
                    status_container.error(f"Error generating image: {error_message}")

    # Only display gallery if there are images
    if st.session_state.generated_images:
        display_gallery()

def main():
    # Handle authentication sidebar
    handle_auth()
    
    # Initialize user data and load images if logged in
    if st.session_state.get('user'):
        user_id = st.session_state.user['userId']
        initialize_user_data(user_id)
        load_user_images()
    
    # Always show main content since auth is on a separate page
    app_content()

def initialize_firebase_db():
    """Initialize Firebase database with root structure"""
    try:
        db = firebase.database()
        
        # First, try to create the root structure
        try:
            db.child("/").set({
                "users": {
                    "_config": {
                        "created_at": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                }
            })
        except:
            pass  # If root already exists, continue
        
        return True
    except Exception as e:
        st.error(f"Failed to initialize Firebase database: {str(e)}")
        return False

def initialize_user_data(user_id):
    """Initialize user data structure in Firestore"""
    try:
        # Get reference to user document
        user_ref = db.collection('users').document(user_id)
        
        # Check if user document exists
        doc = user_ref.get()
        if not doc.exists:
            # Create initial data structure
            initial_data = {
                "images": {},
                "created_at": datetime.datetime.now(),
                "uid": user_id
            }
            user_ref.set(initial_data)
        
        return True
    except Exception as e:
        st.warning(f"Failed to initialize user data: {str(e)}")
        return False

def store_image(image_data):
    """Store image data in user's account or session state"""
    # Add to session state
    st.session_state.generated_images.append(image_data)
    
    # If user is logged in, store in Firestore
    if st.session_state.get('user'):
        try:
            user_id = st.session_state.user['userId']
            
            # Convert datetime to timestamp for Firestore
            image_data_copy = image_data.copy()
            image_data_copy['timestamp'] = datetime.datetime.now()
            
            # Store the image
            user_ref = db.collection('users').document(user_id)
            images_ref = user_ref.collection('images')
            
            # Add new image with auto-generated ID
            images_ref.add(image_data_copy)
            
            st.success("Image saved to your account!")
        except Exception as e:
            st.warning(f"Failed to save image to account: {str(e)}")

def load_user_images():
    """Load images from user's account if logged in"""
    if st.session_state.get('user'):
        try:
            user_id = st.session_state.user['userId']
            
            # Get images for current user
            images_ref = db.collection('users').document(user_id).collection('images')
            images = images_ref.order_by('timestamp', direction=firestore.Query.DESCENDING).get()
            
            if images:
                # Clear current session images
                st.session_state.generated_images = []
                
                # Convert the images to a list
                for doc in images:
                    image_data = doc.to_dict()
                    st.session_state.generated_images.append(image_data)
                
        except Exception as e:
            st.warning(f"Failed to load images from your account: {str(e)}")

def check_token():
    """Check if the user's token is still valid"""
    if 'user' in st.session_state:
        try:
            # Refresh the ID token
            user = auth_firebase.refresh(st.session_state.user['refreshToken'])
            st.session_state.user = user
            return True
        except Exception as e:
            st.session_state.user = None
            return False
    return False

def delete_image(image_id):
    """Delete an image from Firestore"""
    try:
        if 'user' in st.session_state:
            user_id = st.session_state.user['userId']
            
            # Get images for current user
            images_ref = db.collection('users').document(user_id).collection('images')
            
            # Query for the image with matching id
            query = images_ref.where('id', '==', image_id).limit(1).get()
            
            # Delete the document if found
            for doc in query:
                doc.reference.delete()
                return True
                
            st.warning("Image not found")
            return False
            
    except Exception as e:
        st.error(f"Failed to delete image: {str(e)}")
        return False

if __name__ == "__main__":
    main() 