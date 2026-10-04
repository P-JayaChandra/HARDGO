import unittest
from database import init_db, get_db_connection
from seed import seed_database
from models import (
    search_nearby_products, get_product_details_across_shops,
    place_order, update_order_status, get_order_details,
    calculate_haversine_distance, calculate_estimated_delivery_time
)
from ai_engine import analyze_image_and_find_product, get_ai_recommendations, predict_shop_demand

class TestHardGoBackend(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        seed_database()

    def test_haversine_distance(self):
        # Benz Circle to M.G. Road Executive Club (~0.8km)
        dist = calculate_haversine_distance(16.5062, 80.6480, 16.5020, 80.6430)
        self.assertGreater(dist, 0.4)
        self.assertLess(dist, 1.2)

    def test_delivery_time_estimation(self):
        min_t, max_t, est_t = calculate_estimated_delivery_time(0.8, shop_prep_time_mins=8)
        self.assertLessEqual(min_t, 10)
        self.assertGreaterEqual(max_t, 12)

    def test_search_nearby_led_bulb_scenario(self):
        """
        Demo scenario verification:
        Customer searches '12W LED Bulb' from Benz Circle.
        Must return Sri Sai Electricals (0.8km away, stock 12, price 120) and Lakshmi Electricals (1.5km away, stock 5, price 115)
        ordered by distance and availability!
        """
        results = search_nearby_products(query="12W LED Bulb", customer_lat=16.5062, customer_lng=80.6480)
        self.assertGreaterEqual(len(results), 2)

        first_hit = results[0]
        self.assertEqual(first_hit['shop_name'], 'Sri Sai Electricals')
        self.assertEqual(first_hit['stock'], 12)
        self.assertEqual(first_hit['price'], 120.0)
        self.assertLess(first_hit['distance_km'], 1.0)

        second_hit = results[1]
        self.assertEqual(second_hit['shop_name'], 'Lakshmi Electricals & Hardware')
        self.assertEqual(second_hit['stock'], 5)
        self.assertEqual(second_hit['price'], 115.0)

    def test_order_stock_decrement_and_refund_lifecycle(self):
        """
        Tests order placement stock reduction (12 -> 10) and stock refund upon order rejection (10 -> 12).
        """
        conn = get_db_connection()
        user = conn.execute("SELECT id FROM users WHERE email = 'customer@hardgo.com'").fetchone()
        customer_id = user['id']
        conn.close()

        # Place order for 2 units of 12W LED Bulb at Sri Sai Electricals (Shop 1, Product 1)
        items = [{'product_id': 1, 'quantity': 2}]
        order_id, order_number = place_order(
            customer_id=customer_id,
            shop_id=1,
            items=items,
            delivery_address="Benz Circle Vijayawada",
            customer_lat=16.5062,
            customer_lng=80.6480,
            payment_method="COD"
        )

        self.assertIsNotNone(order_id)
        self.assertTrue(order_number.startswith("HG-"))

        # Check stock reduced from 12 to 10
        conn = get_db_connection()
        sp = conn.execute("SELECT stock FROM shop_products WHERE shop_id = 1 AND product_id = 1").fetchone()
        self.assertEqual(sp['stock'], 10)
        conn.close()

        # Test Shop Owner Rejection -> Stock should be refunded back to 12!
        update_order_status(order_id, 'Rejected', rejection_reason='Out of stock for bulk delivery')

        conn = get_db_connection()
        sp_refunded = conn.execute("SELECT stock FROM shop_products WHERE shop_id = 1 AND product_id = 1").fetchone()
        self.assertEqual(sp_refunded['stock'], 12)
        conn.close()

    def test_ai_features(self):
        # 1. Visual Search
        v_res = analyze_image_and_find_product(filename='led_bulb')
        self.assertEqual(v_res['matched_signature'], 'led_bulb')
        self.assertGreater(len(v_res['nearby_in_stock_products']), 0)

        # 2. Recommendations
        recs = get_ai_recommendations(current_product_id=1)
        self.assertGreaterEqual(len(recs), 1)

        # 3. Demand Prediction
        preds = predict_shop_demand(shop_id=1)
        self.assertGreater(len(preds), 0)
        self.assertIn('predicted_7day_demand', preds[0])

if __name__ == '__main__':
    unittest.main()
