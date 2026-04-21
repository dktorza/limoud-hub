"""
app.py — Point d'entrée de Limoud Hub.
"""

import os
from flask import Flask, render_template, redirect, url_for
from flask_login import LoginManager, current_user

from config import config
from database import close_db, init_db


def create_app(env=None):
    """Factory Flask — crée et configure l'application."""

    env = env or os.environ.get('FLASK_ENV', 'development')
    app = Flask(__name__)
    app.config.from_object(config.get(env, config['default']))

    # ------------------------------------------------------------------
    # Dossiers de données (création si absent)
    # ------------------------------------------------------------------
    for folder in [
        os.path.dirname(app.config['DATABASE_PATH']),
        app.config['UPLOAD_FOLDER'],
        app.config['BADGE_OUTPUT_FOLDER'],
        app.config['LIVRET_OUTPUT_FOLDER'],
    ]:
        os.makedirs(folder, exist_ok=True)

    # ------------------------------------------------------------------
    # Base de données
    # ------------------------------------------------------------------
    app.teardown_appcontext(close_db)
    init_db(app)

    # ------------------------------------------------------------------
    # Flask-Login
    # ------------------------------------------------------------------
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        from modules.auth.models import Utilisateur
        return Utilisateur.get_by_id(int(user_id))

    # ------------------------------------------------------------------
    # Blueprints (modules)
    # ------------------------------------------------------------------
    from modules.auth.routes         import bp as auth_bp
    from modules.admin.routes        import bp as admin_bp
    from modules.intervenants.routes import bp as intervenants_bp
    from modules.sessions.routes     import bp as sessions_bp
    from modules.badges.routes       import bp as badges_bp
    from modules.participants.routes import bp as participants_bp
    from modules.helloasso.routes    import bp as helloasso_bp
    from modules.planning.routes     import bp as planning_bp
    from modules.livret.routes       import bp as livret_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp,        url_prefix='/admin')
    app.register_blueprint(intervenants_bp, url_prefix='/intervenants')
    app.register_blueprint(sessions_bp,     url_prefix='/sessions')
    app.register_blueprint(badges_bp,       url_prefix='/badges')
    app.register_blueprint(participants_bp, url_prefix='/participants')
    app.register_blueprint(helloasso_bp,    url_prefix='/helloasso')
    app.register_blueprint(planning_bp,     url_prefix='/planning')
    app.register_blueprint(livret_bp,       url_prefix='/livret')

    # ------------------------------------------------------------------
    # Filtres Jinja2 utiles
    # ------------------------------------------------------------------
    @app.template_filter('date_fr')
    def date_fr(value):
        """Formate une date ISO en format français."""
        if not value:
            return ''
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(str(value))
            mois = ['', 'janvier', 'février', 'mars', 'avril', 'mai', 'juin',
                    'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']
            return f"{dt.day} {mois[dt.month]} {dt.year}"
        except Exception:
            return str(value)

    @app.template_filter('heure_fr')
    def heure_fr(value):
        """Formate une heure HH:MM."""
        if not value:
            return ''
        return str(value)[:5]

    @app.template_filter('oui_non')
    def oui_non(value):
        return 'Oui' if value else 'Non'

    # ------------------------------------------------------------------
    # Contexte global pour tous les templates
    # ------------------------------------------------------------------
    @app.context_processor
    def inject_globals():
        edition_courante = None
        if current_user.is_authenticated:
            # Récupère l'édition "active" pour l'afficher dans la nav
            from database import query
            edition_courante = query(
                """SELECT e.* FROM editions e
                   JOIN ref_statuts_edition s ON e.statut_code = s.code
                   WHERE s.est_actif_defaut = 0 AND e.statut_code != 'archivee'
                   ORDER BY e.date_debut DESC LIMIT 1""",
                one=True
            )
        return {
            'app_name': app.config['APP_NAME'],
            'edition_courante': edition_courante,
        }

    # ------------------------------------------------------------------
    # Routes racine
    # ------------------------------------------------------------------
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return redirect(url_for('auth.login'))

    @app.route('/dashboard')
    def dashboard():
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        from database import query as db_query
        widgets = db_query("""
            SELECT DISTINCT dw.code, dw.titre, dw.icone, drw.taille, drw.ordre
            FROM dashboard_roles_widgets drw
            JOIN dashboard_widgets dw ON dw.code = drw.widget_code
            WHERE drw.actif = 1 AND dw.actif = 1
              AND drw.role_code IN (
                  SELECT role_code FROM utilisateur_roles
                  WHERE utilisateur_id = ? AND actif = 1
                    AND (expire_le IS NULL OR expire_le > datetime('now'))
              )
            ORDER BY drw.ordre
        """, (current_user.id,))
        return render_template('dashboard.html', widgets=widgets)

    # ------------------------------------------------------------------
    # Gestion des erreurs
    # ------------------------------------------------------------------
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('shared/403.html'), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template('shared/404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template('shared/500.html'), 500

    return app


# ------------------------------------------------------------------
# Point d'entrée direct (dev local)
# ------------------------------------------------------------------
if __name__ == '__main__':
    app = create_app('development')
    app.run(debug=True, host='0.0.0.0', port=5001)
