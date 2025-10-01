import argparse
import queue
import pandas as pd
from dk_api_logic import scrape_and_parse_draftkings, apply_smart_formatting

def main():
    parser = argparse.ArgumentParser(description="Scrape DraftKings API from the command line.")
    parser.add_argument("input_file", help="Path to the input file (CSV or TXT).")
    parser.add_argument("output_file", help="Path to the output file (CSV or Excel).")
    args = parser.parse_args()

    try:
        with open(args.input_file, 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: Input file not found at {args.input_ax}")
        return

    all_results = []
    log_queue = queue.Queue()

    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        parts = [part.strip() for part in line.split(',')]
        if len(parts) < 2:
            print(f"Skipping invalid line: {line}")
            continue

        league_id, category_id = parts[0], parts[1]
        subcategory_id = parts[2] if len(parts) > 2 else ""

        print(f"\nProcessing: League={league_id}, Category={category_id}, Sub-Category={subcategory_id or 'None'}")

        raw_df, market_type, _ = scrape_and_parse_draftkings(
            log_queue, league_id, category_id, subcategory_id
        )

        if not raw_df.empty:
            formatted_df = apply_smart_formatting(raw_df, market_type)
            if not formatted_df.empty:
                all_results.append(formatted_df)
                print(f"  Successfully processed and found {len(formatted_df)} rows.")
            else:
                print("  No results after formatting.")
        else:
            print("  No data returned from API.")

    if not all_results:
        print("\nNo data was scraped. The output file will not be created.")
        return

    final_df = pd.concat(all_results, ignore_index=True)

    try:
        if args.output_file.endswith('.xlsx'):
            final_df.to_excel(args.output_file, index=False)
        else:
            final_df.to_csv(args.output_file, index=False)
        print(f"\nSuccessfully saved {len(final_df)} total rows to {args.output_file}")
    except Exception as e:
        print(f"\nError saving file: {e}")

if __name__ == "__main__":
    main()
