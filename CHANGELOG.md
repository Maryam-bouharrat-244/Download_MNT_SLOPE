# Changelog

Tous les changements notables de ce projet sont documentés dans ce fichier.

## [1.0.0] - 2026-03-13

### ✨ Fonctionnalités

- **Application Streamlit complète** pour téléchargement et génération de MNT
- **Mode Simple** : Traiter un département individuellement
- **Mode Batch** : Traiter plusieurs ou tous les départements automatiquement
- **Calcul des pentes** :
  - Pentes complètes (valeurs continues en %)
  - Pentes > 5% (raster binaire)
  - Pentes > 10% (raster binaire)
- **Export automatique en GeoTIFF**
- **Validation d'intégrité** :
  - Vérification des téléchargements
  - Comparaison VRT ↔ TIFF
  - Statistiques détaillées
- **Logs détaillés** pour suivi et débogage
- **Configuration GDAL auto-détectée** (QGIS)
- **Gestion des erreurs et retry automatiques**

### 🔧 Composants principaux

- `mnt_app.py` : Application Streamlit principale
- `batch_processor.py` : Processeur pour traitement batch
- `convert_vrt_to_geotiff.py` : Conversion VRT vers TIFF avec gdaldem
- `validate_all_mnt.py` : Validation complète des fichiers
- `config.py` : Configuration commune
- `test_vrt_integrity.py` : Tests d'intégrité VRT

### 📊 Données supportées

- Format : RGEALTI 5M ASC (IGN)
- Projection : Lambert93 (EPSG:2154)
- Couverture : France métropolitaine et DROM-COM (96 départements)

### 🐛 Corrections de bugs (v1.0)

- [Fixed] Mode "Départements manquants" corrigé pour exécuter les deux calculs de pente (> 5% et > 10%)
- [Cleaned] Suppression du mode "Départements manquants" pour simplifier l'interface
- [Cleaned] Nettoyage des imports Python en doublon

### 📝 Documentation

- `README.md` : Guide installation et utilisation
- `README_APP.md` : Guide utilisateur détaillé
- `GUIDE_VALIDATION.md` : Guide de validation
- `FIX_CORRUPTED_7Z.md` : Dépannage des fichiers 7z corrompus
- `CHANGELOG.md` : Historique des versions

---

## Prochaines améliorations (roadmap)

- [ ] Interface de configuration avancée
- [ ] Support d'autres sources de MNT
- [ ] Parallélisation améliorée
- [ ] API REST pour intégration externe
- [ ] Docker pour déploiement cloud
- [ ] Tests unitaires automatisés
- [ ] Support internationalisé

