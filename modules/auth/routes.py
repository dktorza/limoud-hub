"""
modules/auth/routes.py — Authentification : login, logout, MFA, reset mdp.
"""

from flask import (Blueprint, render_template, redirect, url_for,
                   request, flash, session, current_app)
from flask_login import login_user, logout_user, login_required, current_user

from .models import Utilisateur
from database import audit

bp = Blueprint('auth', __name__, template_folder='templates')


# ------------------------------------------------------------------
# Middleware : changement de mot de passe forcé
# ------------------------------------------------------------------
@bp.before_app_request
def verifier_changement_mdp_requis():
    if not current_user.is_authenticated:
        return
    if not getattr(current_user, 'doit_changer_mdp', False):
        return
    # Laisser passer : la page de changement forcé, le logout, et les assets
    if request.endpoint in ('auth.changer_mdp_force', 'auth.logout', 'static'):
        return
    return redirect(url_for('auth.changer_mdp_force'))


# ------------------------------------------------------------------
# Login
# ------------------------------------------------------------------
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        mdp   = request.form.get('mot_de_passe', '')

        utilisateur = Utilisateur.get_by_email(email)

        # Vérifications de sécurité
        if not utilisateur:
            flash('Email ou mot de passe incorrect.', 'danger')
            return render_template('auth/login.html')

        if utilisateur.est_bloque():
            flash('Compte temporairement bloqué. Réessayez dans quelques minutes.', 'danger')
            audit('FAILED_LOGIN', detail=f'Compte bloqué : {email}',
                  ip_address=request.remote_addr)
            return render_template('auth/login.html')

        if not utilisateur.verifier_mot_de_passe(mdp):
            utilisateur.incrementer_echecs(
                max_tentatives=current_app.config['MAX_LOGIN_ATTEMPTS'],
                duree_blocage_min=current_app.config['LOGIN_LOCKOUT_MINUTES']
            )
            audit('FAILED_LOGIN', utilisateur_id=utilisateur.id,
                  detail='Mot de passe incorrect',
                  ip_address=request.remote_addr)
            flash('Email ou mot de passe incorrect.', 'danger')
            return render_template('auth/login.html')

        # Mot de passe OK
        if utilisateur.mfa_active:
            # Stocker l'id en session et rediriger vers MFA
            session['mfa_user_id'] = utilisateur.id
            session['mfa_next']    = request.args.get('next', url_for('dashboard'))
            return redirect(url_for('auth.mfa'))

        # Connexion directe (sans MFA)
        utilisateur.reinitialiser_echecs()
        login_user(utilisateur, remember=bool(request.form.get('remember_me')))
        audit('LOGIN', utilisateur_id=utilisateur.id,
              ip_address=request.remote_addr,
              user_agent=request.headers.get('User-Agent', '')[:200])

        next_page = request.args.get('next') or url_for('dashboard')
        return redirect(next_page)

    return render_template('auth/login.html')


