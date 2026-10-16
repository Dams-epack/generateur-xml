# Générateur XML e-Pack

Outil interne ePackPro (Support SGC) : à partir d'un fichier Excel client, génère des fichiers XML prêts à importer dans e-Pack Manager, un par onglet (langue, pays, site) et par module.

## Modules gérés

Service, Production, Stickers, Freezing, Frozen, StockIn.
Non gérés pour l'instant : CheckLists, Cleanings (structures imbriquées), et les autres exports du pack.

Les sorties suivent les règles de la skill `completer-produits-xml` : ordre des balises, `idFileAttente` et `Disable` ajoutés, espaces et ligatures Œ/Æ nettoyés, fin de ligne et déclaration XML propres à chaque type, Id/TS jamais modifiés quand ils sont fournis.

## Deux façons de l'utiliser

### 1. Page web autonome : `index.html`

Un seul fichier, sans dépendance serveur. Il charge SheetJS et JSZip depuis cdnjs, donc une connexion est nécessaire à l'ouverture.

1. Déposer le fichier Excel du client tel quel (tous les onglets sont lus).
2. Choisir le module. Les colonnes sont reconnues automatiquement dans chaque onglet (« Category » = « Catégorie », « DESIGNATION » = `Name`, etc.). Un tableau permet de contrôler la détection.
3. Pour les Stickers : choisir le Type de DLC, l'IsDDM par défaut, et cocher « Boulangerie Ange » si la règle DDM SECONDAIRE s'applique.
4. Générer, puis enregistrer chaque fichier ou tout en ZIP (`XML_<Module>.zip`, un dossier par onglet).

Dans claude.ai, l'enregistrement passe par la capacité `downloads` des artefacts (confirmation demandée). Ailleurs (fichier ouvert en local, GitHub Pages), la page utilise un téléchargement navigateur classique.

### 2. Ligne de commande : `tools/`

Prérequis : Python 3 et `pip install openpyxl`.

```bash
# Voir les onglets, en-têtes et premières lignes d'un fichier client
python3 tools/excel_to_xml.py client.xlsx --inspect

# Un module depuis un onglet libre, avec correspondance des colonnes
python3 tools/excel_to_xml.py client.xlsx --modules Production --sheet FR --header-row 1 \
  --map '{"Name":"Désignation","Category":"Famille","DateLimit":"=-1"}' --out-dir sortie_xml/FR

# Stickers
python3 tools/excel_to_xml.py client.xlsx --modules Stickers --sheet FR \
  --map '{"Name":"Nom","Category":"Catégorie","DateLimit":"DLC"}' \
  --dltype 2 --isddm false --isddm-exception-category "DDM SECONDAIRE" --out-dir sortie_xml/FR
```

`--map` associe une balise e-Pack à une colonne source. Une valeur `=x` applique `x` à toutes les lignes.
`tools/complete_xml_products.py` est le script de la skill `completer-produits-xml` ; `excel_to_xml.py` y fait passer chaque XML généré.

## Règles et valeurs par défaut

- Id vide : généré (18 chiffres, unique). TS vide : heure de génération. Id ou TS fournis : conservés tels quels.
- Champ numérique obligatoire absent (`DateLimit`, `Dlc`, `Ddm`, `Du`, `TempMin`, `TempMax`) : -1, signalé en alerte. Attention, -1 est une vraie température pour Service et StockIn.
- Service : `Delete` est toujours remis à `false`.
- Stickers : le Type de DLC n'est demandé que si une `DateLimit` est différente de -1 ; sinon `DLType` vaut -1.
- Un onglet en erreur (valeur obligatoire manquante, nombre invalide, Id en double) n'est pas généré.

## Tests

```bash
node tests/test_core.js                 # coeur JS (extrait de la page), données fictives
python3 -m unittest discover -s tests   # outil en ligne de commande
```

## Données

Ne jamais versionner de fichiers clients ni de XML générés : `.gitignore` exclut `*.xlsx` et `*.xml`.
