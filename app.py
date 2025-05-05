import streamlit as st
import pandas as pd
from datetime import datetime
import os
import time
from dotenv import load_dotenv
import base64
from io import BytesIO
import requests
import json

# Import utility modules
from utils.airtable_client import AirtableClient
from utils.email_sender import send_email
from utils.analytics import log_view, display_analytics
from utils.pdf_generator import generate_pdf

# Load environment variables
load_dotenv()

# Set page configuration
st.set_page_config(
    page_title="Chamber of Commerce - AI Image Ideas",
    page_icon="🏢",
    layout="wide"
)

# Initialize session state
if 'selected_company' not in st.session_state:
    st.session_state.selected_company = None
if 'previous_company' not in st.session_state:
    st.session_state.previous_company = None
if 'show_analytics' not in st.session_state:
    st.session_state.show_analytics = False
if 'generated_images' not in st.session_state:
    st.session_state.generated_images = {}
if 'generated_idea' not in st.session_state:
    st.session_state.generated_idea = None
if 'force_refresh' not in st.session_state:
    st.session_state.force_refresh = False

# Check if we need to force a refresh due to image generation
if st.session_state.force_refresh:
    # Reset the flag
    st.session_state.force_refresh = False
    # Ensure rerun happens only once
    st.rerun()

# Initialize Airtable client
airtable_client = AirtableClient(
    pat=os.getenv("AIRTABLE_PAT"),
    base_name="Chamber of Commerce List",
    table_name="Chamber-BS"
)

# Get all records from Airtable
@st.cache_data(ttl=300)  # Cache data for 5 minutes
def get_companies():
    return airtable_client.get_all_records()

# Function to check for existing images via webhook
def check_image_status(company_name):
    webhook_url = "https://hook.eu2.make.com/z31ifl3yfwdpu23bgbefzy96q5xr5zun"
    
    # Call with idea_number set to 0 to just check status
    payload = {
        "company_name": company_name,
        "idea_number": 0,
        "description": ""
    }
    
    try:
        response = requests.post(webhook_url, json=payload)
        if response.status_code == 200:
            try:
                # Handle potentially malformed JSON
                response_text = response.text
                
                # More aggressive JSON cleaning:
                # 1. Fix missing comma after file_name
                response_text = response_text.replace('\"file_name\": \"', '\"file_name\": \"').replace('\"\n  \"', '\",\n  \"')
                
                # 2. Remove any newlines or control characters within JSON string values
                import re
                # First, let's extract the JSON structure
                matches = re.findall(r'\"([^\"]+)\"\s*:\s*\"([^\"]+)\"', response_text)
                for key, value in matches:
                    # Replace any newlines or control chars in the value with empty string
                    clean_value = re.sub(r'[\n\r\t]', '', value)
                    # Replace the original value with the cleaned one
                    response_text = response_text.replace(f'"{key}": "{value}"', f'"{key}": "{clean_value}"')
                
                # 3. Ensure proper comma after file_name field
                response_text = response_text.replace('"file_name": "', '"file_name": "')
                response_text = response_text.replace('"\n  "generated_date"', '",\n  "generated_date"')
                
                # Handle single line responses - another pattern
                if '"file_name":' in response_text and '"generated_date":' in response_text:
                    response_text = response_text.replace('"file_name": "', '"file_name": "')
                    response_text = response_text.replace('png"\n', 'png",\n')
                    response_text = response_text.replace('png" ', 'png", ')
                
                try:
                    # Try to parse the cleaned JSON
                    data = json.loads(response_text)
                except json.JSONDecodeError:
                    # If still failing, try a more comprehensive approach
                    # Extract the essential fields and rebuild the JSON
                    status_match = re.search(r'"status":\s*"([^"]+)"', response_text)
                    company_match = re.search(r'"company_name":\s*"([^"]+)"', response_text)
                    idea_match = re.search(r'"idea_number":\s*(\d+)', response_text)
                    image_match = re.search(r'"image_url":\s*"([^"]+)"', response_text)
                    file_match = re.search(r'"file_name":\s*"([^"]+)"', response_text)
                    date_match = re.search(r'"generated_date":\s*"([^"]+)"', response_text)
                    
                    # Create a clean JSON object
                    data = {
                        "status": status_match.group(1) if status_match else "error",
                        "company_name": company_match.group(1) if company_match else "",
                        "idea_number": int(idea_match.group(1)) if idea_match else 0,
                        "image_url": image_match.group(1) if image_match else "",
                        "file_name": file_match.group(1) if file_match else "",
                        "generated_date": date_match.group(1) if date_match else datetime.now().strftime("%Y-%m-%d")
                    }
                # Fix image URLs if needed
                if "image_url" in data and data["image_url"]:
                    # We're now getting Airtable URLs directly, so just fix ampersand encoding
                    data["image_url"] = data["image_url"].replace("&amp;", "&")
                return data
            except json.JSONDecodeError as e:
                st.error(f"Error parsing JSON response: {str(e)}")
                st.code(response.text)  # Display the raw response for debugging
                return {"status": "error", "message": f"JSON parsing error: {str(e)}"}
        else:
            return {"status": "error", "message": f"Error: {response.text}"}
    except Exception as e:
        return {"status": "error", "message": f"Exception: {str(e)}"}

