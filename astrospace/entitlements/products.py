"""What each store product grants, and the prices the paywall shows.

Store product ids are the only place commerce meets capability: a purchase
resolves to either a plan (tier for a period) or a number of Ask question
credits, and nothing downstream reads a product id again.

Prices here are the D2 launch prices in rupees, shown before the store has
answered. The store's own localised price always replaces them on the phone
(`ui/src/app/core/purchase.service.ts`), because the store is what charges.
"""
from dataclasses import dataclass
from typing import Literal

ProductKind = Literal["plan", "question_pack"]


@dataclass(frozen=True)
class Product:
    id: str
    kind: ProductKind
    title: str
    price_inr: int
    tier: str | None = None
    months: int | None = None
    questions: int | None = None


PRODUCTS: dict[str, Product] = {
    product.id: product
    for product in (
        Product("astrospace_plus_monthly", "plan", "Plus, monthly", 299, tier="plus", months=1),
        Product("astrospace_plus_yearly", "plan", "Plus, yearly", 1999, tier="plus", months=12),
        Product("astrospace_questions_3", "question_pack", "3 questions", 99, questions=3),
        Product("astrospace_questions_15", "question_pack", "15 questions", 399, questions=15),
    )
}


def public_products() -> list[dict]:
    return [
        {
            "id": product.id,
            "kind": product.kind,
            "title": product.title,
            "price_inr": product.price_inr,
            "tier": product.tier,
            "months": product.months,
            "questions": product.questions,
        }
        for product in PRODUCTS.values()
    ]
