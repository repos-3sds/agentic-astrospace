"""Create the monthly Razorpay plans the website sells, once per key pair.

Razorpay plans can't be edited after creation, so a price change means
running this again and swapping RAZORPAY_PLAN_IDS on Cloud Run. Prices come
from astrospace/entitlements/products.py, the same table the app uses.

    RAZORPAY_KEY_ID=... RAZORPAY_KEY_SECRET=... python3 scripts/razorpay_setup.py
    python3 scripts/razorpay_setup.py --check     # list existing plans, create nothing

Prints the RAZORPAY_PLAN_IDS value to set on the API service. Test keys
(rzp_test_) and live keys have separate plans.
"""
import argparse
import os
import sys

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from astrospace.entitlements.products import PRODUCTS  # noqa: E402

API = "https://api.razorpay.com/v1/plans"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="list plans and create nothing")
    args = parser.parse_args()
    key_id, secret = os.getenv("RAZORPAY_KEY_ID", ""), os.getenv("RAZORPAY_KEY_SECRET", "")
    if not key_id or not secret:
        print("Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET first.", file=sys.stderr)
        return 2
    auth = (key_id, secret)
    existing = requests.get(API, params={"count": 100}, auth=auth, timeout=15)
    existing.raise_for_status()
    by_product = {}
    for plan in existing.json().get("items", []):
        product = PRODUCTS.get((plan.get("notes") or {}).get("product_id") or "")
        # A plan at an old price is left alone; a new one is made at today's price.
        if product and plan["item"]["amount"] == product.price_inr * 100:
            by_product.setdefault(product.id, plan["id"])
    print(f"Mode: {'TEST' if key_id.startswith('rzp_test_') else 'LIVE'}")
    for product in PRODUCTS.values():
        if product.kind != "plan":
            continue
        if product.id in by_product:
            print(f"  {product.id}: exists ({by_product[product.id]}, ₹{product.price_inr})")
            continue
        if args.check:
            print(f"  {product.id}: missing (₹{product.price_inr}/month)")
            continue
        created = requests.post(API, auth=auth, timeout=15, json={
            "period": "monthly", "interval": product.months or 1,
            "item": {"name": f"Siddha {product.title}", "amount": product.price_inr * 100, "currency": "INR"},
            "notes": {"product_id": product.id},
        })
        created.raise_for_status()
        by_product[product.id] = created.json()["id"]
        print(f"  {product.id}: created ({by_product[product.id]}, ₹{product.price_inr})")
    if by_product:
        print("\nRAZORPAY_PLAN_IDS=" + ",".join(f"{k}={v}" for k, v in sorted(by_product.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
