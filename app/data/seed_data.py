"""Static reference data for Scarlet & Violet sets and products."""
from datetime import date
from sqlalchemy import select
from app.data.database import get_engine, sets_table, products_table

# --- Set definitions ---
SV_SETS = [
    {"code": "sv1",    "name": "Scarlet & Violet Base",  "release_date": date(2023, 3, 31)},
    {"code": "sv2",    "name": "Paldea Evolved",          "release_date": date(2023, 6, 9)},
    {"code": "sv3",    "name": "Obsidian Flames",         "release_date": date(2023, 8, 11)},
    {"code": "sv4",    "name": "Paradox Rift",            "release_date": date(2023, 11, 3)},
    {"code": "sv3pt5", "name": "Paldean Fates",           "release_date": date(2024, 1, 26)},
    {"code": "sv5",    "name": "Temporal Forces",         "release_date": date(2024, 3, 22)},
    {"code": "sv6",    "name": "Twilight Masquerade",     "release_date": date(2024, 5, 24)},
    {"code": "sv6pt5", "name": "Shrouded Fable",          "release_date": date(2024, 8, 2)},
    {"code": "sv7",    "name": "Stellar Crown",           "release_date": date(2024, 9, 13)},
    {"code": "sv8",    "name": "Surging Sparks",          "release_date": date(2024, 11, 8)},
    {"code": "sv8pt5", "name": "Prismatic Evolutions",    "release_date": date(2025, 1, 17)},
]

# Products per set: (product_type, has_product, msrp, name_suffix)
# msrp values: BB ~$144, ETB ~$50, PC ETB ~$65
PRODUCT_MATRIX = {
    "sv1":    [("booster_box", True, 143.64, "Booster Box"),
               ("etb", True, 49.99, "Elite Trainer Box"),
               ("pc_etb", True, 64.99, "Pokemon Center ETB")],
    "sv2":    [("booster_box", True, 143.64, "Booster Box"),
               ("etb", True, 49.99, "Elite Trainer Box"),
               ("pc_etb", False, None, None)],
    "sv3":    [("booster_box", True, 143.64, "Booster Box"),
               ("etb", True, 49.99, "Elite Trainer Box"),
               ("pc_etb", False, None, None)],
    "sv4":    [("booster_box", True, 143.64, "Booster Box"),
               ("etb", True, 49.99, "Elite Trainer Box"),
               ("pc_etb", True, 64.99, "Pokemon Center ETB")],
    "sv3pt5": [("booster_box", True, 143.64, "Booster Box"),
               ("etb", True, 49.99, "Elite Trainer Box"),
               ("pc_etb", True, 64.99, "Pokemon Center ETB")],
    "sv5":    [("booster_box", True, 143.64, "Booster Box"),
               ("etb", True, 49.99, "Elite Trainer Box"),
               ("pc_etb", False, None, None)],
    "sv6":    [("booster_box", True, 143.64, "Booster Box"),
               ("etb", True, 49.99, "Elite Trainer Box"),
               ("pc_etb", True, 64.99, "Pokemon Center ETB")],
    "sv6pt5": [("booster_box", True, 143.64, "Booster Box"),
               ("etb", True, 49.99, "Elite Trainer Box"),
               ("pc_etb", True, 64.99, "Pokemon Center ETB")],
    "sv7":    [("booster_box", True, 143.64, "Booster Box"),
               ("etb", True, 49.99, "Elite Trainer Box"),
               ("pc_etb", False, None, None)],
    "sv8":    [("booster_box", True, 143.64, "Booster Box"),
               ("etb", True, 49.99, "Elite Trainer Box"),
               ("pc_etb", True, 64.99, "Pokemon Center ETB")],
    "sv8pt5": [("booster_box", True, 143.64, "Booster Box"),
               ("etb", True, 49.99, "Elite Trainer Box"),
               ("pc_etb", True, 64.99, "Pokemon Center ETB")],
}

