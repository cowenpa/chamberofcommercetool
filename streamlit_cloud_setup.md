# Deploying to Streamlit Cloud

This document provides detailed instructions for deploying this application to Streamlit Cloud.

## Prerequisites

1. A GitHub account
2. A Streamlit Cloud account (sign up at https://streamlit.io/cloud)
3. Your Airtable Personal Access Token (PAT)

## Deployment Steps

1. **Push to GitHub**
   - Create a new repository on GitHub
   - Push this codebase to your GitHub repository
   - Make sure to include all the files, including:
     - app.py
     - utils/ directory
     - .streamlit/ directory
     - streamlit-requirements.txt (rename to requirements.txt before uploading)
     - runtime.txt

2. **Connect Streamlit Cloud to GitHub**
   - Visit https://streamlit.io/cloud and sign in
   - Click on "New app"
   - Connect to your GitHub account if not already connected
   - Select the repository where you pushed this code

3. **Configure the App**
   - Main file path: `app.py`
   - Branch: `main` (or your default branch)
   - Python version: Should use 3.9+ (automatically detected from runtime.txt)
   - Packages: Will be installed from requirements.txt (renamed from streamlit-requirements.txt)

4. **Add Secrets**
   - In the Streamlit Cloud dashboard, find your deployed app
   - Click on "Settings" > "Secrets"
   - Add the following secrets:
     ```
     AIRTABLE_PAT = "your_airtable_pat_here"
     ```

5. **Advanced Settings (Optional)**
   - You can customize the app's URL, privacy settings, and more through the app's settings

## Troubleshooting

- If the app fails to deploy, check the logs in Streamlit Cloud
- Ensure all dependencies are correctly listed in requirements.txt
- Verify that your Airtable PAT is correct and properly configured in the secrets

## Updating the App

When you push changes to your GitHub repository, Streamlit Cloud will automatically detect the changes and redeploy your app.

## Local Testing Before Deployment

To test locally before deployment:

```bash
# Install dependencies
pip install -r streamlit-requirements.txt

# Set environment variables
export AIRTABLE_PAT="your_airtable_pat_here"

# Run the app
streamlit run app.py
```