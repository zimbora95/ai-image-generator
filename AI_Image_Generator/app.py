import streamlit as st
import fal_client
import os
import tempfile
import random
import datetime
from logo import LOGO_BASE64
import pandas as pd
from pathlib import Path

# Set page config first, before any other st commands
st.set_page_config(
    page_title="Portrait AI Generator",
    page_icon="🎨",
    layout="wide"
)

# Set the API key
API_KEY = os.getenv('FAL_KEY', '19a6ca05-3a0c-4917-8853-9ed685ca6864:5bc9d0f5876a4fdc0c2838a3ff2ba67e')
os.environ['FAL_KEY'] = API_KEY

# Initialize session states
if 'generated_images' not in st.session_state:
    st.session_state.generated_images = []
if 'input_method' not in st.session_state:
    st.session_state.input_method = None
if 'clear_upload' not in st.session_state:
    st.session_state.clear_upload = False
if 'selected_category' not in st.session_state:
    st.session_state.selected_category = 'Man'
if 'selected_style' not in st.session_state:
    st.session_state.selected_style = None

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

            /* Button Styles */
            .stButton > button {
                background: linear-gradient(45deg, var(--toonzon-orange), var(--toonzon-yellow));
                color: white;
                border: none;
                border-radius: 10px;
                padding: 0.6rem 1.2rem;
                font-weight: 600;
                font-size: 1.1rem;
                transition: transform 0.2s ease;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }

            .stButton > button:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 8px rgba(0,0,0,0.15);
            }

            /* Input Fields */
            .stTextInput > div > div {
                border-radius: 8px;
                border: 2px solid #E0E0E0;
            }

            .stTextInput > div > div:focus-within {
                border-color: var(--toonzon-purple);
                box-shadow: 0 0 0 1px var(--toonzon-purple);
            }

            /* Slider Customization */
            .stSlider > div > div > div[data-baseweb="slider"] {
                background-color: var(--toonzon-purple);
            }
            
            /* Make slider background transparent */
            .stSlider > div {
                background-color: transparent !important;
            }
            
            /* Remove default number input styling */
            .stSlider input[type="number"] {
                display: none;
            }
            
            /* Custom range numbers for Inference Steps */
            div[data-testid="stSlider"]:has(label:contains("Num Inference Steps")) > div > div > div[data-baseweb="slider"] > div:first-child::before {
                content: "1" !important;
                position: absolute;
                left: -20px;
                color: #666;
            }
            
            div[data-testid="stSlider"]:has(label:contains("Num Inference Steps")) > div > div > div[data-baseweb="slider"] > div:last-child::after {
                content: "50" !important;
                position: absolute;
                right: -20px;
                color: #666;
            }
            
            /* Custom range numbers for Guidance Scale */
            div[data-testid="stSlider"]:has(label:contains("Guidance Scale")) > div > div > div[data-baseweb="slider"] > div:first-child::before {
                content: "0.00" !important;
                position: absolute;
                left: -30px;
                color: #666;
            }
            
            div[data-testid="stSlider"]:has(label:contains("Guidance Scale")) > div > div > div[data-baseweb="slider"] > div:last-child::after {
                content: "20.00" !important;
                position: absolute;
                right: -35px;
                color: #666;
            }
            
            /* Remove slider thumb background */
            .stSlider > div > div > div[data-baseweb="slider"] [role="slider"] {
                background-color: white !important;
                border: 2px solid var(--toonzon-purple) !important;
            }

            /* Gallery Styles */
            .gallery-item {
                background: white;
                border-radius: 15px;
                padding: 1rem;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                margin-bottom: 1.5rem;
            }

            .gallery-item img {
                border-radius: 10px;
            }

            .gallery-prompt {
                color: var(--toonzon-text);
                font-weight: 600;
                margin: 0.5rem 0;
            }

            .gallery-timestamp {
                color: #666;
                font-size: 0.9rem;
            }

            /* Add custom font */
            @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');
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

