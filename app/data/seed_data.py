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
# Verified against live TCGCSV data 2026-03-10
# sv3pt5 (Paldean Fates), sv6pt5 (Shrouded Fable), sv8pt5 (Prismatic Evolutions)
# were special sets with no traditional booster box retail release.
PRODUCT_MATRIX = {
    "sv1":    [("booster_box", True, 143.64, "Booster Box"),
               ("etb", True, 49.99, "Elite Trainer Box"),
               ("pc_etb", True, 64.99, "Pokemon Center ETB")],
    "sv2":    [("booster_box", True, 143.64, "Booster Box"),
               ("etb", True, 49.99, "Elite Trainer Box"),
               ("pc_etb", True, 64.99, "Pokemon Center ETB")],
    "sv3":    [("booster_box", True, 143.64, "Booster Box"),
               ("etb", True, 49.99, "Elite Trainer Box"),
               ("pc_etb", True, 64.99, "Pokemon Center ETB")],
    "sv4":    [("booster_box", True, 143.64, "Booster Box"),
               ("etb", True, 49.99, "Elite Trainer Box"),
               ("pc_etb", True, 64.99, "Pokemon Center ETB")],
    "sv3pt5": [("booster_box", False, None, None),
               ("etb", True, 49.99, "Elite Trainer Box"),
               ("pc_etb", True, 64.99, "Pokemon Center ETB")],
    "sv5":    [("booster_box", True, 143.64, "Booster Box"),
               ("etb", True, 49.99, "Elite Trainer Box"),
               ("pc_etb", True, 64.99, "Pokemon Center ETB")],
    "sv6":    [("booster_box", True, 143.64, "Booster Box"),
               ("etb", True, 49.99, "Elite Trainer Box"),
               ("pc_etb", True, 64.99, "Pokemon Center ETB")],
    "sv6pt5": [("booster_box", False, None, None),
               ("etb", True, 49.99, "Elite Trainer Box"),
               ("pc_etb", True, 64.99, "Pokemon Center ETB")],
    "sv7":    [("booster_box", True, 143.64, "Booster Box"),
               ("etb", True, 49.99, "Elite Trainer Box"),
               ("pc_etb", True, 64.99, "Pokemon Center ETB")],
    "sv8":    [("booster_box", True, 143.64, "Booster Box"),
               ("etb", True, 49.99, "Elite Trainer Box"),
               ("pc_etb", True, 64.99, "Pokemon Center ETB")],
    "sv8pt5": [("booster_box", False, None, None),
               ("etb", True, 49.99, "Elite Trainer Box"),
               ("pc_etb", True, 64.99, "Pokemon Center ETB")],
}

# Correct TCGCSV group IDs — verified live against tcgcsv.com/tcgplayer/3/groups
TCGCSV_GROUP_IDS = {
    "sv1":    "22873",
    "sv2":    "23120",
    "sv3":    "23228",
    "sv4":    "23286",
    "sv3pt5": "23353",
    "sv5":    "23381",
    "sv6":    "23473",
    "sv6pt5": "23529",
    "sv7":    "23537",
    "sv8":    "23651",
    "sv8pt5": "23821",
}

# Correct TCGCSV product IDs — verified live against tcgcsv.com products endpoints.
# For sets with multiple ETB variants (Koraidon/Miraidon, Iron Valiant/Roaring Moon, etc.)
# we track one representative product; the aggregator matches by product ID.
TCGCSV_PRODUCT_IDS = {
    "sv1":    {"booster_box": "476452", "etb": "478335", "pc_etb": "478756"},
    "sv2":    {"booster_box": "493975", "etb": "493974", "pc_etb": "493973"},
    "sv3":    {"booster_box": "501257", "etb": "501264", "pc_etb": "501266"},
    "sv4":    {"booster_box": "512821", "etb": "512813", "pc_etb": "512801"},
    "sv3pt5": {                         "etb": "528040", "pc_etb": "528039"},
    "sv5":    {"booster_box": "536225", "etb": "532845", "pc_etb": "532853"},
    "sv6":    {"booster_box": "543846", "etb": "543845", "pc_etb": "543844"},
    "sv6pt5": {                         "etb": "552999", "pc_etb": "552998"},
    "sv7":    {"booster_box": "557354", "etb": "557350", "pc_etb": "557340"},
    "sv8":    {"booster_box": "565606", "etb": "565630", "pc_etb": "565632"},
    "sv8pt5": {                         "etb": "593355", "pc_etb": "593324"},
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
