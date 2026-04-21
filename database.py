"""
database.py — Gestion de la connexion SQLite et utilitaires de base.
Toutes les interactions avec la BDD passent par ce module.
"""

import sqlite3
import os
from flask import g, current_app


def get_db():
    """Retourne la connexion SQLite pour la requête en cours (via Flask g)."""
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE_PATH'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row   # accès par nom de colonne
        g.db.execute("PRAGMA foreign_keys = ON")
        g.db.execute("PRAGMA journal_mode = WAL")
    return g.db


def close_db(e=None):
    """Ferme la connexion en fin de requête."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db(app):
    """Crée les tables si elles n'existent pas (appel au démarrage)."""
    migrations_dir = os.path.join(os.path.dirname(__file__), 'migrations')
    
    with app.app_context():
        db = get_db()
        
        # Lire et exécuter toutes les migrations dans l'ordre
        migration_files = sorted([
            f for f in os.listdir(migrations_dir)
            if f.endswith('.sql')
        ])
        
        for filename in migration_files:
            filepath = os.path.join(migrations_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                sql = f.read()
            try:
                db.executescript(sql)
                print(f"✓ Migration appliquée : {filename}")
            except sqlite3.Error as e:
                print(f"⚠ Migration {filename} : {e}")
        
        db.commit()


# ---------------------------------------------------------------------------
# Helpers génériques
# ---------------------------------------------------------------------------

def query(sql, params=(), one=False):
    """
    Execute une requête SELECT.
    - one=True  → retourne une seule ligne (ou None)
    - one=False → retourne une liste de lignes
    """
    cur = get_db().execute(sql, params)
    result = cur.fetchone() if one else cur.fetchall()
    return result


def execute(sql, params=()):
    """
    Execute une requête INSERT / UPDATE / DELETE.
    Retourne le cursor (pour lastrowid, rowcount...).
    Commit automatique.
    """
    db = get_db()
    cur = db.execute(sql, params)
    db.commit()
    return cur


def insert(table, data: dict):
    """
    Insère un dict dans une table.
    Retourne l'id de la ligne créée.
    
    Exemple :
        insert('intervenants', {'nom': 'Halber', 'prenom': 'Rose'})
    """
    if not data:
        raise ValueError("data ne peut pas être vide")
    
    colonnes = ', '.join(data.keys())
    placeholders = ', '.join(['?' for _ in data])
    sql = f"INSERT INTO {table} ({colonnes}) VALUES ({placeholders})"
    cur = execute(sql, list(data.values()))
    return cur.lastrowid


def update(table, data: dict, where_clause: str, where_params=()):
    """
    Met à jour une table.
    
    Exemple :
        update('intervenants', {'nom': 'Halber'}, 'id = ?', (42,))
    """
    if not data:
        raise ValueError("data ne peut pas être vide")
    
    # Ajoute updated_at automatiquement si la table en a un
    if 'updated_at' not in data:
        data = {**data, 'updated_at': "datetime('now')"}
        set_clause = ', '.join([
            f"{k} = {v}" if k == 'updated_at' else f"{k} = ?"
            for k, v in data.items()
        ])
        values = [v for k, v in data.items() if k != 'updated_at']
    else:
        set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
        values = list(data.values())
    
    sql = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
    cur = execute(sql, values + list(where_params))
    return cur.rowcount


def row_to_dict(row):
    """Convertit un sqlite3.Row en dict classique."""
    if row is None:
        return None
    return dict(row)


def rows_to_list(rows):
    """Convertit une liste de sqlite3.Row en liste de dicts."""
    return [dict(row) for row in rows]


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

def audit(action, entite=None, entite_id=None, champ=None,
          ancienne_valeur=None, nouvelle_valeur=None,
          detail=None, utilisateur_id=None,
          organisation_id=None, edition_id=None,
          ip_address=None, user_agent=None):
    """
    Enregistre une action dans l'audit log.
    NE JAMAIS modifier ou supprimer des entrées d'audit.
    """
    try:
        db = get_db()
        db.execute("""
            INSERT INTO audit_log
            (utilisateur_id, organisation_id, edition_id, action,
             entite, entite_id, champ_modifie, ancienne_valeur,
             nouvelle_valeur, ip_address, user_agent, detail)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (utilisateur_id, organisation_id, edition_id, action,
              entite, entite_id, champ,
              str(ancienne_valeur) if ancienne_valeur is not None else None,
              str(nouvelle_valeur) if nouvelle_valeur is not None else None,
              ip_address, user_agent, detail))
        db.commit()
    except Exception as e:
        # L'audit ne doit jamais bloquer l'application
        current_app.logger.error(f"Erreur audit_log : {e}")