def main():
    add_logo()
    
    # Add the header with gradient background and title
    st.markdown("""
        <div style="
            background: linear-gradient(135deg, #7B2CBF 0%, #4361EE 100%);
            padding: 2rem;
            border-radius: 15px;
            margin: 2rem 0 3rem 0;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        ">
            <h1 style="
                color: white;
                font-size: 2.8rem;
                font-weight: 700;
                margin: 0;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
            ">Portrait AI Image Generator</h1>
        </div>
    """, unsafe_allow_html=True)
    
    # Input section
    st.markdown("## Input", unsafe_allow_html=True)

    # Style Selection
    st.markdown("## Style Selection", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        category = st.selectbox(
            "Gender:",
            options=['Man', 'Woman'],
            key='category',
            index=0 if st.session_state.selected_category == 'Man' else 1
        )
        
        # Show gender preview image
        gender_preview_path = Path(__file__).parent / 'static' / 'styles' / category / 'preview.png'
        if gender_preview_path.exists():
            st.image(gender_preview_path, use_container_width=True)

    # Load styles for the selected category
    styles_df = load_styles(category)
    styles_df['display_name'] = styles_df['name'].apply(lambda x: x.replace('style_', '') if isinstance(x, str) else x)
    style_options = ['None'] + styles_df['display_name'].tolist()

    with col2:
        selected_style = st.selectbox(
            "Style:",
            options=style_options,
            key='style'
        )
    
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
                st.image(preview_path, use_container_width=True)
            else:
                st.info(f"No preview available for style: {selected_style}")

    # Update prompt and negative prompt based on selected style
    if selected_style != 'None' and selected_style in styles_df['display_name'].values:
        style_data = styles_df[styles_df['display_name'] == selected_style].iloc[0]
        default_prompt = style_data['Prompt']
        default_negative_prompt = style_data['negative_prompt']
    else:
        # Set default prompt based on selected gender with trailing comma and space
        default_prompt = f"Portrait, {category.lower()}, "
        default_negative_prompt = "bad quality, worst quality, text, signature, watermark, extra limbs"

    # Required fields
    prompt = st.text_input("Prompt*:", 
                          value=default_prompt,
                          help="Enter a description of the image you want to generate")
    negative_prompt = st.text_input("Negative Prompt:", 
                                  value=default_negative_prompt,
                                  help="Specify what you don't want in the image")

    # Add spacing
    st.markdown("<br>", unsafe_allow_html=True)

    # Upload field for reference image with camera option
    col1, col2, col3 = st.columns([2, 1, 1])  # Adjusted ratio for better layout

    with col1:
        if 'uploaded_file_key' not in st.session_state:
            st.session_state.uploaded_file_key = 0
        
        # Only reset the key when we need to clear the upload
        if st.session_state.clear_upload:
            st.session_state.uploaded_file_key += 1
            st.session_state.clear_upload = False
        
        # Use the key to force a reset of the file uploader when needed
        uploaded_file = st.file_uploader("Upload an image:", 
                                       type=['jpg', 'jpeg', 'png'],
                                       key=f"uploader_{st.session_state.uploaded_file_key}")
        
        if uploaded_file is not None and st.session_state.input_method != 'upload':
            st.session_state.input_method = 'upload'
            st.session_state.camera_enabled = False

    # Add line break
    st.markdown("<br>", unsafe_allow_html=True)

    # Camera controls on new line
    col1, col2, col3 = st.columns([2, 1, 1])  # Keep same ratio for consistency

    with col1:
        def on_camera_toggle():
            if st.session_state.camera_enabled:
                st.session_state.input_method = 'camera'
                st.session_state.clear_upload = True
            else:
                st.session_state.input_method = None

        # Create a container div with flexbox layout
        st.markdown("""
            <div style='display: flex; align-items: center; gap: 10px;'>
                <span style='font-size: 14px; font-family: "Source Sans Pro", sans-serif; font-weight: 400; color: rgb(49, 51, 63);'>
                    Enable Camera:
                </span>
                <div style='margin-top: 5px;'>
                    <!-- Placeholder for checkbox -->
                    &nbsp;
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # Place the checkbox slightly higher to align with the text
        st.markdown("<style>div[data-testid='stCheckbox'] {margin-top: -40px;}</style>", unsafe_allow_html=True)
        camera_enabled = st.checkbox("", 
                                   value=False, 
                                   key='camera_enabled',
                                   on_change=on_camera_toggle,
                                   label_visibility="collapsed")

    with col2:
        camera_file = st.camera_input("Take a picture", disabled=not camera_enabled) if camera_enabled else None

    # Use either uploaded file or camera file based on input method
    if st.session_state.input_method == 'upload':
        reference_file = uploaded_file
    elif st.session_state.input_method == 'camera':
        reference_file = camera_file
    else:
        reference_file = None

    # Show image preview if either file is uploaded or picture is taken
    if reference_file is not None:
        col1, col2, col3 = st.columns([1, 2, 1])  # Creates three columns with middle one being larger
        with col2:  # Use the middle column for the image
            st.image(reference_file, caption="Reference Image Preview", use_container_width=True)

    # Additional settings in an expandable section
    with st.expander("Additional Settings", expanded=False):
        # Image size selection
        image_size_options = {
            "Square (512 x 512)": "square",
            "Square HD (1024 x 1024)": "square_hd",
            "Portrait 3:4 (768 x 1024)": "portrait_4_3",
            "Portrait 9:16 (576 x 1024)": "portrait_16_9",
            "Landscape 4:3 (1024 x 768)": "landscape_4_3",
            "Landscape 16:9 (1024 x 576)": "landscape_16_9"
        }
        image_size = st.selectbox(
            "Image Size:",
            options=list(image_size_options.keys()),
            index=1  # Default to Square HD
        )
        
        # Advanced parameters
        col1, col2 = st.columns(2)
        with col1:
            num_inference_steps = st.slider("Num Inference Steps:", 
                                          min_value=1, 
                                          max_value=50, 
                                          value=20,
                                          format="%d")
            seed = st.number_input("Seed (-1 for random):", -1, 2147483647, -1)
        with col2:
            guidance_scale = st.slider("Guidance Scale (CFG):", 
                                     min_value=0.0, 
                                     max_value=20.0, 
                                     value=4.0, 
                                     step=0.5,
                                     format="%.2f")

    # Generate image button - centered and styled
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        generate_button = st.button(
            "Generate Image",
            type="primary",
            use_container_width=True
        )

    # Change the if condition to use our new button
    if generate_button:
        # Validation
        if not prompt:
            st.error("Please enter a prompt.")
            st.stop()
        
        if reference_file is None:
            st.error("Please upload a reference image or take a picture.")
            st.stop()

        try:
            # Save the uploaded file to a temporary location
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                temp_file.write(reference_file.getvalue())
                temp_file_path = temp_file.name

            # Upload the file to fal.ai
            file_url = fal_client.upload_file(temp_file_path)
            
            # Use random seed if -1
            actual_seed = random.randint(0, 2147483647) if seed == -1 else seed
            
            # Prepare input with required fields
            request_data = {
                "prompt": prompt,
                "reference_image_url": file_url,
                "image_size": image_size_options[image_size],
                "num_inference_steps": num_inference_steps,
                "negative_prompt": negative_prompt,
                "guidance_scale": guidance_scale,
                "seed": actual_seed,
                "true_cfg": 1,
                "id_weight": 1,
                "enable_safety_checker": True,
                "max_sequence_length": "128"
            }

            # Call the API
            with st.spinner('Generating image...'):
                result = fal_client.subscribe("fal-ai/flux-pulid", request_data)
                
                # Check if result contains images
                if isinstance(result, dict) and 'images' in result:
                    image_url = result['images'][0]['url']
                    st.image(image_url)
                    st.write("✨ Image generated successfully!")
                    
                    # Store the new image with timestamp and prompt
                    st.session_state.generated_images.append({
                        'url': image_url,
                        'prompt': prompt,
                        'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'reference_image': reference_file
                    })
                else:
                    st.error("Failed to generate image. No images in response.")

        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
        
        finally:
            # Clean up the temporary file
            if 'temp_file_path' in locals():
                os.unlink(temp_file_path)

    # After the generate button section, display the gallery
    if st.session_state.generated_images:
        st.markdown("<h2 style='color: var(--toonzon-purple); text-align: center; margin-top: 3rem;'>Generated Images Gallery</h2>", unsafe_allow_html=True)
        
        cols = st.columns(3)
        
        for idx, img_data in enumerate(reversed(st.session_state.generated_images)):
            with cols[idx % 3]:
                st.markdown("""
                    <div class="gallery-item">
                        <img src="{}" style="width: 100%;">
                        <p class="gallery-prompt">✨ {}</p>
                        <p class="gallery-timestamp">🕒 {}</p>
                    </div>
                """.format(img_data['url'], img_data['prompt'], img_data['timestamp']), unsafe_allow_html=True)

if __name__ == "__main__":
    main()
