# Dashboard Usage

## Local monitoring dashboard

The local dashboard reads:

- PostgreSQL
- Local pipeline logs
- Local OHLC investigation CSV

Run:

```bash
streamlit run dashboard/local_app.py
```

## Online snapshot dashboard

First run the ETL pipeline locally:

```bash
python main.py
```

Then export snapshots:

```bash
python dashboard/export_dashboard_snapshots.py
```

Commit the generated files under:

```text
dashboard/snapshots/
```

Run locally for testing:

```bash
streamlit run dashboard/online_app.py
```

For Streamlit Cloud, set the app entry point to:

```text
dashboard/online_app.py
```

The online version does not require database credentials.
