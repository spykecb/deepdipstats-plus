# Deepdipstats Plus

This is just a little script for the Deep Dip 2 event.

It will extract the API data of deepdipstats.com and analyze each floor's difficulty among the top players.
The produced output will be in csv format

## Requirements

1. Python (3.9+ preferrably)
2. Twitch API access (optional; only if you want to enable Twitch URL's in the debug log for each fall/completion)

## How to run

Normally:
`python main.py --players BrenTM eLconn21 Hazardu. Larstm Schmaniol`
Replace player names as you wish.

After the execution is completed, you can check the result folder. `result.csv` will show each fall and success one-by-one, and `aggregated.csv` will show the success and fail counts grouped by player and floor

If you want to enable Twitch URLs:

1. Make sure that you have `.env` file created in the root folder (look at `.env.TEMPLATE` file for reference). Insert your Client ID and secret there.
2. Add more player's twitch account in the `tmuser_to_twitchuser.json` file
3. Run `python main.py --enable-twitch-url`
