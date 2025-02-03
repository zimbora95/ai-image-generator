import streamlit as st
from pathlib import Path
import pandas as pd

def load_styles(category):
    try:
        file_path = Path(__file__).parent.parent / 'static' / 'styles' / f'styles-{category.lower()}.csv'
        df = pd.read_csv(file_path, on_bad_lines='skip', encoding='utf-8')
        df = df.dropna(subset=['name'])
        df = df.fillna({'Prompt': '', 'negative_prompt': ''})
        return df
    except Exception as e:
        return pd.DataFrame(columns=['name', 'Prompt', 'negative_prompt'])

def show_styles_gallery():
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
            ">Style Gallery</h1>
        </div>
    """, unsafe_allow_html=True)

    # Add tabs for Man and Woman styles
    tab1, tab2 = st.tabs(["👨 Men's Styles", "👩 Women's Styles"])

    def display_style_gallery(category):
        styles_df = load_styles(category)
        styles_df['display_name'] = styles_df['name'].apply(lambda x: x.replace('style_', '') if isinstance(x, str) else x)
        
        # Create a grid layout
        cols = st.columns(3)
        
        for idx, style in enumerate(styles_df['display_name']):
            with cols[idx % 3]:
                # Style card container
                st.markdown(f"""
                    <div style="
                        background: white;
                        border-radius: 15px;
                        padding: 1rem;
                        margin-bottom: 1.5rem;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    ">
                        <h3 style="
                            color: #7B2CBF;
                            text-align: center;
                            margin-bottom: 1rem;
                        ">{style}</h3>
                    </div>
                """, unsafe_allow_html=True)
                
                # Try to load and display the style preview
                file_name = style.lower().replace(' ', '_')
                possible_paths = [
                    Path(__file__).parent.parent / 'static' / 'styles' / category / 'Output' / style / f'{file_name}.png',
                    Path(__file__).parent.parent / 'static' / 'styles' / category / 'Output' / style / f'{style}.png',
                ]
                
                preview_path = next((path for path in possible_paths if path.exists()), None)
                if preview_path:
                    st.image(preview_path, use_container_width=True)
                
                # Display style information
                style_data = styles_df[styles_df['display_name'] == style].iloc[0]
                with st.expander("View Style Details"):
                    st.markdown(f"""
                        **Default Prompt:**  
                        {style_data['Prompt']}
                        
                        **Negative Prompt:**  
                        {style_data['negative_prompt']}
                    """)

    with tab1:
        display_style_gallery("Man")
    
    with tab2:
        display_style_gallery("Woman")

if __name__ == "__main__":
    show_styles_gallery() 