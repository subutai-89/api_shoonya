import pandas as pd
from src.data.data_utils import save_to_csv


def fetch_option_chain_with_market_data(
    api,
    exchange: str,
    tradingsymbol: str,
    strikeprice: int,
    count: int = 10,
    data_dir: str = "data/historical/option_chain"
):
    """Fetch option chain + LTP quotes for each contract."""
    option_chain = api.get_option_chain(
        exchange=exchange,
        tradingsymbol=tradingsymbol,
        strikeprice=strikeprice,
        count=count
    )

    if not option_chain or "values" not in option_chain:
        print("No option chain data returned.")
        return None

    df = pd.DataFrame(option_chain["values"])
    print(f"Fetched {len(df)} contracts for {tradingsymbol}")

    enriched = []
    for _, row in df.iterrows():
        quote = api.get_quotes(exchange=row["exch"], token=row["token"])

        enriched.append({
            "token": row["token"],
            "tsym": row["tsym"],
            "ltp": quote.get("lp") if quote else None,
            "bid": quote.get("bp1") if quote else None,
            "ask": quote.get("sp1") if quote else None,
            "volume": quote.get("v") if quote else None,
            "open_interest": quote.get("oi") if quote else None,
        })

    result_df = pd.DataFrame(enriched)

    filename = f"{tradingsymbol}_option_chain_with_market_data.csv"
    save_to_csv(result_df, filename, data_dir)

    print(f"Saved enriched option chain to {data_dir}/{filename}")
    return result_df
