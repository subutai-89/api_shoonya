'''
/data = download, clean, store, export

✔ OHLCV
✔ option chains
✔ account snapshots
✔ exporting/cleaning/analyzing data
✔ reporting

src/data/
    loaders/          ← functions that fetch (broker_data_fetcher, ohlcv_downloader)
    transforms/       ← cleaning, validation, enrichment
    stores/           ← persistent storage (ticks, orders)
    exports/          ← saving CSV/Parquet

'''