import pandas as pd
import os
import json
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------
# DataFrame creation
# ---------------------------------------------------------

def to_dataframe(api_response):
    """Convert Shoonya API response (list/dict) to a DataFrame."""
    if isinstance(api_response, list):
        return pd.DataFrame(api_response)
    if isinstance(api_response, dict):
        return pd.DataFrame([api_response])
    return pd.DataFrame()


# ---------------------------------------------------------
# Data validation & cleaning
# ---------------------------------------------------------

def validate_data(df):
    if df.empty:
        logger.warning("DataFrame is empty.")
    else:
        logger.info("DataFrame shape: %s", df.shape)
        logger.info("Missing values:\n%s", df.isnull().sum())


def clean_data(df):
    return df.dropna()


# ---------------------------------------------------------
# Saving utilities
# ---------------------------------------------------------

def save_to_csv(df, filename, data_dir='data'):
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    filepath = os.path.join(data_dir, filename)
    df.to_csv(filepath, index=False)
    logger.info("Saved DataFrame to %s", filepath)
    return filepath


# ---------------------------------------------------------
# Pretty-print JSON
# ---------------------------------------------------------

def print_json(data):
    print(json.dumps(data, indent=4))
