# Définition des modules produits gérés par l'outil Excel -> XML e-Pack Manager.
# Ordre des colonnes = ordre des balises dans les exports du pack.
# kind : text | int | num | bool | id | ts
MODULES = {
    "Service": {
        "element": "DefProductService",
        "columns": [("Id","id"),("TS","ts"),("Name","text"),("Category","text"),
                    ("TempMin","num"),("TempMax","num"),("Delete","bool")],
        "required": ["Name","TempMin","TempMax"],
        "output": "ProductsService.xml",
    },
    "Production": {
        "element": "DefProductProduction",
        "columns": [("Id","id"),("TS","ts"),("Name","text"),("Category","text"),
                    ("DateLimit","int"),("Delete","bool")],
        "required": ["Name","DateLimit"],
        "output": "ProductsProduction.xml",
    },
    "Stickers": {
        "element": "DefProductStickerV3",
        "columns": [("Id","id"),("TS","ts"),("Name","text"),("Category","text"),
                    ("DateLimit","int"),("Fridge","text"),("Printer","text"),
                    ("MustIndicateOrigin","bool"),("Photo","text"),("Delete","bool")],
        "required": ["Name","DateLimit"],
        "output": "ProductsStickers.xml",
        "needs_params": True,
    },
    "Freezing": {
        "element": "DefProductFreezing",
        "columns": [("Id","id"),("TS","ts"),("Name","text"),("Category","text"),
                    ("Printer","text"),("Dlc","int"),("Ddm","int"),("Du","int"),("Delete","bool")],
        "required": ["Name","Dlc","Ddm","Du"],
        "output": "ProductsFreezing.xml", "omit_if_empty": ("Printer",),
    },
    "Frozen": {
        "element": "DefProductFrozen",
        "columns": [("Id","id"),("TS","ts"),("Name","text"),("Category","text"),
                    ("DateLimit","int"),("Printer","text"),("Delete","bool")],
        "required": ["Name","DateLimit"],
        "output": "ProductsFrozen.xml", "omit_if_empty": ("Printer",),
    },
    "StockIn": {
        "element": "DefStockInV3",
        "columns": [("Id","id"),("TS","ts"),("Name","text"),("Category","text"),
                    ("TempMin","num"),("TempMax","num"),("TempLimit","num"),
                    ("CheckList_Name","text"),("CheckList_AllMandatoryToValid","bool"),
                    ("OrderId","text"),("CategoryId","text"),("SupplierId","text"),
                    ("ProductReference","text"),("Quantity","text"),("DLCTheorique","text"),
                    ("Delete","bool"),("NumLot","text")],
        "required": ["Name","TempMin","TempMax"],
        "output": "ProductsStockIn.xml",
        "omit_if_empty": ("OrderId","CategoryId","SupplierId","ProductReference","Quantity","DLCTheorique","NumLot"),
    },
}