# Header
st.title("Chamber of Commerce AI Image Ideas")
st.markdown("Welcome to the AI Image Ideas portal. Select a company to view AI-generated image suggestions.")

# Pre-fetched stock photos
modern_business_imagery = [
    "https://images.unsplash.com/photo-1507679799987-c73779587ccf",
    "https://images.unsplash.com/photo-1444653614773-995cb1ef9efa",
    "https://images.unsplash.com/photo-1444653389962-8149286c578a",
    "https://images.unsplash.com/photo-1431540015161-0bf868a2d407"
]

creative_ai_concept_illustrations = [
    "https://images.unsplash.com/photo-1471666875520-c75081f42081",
    "https://images.unsplash.com/photo-1485546784815-e380f3297414",
    "https://images.unsplash.com/photo-1490186969638-fe0c8aea80bd",
    "https://images.unsplash.com/photo-1497048679117-1a29644559e3"
]

# Load data
companies = get_companies()
# Get company names and sort them alphabetically
company_names = [company.get('fields', {}).get('Company Name', 'Unknown') for company in companies if 'Company Name' in company.get('fields', {})]
company_names.sort()  # Sort alphabetically

# Sidebar
with st.sidebar:
    st.header("Navigation")
    
    # Company selector
    selected_company_name = st.selectbox(
        "Select a company", 
        options=company_names,
        index=0 if company_names else None
    )
    
    # Find the selected company record
    selected_company = next((company for company in companies 
                            if company.get('fields', {}).get('Company Name') == selected_company_name), 
                            None)
    
    # Check if the company selection has changed
    company_changed = (st.session_state.previous_company != selected_company_name)
    
    if company_changed and selected_company_name:
        # Clear any previously generated idea when switching companies
        if 'generated_idea' in st.session_state:
            st.session_state.generated_idea = None
            
        # Check for existing images for this company
        image_status = check_image_status(selected_company_name)
        
        # Store the status in session state
        if image_status.get("status") == "exists":
            # Image already exists for this company
            
            # Store both idea_number and idea_chosen (if available)
            idea_number = str(image_status.get("idea_number"))
            idea_chosen = str(image_status.get("idea_chosen", ""))  # Try to get idea_chosen
            st.session_state.generated_idea = idea_chosen if idea_chosen else idea_number
            
            # Get the image URL and process it if needed
            image_url = image_status.get("image_url", "")
            
            # Just handle ampersand encoding since we're using Airtable URLs directly
            if image_url:
                image_url = image_url.replace("&amp;", "&")
            
            st.session_state.generated_images[selected_company_name] = {
                "idea_number": idea_number,
                "idea_chosen": idea_chosen,  # Store the new field
                "image_url": image_url,  # Use the processed URL
                "file_name": image_status.get("file_name", ""),
                "generated_date": image_status.get("generated_date", datetime.now().strftime("%Y-%m-%d"))
            }
    
    # Update session state
    st.session_state.selected_company = selected_company
    st.session_state.previous_company = selected_company_name
    
    # Navigation buttons using JavaScript to scroll to anchors
    st.markdown("""
    <style>
    .stButton button {
        width: 100%;
    }
    </style>
    """, unsafe_allow_html=True)
    
    if st.button("Jump to Behind the Scenes Video"):
        # Use JavaScript to scroll to the video section
        st.markdown("""
        <script>
            document.querySelector('#video-section').scrollIntoView({
                behavior: 'smooth'
            });
        </script>
        """, unsafe_allow_html=True)
    
    if st.button("Jump to Ideas Flipbook"):
        # Use JavaScript to scroll to the flipbook section
        st.markdown("""
        <script>
            document.querySelector('#flipbook-section').scrollIntoView({
                behavior: 'smooth'
            });
        </script>
        """, unsafe_allow_html=True)
    
    # Analytics Dashboard with password protection
    st.divider()
    st.subheader("Admin Area")
    admin_password = st.text_input("Admin Password", type="password")
    if st.button("Access Analytics Dashboard") and admin_password == "chamber2024":
        st.session_state.show_analytics = True

