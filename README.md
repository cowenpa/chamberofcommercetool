# Chamber of Commerce AI Image Ideas

A Streamlit web application that leverages Airtable integration to showcase Chamber of Commerce company profiles with advanced image generation and document management capabilities.

## Features

- Company profile display with contact information
- AI-powered image generation suggestions
- PDF export of AI image ideas
- Behind the scenes video integration
- Interactive image ideas flipbook
- Analytics dashboard for tracking company views

## Deployment to Streamlit Cloud

This application can be deployed directly to Streamlit Cloud from GitHub. Here's how:

1. Push this code to your GitHub repository
2. Visit [Streamlit Cloud](https://streamlit.io/cloud)
3. Click "New app" and select your repository
4. Set the main file path to `app.py`
5. Add the following secrets in the Streamlit Cloud dashboard:
   - `AIRTABLE_PAT`: Your Airtable Personal Access Token
6. For the requirements file, you'll need to rename `streamlit-requirements.txt` to `requirements.txt` before uploading to GitHub

## Local Development

To run this application locally:

1. Create a `.env` file with the following content:
   ```
   AIRTABLE_PAT=your_airtable_pat_here
   ```
2. Install the required packages:
   ```
   pip install -r streamlit-requirements.txt
   ```
3. Run the Streamlit app:
   ```
   streamlit run app.py
   ```

## Repository Structure

- `app.py`: Main application file
- `utils/`: Utility modules
  - `airtable_client.py`: Airtable API integration
  - `analytics.py`: View tracking and analytics
  - `pdf_generator.py`: PDF generation utilities
  - `email_sender.py`: Email functionality
- `.streamlit/`: Streamlit configuration
- `streamlit-requirements.txt`: Python package dependencies
- `packages.txt`: System dependencies (empty for this project)