# TCGCSV group IDs for each set (TCGPlayer group IDs for sealed products)
# These are the actual TCGPlayer group IDs from TCGCSV
TCGCSV_GROUP_IDS = {
    "sv1":    "23057",
    "sv2":    "23223",
    "sv3":    "23475",
    "sv4":    "23737",
    "sv3pt5": "23868",
    "sv5":    "23977",
    "sv6":    "24077",
    "sv6pt5": "24273",
    "sv7":    "24396",
    "sv8":    "24501",
    "sv8pt5": "24583",
}

# Known TCGPlayer product IDs for specific sealed products
# Format: {set_code: {product_type: product_id}}
TCGCSV_PRODUCT_IDS = {
    "sv1":    {"booster_box": "513416", "etb": "513418", "pc_etb": "513421"},
    "sv2":    {"booster_box": "524397", "etb": "524399"},
    "sv3":    {"booster_box": "530720", "etb": "530722"},
    "sv4":    {"booster_box": "538637", "etb": "538639", "pc_etb": "538642"},
    "sv3pt5": {"booster_box": "541901", "etb": "541903", "pc_etb": "541906"},
    "sv5":    {"booster_box": "544771", "etb": "544773"},
    "sv6":    {"booster_box": "548271", "etb": "548273", "pc_etb": "548276"},
    "sv6pt5": {"booster_box": "553041", "etb": "553043", "pc_etb": "553046"},
    "sv7":    {"booster_box": "556521", "etb": "556523"},
    "sv8":    {"booster_box": "559961", "etb": "559963", "pc_etb": "559966"},
    "sv8pt5": {"booster_box": "562081", "etb": "562083", "pc_etb": "562086"},
}


def upsert_all():
    """Insert or update all seed sets and products."""
    engine = get_engine()
    with engine.begin() as conn:
        # Upsert sets
        for s in SV_SETS:
            existing = conn.execute(
                select(sets_table.c.id).where(sets_table.c.code == s["code"])
            ).fetchone()
            if existing:
                conn.execute(
                    sets_table.update()
                    .where(sets_table.c.code == s["code"])
                    .values(name=s["name"], release_date=s["release_date"],
                            series="Scarlet & Violet")
                )
            else:
                conn.execute(sets_table.insert().values(
                    code=s["code"], name=s["name"],
                    release_date=s["release_date"], series="Scarlet & Violet"
                ))

        # Get set id map
        rows = conn.execute(select(sets_table.c.id, sets_table.c.code)).fetchall()
        set_id_map = {row.code: row.id for row in rows}

        # Upsert products
        for set_code, products in PRODUCT_MATRIX.items():
            set_id = set_id_map.get(set_code)
            if not set_id:
                continue
            set_name = next(s["name"] for s in SV_SETS if s["code"] == set_code)
            group_id = TCGCSV_GROUP_IDS.get(set_code)
            product_ids = TCGCSV_PRODUCT_IDS.get(set_code, {})

            for product_type, has_product, msrp, name_suffix in products:
                if not has_product:
                    continue
                name = f"{set_name} {name_suffix}"
                tcgcsv_product_id = product_ids.get(product_type)

                existing = conn.execute(
                    select(products_table.c.id).where(
                        (products_table.c.set_id == set_id) &
                        (products_table.c.product_type == product_type)
                    )
                ).fetchone()

                if existing:
                    conn.execute(
                        products_table.update()
                        .where(products_table.c.id == existing.id)
                        .values(name=name, tcgcsv_group_id=group_id,
                                tcgcsv_product_id=tcgcsv_product_id, msrp=msrp)
                    )
                else:
                    conn.execute(products_table.insert().values(
                        set_id=set_id, product_type=product_type, name=name,
                        tcgcsv_group_id=group_id,
                        tcgcsv_product_id=tcgcsv_product_id, msrp=msrp
                    ))
