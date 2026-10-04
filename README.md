# HardGo - Multi-Role Electrical & Electronics Delivery App

## What this version contains
- One HardGo app with role-based login.
- Customer: browse, search, cart, checkout, order tracking.
- Shop Owner: own shop inventory, stock/price updates, incoming orders, order status, AI demand view.
- Delivery Partner: assigned/available deliveries and delivery status.
- Admin: platform statistics and recent orders.
- Customers do not get the staff role-switcher or staff dashboard links.
- Backend APIs enforce roles, so manually opening `/admin`, `/owner`, or staff APIs is blocked.
- Product-specific local SVG images are included, so product names and images stay matched without depending on external image URLs.
- Google Maps integration is supported through `GOOGLE_MAPS_API_KEY`; Leaflet is retained as a fallback when no Google key is configured.

## Recommended Python
Use Python 3.10 or 3.11 for the easiest OpenCV/scikit-learn setup.

## Windows CMD setup
Open CMD inside the `hardgo` folder.

```bat
py -3.10 -m venv venv
venv\\Scripts\\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python seed.py
python app.py
```

Then open:

`http://127.0.0.1:5000/login`

## Demo logins
- Customer: `customer@hardgo.com` / `pass123`
- Shop Owner: `srisai@hardgo.com` / `pass123`
- Delivery Partner: `raju@hardgo.com` / `pass123`
- Admin: `admin@hardgo.com` / `admin123`

After login, HardGo automatically sends the user to the correct module.

## Google Maps
Copy `.env.example` to `.env` and set your API key as `GOOGLE_MAPS_API_KEY`. For local testing, the app still works with the fallback map if no Google key is configured.
See `GOOGLE_MAPS_SETUP.md`.

## Reset demo data
If you change inventory/orders and want the original demo data again:

```bat
python seed.py
```

This clears and recreates the demo database.

## Important
The included demo passwords are plain-text demo credentials for local development only. For production, use password hashing, HTTPS, CSRF protection, secure cookies, and proper secret management.


## HardGo order flow

1. Customer adds products to cart and places an order.
2. Shop Owner accepts the order and marks it Preparing / Ready for Pickup.
3. Delivery Partner sees only unassigned Ready/Preparing pickup requests.
4. Delivery Partner explicitly clicks Accept Delivery. The order is atomically assigned to that partner.
5. Partner updates Picked Up -> On the Way -> Delivered.
6. After delivery, the partner becomes available again.

## Fresh demo database

Run `python seed.py` to reset the demo database and restore all demo accounts, products, inventory and sample sales history. This clears existing demo orders.

## Product images

The demo catalog uses real-world product photographs from Wikimedia Commons, mapped by product type. See `IMAGE_CREDITS.md`. An internet connection is required for those remote photographs; a local SVG fallback is used if an image cannot load.
