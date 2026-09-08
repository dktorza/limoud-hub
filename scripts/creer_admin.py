"""
Création ou réinitialisation d'un compte super_admin.
Aucun secret en dur : email et mot de passe sont demandés au clavier.

Usage (sur le serveur, virtualenv activé, depuis la racine du projet) :
    python3 scripts/creer_admin.py
"""
import sys, os, getpass

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
os.chdir(RACINE)

from app import create_app
from werkzeug.security import generate_password_hash
from database import get_db

email  = input("Email : ").strip()
nom    = input("Nom : ").strip()
prenom = input("Prénom : ").strip()
mdp    = getpass.getpass("Mot de passe : ")
if mdp != getpass.getpass("Confirmer le mot de passe : "):
    sys.exit("Les mots de passe ne correspondent pas.")

app = create_app('production')
with app.app_context():
    db = get_db()
    db.execute(
        "INSERT OR IGNORE INTO organisations (nom, slug, ville) VALUES (?, ?, ?)",
        ('Limoud Paris', 'limoud-paris', 'Paris'),
    )
    existant = db.execute("SELECT id FROM utilisateurs WHERE email = ?", (email,)).fetchone()
    if existant:
        db.execute(
            "UPDATE utilisateurs SET password_hash=?, nom=?, prenom=?, actif=1, "
            "mfa_active=0, mfa_secret=NULL, nb_echecs_connexion=0, bloque_jusqu_a=NULL WHERE id=?",
            (generate_password_hash(mdp), nom, prenom, existant['id']),
        )
        uid = existant['id']
        action = "réinitialisé"
    else:
        db.execute(
            "INSERT INTO utilisateurs (email, password_hash, nom, prenom, actif) VALUES (?, ?, ?, ?, 1)",
            (email, generate_password_hash(mdp), nom, prenom),
        )
        uid = db.execute("SELECT id FROM utilisateurs WHERE email = ?", (email,)).fetchone()['id']
        action = "créé"
    db.execute(
        "INSERT OR IGNORE INTO utilisateur_roles (utilisateur_id, role_code, actif) VALUES (?, 'super_admin', 1)",
        (uid,),
    )
    db.commit()
    print(f"Compte {action} (ID {uid}), rôle super_admin, MFA désactivé.")
