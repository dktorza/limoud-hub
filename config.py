"""
config.py — Configuration de Limoud Hub.
Les valeurs sensibles (clés API, mots de passe) viennent
exclusivement du fichier .env — jamais codées en dur ici.
"""

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # -------------------------------------------------------------------
    # Sécurité Flask
    # -------------------------------------------------------------------
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'changez-moi-en-production'

    # -------------------------------------------------------------------
    # Base de données SQLite
    # -------------------------------------------------------------------
    # En production O2Switch, le fichier BDD est HORS du dossier web
    # Ex: /home/votre_compte/limoud_data/limoud.db
    DATABASE_PATH = os.environ.get('DATABASE_PATH') or os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'data', 'limoud.db'
    )

    # -------------------------------------------------------------------
    # HelloAsso API
    # -------------------------------------------------------------------
    HELLOASSO_CLIENT_ID     = os.environ.get('HELLOASSO_CLIENT_ID', '')
    HELLOASSO_CLIENT_SECRET = os.environ.get('HELLOASSO_CLIENT_SECRET', '')
    HELLOASSO_BASE_URL      = 'https://api.helloasso.com/v5'
    HELLOASSO_OAUTH_URL     = 'https://api.helloasso.com/oauth2/token'
    # Slug de l'organisation Limoud sur HelloAsso
    HELLOASSO_ORG_SLUG      = os.environ.get('HELLOASSO_ORG_SLUG', 'limoud-france')

    # -------------------------------------------------------------------
    # Email (mot de passe oublié, notifications)
    # -------------------------------------------------------------------
    MAIL_SERVER   = os.environ.get('MAIL_SERVER', 'smtp.o2switch.net')
    MAIL_PORT     = int(os.environ.get('MAIL_PORT', 465))
    MAIL_USE_SSL  = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_FROM     = os.environ.get('MAIL_FROM', 'intranet@limoud.org')

    # -------------------------------------------------------------------
    # SMS MFA (OVH SMS ou Twilio)
    # -------------------------------------------------------------------
    SMS_PROVIDER     = os.environ.get('SMS_PROVIDER', 'ovh')  # 'ovh' | 'twilio'
    OVH_APP_KEY      = os.environ.get('OVH_APP_KEY', '')
    OVH_APP_SECRET   = os.environ.get('OVH_APP_SECRET', '')
    OVH_CONSUMER_KEY = os.environ.get('OVH_CONSUMER_KEY', '')
    OVH_SMS_SERVICE  = os.environ.get('OVH_SMS_SERVICE', '')  # ex: sms-xx1234-1

    # -------------------------------------------------------------------
    # Fichiers / uploads
    # -------------------------------------------------------------------
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'data', 'uploads'
    )
    BADGE_OUTPUT_FOLDER = os.environ.get('BADGE_OUTPUT_FOLDER') or os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'data', 'badges'
    )
    LIVRET_OUTPUT_FOLDER = os.environ.get('LIVRET_OUTPUT_FOLDER') or os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'data', 'livrets'
    )
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload

    # Extensions autorisées pour les photos intervenants
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

    # -------------------------------------------------------------------
    # Application
    # -------------------------------------------------------------------
    APP_NAME     = 'Limoud Hub'
    APP_VERSION  = '0.1.0'
    DEBUG        = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'

    # Durée du token de réinitialisation de mot de passe (en secondes)
    PASSWORD_RESET_EXPIRY = 3600  # 1 heure

    # Nombre max de tentatives de connexion avant blocage
    MAX_LOGIN_ATTEMPTS = 5
    LOGIN_LOCKOUT_MINUTES = 30

    # Pagination par défaut
    ITEMS_PER_PAGE = 25


class ProductionConfig(Config):
    DEBUG = False
    # En prod, SECRET_KEY doit absolument venir du .env


class DevelopmentConfig(Config):
    DEBUG = True
    # Afficher les erreurs SQL dans la console
    SQLALCHEMY_ECHO = True


# Sélection de la config selon l'environnement
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
