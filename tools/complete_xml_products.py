#!/usr/bin/env python3
"""
Complète les balises manquantes sur un export XML e-Pack Manager, quel que
soit le type d'objet (ProductStickers, ProductsProduction,
ProductsFreezing, CheckLists, Cleanings, ...), à condition que ce type
figure dans le registre PROFILES ci-dessous.

Usage:
    python3 complete_xml_products.py <entrée.xml> <sortie.xml> [options]

Options (selon le profil détecté) :
    --dltype VALEUR          Requis si le profil a has_dltype=True.
    --isddm true|false       Requis si le profil a une balise forcée IsDDM.
    --isddm-exception-category "CATEGORIE"
    --isddm-exception-value true|false
    --reference FICHIER.xml  Fichier de référence d'où lire les valeurs
                              métier listées dans "reference_tags" du profil
                              (appariement par <Id>). Jamais inventées.
    --list-profiles          Affiche les types connus et quitte.
"""
import argparse
import re
import sys

PROFILES = {
    "DefProductStickerV3": {
        "element": "DefProductStickerV3",
        "leading_tag": ("idFileAttente", "0"),
        "required_tags": [
            ("Delete", "false"),
            ("MustIndicateOrigin", "false"),
            ("MustIndicateDLC", "false"),
            ("Photo", None),
            ("IsDLUO", "false"),
            ("Disable", "false"),
        ],
        "forced_tag": "IsDDM",
        "trim_tags": ["Name", "Category"],
        "has_dltype": True,
        "tag_order": None,
        "root_attrs": None,
        "never_invent": ["Id", "TS", "Name", "Category", "DateLimit"],
        "force_eol": None,
    },
    "DefProductProduction": {
        "element": "DefProductProduction",
        "leading_tag": ("idFileAttente", "0"),
        "required_tags": [
            ("Delete", "false"),
            ("Disable", "false"),
        ],
        "forced_tag": None,
        "trim_tags": ["Name", "Category"],
        "has_dltype": False,
        "tag_order": None,
        "root_attrs": None,
        "never_invent": ["Id", "TS", "Name", "Category", "DateLimit"],
        "force_eol": None,
    },
    "DefProductFreezing": {
        "element": "DefProductFreezing",
        "leading_tag": ("idFileAttente", "0"),
        "required_tags": [
            ("Delete", "false"),
            ("Disable", "false"),
        ],
        "forced_tag": None,
        "trim_tags": ["Name", "Category"],
        "has_dltype": False,
        "tag_order": [
            "idFileAttente", "Id", "TS", "Name", "Category",
            "Ddm", "Dlc", "Du", "Delete", "Disable",
        ],
        "root_attrs": (
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            'xmlns:xsd="http://www.w3.org/2001/XMLSchema"'
        ),
        "never_invent": ["Id", "TS", "Name", "Category", "Ddm", "Dlc", "Du"],
        "force_eol": "\r\n",
    },
    "DefCheckList": {
        "element": "DefCheckList",
        "leading_tag": None,
        "required_tags": [
            ("Delete", "false"),
        ],
        "forced_tag": None,
        "trim_tags": ["Name"],
        "has_dltype": False,
        "tag_order": ["Id", "TS", "Name", "Items", "Delete"],
        "root_attrs": (
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            'xmlns:xsd="http://www.w3.org/2001/XMLSchema"'
        ),
        "never_invent": ["Id", "TS", "Name"],
        "force_eol": "\n",
        "children": {
            "container": "Items",
            "element": "DefCheckItem",
            "required_tags": [
                ("Delete", "false"),
                ("IsMandatory", "true"),
                ("IsSelected", "true"),
            ],
            "trim_tags": ["Name"],
            "tag_order": ["Name", "Delete", "IsMandatory", "IsSelected"],
            "never_invent": ["Name"],
        },
        "strip_bom": True,
        "xml_decl_encoding": "UTF-8",
        "final_newline": True,
        "output_name": "CheckLists.xml",
        "label_plural": "checklist(s)",
    },
    # Nettoyages / plans de nettoyage (e-Pack Manager -> Cleanings.xml).
    # Profil établi par comparaison CleaningsConfig.xml (export brut) vs
    # CleaningsOK.xml (fichier de référence validé).
    "DefCleaningV3": {
        "element": "DefCleaningV3",
        "leading_tag": ("idFileAttente", "0"),
        "required_tags": [
            ("ProductCode", None),
            ("IsDeleted", "false"),
            ("Disable", "false"),
            ("Delete", "false"),
        ],
        "forced_tag": None,
        "trim_tags": ["Name", "Category", "CheckList_Name"],
        "has_dltype": False,
        "tag_order": [
            "idFileAttente", "Id", "TS", "Name", "Category", "ProductCode",
            "Recurrence", "CheckList_Name", "CheckList_AllMandatoryToValid",
            "IsDeleted", "Disable", "Delete",
        ],
        "root_attrs": (
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            'xmlns:xsd="http://www.w3.org/2001/XMLSchema"'
        ),
        "never_invent": ["Id", "TS", "Name", "Category", "CheckList_Name"],
        "force_eol": "\r\n",
        "subblocks": [
            {
                "container": "Recurrence",
                "required_tags": [
                    ("NextDate", None),
                    ("IsDisable", "false"),
                ],
                # NextDate est une valeur métier : jamais inventée, lue dans
                # le fichier passé à --reference (appariement par <Id>).
                "reference_tags": ["NextDate"],
                "tag_order": ["Type", "Moments", "Nb", "NextDate", "IsDisable"],
                "never_invent": ["Type", "Nb"],
            },
        ],
        "strip_bom": True,
        "xml_decl_encoding": "utf-8",
        # Le fichier de référence ne se termine PAS par un saut de ligne.
        "final_newline": None,
        "output_name": "Cleanings.xml",
        "label_plural": "nettoyage(s)",
    },
    # Produits d'entrée en stock (e-Pack Manager -> ProductsStockIn).
    # Profil établi par comparaison ProductsStockInPasOK.xml (export brut,
    # avec BOM) vs ProductsStockInOK.xml (fichier de référence validé,
    # sans BOM).
    "DefStockInV3": {
        "element": "DefStockInV3",
        "leading_tag": ("idFileAttente", "0"),
        "required_tags": [
            ("CheckList_Name", None),
            ("Delete", "false"),
            ("Disable", "false"),
            ("ProductReference", None),
        ],
        "forced_tag": None,
        "trim_tags": ["Name", "Category", "CheckList_Name"],
        "has_dltype": False,
        "tag_order": [
            "idFileAttente", "Id", "TS", "Name", "Category",
            "TempMin", "TempMax", "TempLimit", "CheckList_Name",
            "CheckList_AllMandatoryToValid", "Delete", "Disable",
            "ProductReference",
        ],
        "root_attrs": (
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            'xmlns:xsd="http://www.w3.org/2001/XMLSchema"'
        ),
        "never_invent": ["Id", "TS", "Name", "Category"],
        "force_eol": "\r\n",
        "strip_bom": True,
    },
    # Produits congelés (e-Pack Manager -> ProductsFrozen).
    # Profil établi par comparaison ProductsFrozenPasOK.xml (export brut,
    # avec BOM, sans namespaces) vs ProductsFrozenOK.xml (fichier de
    # référence validé). Distinct de DefProductFreezing (Ddm/Dlc/Du) :
    # ici la durée est portée par DateLimit.
    "DefProductFrozen": {
        "element": "DefProductFrozen",
        "leading_tag": ("idFileAttente", "0"),
        "required_tags": [
            ("Delete", "false"),
            ("Disable", "false"),
        ],
        "forced_tag": None,
        "trim_tags": ["Name", "Category"],
        "has_dltype": False,
        "tag_order": [
            "idFileAttente", "Id", "TS", "Name", "Category",
            "DateLimit", "Delete", "Disable",
        ],
        "root_attrs": (
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            'xmlns:xsd="http://www.w3.org/2001/XMLSchema"'
        ),
        "never_invent": ["Id", "TS", "Name", "Category", "DateLimit"],
        "force_eol": "\r\n",
        "strip_bom": True,
        "xml_decl_encoding": "utf-8",
        # Le fichier de référence ne se termine PAS par un saut de ligne.
        "final_newline": None,
        "output_name": "ProductsFrozen.xml",
    },
    # Produits de service (e-Pack Manager -> ProductsService).
    # Profil établi par comparaison ProductsServicePasOK.xml (export brut)
    # vs ProductsServiceOK.xml (référence validée). Consignes utilisateur :
    # Delete/Disable TOUJOURS à false (même si l'export dit autre chose),
    # IsInactif supprimée, pas de tri des produits.
    "DefProductService": {
        "element": "DefProductService",
        "leading_tag": ("idFileAttente", "0"),
        "required_tags": [
            ("Delete", "false"),
            ("Disable", "false"),
        ],
        "forced_values": [
            ("Delete", "false"),
            ("Disable", "false"),
        ],
        "drop_tags": ["IsInactif"],
        "forced_tag": None,
        "trim_tags": ["Name", "Category"],
        "has_dltype": False,
        "tag_order": [
            "idFileAttente", "Id", "TS", "Delete", "Disable", "Name",
            "Category", "TempMin", "TempMax",
        ],
        "root_attrs": (
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            'xmlns:xsd="http://www.w3.org/2001/XMLSchema"'
        ),
        "never_invent": ["Id", "TS", "Name", "Category", "TempMin", "TempMax"],
        "force_eol": "\r\n",
        "strip_bom": True,
        "xml_decl_encoding": "utf-8",
        "final_newline": None,
        "output_name": "ProductsService.xml",
    },
}

