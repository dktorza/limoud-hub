"""
modules/auth/models.py — Modèle Utilisateur pour Flask-Login.
"""

from flask_login import UserMixin
from database import query, execute, row_to_dict, audit
from werkzeug.security import generate_password_hash, check_password_hash
import pyotp
import secrets
from datetime import datetime, timedelta


class Utilisateur(UserMixin):
    """
    Représente un utilisateur connecté.
    Flask-Login appelle get_id() pour stocker l'id en session.
    """

    def __init__(self, row):
        d = dict(row)
        self.id             = d['id']
        self.email          = d['email']
        self.nom            = d['nom']
        self.prenom         = d['prenom']
        self.telephone      = d.get('telephone')
        self.actif          = bool(d.get('actif', 1))
        self.mfa_active     = bool(d.get('mfa_active', 0))
        self.mfa_secret     = d.get('mfa_secret')
        self.mfa_telephone  = d.get('mfa_telephone')
        self.nb_echecs      = d.get('nb_echecs_connexion', 0)
        self.bloque_jusqu_a = d.get('bloque_jusqu_a')

    # ------------------------------------------------------------------
    # Flask-Login requis
    # ------------------------------------------------------------------
    def get_id(self):
        return str(self.id)

    @property
    def is_active(self):
        return self.actif

    @property
    def nom_complet(self):
        return f"{self.prenom} {self.nom}"

    # ------------------------------------------------------------------
    # Récupération depuis la BDD
    # ------------------------------------------------------------------
    @classmethod
    def get_by_id(cls, user_id):
        row = query("SELECT * FROM utilisateurs WHERE id = ?", (user_id,), one=True)
        return cls(row) if row else None

    @classmethod
    def get_by_email(cls, email):
        row = query(
            "SELECT * FROM utilisateurs WHERE email = ? AND actif = 1",
            (email.strip().lower(),), one=True
        )
        return cls(row) if row else None

    # ------------------------------------------------------------------
    # Authentification
    # ------------------------------------------------------------------
    def verifier_mot_de_passe(self, mot_de_passe):
        row = query("SELECT password_hash FROM utilisateurs WHERE id = ?",
                    (self.id,), one=True)
        if not row:
            return False
        return check_password_hash(row['password_hash'], mot_de_passe)

    def verifier_totp(self, code_totp):
        """Vérifie un code TOTP (Google Authenticator)."""
        if not self.mfa_secret:
            return False
        totp = pyotp.TOTP(self.mfa_secret)
        return totp.verify(code_totp, valid_window=1)

    def est_bloque(self):
        """Vérifie si le compte est temporairement bloqué."""
        if not self.bloque_jusqu_a:
            return False
        return datetime.now() < datetime.fromisoformat(self.bloque_jusqu_a)

    def incrementer_echecs(self, max_tentatives=5, duree_blocage_min=30):
        """Incrémente le compteur d'échecs, bloque si nécessaire."""
        nouveaux_echecs = self.nb_echecs + 1
        bloque_jusqu_a = None

        if nouveaux_echecs >= max_tentatives:
            bloque_jusqu_a = (
                datetime.now() + timedelta(minutes=duree_blocage_min)
            ).isoformat()

        execute("""
            UPDATE utilisateurs
            SET nb_echecs_connexion = ?,
                bloque_jusqu_a = ?,
                updated_at = datetime('now')
            WHERE id = ?
        """, (nouveaux_echecs, bloque_jusqu_a, self.id))

    def reinitialiser_echecs(self):
        """Réinitialise le compteur d'échecs après connexion réussie."""
        execute("""
            UPDATE utilisateurs
            SET nb_echecs_connexion = 0,
                bloque_jusqu_a = NULL,
                derniere_connexion_at = datetime('now'),
                updated_at = datetime('now')
            WHERE id = ?
        """, (self.id,))

    # ------------------------------------------------------------------
    # Réinitialisation du mot de passe
    # ------------------------------------------------------------------
    def generer_token_reinit(self):
        """Génère un token de réinitialisation (valable 1h)."""
        token = secrets.token_urlsafe(32)
        expiry = (datetime.now() + timedelta(hours=1)).isoformat()
        execute("""
            UPDATE utilisateurs
            SET token_reinit_mdp = ?, token_reinit_expiry = ?
            WHERE id = ?
        """, (token, expiry, self.id))
        return token

    @classmethod
    def verifier_token_reinit(cls, token):
        """Retourne l'utilisateur si le token est valide, None sinon."""
        row = query("""
            SELECT * FROM utilisateurs
            WHERE token_reinit_mdp = ?
            AND token_reinit_expiry > datetime('now')
            AND actif = 1
        """, (token,), one=True)
        return cls(row) if row else None

    def changer_mot_de_passe(self, nouveau_mdp):
        """Change le mot de passe et invalide le token."""
        execute("""
            UPDATE utilisateurs
            SET password_hash = ?,
                token_reinit_mdp = NULL,
                token_reinit_expiry = NULL,
                nb_echecs_connexion = 0,
                bloque_jusqu_a = NULL,
                updated_at = datetime('now')
            WHERE id = ?
        """, (generate_password_hash(nouveau_mdp), self.id))

    # ------------------------------------------------------------------
    # Permissions
    # ------------------------------------------------------------------
    def a_permission(self, module, action, champ=None,
                     organisation_id=None, edition_id=None):
        """
        Vérifie si l'utilisateur a le droit d'effectuer une action.
        
        Logique :
        1. Récupère tous les rôles actifs de l'utilisateur pour cette
           organisation/édition (ou globaux)
        2. Pour chacun, vérifie la table permissions
        3. Un seul rôle qui autorise suffit (union des droits)
        4. Un refus explicite (autorise=0) sur un champ spécifique
           prend le dessus sur une autorisation générale
        
        Principe : par défaut tout est REFUSÉ.
        """
        # Super admin a toujours tout
        if self._a_role('super_admin', organisation_id, edition_id):
            return True

        roles = self._get_roles_actifs(organisation_id, edition_id)
        if not roles:
            return False

        role_codes = [r['role_code'] for r in roles]
        placeholders = ','.join('?' * len(role_codes))

        if champ:
            # Vérification avec champ spécifique :
            # Si une règle de champ existe, elle prime sur la règle générale
            row = query(f"""
                SELECT autorise FROM permissions
                WHERE role_code IN ({placeholders})
                AND module = ? AND action = ? AND champ = ?
                ORDER BY autorise DESC
                LIMIT 1
            """, role_codes + [module, action, champ], one=True)

            if row:
                return bool(row['autorise'])

            # Pas de règle spécifique au champ → vérifie la règle générale
            row = query(f"""
                SELECT autorise FROM permissions
                WHERE role_code IN ({placeholders})
                AND module = ? AND action = ? AND champ IS NULL
                ORDER BY autorise DESC
                LIMIT 1
            """, role_codes + [module, action], one=True)
            return bool(row['autorise']) if row else False
        else:
            # Vérification sans champ
            row = query(f"""
                SELECT autorise FROM permissions
                WHERE role_code IN ({placeholders})
                AND module = ? AND action = ? AND champ IS NULL
                ORDER BY autorise DESC
                LIMIT 1
            """, role_codes + [module, action], one=True)
            return bool(row['autorise']) if row else False

    def _a_role(self, role_code, organisation_id=None, edition_id=None):
        """Vérifie si l'utilisateur a un rôle spécifique."""
        roles = self._get_roles_actifs(organisation_id, edition_id)
        return any(r['role_code'] == role_code for r in roles)

    def _get_roles_actifs(self, organisation_id=None, edition_id=None):
        """Retourne tous les rôles actifs et non expirés pour ce contexte."""
        return query("""
            SELECT role_code FROM utilisateur_roles
            WHERE utilisateur_id = ?
            AND actif = 1
            AND (expire_le IS NULL OR expire_le > datetime('now'))
            AND (organisation_id IS NULL OR organisation_id = ?)
            AND (edition_id IS NULL OR edition_id = ?)
        """, (self.id,
              organisation_id or -1,
              edition_id or -1))

    def get_roles(self, organisation_id=None, edition_id=None):
        """Retourne la liste des rôles de l'utilisateur (pour affichage)."""
        return query("""
            SELECT ur.*, r.libelle, r.couleur_hex
            FROM utilisateur_roles ur
            JOIN roles r ON r.code = ur.role_code
            WHERE ur.utilisateur_id = ?
            AND ur.actif = 1
            AND (ur.expire_le IS NULL OR ur.expire_le > datetime('now'))
        """, (self.id,))

    # ------------------------------------------------------------------
    # Création
    # ------------------------------------------------------------------
    @staticmethod
    def creer(email, mot_de_passe, nom, prenom, telephone=None):
        """Crée un nouvel utilisateur. Retourne son id."""
        from database import insert
        return insert('utilisateurs', {
            'email':         email.strip().lower(),
            'password_hash': generate_password_hash(mot_de_passe),
            'nom':           nom.strip(),
            'prenom':        prenom.strip(),
            'telephone':     telephone,
            'actif':         1,
        })
