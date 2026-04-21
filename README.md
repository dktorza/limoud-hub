# Limoud Hub — Intranet de l'équipe Limoud France

**Version** : 0.1.0 (skeleton)  
**URL de production** : https://intranet.limoud.org  
**Stack** : Python / Flask / SQLite / Bootstrap 5

---

## Installation sur O2Switch

### 1. Créer le sous-domaine

Dans cPanel → **Domaines** → **Sous-domaines** :
- Sous-domaine : `intranet`
- Domaine : `limoud.org`
- Dossier racine : `intranet_limoud` (créé automatiquement)

### 2. Déposer les fichiers

Via FTP ou le gestionnaire de fichiers cPanel, copiez tout le contenu
du dossier `limoud-hub/` dans le dossier du sous-domaine.

### 3. Configurer l'environnement

```bash
cd ~/intranet_limoud
cp .env.example .env
nano .env   # Remplir toutes les valeurs
```

**Variables obligatoires à renseigner :**
- `SECRET_KEY` : générez avec `python3 -c "import secrets; print(secrets.token_hex(32))"`
- `DATABASE_PATH` : chemin absolu **hors** du dossier web, ex: `/home/VOTRE_LOGIN/limoud_data/limoud.db`
- `HELLOASSO_CLIENT_ID` + `HELLOASSO_CLIENT_SECRET`
- `MAIL_USERNAME` + `MAIL_PASSWORD`

### 4. Installer les dépendances

```bash
pip3 install -r requirements.txt --break-system-packages --user
```

### 5. Initialiser la base de données et créer le premier admin

```bash
python3 scripts/setup.py
```

### 6. Configurer Passenger WSGI

Créer le fichier `passenger_wsgi.py` dans le dossier du sous-domaine :

```python
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
os.environ['FLASK_ENV'] = 'production'
from app import create_app
application = create_app('production')
```

Dans cPanel → **Configuration Python** (ou **Setup Python App**) :
- Python version : 3.11+
- Application root : `intranet_limoud`
- Application startup file : `passenger_wsgi.py`
- Application Entry point : `application`

### 7. Redémarrer l'application

```bash
touch passenger_wsgi.py
```

---

## Structure du projet

```
limoud-hub/
├── app.py                    # Factory Flask
├── config.py                 # Configuration (lit .env)
├── database.py               # Helpers SQLite
├── requirements.txt
├── .env.example              # Modèle de configuration
│
├── migrations/
│   ├── 001_initial.sql       # Schéma complet de la BDD
│   └── 002_dashboards_notifs.sql  # Widgets, notifications, scans
│
├── modules/
│   ├── auth/                 # Connexion, MFA, reset mdp
│   ├── admin/                # Utilisateurs, rôles, config
│   ├── intervenants/         # Fiches intervenants (à développer)
│   ├── sessions/             # Sessions (à développer)
│   ├── badges/               # Génération badges PDF (à développer)
│   ├── participants/         # Inscrits HelloAsso (à développer)
│   ├── helloasso/            # Synchronisation HA (à développer)
│   ├── planning/             # Grille horaire interactive (à développer)
│   └── livret/               # Génération livret PDF (à développer)
│
├── templates/
│   ├── base.html             # Layout avec sidebar
│   ├── dashboard.html        # Accueil
│   ├── auth/                 # Login, MFA, reset
│   ├── admin/                # Interface administration
│   └── shared/               # 403, 404, 500
│
├── static/
│   ├── css/
│   ├── js/
│   └── img/
│
└── scripts/
    └── setup.py              # Installation initiale
```

---

## Ordre de développement prévu

| Étape | Module | Description |
|-------|--------|-------------|
| ✅ 1 | Skeleton | Structure, BDD, auth |
| 🔲 2 | Admin | Utilisateurs, rôles, permissions |
| 🔲 3 | Intervenants | CRUD fiches, historique éditions |
| 🔲 4 | HelloAsso | Synchronisation inscriptions |
| 🔲 5 | Participants | Dashboard par rôle métier |
| 🔲 6 | Badges | Génération PDF, scan accueil |
| 🔲 7 | Sessions | CRUD sessions, lien formulaire intervenant |
| 🔲 8 | Planning | Grille interactive drag & drop |
| 🔲 9 | Livret | Génération PDF automatique |

---

## Concept des dashboards contextuels

Chaque rôle voit sur sa page d'accueil uniquement les informations
dont il a besoin, sous forme de **widgets** :

| Rôle | Widgets affichés |
|------|-----------------|
| Resp. transports | Liste participants avec transport, contact direct SMS/email |
| Resp. accueil | Scan temps réel, badges à imprimer |
| Resp. intervenants | Intervenants à confirmer, présents/absents |
| Resp. planning | Sessions non planifiées, grille |
| Resp. traiteur | Contraintes alimentaires |
| Resp. hôtel | Chomer Chabbat, types de chambres |
| Admin édition | Vue synthétique de tout |

Les widgets sont configurables par l'admin via **Admin → Dashboards**.

---

## Système de permissions (granularité fine)

```
Rôle → Permissions → Module + Action + Champ optionnel
```

Exemple :
- `lecteur_intervenants` peut `voir_fiche` sur `intervenants`
- MAIS ne peut **pas** voir le champ `tel_mobile` (règle de refus explicite)
- `resp_intervenants` peut voir ET modifier tous les champs

Configuration via **Admin → Rôles → Permissions**.

---

## API HelloAsso utilisée

Base URL : `https://api.helloasso.com/v5`

Endpoints utilisés :
- `GET /organizations/{slug}/forms` — liste des formulaires
- `GET /organizations/{slug}/forms/{slug}/items` — billets par formulaire
- `GET /organizations/{slug}/orders` — commandes

Chaque formulaire HelloAsso est mappé dans `formulaires_ha`
avec son type (WE 4 étoiles, dimanche, bénévole, navette...).
La synchro peut être lancée manuellement ou planifiée via cron.

---

## Contact technique

Denis Ktorza — Président Limoud France / DSI ACIP