DLTYPE_VALID_VALUES = {-1, 0, 1, 2, 3}
WS_RUN_RE = re.compile("[\\s﻿]+")
LIGATURES = str.maketrans({"Œ": "OE", "œ": "oe", "Æ": "AE", "æ": "ae"})
CHILD_RE = re.compile(r"<([A-Za-z_][\w.\-]*)\s*(?:/>|>(.*?)</\1\s*>)", re.S)
ATTR_NAME_RE = re.compile(r"([\w:.\-]+)\s*=")


def expand_ligatures(value):
    return value.translate(LIGATURES)


def clean_text(value):
    return WS_RUN_RE.sub(" ", expand_ligatures(value)).strip()


def detect_element(text):
    m = re.search(r"<ArrayOf([A-Za-z0-9_]+)[ >]", text)
    return m.group(1) if m else None


def build_block_re(element):
    return re.compile(
        rf"(?P<open>[ \t]*<{element}>[ \t]*\r?\n)"
        rf"(?P<body>.*?)"
        rf"(?P<close>[ \t]*</{element}>[ \t]*\r?\n?)",
        re.S,
    )


def ensure_root_attrs(text, element, attrs):
    if not attrs:
        return text, False
    m = re.search(rf"<ArrayOf{element}(?P<attrs>[^>]*)>", text)
    if not m:
        return text, False
    existing = m.group("attrs")
    existing_names = set(ATTR_NAME_RE.findall(existing))
    missing = [
        a for a in re.findall(r'[\w:.\-]+\s*=\s*"[^"]*"', attrs)
        if ATTR_NAME_RE.match(a).group(1) not in existing_names
    ]
    if not missing:
        return text, False
    new_open = f"<ArrayOf{element}{existing.rstrip()} {' '.join(missing)}>"
    return text[: m.start()] + new_open + text[m.end():], True


