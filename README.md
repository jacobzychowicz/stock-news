# Stock-News (GDELT)

CLI tool that pulls recent news about a stock/company from the GDELT 2.1 Doc API, filters to English by default, and lists matching articles. I will be adding an interface, and other tools in the future.

## Quick start (PowerShell)
```powershell
cd Stock-News
python -m venv .venv    # optional
.venv\Scripts\activate  # if you created a venv
python main.py MSFT -k guidance -k investigation -d 5 -l 40
```

More examples:
- `python main.py "NVIDIA" -k "artificial intelligence"`

## Notes
- Uses GDELT; no API key required. Be polite with request volume.
- English-only filter is applied via `sourcelang:english`; use `--allow-non-english` to disable.
- `-d/--days` defaults to 3; set `0` to search all available history.
- `-l/--limit` capped at 250 (GDELT max for this endpoint).
- Keywords must be at least 3 characters (GDELT restriction).

