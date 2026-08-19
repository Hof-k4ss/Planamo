# PLANAMO — Documentation

Ce dossier contient la documentation de PLANAMO.

## Structure

```
documentation/
├── docs/
│   ├── extra/          ← Pages manuelles HTML (remnux.html, mobsf.html, etc.)
│   └── themes/         ← Générées automatiquement depuis tools_map.conf
├── assets/
│   └── css/
│       └── custom.css  ← Thème PLANAMO (vert Android + style Apple)
└── README.md
```

## Ajouter une page manuelle

1. Créer un fichier HTML dans `docs/extra/` (ex: `mon-outil.html`)
2. Il apparaîtra automatiquement dans la section **Guides** du menu
3. Rebuilder l'ISO ou copier manuellement dans `/opt/planamo/docs/site/extra/`

## Modifier le thème

Éditer `assets/css/custom.css` — pris en compte au prochain build.

## Mise à jour sans rebuild ISO

Sur un système PLANAMO installé :
```bash
sudo cp documentation/docs/extra/*.html /opt/planamo/docs/site/extra/
```
