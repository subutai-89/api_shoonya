import pandas as pd
import os
import json
import logging


# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def to_dataframe(api_response):
    """
    Convert API response (dict or list) to a pandas DataFrame.
    """
    if isinstance(api_response, list):
        return pd.DataFrame(api_response)
    elif isinstance(api_response, dict):
        return pd.DataFrame([api_response])
    else:
        return pd.DataFrame()


def validate_data(df):
    """
    Validate DataFrame for missing or incorrect data.
    """
    if df.empty:
        logger.warning("DataFrame is empty.")
    else:
        logger.info("DataFrame shape: %s", df.shape)
        logger.info("Missing values:\n%s", df.isnull().sum())


def clean_data(df):
    """
    Clean DataFrame by dropping rows with missing values.
    """
    return df.dropna()


def add_timestamp(df):
    """
    Add a timestamp column to the DataFrame.
    """
    df['timestamp'] = pd.Timestamp.now()
    return df


def save_to_csv(df, filename, data_dir='data'):
    """
    Save DataFrame to a CSV file in the specified directory.
    """
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    filepath = os.path.join(data_dir, filename)
    df.to_csv(filepath, index=False)
    logger.info("Saved DataFrame to %s", filepath)


def print_pretty(response):
    """
    Pretty-print JSON response.
    """
    print(json.dumps(response, indent=4))


def process_and_save_data(data_list, data_dir='data'):
    """
    Process and save multiple DataFrames.
    """
    for df, filename in data_list:
        try:
            validate_data(df)
            df = clean_data(df)
            df = add_timestamp(df)
            save_to_csv(df, filename, data_dir=data_dir)
        except Exception as e:
            logger.error("Error processing %s: %s", filename, str(e))
