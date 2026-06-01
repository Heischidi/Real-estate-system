"""Manual scraper runner script — fetches real live property listings from target Nigerian websites.

Usage:
    python run_scraper.py
"""

from __future__ import annotations

import asyncio
import io
import sys
from app.tasks.scrape import _async_scrape_all

# Set encoding to prevent crashes with terminal emojis on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


async def main() -> None:
    print("🚀 Starting RealtorPal property scrapers to fetch real live listings...")
    print("This will run Playwright under the hood to scrape the websites.")
    print("Please wait...")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    try:
        results = await _async_scrape_all()

        print("\n✅ Scraping Cycle Completed!")
        print(f"⏱️  Duration: {results['duration_seconds']:.2f} seconds")
        print(f"🔍 Total Found: {results['total_found']}")
        print(f"✨ Total New: {results['total_new']}")
        print("\n📊 Breakdown per scraper:")
        for scraper_name, stats in results.get("per_scraper", {}).items():
            if "error" in stats:
                print(f" ❌ {scraper_name}: Error - {stats['error']}")
            else:
                print(f"  • {scraper_name}: Found {stats['found']}, New {stats['new']}")
    except KeyboardInterrupt:
        print("\n🛑 Scraping canceled by user.")
    except Exception as e:
        print(f"\n❌ Scraping failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
