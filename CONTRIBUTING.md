# Directives de contribution

Merci de votre intérêt pour contribuer à MNT France Generator! 

## Comment contribuer

### Signaler un bug 🐛

1. **Vérifier** que le bug n'a pas déjà été reporté sur les [Issues](../../issues)
2. **Créer une nouvelle issue** avec :
   - Description claire du problème
   - Étapes pour reproduire
   - Environnement (OS, Python version, QGIS version)
   - Logs d'erreur complets

### Proposer une amélioration ✨

1. **Discuter** de votre idée dans les [Discussions](../../discussions) avant de coder
2. **Créer une issue** avec le tag `enhancement` pour tracer les travaux
3. **Obtenir l'accord** des mainteneurs avant de commencer

### Soumettre du code 💻

1. **Fork** le repository
2. **Créer une branche** : `git checkout -b feature/my-feature`
3. **Commiter** régulièrement avec messages clairs
4. **Respecter** le code style du projet
5. **Tester** vos modifications
6. **Créer une Pull Request** avec description détaillée

## Code Style

### Python
- Respecter [PEP 8](https://pep8.org/)
- Utiliser des noms descriptifs
- Documenter avec docstrings
- Ajouter des commentaires pour la logique complexe

```python
def process_department(dept_code: str, dept_name: str) -> dict:
    """
    Process a single department to generate MNT files.
    
    Args:
        dept_code: Code du département (ex: '75')
        dept_name: Nom du département (ex: 'Paris')
    
    Returns:
        dict: Résultat du traitement avec clés 'success', 'message', etc.
    """
    pass
```

### Commits
```
[TYPE] Description courte

Description détaillée si nécessaire
- Point 1
- Point 2

Closes #123
```

Types de commits :
- `[FEATURE]` : Nouvelle fonctionnalité
- `[FIX]` : Correction de bug
- `[DOCS]` : Mise à jour documentation
- `[REFACTOR]` : Restructuration sans changer le comportement
- `[TEST]` : Ajout/mise à jour de tests
- `[CHORE]` : Maintenance, dépendances

## Tests

Avant de soumettre :
```bash
# Vérifier la syntaxe
python -m py_compile mnt_app.py

# Tester l'application
streamlit run mnt_app.py
```

## Documentation

- Mettre à jour README.md si nécessaire
- Ajouter des commentaires pour le code complexe
- Documenter les changements dans CHANGELOG.md

## Process de review

1. Au moins 1 review requis avant merge
2. Tests de CI doivent passer
3. Pas de conflicts de merge
4. Documentation à jour

## Questions ?

Créer une [Discussion](../../discussions) ou nous contacter.

Merci de votre contribution! 🙏
