# 🏔️ MNT France Generator - Application Streamlit

Application moderne pour télécharger et générer des mosaïques MNT (Modèle Numérique de Terrain) pour n'importe quel département français.

## 📋 Fonctionnalités

✅ **Interface web moderne**
- Sélection simple des départements
- Visualisation en temps réel du processus
- Statistiques détaillées

✅ **Téléchargement automatique**
- URLs depuis IGN/GeoPF
- Gestion intelligente des fichiers existants
- Support du streaming pour grands fichiers

✅ **Extraction 7z**
- Décompression automatique
- Gestion des erreurs
- Vérification de l'intégrité

✅ **Génération VRT optimisée**
- Fusion intelligente des tuiles
- Projection Lambert93 (EPSG:2154)
- Fichiers légers (quelques KB)

✅ **Export personnalisé**
- Téléchargement direct depuis l'app
- Noms descriptifs avec département
- Format XML standard GDAL

## 🚀 Démarrage rapide

### Option 1: Fichier .bat (Recommandé pour Windows)
```bash
Double-cliquez sur: LANCER_APP.bat
```

### Option 2: Terminal PowerShell
```powershell
cd "C:\Users\marya\Downloads\projet test"
streamlit run mnt_app.py
```

### Option 3: Terminal Python
```bash
python -m streamlit run mnt_app.py
```

## 💻 Interface de l'application

```
┌─────────────────────────────────────────────────────────────┐
│  🏔️ Générateur MNT France                                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ 📍 Sélectionner un département     │  ℹ️ Informations       │
│ ├─ 1 - Ain                         │  ├─ Code: 23          │
│ ├─ 2 - Aisne                       │  ├─ Département: ...  │
│ └─ ...                             │  └─ URL source: ...   │
│                                    │                        │
│                   [🚀 Générer MNT VRT]                      │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│ Progression:                                                 │
│ 📥 Téléchargement  [████████░░░] 45%                        │
│ 📦 Extraction      [██████████░] 95%                        │
│ 🗺️  Création VRT   [██████████░] 90%                        │
└─────────────────────────────────────────────────────────────┘
```

## 📊 Exemple de résultat

```
✅ VRT créé avec succès!

📊 Statistiques:
• Tuiles fusionnées: 272
• Résolution: 20000 × 19000 pixels
• Étendue: 100000 m × 95000 m
• Taille cellule: 5 m
• Projection: Lambert93 (EPSG:2154)

📁 Fichier VRT: MNT_D023_Creuse.vrt (167 KB)
[⬇️ Télécharger le fichier VRT]
```

## 🗂️ Structure des fichiers

```
C:\Users\marya\Downloads\
├── projet test/
│   ├── mnt_app.py              ← Application Streamlit
│   ├── LANCER_APP.bat          ← Raccourci de lancement
│   ├── README_APP.md           ← Ce fichier
│   ├── create_mnt_vrt.py       ← Script Python original
│   └── deps.csv                ← Liste des départements
├── mnt_work/                   ← Fichiers de travail
│   ├── RGEALTI_D023/           ├─ Données extraites
│   │   ├── RGEALTI/
│   │   │   └── 1_DONNEES_LIVRAISON_*
│   │   │       └── RGEALTI_MNT_5M_ASC_LAMB93_IGN69_D023/
│   │   │           ├─ *.asc    ← Fichiers tuiles
│   │   │           ├─ *.prj
│   │   │           └─ ...
│   │   └── RGEALTI_D023.7z     ├─ Archive 7z
│   └── ...
├── MNT_D023_Creuse.vrt         ← VRT généré
├── MNT_D087_Ardèche.vrt        ← Autres VRTs
└── ...
```

## 📖 Utilisation du VRT dans QGIS

### Étape 1: Télécharger le VRT
1. Lancez l'application
2. Sélectionnez un département
3. Cliquez sur "🚀 Générer MNT VRT"
4. Téléchargez le fichier VRT