# Main content
if st.session_state.selected_company:
    # Log the view for analytics
    log_view(st.session_state.selected_company.get('fields', {}).get('Company Name', 'Unknown'))
    
    # Get company details
    company_data = st.session_state.selected_company.get('fields', {})
    
    # Display company header and details
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header(company_data.get('Company Name', 'Unknown Company'))
        
        # Display website and contact info
        if 'Website' in company_data:
            st.write(f"🌐 [Website]({company_data['Website']})")
        
        if 'Email' in company_data:
            st.write(f"📧 Email: {company_data['Email']}")
        
        if 'Telephone' in company_data:
            st.write(f"☎️ Phone: {company_data['Telephone']}")
        
        if 'Address' in company_data:
            st.write(f"🏢 Address: {company_data['Address']}")
    
    with col2:
        # Display company description or a summary
        if 'Company Description' in company_data:
            st.subheader("About")
            st.write(company_data['Company Description'])
    
# We'll move the Header Image display to below the website visual style
    
    # Display website thumbnail and visual description if available
    if 'Website Visual Description' in company_data:
        st.subheader("Website Visual Style")
        
        # Display website thumbnail if available
        if 'Website Image' in company_data and company_data['Website Image']:
            col1, col2 = st.columns([1, 3])
            with col1:
                st.image(
                    company_data.get('Website Image', [{'url': ''}])[0].get('url', ''),
                    use_container_width=True,
                    caption="Website Thumbnail"
                )
            with col2:
                st.write(company_data['Website Visual Description'])
        else:
            # If no thumbnail, just show the description
            st.write(company_data['Website Visual Description'])
    
    # Add helpful notices about the AI-generated images
    st.warning("⚠️ We kindly ask that you only generate ONE image for your own business. This is a proof of concept, and while we aim for quality results, occasional variations or mistakes may occur. Thank you for your understanding.")
    
    # Add a message about adapting ideas
    st.info("💡 These AI-generated ideas are meant to serve as inspiration. We encourage you to adapt them to your specific business needs, brand identity, and target audience. Consider uploading your logo or other brand elements to customize the final designs for your business.")
    
    # No heading for AI Image Ideas as the banner image already contains this information
    
    # Display header image for AI Image Ideas for Company just before showing the ideas
    if 'Header Image' in company_data and company_data['Header Image']:
        # Display the image without a heading, but with alt text
        company_name = company_data.get('Company Name', 'Unknown')
        st.image(
            company_data.get('Header Image', [{'url': ''}])[0].get('url', ''), 
            use_container_width=True,
            caption=f"AI Image Ideas for {company_name}"
        )

    # Check if we have AI Image Suggestions in the data
    if 'Open AI Image Suggestions' in company_data and company_data['Open AI Image Suggestions']:
        # Parse the AI suggestions
        ai_suggestions = company_data['Open AI Image Suggestions']
        
        # Create a function to call the webhook
        def generate_image(idea_number, description):
            webhook_url = "https://hook.eu2.make.com/z31ifl3yfwdpu23bgbefzy96q5xr5zun"
            
            # Prepare the payload
            payload = {
                "idea_number": idea_number,
                "description": description,
                "company_name": company_data.get('Company Name', 'Unknown')
            }
            
            try:
                # Call the webhook
                response = requests.post(webhook_url, json=payload)
                if response.status_code == 200:
                    try:
                        # Handle potentially malformed JSON
                        response_text = response.text
                        
                        # More aggressive JSON cleaning:
                        # 1. Fix missing comma after file_name
                        response_text = response_text.replace('\"file_name\": \"', '\"file_name\": \"').replace('\"\n  \"', '\",\n  \"')
                        
                        # 2. Remove any newlines or control characters within JSON string values
                        import re
                        # First, let's extract the JSON structure
                        matches = re.findall(r'\"([^\"]+)\"\s*:\s*\"([^\"]+)\"', response_text)
                        for key, value in matches:
                            # Replace any newlines or control chars in the value with empty string
                            clean_value = re.sub(r'[\n\r\t]', '', value)
                            # Replace the original value with the cleaned one
                            response_text = response_text.replace(f'"{key}": "{value}"', f'"{key}": "{clean_value}"')
                        
                        # 3. Ensure proper comma after file_name field
                        response_text = response_text.replace('"file_name": "', '"file_name": "')
                        response_text = response_text.replace('"\n  "generated_date"', '",\n  "generated_date"')
                        
                        # Handle single line responses - another pattern
                        if '"file_name":' in response_text and '"generated_date":' in response_text:
                            response_text = response_text.replace('"file_name": "', '"file_name": "')
                            response_text = response_text.replace('png"\n', 'png",\n')
                            response_text = response_text.replace('png" ', 'png", ')
                        
                        try:
                            # Try to parse the cleaned JSON
                            data = json.loads(response_text)
                        except json.JSONDecodeError:
                            # If still failing, try a more comprehensive approach
                            # Extract the essential fields and rebuild the JSON
                            status_match = re.search(r'"status":\s*"([^"]+)"', response_text)
                            company_match = re.search(r'"company_name":\s*"([^"]+)"', response_text)
                            idea_match = re.search(r'"idea_number":\s*(\d+)', response_text)
                            image_match = re.search(r'"image_url":\s*"([^"]+)"', response_text)
                            file_match = re.search(r'"file_name":\s*"([^"]+)"', response_text)
                            date_match = re.search(r'"generated_date":\s*"([^"]+)"', response_text)
                            
                            # Create a clean JSON object
                            data = {
                                "status": status_match.group(1) if status_match else "error",
                                "company_name": company_match.group(1) if company_match else "",
                                "idea_number": int(idea_match.group(1)) if idea_match else 0,
                                "image_url": image_match.group(1) if image_match else "",
                                "file_name": file_match.group(1) if file_match else "",
                                "generated_date": date_match.group(1) if date_match else datetime.now().strftime("%Y-%m-%d")
                            }
                        
                        status = data.get("status", "")
                    except json.JSONDecodeError as e:
                        st.error(f"Error parsing JSON response: {str(e)}")
                        st.code(response.text)  # Display the raw response for debugging
                        return False
                    
                    if status == "success":
                        # Store the image data in session state
                        company_name = company_data.get('Company Name', 'Unknown')
                        
                        # Process the image URL from Airtable
                        image_url = data.get("image_url", "")
                        
                        # Just handle ampersand encoding since we're using Airtable URLs directly
                        if image_url:
                            image_url = image_url.replace("&amp;", "&")
                            
                        # For successful generation, we use idea_number (since no idea_chosen yet)
                        # This field will be used to select which idea section shows the image
                        idea_number = str(data.get("idea_number", ""))
                        
                        st.session_state.generated_images[company_name] = {
                            "idea_number": idea_number,
                            "idea_chosen": idea_number,  # For new generations, set idea_chosen to be the same as idea_number
                            "image_url": image_url,  # Use the processed URL
                            "file_name": data.get("file_name", ""),
                            "generated_date": data.get("generated_date", datetime.now().strftime("%Y-%m-%d"))
                        }
                        
                        # Show a success message
                        st.success(f"Successfully generated image for idea {idea_number}.")
                        
                        # Store the current idea number in session state for reloading
                        st.session_state.generated_idea = idea_number
                        
                        # Add a small delay to ensure data is properly saved before refresh
                        time.sleep(0.5)
                        
                        # Flag to force refresh after execution completes
                        st.session_state.force_refresh = True
                        
                        return True
                    elif status == "exists":
                        # Image already exists
                        company_name = company_data.get('Company Name', 'Unknown')
                        
                        # Process the image URL from Airtable
                        image_url = data.get("image_url", "")
                        
                        # Just handle ampersand encoding since we're using Airtable URLs directly
                        if image_url:
                            image_url = image_url.replace("&amp;", "&")
                            
                        # Store both idea_number and idea_chosen (if available)
                        idea_number = str(data.get("idea_number", ""))
                        idea_chosen = str(data.get("idea_chosen", ""))
                        
                        st.session_state.generated_images[company_name] = {
                            "idea_number": idea_number,
                            "idea_chosen": idea_chosen,  # Store the new field
                            "image_url": image_url,  # Use the processed URL
                            "file_name": data.get("file_name", ""),
                            "generated_date": data.get("generated_date", datetime.now().strftime("%Y-%m-%d"))
                        }
                        # Display message with idea_chosen if available, otherwise use idea_number
                        display_idea = idea_chosen if idea_chosen else idea_number
                        st.info(f"Image already exists for idea {display_idea}.")
                        
                        # Add a small delay to ensure data is properly saved before refresh
                        time.sleep(0.5)
                        
                        # Flag to force refresh after execution completes
                        st.session_state.force_refresh = True
                        
                        return True
                    else:
                        # Status should be "no image and no selection exists"
                        st.info(f"Generating AI image for idea {idea_number}. Please wait a moment and check back later.")
                        
                        # Add a small delay to ensure data is properly saved before refresh
                        time.sleep(0.5)
                        
                        # Flag to force refresh after execution completes
                        st.session_state.force_refresh = True
                        
                        return True
                else:
                    st.error(f"Failed to generate image: {response.text}")
                    return False
            except Exception as e:
                st.error(f"Error generating image: {str(e)}")
                return False
        
        # Initialize session state for tracking generated ideas
        if 'generated_idea' not in st.session_state:
            st.session_state.generated_idea = None

        # Parse the ideas - improved version
        ideas = []
        valid_ideas = []
        
        # Split the content by "IDEA" to get each complete idea block
        idea_blocks = ai_suggestions.split("IDEA")
        
        # Process each idea block
        for i, block in enumerate(idea_blocks):
            if not block.strip():
                continue
                
            # Try to extract idea number from the first line
            first_line = block.strip().split('\n')[0]
            if first_line and first_line[0].isdigit():
                idea_number = first_line[0]
                
                # We only want IDEAS 1, 2, 3 (skip IDEA 0 or any others)
                if idea_number in ['1', '2', '3']:
                    # Extract title, description, and purpose
                    title = ""
                    description = ""
                    purpose = ""
                    
                    if "Title:" in block:
                        title_parts = block.split("Title:", 1)[1].split("Description:", 1)
                        if len(title_parts) > 0:
                            title = title_parts[0].strip()
                    
                    if "Description:" in block:
                        desc_parts = block.split("Description:", 1)[1].split("Purpose:", 1)
                        if len(desc_parts) > 0:
                            description = desc_parts[0].strip()
                    
                    if "Purpose:" in block:
                        purpose = block.split("Purpose:", 1)[1].strip()
                    
                    # Create the idea object
                    idea = {
                        "number": idea_number,
                        "title": title,
                        "description": description,
                        "purpose": purpose
                    }
                    
                    valid_ideas.append(idea)
        
        # Sort ideas by number to ensure 1, 2, 3 order
        valid_ideas.sort(key=lambda x: x['number'])
        
        # Display the ideas
        if valid_ideas:
            for i, idea in enumerate(valid_ideas):
                st.subheader(f"IDEA {idea['number']}")
                st.markdown(f"**Title:** {idea.get('title', '')}")
                st.markdown(f"**Description:** {idea.get('description', '')}")
                st.markdown(f"**Purpose:** {idea.get('purpose', '')}")
                
                # Use a unique key for each button
                button_key = f"generate_button_{i}"
                
                # Get company name for image lookup
                company_name = company_data.get('Company Name', 'Unknown')
                
                # Check if we have a generated image for this company and idea
                # First check if we have idea_chosen or fallback to idea_number
                if company_name in st.session_state.generated_images:
                    # Check for idea_chosen first (the new field)
                    stored_idea = st.session_state.generated_images[company_name].get("idea_chosen")
                    
                    # If idea_chosen is None, fall back to idea_number
                    if stored_idea is None:
                        stored_idea = st.session_state.generated_images[company_name].get("idea_number")
                        
                    # Compare with current idea
                    has_image = str(stored_idea) == idea['number']
                else:
                    has_image = False
                
                # Check if any idea for this company has been generated 
                # by looking directly at the generated_images dictionary
                any_idea_generated = company_name in st.session_state.generated_images
                
                # Show appropriate button based on state
                if has_image:
                    # Display the generated image first
                    image_url = st.session_state.generated_images[company_name].get("image_url")
                    gen_date = st.session_state.generated_images[company_name].get("generated_date")
                    
                    if gen_date:
                        # Display the generation date above the image
                        st.markdown(f"**Image Generated: {gen_date}**")
                    
                    if image_url:
                        # Just fix ampersand encoding in URLs to prevent display issues
                        image_url = image_url.replace("&amp;", "&")
                            
                        try:
                            # Display the image above the button
                            st.image(image_url, use_container_width=True)
                        except Exception as e:
                            st.error(f"Unable to display image: {str(e)}")
                            st.markdown(f"[View Image Directly]({image_url})")
                            # Show helpful error message
                            st.info("If the image doesn't display properly, it may be due to temporary Drive permissions. Please try refreshing the page or viewing it directly.")
                    
                    # Green button showing this idea was generated
                    st.markdown(
                        f"""
                        <div style="background-color:#28a745;padding:10px;border-radius:5px;text-align:center;color:white;">
                            Idea {idea['number']} Generated on {gen_date}
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
                            
                elif any_idea_generated:
                    # Red (disabled) button for non-generated ideas, only if another idea already has an image
                    st.markdown(
                        f"""
                        <div style="background-color:#dc3545;padding:10px;border-radius:5px;text-align:center;color:white;">
                            Cannot Generate (Limited to One Image)
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
                else:
                    # Regular button if no image has been generated for this company yet
                    if st.button(f"Generate Image for Idea {idea['number']}", key=button_key):
                        # Store the current idea number in session state for the progress bar
                        st.session_state.generating_idea = idea['number']
                        st.session_state.generation_start_time = datetime.now()
                        
                        # Create a progress bar to indicate the image is being generated
                        progress_placeholder = st.empty()
                        with progress_placeholder.container():
                            st.markdown(f"**Generating image for Idea {idea['number']}...**")
                            progress_bar = st.progress(0)
                            
                            # Use placeholders for status messages to avoid duplicates
                            status_placeholder = st.empty()
                            status_placeholder.markdown("Generating AI image based on description...")
                            
                            # Update progress bar to simulate image generation process (takes about 1 minute)
                            for percent_complete in range(0, 101, 5):
                                # Slow down the progress bar for a more realistic feel of approximately 1 minute total
                                if percent_complete < 25:
                                    time.sleep(0.7)  # First 25% - starting generation
                                elif percent_complete < 70:
                                    time.sleep(0.9)  # Next 45% - main image generation
                                elif percent_complete < 90:
                                    time.sleep(1.1)  # Next 20% - finalizing and uploading
                                else:
                                    time.sleep(1.3)  # Final 10% - finishing up
                                
                                progress_bar.progress(percent_complete)
                                
                                # Update the status message based on progress (using the placeholder)
                                if percent_complete == 25:
                                    status_placeholder.markdown("Processing description and creating image concept...")
                                elif percent_complete == 50:
                                    status_placeholder.markdown("Optimizing image details and quality...")
                                elif percent_complete == 75:
                                    status_placeholder.markdown("Preparing image for upload to database...")
                                elif percent_complete == 90:
                                    status_placeholder.markdown("Almost done - finalizing and saving...")
                        
                        # After the progress bar completes, call the generate_image function
                        success = generate_image(idea['number'], idea.get('description', ''))
                        if success:
                            st.session_state.generated_idea = idea['number']
                            # Clear the progress placeholder
                            progress_placeholder.empty()
                            # Force a rerun to update the UI
                            st.rerun()
            
            # Store all valid ideas for PDF/email
            ideas = valid_ideas
        else:
            st.warning("No AI image ideas found. Please check the data format.")
    else:
        # If no AI suggestions are available, show default content
        st.warning("No AI image suggestions found for this company.")
    
    # Download Ideas as PDF button
    if 'Open AI Image Suggestions' in company_data and company_data['Open AI Image Suggestions']:
        # Parse the AI suggestions again if needed
        if 'valid_ideas' not in locals() or not valid_ideas:
            valid_ideas = []
            ai_suggestions = company_data['Open AI Image Suggestions']
            idea_blocks = ai_suggestions.split("IDEA")
            
            # Process each idea block again
            for i, block in enumerate(idea_blocks):
                if not block.strip():
                    continue
                    
                # Try to extract idea number from the first line
                first_line = block.strip().split('\n')[0]
                if first_line and first_line[0].isdigit():
                    idea_number = first_line[0]
                    
                    # We only want IDEAS 1, 2, 3 (skip IDEA 0 or any others)
                    if idea_number in ['1', '2', '3']:
                        # Extract title, description, and purpose
                        title = ""
                        description = ""
                        purpose = ""
                        
                        if "Title:" in block:
                            title_parts = block.split("Title:", 1)[1].split("Description:", 1)
                            if len(title_parts) > 0:
                                title = title_parts[0].strip()
                        
                        if "Description:" in block:
                            desc_parts = block.split("Description:", 1)[1].split("Purpose:", 1)
                            if len(desc_parts) > 0:
                                description = desc_parts[0].strip()
                        
                        if "Purpose:" in block:
                            purpose = block.split("Purpose:", 1)[1].strip()
                        
                        # Create the idea object
                        idea = {
                            "number": idea_number,
                            "title": title,
                            "description": description,
                            "purpose": purpose
                        }
                        
                        valid_ideas.append(idea)
        
        # Create descriptions from the AI suggestions
        idea_descriptions = []
        for idea in valid_ideas:
            idea_descriptions.append(f"IDEA {idea['number']}: {idea.get('title', '')}\n\n{idea.get('description', '')}\n\nPurpose: {idea.get('purpose', '')}")
        
        # Get any generated images
        images = []
        company_name = company_data.get('Company Name', 'Unknown')
        if company_name in st.session_state.generated_images and st.session_state.generated_images[company_name].get('image_url'):
            images.append(st.session_state.generated_images[company_name].get('image_url'))
        
        # Get header image URL if available
        header_image_url = None
        if 'Header Image' in company_data and company_data['Header Image']:
            header_image_url = company_data.get('Header Image', [{'url': ''}])[0].get('url', '')
        
        # Generate PDF with AI suggestions
        pdf_buffer = generate_pdf(
            company_name=company_data.get('Company Name', 'Unknown'),
            images=images,  # Include generated images if available
            descriptions=idea_descriptions,
            header_image_url=header_image_url
        )
        
        # Convert to bytes for download button
        pdf_bytes = pdf_buffer.getvalue()
        
        # Provide download button
        company_name_clean = company_data.get('Company Name', 'Company').replace(' ', '_')
        st.download_button(
            "Download Ideas as PDF",
            data=pdf_bytes,
            file_name=f"AI_Image_Ideas_{company_name_clean}.pdf",
            mime="application/pdf"
        )
    else:
        st.error("No AI image ideas to download.")
    
    # Add Behind the Scenes Video section with anchor
    st.markdown("<div id='video-section'></div>", unsafe_allow_html=True)
    st.subheader("Behind the Scenes Video")
    st.write("Watch how we create AI image ideas for your business:")
    st.video("https://youtu.be/H4Z15bi0jT4?si=YzVKbw9-ixzPX1fd")
    
    # Add Ideas Flipbook section with anchor
    st.markdown("<div id='flipbook-section'></div>", unsafe_allow_html=True)
    st.subheader("Ideas Flipbook")
    st.write("Flip through our collection of AI image ideas:")
    st.markdown(
        """
        <iframe allowfullscreen="true" src="https://designrr.page/?id=426641&token=1822161547&type=FP&h=4290" 
        height="600" width="100%" frameborder="0"></iframe>
        """, 
        unsafe_allow_html=True
    )

# Show analytics dashboard if selected - we keep this as a separate page
# The video and flipbook pages are removed since we now use anchors for navigation

# Show analytics dashboard if selected
elif st.session_state.show_analytics:
    st.header("Analytics Dashboard")
    display_analytics()

# Default view if no company is selected
else:
    st.header("Welcome to Chamber of Commerce AI Image Ideas")
    st.write("Please select a company from the dropdown menu to view AI image suggestions.")
    
    # Display a sample of companies
    st.subheader("Featured Companies")
    
    # Create a grid of company cards
    cols = st.columns(3)
    for i, company in enumerate(companies[:6]):  # Show first 6 companies
        company_data = company.get('fields', {})
        with cols[i % 3]:
            st.markdown(f"### {company_data.get('Company Name', 'Unknown Company')}")
            if 'Website' in company_data:
                st.write(f"🌐 [Website]({company_data['Website']})")
            st.write("Select this company from the dropdown to view AI image ideas.")