def direct_children(body):
    return [(m.group(1), m.group(0)) for m in CHILD_RE.finditer(body)]


def ensure_xml_decl_encoding(text, encoding):
    if not encoding:
        return text, False
    m = re.match(r"<\?xml[^>]*\?>", text)
    if not m:
        return text, False
    decl = m.group(0)
    new_decl, n = re.subn(r'(encoding\s*=\s*")[^"]*(")',
                          rf"\g<1>{encoding}\g<2>", decl, count=1)
    if not n or new_decl == decl:
        return text, False
    return new_decl + text[m.end():], True


def reorder_body(body, order, indent, eol):
    items = [(m.group(1), m.group(0)) for m in CHILD_RE.finditer(body)]
    if not items:
        return body, []
    rank = {t.lower(): i for i, t in enumerate(order)}
    unknown = [t for t, _ in items if t.lower() not in rank]
    items.sort(key=lambda it: rank.get(it[0].lower(), len(order)))
    return "".join(f"{indent}{rendered}{eol}" for _, rendered in items), unknown


# --------------------------------------------------------------------------
# Fichier de référence : lecture de valeurs métier qu'on ne doit pas inventer
# --------------------------------------------------------------------------
def load_reference(path, element):
    with open(path, "rb") as f:
        raw = f.read()
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    text = raw.decode("utf-8")
    ref = {}
    for m in build_block_re(element).finditer(text):
        body = m.group("body")
        idm = re.search(r"<Id>(.*?)</Id>", body, re.S)
        if idm:
            ref[idm.group(1).strip()] = body
    return ref


def ref_lookup(body, path):
    """Lit une valeur dans un bloc de référence, via un chemin « A/B »."""
    cur = body
    parts = path.split("/")
    for part in parts[:-1]:
        m = re.search(rf"<{part}>(.*?)</{part}>", cur, re.S)
        if not m:
            return None
        cur = m.group(1)
    m = re.search(rf"<{parts[-1]}>(.*?)</{parts[-1]}>", cur, re.S)
    return m.group(1).strip() if m else None