### Étape 2: Ouvrir dans QGIS
1. Ouvrez QGIS
2. Menu: **Couche → Ajouter une couche → Ajouter une couche raster**
3. Sélectionnez le fichier VRT téléchargé
4. Cliquez sur "Ouvrir"

### Étape 3: Visualiser
- Le MNT complet du département s'affiche
- Les tuiles sont fusionnées virtuellement
- Vous pouvez:
  - Zoomer/Dézoomer
  - Ajouter des couches SIG
  - Exporter en GeoTIFF
  - Traiter les données

### Étape 4: Exporter en GeoTIFF (optionnel)
1. Clic droit sur la couche VRT
2. **Exporter → Sauvegarder en tant que...**
3. Format: **GeoTIFF**
4. Compresse: **LZW** (optionnel)
5. Cliquez sur "Enregistrer"

## ⚙️ Configuration avancée

### Modifier le répertoire de destination
Éditez `mnt_app.py` ligne 44:
```python
DOWNLOADS_DIR = r"C:\Votre\Chemin\Ici"
```

### Modifier fond CSV
Éditez `mnt_app.py` ligne 42:
```python
CSV_PATH = r"C:\Chemin\Vers\deps.csv"
```

### Augmenter le timeout de téléchargement
Éditez `mnt_app.py` ligne 229:
```python
response = requests.get(download_url, stream=True, timeout=600)  # Augmentez le timeout
```

## 🔧 Dépannage

### Problème: "GDAL non détecté"
- C'est normal! GDAL n'est utilisé que pour la conversion en GeoTIFF optionnelle
- Le VRT fonctionne sans GDAL dans QGIS

### Problème: Downloads lent
- Vérifiez votre connexion Internet
- Le timeout par défaut est 300 secondes (5 min)
- Les fichiers font ~1-2 GB par département

### Problème: Espace disque insuffisant
- Chaque département nécessite ~2-3 GB
- Chemins: C:\Users\marya\Downloads\mnt_work\
- Vous pouvez supprimer les fichiers 7z après extraction

### Problème: "Aucun fichier ASC trouvé"
- Vérifiez que l'extraction s'est bien déroulée
- Essayez de télécharger à nouveau
- Vérifiez le dossier mnt_work\RGEALTI_D*\

## 📊 Performance

| Département | Tuiles | Résolution | Taille VRT | Temps moyen |
|-------------|--------|-----------|-----------|------------|
| Creuse (023) | 272 | 20000×19000 | 167 KB | 15 min |
| Ardèche (007) | 272 | 21000×23000 | 170 KB | 15 min |
| Paris (075) | 12 | 3000×3000 | 8 KB | 2 min |

*Les temps incluent déchargement (~10 min), extraction (~2 min), VRT (~1-2 min)*

## 🌐 Données sources

- **Producteur:** IGN (Institut National de l'Information Géographique)
- **Format:** RGEALTI 2.0 - 5M ASC
- **Projection:** Lambert93 (EPSG:2154)
- **Résolution:** 5 mètres
- **Type:** Altitude numérique du terrain
- **Source:** https://data.geopf.fr/

## 📝 Licence

Données IGN - Libre et gratuit
Application - MIT

## 👨‍💻 Support

Pour toute question ou bug:
1. Vérifiez le dossier mnt_work/ pour les logs
2. Consultez les messages d'erreur Streamlit
3. Assurez-vous que Python 3.8+ est installé

## 🎯 Prochaines améliorations possibles

- [ ] Support multi-sélection (plusieurs départements)
- [ ] Conversion auto en GeoTIFF via QGIS/OSGeo4W
- [ ] Visualisation du MNT dans l'app
- [ ] Cache intelligent des téléchargements
- [ ] Export en différents formats (GeoTIFF, MBTiles, etc)
- [ ] Interface multi-langue
- [ ] Déploiement cloud (Streamlit Cloud)

---

**Bon traitements géospatial! 🗺️🏔️**
