"""
KCapTrack — Database Seeder.

Reads ``data/food_seed.json`` and inserts rows into the ``food_items``
table.  Skips items that already exist (matched on ``yolo_class_name``).

Usage:
    python -m app.db.seed
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import FoodItem
from app.db.session import Base

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

settings = get_settings()


def seed_food_items(session: Session, data_path: Path) -> int:
    """Insert seed food items that don't already exist.

    Args:
        session: A synchronous SQLAlchemy session.
        data_path: Path to the JSON seed file.

    Returns:
        Number of newly inserted rows.
    """
    with open(data_path, "r", encoding="utf-8") as f:
        items: list[dict] = json.load(f)

    inserted = 0
    for item in items:
        exists = session.execute(
            select(FoodItem).where(FoodItem.yolo_class_name == item["yolo_class_name"])
        ).scalar_one_or_none()

        if exists:
            logger.debug("Skipping existing: %s", item["name"])
            continue

        session.add(FoodItem(**item, source="seed_data"))
        inserted += 1

    session.commit()
    return inserted


async def seed_food_items_async(session, data_path: Path) -> int:
    """Insert seed food items that don't already exist using AsyncSession."""
    with open(data_path, "r", encoding="utf-8") as f:
        items: list[dict] = json.load(f)

    inserted = 0
    for item in items:
        res = await session.execute(
            select(FoodItem).where(FoodItem.yolo_class_name == item["yolo_class_name"])
        )
        if res.scalar_one_or_none():
            continue

        session.add(FoodItem(**item, source="seed_data"))
        inserted += 1

    if inserted > 0:
        await session.commit()
    return inserted


def main() -> None:
    """CLI entry-point: create tables and seed food data."""
    engine = create_engine(settings.DATABASE_URL_SYNC, echo=False)

    logger.info("Creating tables …")
    Base.metadata.create_all(bind=engine)

    data_path = settings.BASE_DIR / "data" / "food_seed.json"
    if not data_path.exists():
        logger.error("Seed file not found: %s", data_path)
        sys.exit(1)

    with Session(engine) as session:
        count = seed_food_items(session, data_path)

    logger.info("Seeding complete — %d new food items inserted.", count)


if __name__ == "__main__":
    main()