# --------------------------------------------------------------------------
# Sous-blocs uniques imbriqués (ex. <Recurrence>), par opposition à children
# qui gère une collection d'éléments répétés (ex. <Items>/<DefCheckItem>).
# --------------------------------------------------------------------------
def process_subblocks(body, subblocks, eol, stats, warnings, label, ref_body):
    touched = False
    for sb in subblocks:
        cname = sb["container"]
        m = re.search(
            rf"(?P<open>[ \t]*<{cname}>[ \t]*\r?\n)(?P<inner>.*?)(?P<close>[ \t]*</{cname}>)",
            body, re.S)
        if m is None:
            warnings.append(f"{label} : bloc <{cname}> absent — non traité")
            continue
        inner = m.group("inner")
        orig_inner = inner

        indent_match = re.search(r"^([ \t]*)\S", inner, re.M)
        indent = indent_match.group(1) if indent_match else "      "

        for tag in sb.get("never_invent", []):
            tm = re.search(rf"<{tag}\s*(?:/>|>(.*?)</{tag}\s*>)", inner, re.S)
            if tm is None or not (tm.group(1) or "").strip():
                warnings.append(
                    f"{label} > {cname} : <{tag}> absente ou vide — à renseigner à la main")

        present = set(t.lower() for t, _ in direct_children(inner))
        additions = []
        for tag, default_value in sb.get("required_tags", []):
            if tag.lower() in present:
                continue
            if tag in sb.get("reference_tags", []):
                value = ref_lookup(ref_body, f"{cname}/{tag}") if ref_body else None
                if value is None:
                    warnings.append(
                        f"{label} > {cname} : <{tag}> absente et introuvable dans le "
                        f"fichier de référence — à renseigner à la main")
                    continue
                additions.append(f"{indent}<{tag}>{value}</{tag}>{eol}")
            elif default_value is None:
                additions.append(f"{indent}<{tag} />{eol}")
            else:
                additions.append(f"{indent}<{tag}>{default_value}</{tag}>{eol}")
            stats[f"{cname}/{tag}"] += 1
        if additions:
            inner = inner.rstrip("\r\n") + eol + "".join(additions)

        if sb.get("tag_order"):
            new_inner, unknown = reorder_body(inner, sb["tag_order"], indent, eol)
            for tag in unknown:
                warnings.append(
                    f"{label} > {cname} : balise inattendue <{tag}> conservée en fin de bloc")
            if new_inner != inner:
                stats[f"{cname} (ordre corrigé)"] += 1
                inner = new_inner

        if inner != orig_inner:
            touched = True
            body = body[: m.start("inner")] + inner + body[m.end("inner"):]
    return body, touched


def process_children(body, child, eol, stats, warnings, parent_label):
    container, element = child["container"], child["element"]
    cont_re = re.compile(rf"(<{container}>)(.*?)(</{container}>)", re.S)
    cm = cont_re.search(body)
    if cm is None:
        warnings.append(f"{parent_label} : conteneur <{container}> absent ou vide")
        return body, False

    block_re = build_block_re(element)
    trim_res = {n: re.compile(rf"(<{n}>)(.*?)(</{n}>)", re.S)
                for n in child.get("trim_tags", [])}
    counter = {"i": 0}

    def fix_item(im):
        open_tag, ibody, close_tag = im.group("open"), im.group("body"), im.group("close")
        counter["i"] += 1
        indent_match = re.search(r"^([ \t]*)\S", ibody, re.M)
        indent = indent_match.group(1) if indent_match else "        "

        for tname, tre in trim_res.items():
            tmatch = tre.search(ibody)
            if not tmatch:
                continue
            raw = tmatch.group(2)
            cleaned = clean_text(raw)
            if cleaned == raw:
                continue
            ibody = (ibody[: tmatch.start()]
                     + f"{tmatch.group(1)}{cleaned}{tmatch.group(3)}"
                     + ibody[tmatch.end():])
            ligatured = expand_ligatures(raw)
            if ligatured != raw:
                stats[f"{element}/{tname} (ligatures décomposées)"] += 1
            if WS_RUN_RE.sub(" ", ligatured).strip() != ligatured:
                stats[f"{element}/{tname} (espaces nettoyés)"] += 1

        nmatch = re.search(r"<Name>(.*?)</Name>", ibody, re.S)
        label = (f"{parent_label} > {nmatch.group(1).strip()}" if nmatch
                 else f"{parent_label} > item #{counter['i']}")

        for tag in child.get("never_invent", []):
            tmatch = re.search(rf"<{tag}\s*(?:/>|>(.*?)</{tag}\s*>)", ibody, re.S)
            if tmatch is None or not (tmatch.group(1) or "").strip():
                warnings.append(f"{label} : <{tag}> absente ou vide — à renseigner à la main")

        present = set(t.lower() for t, _ in direct_children(ibody))
        additions = []
        for name, default_value in child.get("required_tags", []):
            if name.lower() in present:
                continue
            additions.append(f"{indent}<{name} />{eol}" if default_value is None
                             else f"{indent}<{name}>{default_value}</{name}>{eol}")
            stats[f"{element}/{name}"] += 1
        if additions:
            ibody = ibody.rstrip("\r\n") + eol + "".join(additions)

        if child.get("tag_order"):
            new_ibody, unknown = reorder_body(ibody, child["tag_order"], indent, eol)
            for tag in unknown:
                warnings.append(f"{label} : balise inattendue <{tag}> conservée en fin de bloc")
            if new_ibody != ibody:
                stats[f"{element} (ordre corrigé)"] += 1
                ibody = new_ibody

        return open_tag + ibody + close_tag

    inner = cm.group(2)
    new_inner = block_re.sub(fix_item, inner)
    stats[f"{element} (total)"] += counter["i"]
    if counter["i"] == 0:
        warnings.append(f"{parent_label} : aucun <{element}> trouvé dans <{container}>")
    if new_inner == inner:
        return body, False
    new_body = (body[: cm.start()] + cm.group(1) + new_inner + cm.group(3)
                + body[cm.end():])
    return new_body, True


