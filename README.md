# 🏔️ MNT France Generator

Application Streamlit pour télécharger et générer les Modèles Numériques de Terrain (MNT) de la France par département.

## 📋 Fonctionnalités

✅ **Mode Simple** - Traiter un département à la fois
✅ **Mode Batch** - Traiter tous les départements automatiquement
✅ **Calcul des pentes** - Générer des cartes des zones avec pente > 5% et > 10%
✅ **Export TIFF** - Conversion automatique en format GeoTIFF
✅ **Validation** - Vérification de l'intégrité des fichiers générés
✅ **Logs détaillés** - Suivi complet du traitement

## 📊 Sources de données

- **Source** : IGN (Institut National de l'Information Géographique)
- **Format** : RGEALTI 5M ASC
- **Projection** : Lambert93 (EPSG:2154)
- **Couverture** : France métropolitaine et DROM-COM

## 🛠️ Installation

### Prérequis

- Python 3.8+
- QGIS 3.14+ (pour accès à GDAL/gdaldem)
- Espace disque : 50+ GB (pour tous les départements)

### Étapes d'installation

1. **Cloner le repository**
```bash
git clone <votre-repo>
cd projet-mnt
```

2. **Créer un environnement virtuel**
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/macOS
```

3. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

4. **Installer QGIS**
   - Télécharger depuis https://qgis.org/download/
   - L'application détectera automatiquement QGIS

## 🚀 Lancement

```bash
streamlit run mnt_app.py
```

L'application ouvrira automatiquement dans votre navigateur (http://localhost:8501)

## 📁 Structure du projet

```
.
├── mnt_app.py                     # Application principale Streamlit
├── batch_processor.py             # Processeur batch pour traitement automatique
├── config.py                      # Configuration générale
├── convert_vrt_to_geotiff.py      # Conversion VRT vers TIFF
├── validate_all_mnt.py            # Validation des fichiers MNT
├── test_vrt_integrity.py          # Tests d'intégrité VRT
├── deps.csv                       # Base de données des départements
├── README_APP.md                  # Guide utilisateur détaillé
├── requirements.txt               # Dépendances Python
└── MNT_BATCH_RESULTS/            # Dossier de sortie (généré)
    ├── MNT/                       # Fichiers TIFF des MNT
    ├── PENTE/                     # Fichiers de pente complets
    ├── PENTE_SUP5/                # Rasters binaires (pente > 5%)
    ├── PENTE_SUP10/               # Rasters binaires (pente > 10%)
    └── LOGS/                      # Logs et validation
```

## 💾 Mode d'utilisation

### Mode Simple (1 département)
1. Sélectionner un département dans la liste
2. Cliquer sur **"Lancer le traitement"**
3. Le processus télécharge, extrait et génère automatiquement tous les fichiers

### Mode Batch (tous les départements)
1. Sélectionner les départements à traiter
2. Le système vérifie les traitements antérieurs
3. Les fichiers manquants sont téléchargés et traités
4. Tous les résultats sont organisés par département

## 🔧 Configuration GDAL

L'application détecte automatiquement **QGIS** et l'outil **gdaldem**. 

Si la détection échoue :
1. Dans la barre latérale, cliquer sur **⚙️ Configuration GDAL**
2. Entrer le chemin complet vers `gdaldem.exe`
   - Exemple: `C:\Program Files\QGIS\bin\gdaldem.exe`

## 📝 Fichiers générés

### MNT (Modèle Numérique de Terrain)
- Fichier TIFF géoréférencé avec les altitudes
- Nom: `MNT_D{code}_{nom}.tif`

### Pentes
- **Pente complète** : Valeurs continues 0-90% (dossier `PENTE/`)
- **Pente > 5%** : Raster binaire 0/1 (dossier `PENTE_SUP5/`)
- **Pente > 10%** : Raster binaire 0/1 (dossier `PENTE_SUP10/`)

### VRT (Virtual RasterFile)
- Fichiers mosaïque temporaires pour assemblage des tuiles
- Supprimes automatiquement après conversion TIFF

## 🧪 Validation

L'application valide automatiquement :
- ✅ Intégrité des fichiers téléchargés
- ✅ Cohérence des données VRT
- ✅ Comparaison VRT ↔ TIFF
- ✅ Couverture géographique complète

## 📊 Performance

- **Temps par département** : 5-15 minutes (selon CPU/disque)
- **Espace par département** : 100-500 MB
- **Parallélisation** : Jusqu'à 4 traitements simultanés (configurable)

## 🐛 Dépannage

### gdaldem non trouvé
```
Solution : Installer QGIS depuis https://qgis.org/download/
```

### Erreur "Connexion au serveur"
```
Solution : Vérifier la connexion internet et la disponibilité du serveur IGN
```

### Fichiers TIFF corrompus
```
Solution : Supprimer les fichiers défectueux et relancer le traitement
```

### Manque d'espace disque
```
Solution : Nettoyer le dossier WORK/ ou augmenter l'espace disponible
```

## 📚 Documentation

- [README_APP.md](README_APP.md) - Guide utilisateur détaillé
- [GUIDE_VALIDATION.md](GUIDE_VALIDATION.md) - Guide de validation
- [FIX_CORRUPTED_7Z.md](FIX_CORRUPTED_7Z.md) - Correction des fichiers 7z

## 🔐 Licence

Ce projet utilise les données de l'IGN qui sont librement disponibles.

## 👨‍💻 Auteur

Mary

## 📧 Support

Pour les problèmes ou suggestions, veuillez créer une issue sur GitHub.

---

**Note** : Ce projet nécessite une connexion internet pour télécharger les données depuis les serveurs de l'IGN.
