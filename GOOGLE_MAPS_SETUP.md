# HardGo Google Maps setup

HardGo is prepared to use a real Google Maps API key through the environment variable `GOOGLE_MAPS_API_KEY`.

1. Create a Google Cloud project.
2. Enable **Maps JavaScript API** (and Places API if you add address autocomplete).
3. Create an API key.
4. Restrict the key to your local/deployed web origins.
5. Copy `.env.example` to `.env` and set `GOOGLE_MAPS_API_KEY`.

The app currently has a Leaflet/OpenStreetMap fallback map so it still runs without a Google key. The Google key should never be committed to GitHub.