# ------------------------------------------------------------------
# MFA (TOTP)
# ------------------------------------------------------------------
@bp.route('/mfa', methods=['GET', 'POST'])
def mfa():
    user_id = session.get('mfa_user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    utilisateur = Utilisateur.get_by_id(user_id)
    if not utilisateur:
        session.pop('mfa_user_id', None)
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        code = request.form.get('code_totp', '').strip()

        if utilisateur.verifier_totp(code):
            session.pop('mfa_user_id', None)
            next_page = session.pop('mfa_next', url_for('dashboard'))
            utilisateur.reinitialiser_echecs()
            login_user(utilisateur)
            audit('LOGIN', utilisateur_id=utilisateur.id,
                  detail='MFA validé',
                  ip_address=request.remote_addr)
            return redirect(next_page)
        else:
            utilisateur.incrementer_echecs()
            flash('Code incorrect. Vérifiez votre application d\'authentification.', 'danger')

    return render_template('auth/mfa.html', utilisateur=utilisateur)


# ------------------------------------------------------------------
# Logout
# ------------------------------------------------------------------
@bp.route('/logout')
@login_required
def logout():
    audit('LOGOUT', utilisateur_id=current_user.id,
          ip_address=request.remote_addr)
    logout_user()
    flash('Vous êtes déconnecté.', 'info')
    return redirect(url_for('auth.login'))


# ------------------------------------------------------------------
# Mot de passe oublié — étape 1 : demande de réinitialisation
# ------------------------------------------------------------------
@bp.route('/mot-de-passe-oublie', methods=['GET', 'POST'])
def mot_de_passe_oublie():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        utilisateur = Utilisateur.get_by_email(email)

        # On affiche toujours le même message pour ne pas révéler
        # si l'email existe ou non (sécurité)
        if utilisateur:
            token = utilisateur.generer_token_reinit()
            _envoyer_email_reinit(utilisateur, token)
            audit('PASSWORD_RESET_REQUEST', utilisateur_id=utilisateur.id,
                  ip_address=request.remote_addr)

        flash('Si cet email existe, vous recevrez un lien de réinitialisation.', 'info')
        return redirect(url_for('auth.login'))

    return render_template('auth/mot_de_passe_oublie.html')


# ------------------------------------------------------------------
# Mot de passe oublié — étape 2 : formulaire nouveau mot de passe
# ------------------------------------------------------------------
@bp.route('/reinitialiser-mot-de-passe/<token>', methods=['GET', 'POST'])
def reinitialiser_mot_de_passe(token):
    utilisateur = Utilisateur.verifier_token_reinit(token)

    if not utilisateur:
        flash('Ce lien est invalide ou a expiré.', 'danger')
        return redirect(url_for('auth.mot_de_passe_oublie'))

    if request.method == 'POST':
        nouveau_mdp    = request.form.get('nouveau_mdp', '')
        confirmation   = request.form.get('confirmation_mdp', '')

        erreurs = _valider_mot_de_passe(nouveau_mdp, confirmation)
        if erreurs:
            for erreur in erreurs:
                flash(erreur, 'danger')
            return render_template('auth/reinitialiser_mot_de_passe.html', token=token)

        utilisateur.changer_mot_de_passe(nouveau_mdp)
        audit('PASSWORD_CHANGED', utilisateur_id=utilisateur.id,
              ip_address=request.remote_addr)
        flash('Mot de passe modifié avec succès. Vous pouvez vous connecter.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/reinitialiser_mot_de_passe.html', token=token)


# ------------------------------------------------------------------
# Profil — changer son mot de passe (utilisateur connecté)
# ------------------------------------------------------------------
@bp.route('/changer-mot-de-passe', methods=['GET', 'POST'])
@login_required
def changer_mot_de_passe():
    if request.method == 'POST':
        mdp_actuel = request.form.get('mdp_actuel', '')
        nouveau    = request.form.get('nouveau_mdp', '')
        confirm    = request.form.get('confirmation_mdp', '')

        if not current_user.verifier_mot_de_passe(mdp_actuel):
            flash('Mot de passe actuel incorrect.', 'danger')
            return render_template('auth/changer_mot_de_passe.html')

        erreurs = _valider_mot_de_passe(nouveau, confirm)
        if erreurs:
            for erreur in erreurs:
                flash(erreur, 'danger')
            return render_template('auth/changer_mot_de_passe.html')

        current_user.changer_mot_de_passe(nouveau)
        audit('PASSWORD_CHANGED', utilisateur_id=current_user.id,
              ip_address=request.remote_addr)
        flash('Mot de passe modifié avec succès.', 'success')
        return redirect(url_for('dashboard'))

    return render_template('auth/changer_mot_de_passe.html')


# ------------------------------------------------------------------
# Changement de mot de passe forcé (première connexion)
# ------------------------------------------------------------------
@bp.route('/changer-mdp-force', methods=['GET', 'POST'])
@login_required
def changer_mdp_force():
    if request.method == 'POST':
        nouveau  = request.form.get('nouveau_mdp', '')
        confirm  = request.form.get('confirmation_mdp', '')
        erreurs  = _valider_mot_de_passe(nouveau, confirm)
        if erreurs:
            for erreur in erreurs:
                flash(erreur, 'danger')
            return render_template('auth/changer_mdp_force.html')
        current_user.changer_mot_de_passe(nouveau)
        audit('PASSWORD_CHANGED', utilisateur_id=current_user.id,
              detail='Premier changement de mot de passe obligatoire',
              ip_address=request.remote_addr)
        flash('Mot de passe défini avec succès. Bienvenue !', 'success')
        return redirect(url_for('dashboard'))
    return render_template('auth/changer_mdp_force.html')


# ------------------------------------------------------------------
# Helpers privés
# ------------------------------------------------------------------
def _valider_mot_de_passe(mdp, confirmation):
    erreurs = []
    if len(mdp) < 8:
        erreurs.append('Le mot de passe doit contenir au moins 8 caractères.')
    if mdp != confirmation:
        erreurs.append('Les deux mots de passe ne correspondent pas.')
    return erreurs


def _envoyer_email_reinit(utilisateur, token):
    """Envoie l'email de réinitialisation."""
    try:
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        lien = url_for('auth.reinitialiser_mot_de_passe',
                       token=token, _external=True)

        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Limoud Hub — Réinitialisation de votre mot de passe'
        msg['From']    = current_app.config['MAIL_FROM']
        msg['To']      = utilisateur.email

        html = render_template('auth/email_reinit_mdp.html',
                               utilisateur=utilisateur, lien=lien)
        texte = f"""Bonjour {utilisateur.prenom},

Vous avez demandé la réinitialisation de votre mot de passe Limoud Hub.

Cliquez sur ce lien (valable 1 heure) :
{lien}

Si vous n'avez pas fait cette demande, ignorez cet email.

L'équipe Limoud
"""
        msg.attach(MIMEText(texte, 'plain', 'utf-8'))
        msg.attach(MIMEText(html, 'html', 'utf-8'))

        with smtplib.SMTP_SSL(
            current_app.config['MAIL_SERVER'],
            current_app.config['MAIL_PORT']
        ) as server:
            server.login(
                current_app.config['MAIL_USERNAME'],
                current_app.config['MAIL_PASSWORD']
            )
            server.sendmail(
                current_app.config['MAIL_FROM'],
                utilisateur.email,
                msg.as_string()
            )
    except Exception as e:
        current_app.logger.error(f"Erreur envoi email réinitialisation : {e}")
