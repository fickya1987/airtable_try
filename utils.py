"""
Utility functions
"""

import re
from io import BytesIO
from PIL import Image, UnidentifiedImageError
import tempfile
import streamlit as st
import requests
import pandas as pd

from langchain.agents import create_csv_agent
from langchain.chat_models import ChatOpenAI
from langchain.agents.agent_types import AgentType

from pyairtable import Table

# Constants
airtable_logo_url = "https://www.pelindo.co.id/uploads/config/MdO1jALfvFLVuhy81XVHr8LnxnHBI9riZImH7CCD.png"
models = ["gpt-3.5-turbo", "gpt-4", "gpt-4o", "gpt-4o-mini", "gpt-4-0613", "gpt-3.5-turbo-0613", "gpt-3.5-turbo-16k", "gpt-3.5-turbo-16k-0613"]

def extract_ids_from_base_url(base_url):
    """
    Extract base and table ID or name from the base URL using regular expressions
    """
    pattern = r'https://airtable.com/([\w\d]+)/(.*?)(?:/|$)'
    match = re.match(pattern, base_url)
  
    if match:
        base_id = match.group(1)
        table_id = match.group(2)

        return dict(base_id=base_id, table_id=table_id)
    else:
        raise ValueError("Invalid base URL")

def airtable_to_csv():
    """
    Convert Airtable contents into CSV
    """
    access_token = st.session_state.get("AIRTABLE_PAT")
    if not access_token:
        raise ValueError("Airtable Personal Access Token is not set.")

    # Extract the base and table ID from the base URL
    ids_from_url = extract_ids_from_base_url(st.session_state.get("AIRTABLE_URL", ""))
    base_id, table_id = ids_from_url['base_id'], ids_from_url['table_id']

    # Initialize Airtable Python SDK
    table = Table(access_token, base_id, table_id)

    # Get all records from the table
    all_records = table.all()

    # Extract the data from the JSON response and create a pandas DataFrame
    rows = []
    for record in all_records:
        row = record['fields']
        row['id'] = record['id']
        rows.append(row)
    df = pd.DataFrame(rows)

    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        df.to_csv(tmp_file.name, index=False)

    return tmp_file.name

def clear_submit():
    """
    Clears the 'submit' value in the session state.
    """
    st.session_state["submit"] = False

def run_agent(file_name, query):
    """
    Runs the agent on the given file with the specified query.
    """
    openai_key = st.session_state.get("OPENAI_API_KEY")
    if not openai_key:
        raise ValueError("OpenAI API Key is not set.")

    openai_model_chosen = st.session_state.get("OPENAI_MODEL_CHOSEN", models[0])
    agent = create_csv_agent(
        ChatOpenAI(openai_api_key=openai_key, model=openai_model_chosen, temperature=0),
        file_name,
        verbose=True,
        agent_type=AgentType.OPENAI_FUNCTIONS,
        agent_executor_kwargs={"handle_parsing_errors": True}
    )
    return agent.run(query).__str__()

def validate_api_key(api_key_input):
    """
    Validates the provided API key.
    """
    api_key_regex = r"^sk-"
    return re.match(api_key_regex, api_key_input) is not None

def validate_pat(airtable_pat_input):
    """
    Validates the provided Airtable personal access token (PAT).
    """
    airtable_pat_regex = r"^pat"
    return re.match(airtable_pat_regex, airtable_pat_input) is not None

def validate_base_url(airtable_base_url_input):
    """
    Validates the provided Airtable base URL.
    """
    airtable_base_url_regex = r"^https:\/\/airtable.com\/app[^\/]+\/tbl[^\/]+"
    return re.match(airtable_base_url_regex, airtable_base_url_input) is not None

def set_logo_and_page_config():
    """
    Sets the Airtable logo image and page config.
    """
    try:
        response = requests.get(airtable_logo_url, timeout=10)
        response.raise_for_status()  # Ensure the request was successful
        im = Image.open(BytesIO(response.content))
        st.set_page_config(page_title="Airtable-QnA", page_icon=im, layout="wide")
    except (requests.RequestException, UnidentifiedImageError) as e:
        st.set_page_config(page_title="Airtable-QnA", page_icon="📝", layout="wide")
        st.error(f"Failed to load logo image: {e}")

    st.image(airtable_logo_url, width=400)
    st.header("TKMP Pelindo AI Tabular Data Analytics")

def populate_markdown():
    """
    Populates markdown for sidebar.
    """
    st.markdown("## Configuration")
    st.write("\n")
    st.session_state["OPENAI_MODEL_CHOSEN"] = st.selectbox(
        'OpenAI Model', models, key='model', help="Learn more at [OpenAI Documentation](https://platform.openai.com/docs/models/)"
    )
    api_key_input = st.text_input(
        "OpenAI API Key",
        type="password",
        placeholder="sk-...",
        help="You can get your API key from [OpenAI Platform](https://platform.openai.com/account/api-keys)", 
        value=st.session_state.get("OPENAI_API_KEY", "")
    )
    airtable_pat_input = st.text_input(
        "Airtable Personal Access Token",
        type="password",
        placeholder="pat...",
        help="You can get your Airtable PAT from [Airtable](https://airtable.com/developers/web/guides/personal-access-tokens#creating-a-token)",
        value=st.session_state.get("AIRTABLE_PAT", "")
    )
    airtable_base_url_input = st.text_input(
        "Airtable Base URL",
        type="default",
        placeholder="https://airtable.com/app.../tbl...",
        help="You can get your Airtable Base URL by simply copy pasting the URL",
        value=st.session_state.get("AIRTABLE_URL", "")
    )
    return api_key_input, airtable_pat_input, airtable_base_url_input