def process(text, eol, profile, dltype_value, isddm_value,
            isddm_exc_category, isddm_exc_value, reference):
    element = profile["element"]
    block_re = build_block_re(element)
    count_products = len(re.findall(rf"<{element}>", text))

    stats = {}
    if profile["leading_tag"]:
        stats[profile["leading_tag"][0]] = 0
    for name, _ in profile["required_tags"]:
        stats[name] = 0
    if profile["forced_tag"]:
        stats[f"{profile['forced_tag']} (ajoutée)"] = 0
        stats[f"{profile['forced_tag']} (mise à jour)"] = 0
        if isddm_exc_category:
            stats[f"{profile['forced_tag']} (exception catégorie)"] = 0
    for trim_name in profile["trim_tags"]:
        stats[f"{trim_name} (espaces nettoyés)"] = 0
        stats[f"{trim_name} (ligatures décomposées)"] = 0
    for drop_name in profile.get("drop_tags", []):
        stats[f"{drop_name} (supprimée)"] = 0
    for fv_name, fv_value in profile.get("forced_values", []):
        stats[f"{fv_name} (remise à {fv_value})"] = 0
    if profile["has_dltype"]:
        stats["DLType (ajoutée)"] = 0
        stats["DLType (mise à jour)"] = 0
        stats["DLType (forcée -1)"] = 0
    if profile.get("tag_order"):
        stats["Ordre des balises corrigé"] = 0
    for sb in profile.get("subblocks", []):
        for name, _ in sb.get("required_tags", []):
            stats[f"{sb['container']}/{name}"] = 0
        if sb.get("tag_order"):
            stats[f"{sb['container']} (ordre corrigé)"] = 0
    child = profile.get("children")
    if child:
        ce = child["element"]
        stats[f"{ce} (total)"] = 0
        for name, _ in child.get("required_tags", []):
            stats[f"{ce}/{name}"] = 0
        for trim_name in child.get("trim_tags", []):
            stats[f"{ce}/{trim_name} (espaces nettoyés)"] = 0
            stats[f"{ce}/{trim_name} (ligatures décomposées)"] = 0
        if child.get("tag_order"):
            stats[f"{ce} (ordre corrigé)"] = 0

    products_touched = 0
    products_missing_datelimit = 0
    warnings = []

    forced_re = None
    if profile["forced_tag"]:
        forced_re = re.compile(
            rf"(<{profile['forced_tag']}>)[^<]*(</{profile['forced_tag']}>)", re.IGNORECASE)
    trim_res = {name: re.compile(rf"(<{name}>)(.*?)(</{name}>)", re.S)
                for name in profile["trim_tags"]}
    category_re = re.compile(r"<Category>(.*?)</Category>", re.S)
    datelimit_re = re.compile(r"<DateLimit>(.*?)</DateLimit>", re.S)
    dltype_re = re.compile(r"(<DLType>)-?\d+(</DLType>)", re.IGNORECASE)
    name_re = re.compile(r"<Name>(.*?)</Name>", re.S)

    isddm_exc_category_norm = isddm_exc_category.strip().lower() if isddm_exc_category else None
    counter = {"i": 0}

    def process_block(m):
        nonlocal products_touched, products_missing_datelimit
        open_tag, body, close_tag = m.group("open"), m.group("body"), m.group("close")
        touched = False
        counter["i"] += 1

        indent_match = re.search(r"^([ \t]*)\S", body, re.M)
        indent = indent_match.group(1) if indent_match else "    "

        if child or profile.get("subblocks"):
            present = set(t.lower() for t, _ in direct_children(body))
        else:
            present = set(t.lower() for t in re.findall(r"<([A-Za-z_][\w.\-]*)[ >/]", body))

        for trim_name, trim_re in trim_res.items():
            tmatch = trim_re.search(body)
            if tmatch:
                raw = tmatch.group(2)
                cleaned = clean_text(raw)
                if cleaned != raw:
                    body = (body[: tmatch.start()]
                            + f"{tmatch.group(1)}{cleaned}{tmatch.group(3)}"
                            + body[tmatch.end():])
                    ligatured = expand_ligatures(raw)
                    if ligatured != raw:
                        stats[f"{trim_name} (ligatures décomposées)"] += 1
                    if WS_RUN_RE.sub(" ", ligatured).strip() != ligatured:
                        stats[f"{trim_name} (espaces nettoyés)"] += 1
                    touched = True

        name_match = name_re.search(body)
        label = name_match.group(1).strip() if name_match else f"objet #{counter['i']}"
        cat_match0 = category_re.search(body)
        if cat_match0:
            label = f"{label} / {cat_match0.group(1).strip()}"

        for tag in profile.get("never_invent", []):
            tag_match = re.search(rf"<{tag}\s*(?:/>|>(.*?)</{tag}\s*>)", body, re.S)
            if tag_match is None or not (tag_match.group(1) or "").strip():
                warnings.append(f"{label} : <{tag}> absente ou vide — à renseigner à la main")

        if child:
            body, child_touched = process_children(body, child, eol, stats, warnings, label)
            if child_touched:
                touched = True

        if profile.get("subblocks"):
            id_match = re.search(r"<Id>(.*?)</Id>", body, re.S)
            ref_body = reference.get(id_match.group(1).strip()) if (reference and id_match) else None
            if reference and ref_body is None:
                warnings.append(f"{label} : aucun bloc correspondant dans le fichier de référence")
            body, sb_touched = process_subblocks(
                body, profile["subblocks"], eol, stats, warnings, label, ref_body)
            if sb_touched:
                touched = True

        for drop_name in profile.get("drop_tags", []):
            drop_re = re.compile(
                rf"^[ \t]*<{drop_name}\b[^>]*?(?:/>|>.*?</{drop_name}\s*>)[ \t]*\r?\n?",
                re.M | re.S | re.IGNORECASE)
            body, n = drop_re.subn("", body)
            if n:
                stats[f"{drop_name} (supprimée)"] += n
                present.discard(drop_name.lower())
                touched = True

        for fv_name, fv_value in profile.get("forced_values", []):
            fv_re = re.compile(
                rf"<{fv_name}\s*/>|<{fv_name}>([^<]*)</{fv_name}\s*>", re.IGNORECASE)
            fv_match = fv_re.search(body)
            if fv_match and (fv_match.group(1) or "").strip() != fv_value:
                body = (body[: fv_match.start()] + f"<{fv_name}>{fv_value}</{fv_name}>"
                        + body[fv_match.end():])
                stats[f"{fv_name} (remise à {fv_value})"] += 1
                touched = True

        if profile["leading_tag"]:
            leading_name, leading_default = profile["leading_tag"]
            if leading_name.lower() not in present:
                id_match = re.search(r"^([ \t]*)<Id>", body, re.M)
                if id_match:
                    insertion = f"{id_match.group(1)}<{leading_name}>{leading_default}</{leading_name}>{eol}"
                    body = body[: id_match.start()] + insertion + body[id_match.start():]
                    stats[leading_name] += 1
                    touched = True

        if profile["has_dltype"]:
            dl_match = datelimit_re.search(body)
            if not dl_match:
                products_missing_datelimit += 1
            else:
                datelimit_value = dl_match.group(1).strip()
                effective_dltype = -1 if datelimit_value == "-1" else dltype_value
                if dltype_re.search(body):
                    body, n = dltype_re.subn(rf"\g<1>{effective_dltype}\g<2>", body)
                    if n:
                        stats["DLType (mise à jour)"] += n
                        touched = True
                else:
                    line_start = body.rfind("\n", 0, dl_match.start()) + 1
                    dl_indent = re.match(r"[ \t]*", body[line_start:]).group(0)
                    insertion = f"{dl_indent}<DLType>{effective_dltype}</DLType>{eol}"
                    insert_pos = body.find("\n", dl_match.end())
                    insert_pos = insert_pos + 1 if insert_pos != -1 else len(body)
                    body = body[:insert_pos] + insertion + body[insert_pos:]
                    stats["DLType (ajoutée)"] += 1
                    touched = True
                if datelimit_value == "-1":
                    stats["DLType (forcée -1)"] += 1

        additions = []
        if profile["forced_tag"]:
            effective_value = isddm_value
            if isddm_exc_category_norm is not None:
                cat_match = category_re.search(body)
                if cat_match and cat_match.group(1).strip().lower() == isddm_exc_category_norm:
                    effective_value = isddm_exc_value
                    stats[f"{profile['forced_tag']} (exception catégorie)"] += 1
            if profile["forced_tag"].lower() in present:
                body, n = forced_re.subn(rf"\g<1>{effective_value}\g<2>", body)
                if n:
                    stats[f"{profile['forced_tag']} (mise à jour)"] += n
                    touched = True
            else:
                additions.append(
                    f"{indent}<{profile['forced_tag']}>{effective_value}</{profile['forced_tag']}>{eol}")
                stats[f"{profile['forced_tag']} (ajoutée)"] += 1

        for name, default_value in profile["required_tags"]:
            if name.lower() in present:
                continue
            if default_value is None:
                additions.append(f"{indent}<{name} />{eol}")
            else:
                additions.append(f"{indent}<{name}>{default_value}</{name}>{eol}")
            stats[name] += 1

        if additions:
            touched = True
            body = body.rstrip("\r\n") + eol + "".join(additions)

        if profile.get("tag_order"):
            new_body, unknown = reorder_body(body, profile["tag_order"], indent, eol)
            for tag in unknown:
                warnings.append(f"{label} : balise inattendue <{tag}> conservée en fin de bloc")
            if new_body != body:
                stats["Ordre des balises corrigé"] += 1
                body = new_body
                touched = True

        if touched:
            products_touched += 1
        return open_tag + body + close_tag

    new_text = block_re.sub(process_block, text)

    if len(re.findall(rf"<{element}>", new_text)) != count_products:
        raise RuntimeError("Le nombre d'objets a changé après traitement — sortie non fiable.")

    new_text, attrs_added = ensure_root_attrs(new_text, element, profile.get("root_attrs"))

    return (new_text, count_products, products_touched, products_missing_datelimit,
            stats, warnings, attrs_added)


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("input", nargs="?")
    parser.add_argument("output", nargs="?")
    parser.add_argument("--dltype", type=int)
    parser.add_argument("--isddm", choices=["true", "false"])
    parser.add_argument("--isddm-exception-category")
    parser.add_argument("--isddm-exception-value", choices=["true", "false"])
    parser.add_argument("--reference")
    parser.add_argument("--list-profiles", action="store_true")
    parser.add_argument("-h", "--help", action="store_true")
    args = parser.parse_args()

    if args.help or (not args.list_profiles and (not args.input or not args.output)):
        print(__doc__)
        sys.exit(0 if args.help else 1)

    if args.list_profiles:
        print("Types connus (profils) :")
        for name, p in PROFILES.items():
            notes = []
            if p["has_dltype"]:
                notes.append("DLType")
            if p["forced_tag"]:
                notes.append(f"balise forcée: {p['forced_tag']}")
            if p.get("forced_values"):
                notes.append("valeurs forcées: " + ", ".join(f"{n}={v}" for n, v in p["forced_values"]))
            if p.get("drop_tags"):
                notes.append("supprimées: " + ", ".join(p["drop_tags"]))
            if p.get("tag_order"):
                notes.append("ordre imposé")
            if p.get("root_attrs"):
                notes.append("namespaces racine")
            if p.get("children"):
                notes.append(f"enfants: {p['children']['container']}/{p['children']['element']}")
            for sb in p.get("subblocks", []):
                notes.append(f"sous-bloc: {sb['container']}")
                if sb.get("reference_tags"):
                    notes.append(f"--reference requis pour {', '.join(sb['reference_tags'])}")
            if p.get("output_name"):
                notes.append(f"sortie: {p['output_name']}")
            suffix = f" [{'] ['.join(notes)}]" if notes else ""
            print(f"  - {name}{suffix}")
        sys.exit(0)

    with open(args.input, "rb") as f:
        raw = f.read()

    bom = b""
    if raw.startswith(b"\xef\xbb\xbf"):
        bom = raw[:3]
        raw = raw[3:]

    eol = "\r\n" if raw.count(b"\r\n") > 0 else "\n"
    text = raw.decode("utf-8")

    element = detect_element(text)
    if element is None:
        print("ERREUR : impossible de détecter la racine <ArrayOfXxx> du fichier.")
        sys.exit(2)

    profile = PROFILES.get(element)
    if profile is None:
        print(f"ERREUR : type inconnu « {element} ».")
        print("Ce script ne traite que les types enregistrés (voir --list-profiles).")
        sys.exit(3)

    out_eol = profile.get("force_eol") or eol
    strip_bom = profile.get("strip_bom")
    if strip_bom is True:
        bom = b""
    elif strip_bom is False:
        bom = b"\xef\xbb\xbf"

    if profile["has_dltype"] and args.dltype is None:
        print(f"ERREUR : le profil {element} nécessite --dltype (-1, 0, 1, 2 ou 3).")
        sys.exit(1)
    if profile["has_dltype"] and args.dltype not in DLTYPE_VALID_VALUES:
        print(f"ERREUR : --dltype invalide ({args.dltype}).")
        sys.exit(1)
    if profile["forced_tag"] and args.isddm is None:
        print(f"ERREUR : le profil {element} nécessite --isddm true|false.")
        sys.exit(1)
    if bool(args.isddm_exception_category) != bool(args.isddm_exception_value):
        print("ERREUR : --isddm-exception-category et --isddm-exception-value vont ensemble.")
        sys.exit(1)

    needs_ref = any(sb.get("reference_tags") for sb in profile.get("subblocks", []))
    reference = None
    if args.reference:
        reference = load_reference(args.reference, element)
        print(f"Référence chargée : {len(reference)} bloc(s) depuis {args.reference}")
    elif needs_ref:
        print(f"AVERTISSEMENT : le profil {element} attend --reference pour les valeurs "
              f"métier non inventables — elles seront signalées comme manquantes.")

    try:
        new_text, count_products, touched, missing_dl, stats, warnings, attrs_added = process(
            text, out_eol, profile,
            dltype_value=args.dltype,
            isddm_value=args.isddm,
            isddm_exc_category=args.isddm_exception_category,
            isddm_exc_value=args.isddm_exception_value,
            reference=reference,
        )
    except RuntimeError as e:
        print(f"ATTENTION : {e}")
        sys.exit(2)

    if profile.get("force_eol"):
        new_text = new_text.replace("\r\n", "\n").replace("\n", profile["force_eol"])

    new_text, decl_changed = ensure_xml_decl_encoding(
        new_text, profile.get("xml_decl_encoding"))

    if profile.get("final_newline") and not new_text.endswith(out_eol):
        new_text += out_eol

    if profile["has_dltype"] and missing_dl:
        print(f"ATTENTION : {missing_dl} produit(s) sans <DateLimit>.")
        sys.exit(2)

    with open(args.output, "wb") as f:
        f.write(bom + new_text.encode("utf-8"))

    unit = profile.get("label_plural", "produit(s)")
    print(f"OK : type détecté « {element} » — {count_products} {unit} vérifié(e)s, {touched} modifié(e)s.")
    if profile["leading_tag"]:
        name = profile["leading_tag"][0]
        print(f"  {name} ajoutée sur {stats[name]} objet(s)")
    if profile["has_dltype"]:
        print(f"  DLType ajoutée sur {stats['DLType (ajoutée)']}, mise à jour sur {stats['DLType (mise à jour)']}, "
              f"forcée à -1 sur {stats['DLType (forcée -1)']}")
    if profile["forced_tag"]:
        ft = profile["forced_tag"]
        print(f"  {ft} ajoutée sur {stats[f'{ft} (ajoutée)']}, mise à jour sur {stats[f'{ft} (mise à jour)']}")
    for trim_name in profile["trim_tags"]:
        print(f"  {trim_name} : espaces nettoyés sur {stats[f'{trim_name} (espaces nettoyés)']} objet(s), "
              f"ligatures décomposées sur {stats[f'{trim_name} (ligatures décomposées)']} objet(s)")
    for name, _ in profile["required_tags"]:
        print(f"  {name} ajoutée sur {stats[name]} objet(s)")
    for fv_name, fv_value in profile.get("forced_values", []):
        print(f"  {fv_name} remise à {fv_value} sur {stats[f'{fv_name} (remise à {fv_value})']} objet(s)")
    for drop_name in profile.get("drop_tags", []):
        print(f"  {drop_name} supprimée sur {stats[f'{drop_name} (supprimée)']} objet(s)")
    for sb in profile.get("subblocks", []):
        cname = sb["container"]
        for name, _ in sb.get("required_tags", []):
            print("  {}/{} ajoutée sur {} objet(s)".format(
                cname, name, stats["{}/{}".format(cname, name)]))
        if sb.get("tag_order"):
            print("  Ordre corrigé dans <{}> sur {} objet(s)".format(
                cname, stats["{} (ordre corrigé)".format(cname)]))
    if profile.get("tag_order"):
        print(f"  Ordre des balises corrigé sur {stats['Ordre des balises corrigé']} objet(s)")
    child = profile.get("children")
    if child:
        ce = child["element"]
        print(f"  {stats[f'{ce} (total)']} <{ce}> traités")
        for name, _ in child.get("required_tags", []):
            print(f"    {ce}/{name} ajoutée sur {stats[f'{ce}/{name}']} item(s)")
    if attrs_added:
        print("  Namespaces xsi/xsd ajoutés sur la balise racine")
    if decl_changed:
        print(f"  Déclaration XML normalisée en encoding=\"{profile['xml_decl_encoding']}\"")
    if profile.get("strip_bom") is True:
        print("  BOM retiré en sortie")
    if warnings:
        print(f"ATTENTION : {len(warnings)} point(s) à vérifier à la main —")
        for w in warnings:
            print(f"  - {w}")
    print(f"Fichier écrit : {args.output}")
    if profile.get("output_name"):
        print(f"RAPPEL : ce type doit être livré sous le nom exact « {profile['output_name']} ».")


if __name__ == "__main__":
    main()
