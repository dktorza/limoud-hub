#!/usr/bin/env python3
"""
scripts/setup.py — Installation initiale de Limoud Hub.

Lance ce script UNE SEULE FOIS après le premier déploiement pour :
  1. Créer la base de données et toutes les tables
  2. Créer l'organisation Limoud Paris
  3. Créer le premier compte super administrateur
  4. Créer les dossiers de données nécessaires

Usage :
    python3 scripts/setup.py
"""

import os
import sys

# Ajouter le dossier parent au path pour importer app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from werkzeug.security import generate_password_hash


def setup():
    print("=" * 60)
    print("  Limoud Hub — Installation initiale")
    print("=" * 60)

    # ------------------------------------------------------------------
    # Créer les dossiers de données
    # ------------------------------------------------------------------
    dossiers = ['data', 'data/uploads', 'data/badges', 'data/livrets',
                'data/uploads/intervenants', 'data/uploads/editions']
    for d in dossiers:
        os.makedirs(d, exist_ok=True)
        print(f"✓ Dossier créé : {d}")

    # ------------------------------------------------------------------
    # Initialiser l'app Flask et la BDD
    # ------------------------------------------------------------------
    from app import create_app
    app = create_app('development')

    with app.app_context():
        from database import get_db, execute, query

        # Vérifier si déjà installé
        existing = query("SELECT COUNT(*) as n FROM utilisateurs", one=True)
        if existing and existing['n'] > 0:
            print("\n⚠ La base de données contient déjà des utilisateurs.")
            rep = input("Voulez-vous quand même créer un super admin ? (o/N) : ")
            if rep.lower() != 'o':
                print("Installation annulée.")
                return

        # ------------------------------------------------------------------
        # Créer l'organisation Limoud Paris
        # ------------------------------------------------------------------
        org_existante = query(
            "SELECT id FROM organisations WHERE slug = ?",
            ('limoud-paris',), one=True
        )
        if not org_existante:
            execute("""
                INSERT INTO organisations (nom, slug, ville, email_contact, site_web)
                VALUES (?, ?, ?, ?, ?)
            """, ('Limoud Paris', 'limoud-paris', 'Paris',
                  'contact@limoud.org', 'https://limoud.org'))
            print("✓ Organisation 'Limoud Paris' créée")
        else:
            print("→ Organisation 'Limoud Paris' existe déjà")

        # ------------------------------------------------------------------
        # Créer le premier super admin
        # ------------------------------------------------------------------
        print("\n--- Création du compte super administrateur ---")

        prenom = input("Prénom : ").strip()
        nom    = input("Nom    : ").strip()
        email  = input("Email  : ").strip().lower()

        mdp1 = input_mdp("Mot de passe (min 8 caractères) : ")
        mdp2 = input_mdp("Confirmez le mot de passe       : ")

        if mdp1 != mdp2:
            print("✗ Les mots de passe ne correspondent pas.")
            return

        if len(mdp1) < 8:
            print("✗ Le mot de passe doit contenir au moins 8 caractères.")
            return

        # Vérifier que l'email n'existe pas déjà
        existant = query(
            "SELECT id FROM utilisateurs WHERE email = ?", (email,), one=True
        )
        if existant:
            print(f"✗ Un compte avec l'email '{email}' existe déjà.")
            return

        # Créer l'utilisateur
        execute("""
            INSERT INTO utilisateurs (email, password_hash, nom, prenom, actif)
            VALUES (?, ?, ?, ?, 1)
        """, (email, generate_password_hash(mdp1), nom, prenom))

        user = query(
            "SELECT id FROM utilisateurs WHERE email = ?", (email,), one=True
        )
        user_id = user['id']

        # Attribuer le rôle super_admin
        execute("""
            INSERT INTO utilisateur_roles
            (utilisateur_id, role_code, organisation_id, edition_id, actif)
            VALUES (?, 'super_admin', NULL, NULL, 1)
        """, (user_id,))

        print(f"\n✓ Super administrateur créé : {prenom} {nom} <{email}>")

        # ------------------------------------------------------------------
        # Résumé
        # ------------------------------------------------------------------
        print("\n" + "=" * 60)
        print("  Installation terminée avec succès !")
        print("=" * 60)
        print(f"\n  → Connectez-vous sur https://intranet.limoud.org")
        print(f"  → Email    : {email}")
        print(f"  → Mot de passe : celui que vous venez de définir")
        print()
        print("  Prochaines étapes :")
        print("  1. Configurer une édition dans Admin → Éditions")
        print("  2. Configurer les formulaires HelloAsso")
        print("  3. Inviter les autres membres de l'équipe")
        print()


def input_mdp(prompt):
    """Saisie de mot de passe (masqué si possible)."""
    try:
        import getpass
        return getpass.getpass(prompt)
    except Exception:
        return input(prompt)


if __name__ == '__main__':
    setup()
