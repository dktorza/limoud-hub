"""
modules/intervenants/routes.py
Liste, fiche, création, modification des intervenants.
Lié aux sessions et aux participations par édition.
"""
from flask import (Blueprint, render_template, redirect, url_for,
                   request, flash, session as flask_session, jsonify)
from flask_login import login_required, current_user
from database import query, execute, insert, row_to_dict, audit

bp = Blueprint('intervenants', __name__, template_folder='templates')

_ALLOWED_PHOTO_EXTS = {'jpg', 'jpeg', 'png', 'webp'}
_MAX_PHOTO_BYTES = 5 * 1024 * 1024  # 5 MB


def _save_photo(file, iid):
    """
    Sauvegarde la photo uploadée pour l'intervenant iid.
    Retourne (chemin_relatif, None) ou (None, message_erreur).
    """
    import os
    from flask import current_app

    if not file or not file.filename:
        return None, None

    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in _ALLOWED_PHOTO_EXTS:
        return None, f"Format non autorisé ({ext}). Utilisez JPG, PNG ou WEBP."

    # Vérifier la taille sans charger tout en mémoire
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size > _MAX_PHOTO_BYTES:
        return None, "La photo dépasse la taille limite de 5 MB."

    upload_folder = current_app.config['UPLOAD_FOLDER']
    folder = os.path.join(upload_folder, 'intervenants', str(iid))
    os.makedirs(folder, exist_ok=True)

    # Supprimer l'ancienne photo quelle que soit son extension
    for old_ext in _ALLOWED_PHOTO_EXTS:
        old_path = os.path.join(folder, f'photo.{old_ext}')
        if os.path.exists(old_path):
            os.remove(old_path)

    dest = os.path.join(folder, f'photo.{ext}')
    file.save(dest)
    return f'intervenants/{iid}/photo.{ext}', None


def edition_courante_id():
    """Retourne l'id de l'édition sélectionnée (session Flask) ou la plus récente active."""
    eid = flask_session.get('edition_id')
    if eid:
        return eid
    row = query("""
        SELECT id FROM editions
        WHERE statut_code NOT IN ('archivee')
        ORDER BY date_debut DESC LIMIT 1
    """, one=True)
    return row['id'] if row else None


# ------------------------------------------------------------------
# Sélecteur d'édition (appelé via AJAX ou formulaire)
# ------------------------------------------------------------------
@bp.route('/changer-edition', methods=['POST'])
@login_required
def changer_edition():
    edition_id = request.form.get('edition_id')
    if edition_id:
        flask_session['edition_id'] = int(edition_id)
    next_url = request.form.get('next') or url_for('intervenants.liste')
    return redirect(next_url)


# ------------------------------------------------------------------
# LISTE DES INTERVENANTS
# ------------------------------------------------------------------
@bp.route('/')
@login_required
def liste():
    if not current_user.a_permission('intervenants', 'voir_liste'):
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('dashboard'))

    eid = edition_courante_id()
    search = request.args.get('q', '').strip()
    statut = request.args.get('statut', '')
    page   = int(request.args.get('page', 1))
    par_page = 25
    offset = (page - 1) * par_page

    # Construction de la requête
    conditions = []
    params = []

    if search:
        conditions.append("(i.nom LIKE ? OR i.prenom LIKE ? OR i.email_principal LIKE ?)")
        params += [f'%{search}%', f'%{search}%', f'%{search}%']

    if statut and eid:
        conditions.append("pi.statut_code = ?")
        params.append(statut)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    if eid:
        sql = f"""
            SELECT i.*,
                   pi.statut_code,
                   pi.ha_inscrit,
                   pi.type_presence_code,
                   pi.referent_id,
                   COUNT(DISTINCT si.session_id) as nb_sessions
            FROM intervenants i
            LEFT JOIN participations_intervenants pi
                ON pi.intervenant_id = i.id AND pi.edition_id = ?
            LEFT JOIN session_intervenants si
                ON si.intervenant_id = i.id
            LEFT JOIN sessions s
                ON s.id = si.session_id AND s.edition_id = ?
            {where}
            GROUP BY i.id
            ORDER BY i.nom, i.prenom
            LIMIT ? OFFSET ?
        """
        intervenants = query(sql, [eid, eid] + params + [par_page, offset])
        total = query(f"""
            SELECT COUNT(DISTINCT i.id) as n FROM intervenants i
            LEFT JOIN participations_intervenants pi
                ON pi.intervenant_id = i.id AND pi.edition_id = ?
            {where}
        """, [eid] + params, one=True)['n']
    else:
        sql = f"""
            SELECT i.*, NULL as statut_code, 0 as ha_inscrit,
                   NULL as type_presence_code, NULL as referent_id,
                   COUNT(DISTINCT si.session_id) as nb_sessions
            FROM intervenants i
            LEFT JOIN session_intervenants si ON si.intervenant_id = i.id
            {where}
            GROUP BY i.id
            ORDER BY i.nom, i.prenom
            LIMIT ? OFFSET ?
        """
        intervenants = query(sql, params + [par_page, offset])
        total = query(f"SELECT COUNT(*) as n FROM intervenants i {where}",
                      params, one=True)['n']

    editions    = query("SELECT * FROM editions ORDER BY annee DESC")
    statuts     = query("SELECT * FROM ref_statuts_participation ORDER BY ordre")
    edition_sel = query("SELECT * FROM editions WHERE id=?", (eid,), one=True) if eid else None
    peut_modifier = current_user.a_permission('intervenants', 'modifier')

    return render_template('intervenants/liste.html',
                           intervenants=intervenants,
                           editions=editions,
                           edition_sel=edition_sel,
                           statuts=statuts,
                           search=search,
                           statut_filtre=statut,
                           page=page, par_page=par_page, total=total,
                           edition_id=eid,
                           peut_modifier=peut_modifier)


# ------------------------------------------------------------------
# FICHE INTERVENANT
# ------------------------------------------------------------------
@bp.route('/<int:iid>')
@login_required
def fiche(iid):
    if not current_user.a_permission('intervenants', 'voir_fiche'):
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('intervenants.liste'))

    intervenant = query("SELECT * FROM intervenants WHERE id=?", (iid,), one=True)
    if not intervenant:
        flash('Intervenant introuvable.', 'danger')
        return redirect(url_for('intervenants.liste'))

    eid = edition_courante_id()

    # Participation à l'édition courante
    participation = None
    if eid:
        participation = query("""
            SELECT pi.*, u.prenom || ' ' || u.nom as referent_nom
            FROM participations_intervenants pi
            LEFT JOIN utilisateurs u ON u.id = pi.referent_id
            WHERE pi.intervenant_id = ? AND pi.edition_id = ?
        """, (iid, eid), one=True)

    # Toutes les participations (historique)
    historique = query("""
        SELECT pi.*, e.nom as edition_nom, e.annee,
               u.prenom || ' ' || u.nom as referent_nom
        FROM participations_intervenants pi
        JOIN editions e ON e.id = pi.edition_id
        LEFT JOIN utilisateurs u ON u.id = pi.referent_id
        WHERE pi.intervenant_id = ?
        ORDER BY e.annee DESC
    """, (iid,))

    # Sessions pour l'édition courante
    sessions = []
    if eid:
        sessions = query("""
            SELECT s.*, si.role_code,
                   GROUP_CONCAT(c.jour || ' ' || c.heure_debut, ', ') as creneaux
            FROM sessions s
            JOIN session_intervenants si ON si.session_id = s.id
            LEFT JOIN creneaux c ON c.session_id = s.id
            WHERE si.intervenant_id = ? AND s.edition_id = ?
            GROUP BY s.id
            ORDER BY s.titre
        """, (iid, eid))

    # Droits d'accès aux champs sensibles
    peut_voir_contacts = current_user.a_permission('intervenants', 'voir_fiche', 'email_principal')
    peut_modifier = current_user.a_permission('intervenants', 'modifier')

    # Token formulaire actif
    token_actif = None
    if eid:
        token_actif = query("""
            SELECT * FROM tokens_formulaire_intervenant
            WHERE intervenant_id = ? AND edition_id = ? AND utilise = 0
              AND expire_at > datetime('now')
            ORDER BY created_at DESC LIMIT 1
        """, (iid, eid), one=True)

    editions = query("SELECT * FROM editions ORDER BY annee DESC")
    edition_sel = query("SELECT * FROM editions WHERE id=?", (eid,), one=True) if eid else None

    return render_template('intervenants/fiche.html',
                           intervenant=intervenant,
                           participation=participation,
                           historique=historique,
                           sessions=sessions,
                           token_actif=token_actif,
                           peut_voir_contacts=peut_voir_contacts,
                           peut_modifier=peut_modifier,
                           editions=editions,
                           edition_sel=edition_sel,
                           edition_id=eid)


# ------------------------------------------------------------------
# CRÉER / MODIFIER UN INTERVENANT
# ------------------------------------------------------------------
@bp.route('/nouveau', methods=['GET', 'POST'])
@bp.route('/<int:iid>/modifier', methods=['GET', 'POST'])
@login_required
def form(iid=None):
    if not current_user.a_permission('intervenants', 'creer' if not iid else 'modifier'):
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('intervenants.liste'))

    intervenant = None
    if iid:
        intervenant = query("SELECT * FROM intervenants WHERE id=?", (iid,), one=True)
        if not intervenant:
            flash('Introuvable.', 'danger')
            return redirect(url_for('intervenants.liste'))

    session_id = request.args.get('session_id') or request.form.get('session_id') or ''

    if request.method == 'POST':
        data = {
            'civilite_code':        request.form.get('civilite_code') or None,
            'nom':                  request.form.get('nom', '').strip().upper(),
            'prenom':               request.form.get('prenom', '').strip(),
            'nom_affichage':        request.form.get('nom_affichage', '').strip() or None,
            'email_principal':      request.form.get('email_principal', '').strip() or None,
            'email_secondaire':     request.form.get('email_secondaire', '').strip() or None,
            'tel_mobile':           request.form.get('tel_mobile', '').strip() or None,
            'tel_fixe':             request.form.get('tel_fixe', '').strip() or None,
            'adresse':              request.form.get('adresse', '').strip() or None,
            'code_postal':          request.form.get('code_postal', '').strip() or None,
            'ville':                request.form.get('ville', '').strip() or None,
            'pays':                 request.form.get('pays', 'France').strip(),
            'site_web':             request.form.get('site_web', '').strip() or None,
            'facebook':             request.form.get('facebook', '').strip() or None,
            'twitter':              request.form.get('twitter', '').strip() or None,
            'instagram':            request.form.get('instagram', '').strip() or None,
            'linkedin':             request.form.get('linkedin', '').strip() or None,
            'fonction_titre':       request.form.get('fonction_titre', '').strip() or None,
            'mini_bio':             request.form.get('mini_bio', '').strip() or None,
            'specialites':          request.form.get('specialites', '').strip() or None,
            'institutions':         request.form.get('institutions', '').strip() or None,
            'oeuvres_publications': request.form.get('oeuvres_publications', '').strip() or None,
            'email_livret_choix':   request.form.get('email_livret_choix', 'aucun'),
            'nom_diffuse':          1 if request.form.get('nom_diffuse') else 0,
            'accord_photo':         1 if request.form.get('accord_photo') else 0,
            'accord_photo_video_com': 1 if request.form.get('accord_photo_video_com') else 0,
            'accord_podcast':       1 if request.form.get('accord_podcast') else 0,
            'notes_internes':       request.form.get('notes_internes', '').strip() or None,
        }

        # Traitement photo (upload optionnel)
        photo_file = request.files.get('photo')
        photo_path_new, photo_err = _save_photo(photo_file, iid or 0)
        if photo_err:
            flash(photo_err, 'warning')

        try:
            if iid:
                # Audit des changements
                for champ, nouvelle_val in data.items():
                    ancienne_val = intervenant.get(champ)
                    if str(ancienne_val) != str(nouvelle_val):
                        audit('UPDATE', 'intervenants', iid,
                              champ=champ,
                              ancienne_valeur=ancienne_val,
                              nouvelle_valeur=nouvelle_val,
                              utilisateur_id=current_user.id)

                if photo_path_new:
                    data['photo_path'] = photo_path_new

                cols = ', '.join(f"{k} = ?" for k in data.keys())
                execute(f"UPDATE intervenants SET {cols}, updated_at = datetime('now') WHERE id = ?",
                        list(data.values()) + [iid])
                flash('Intervenant mis à jour.', 'success')
                return redirect(url_for('intervenants.fiche', iid=iid))
            else:
                data['created_by'] = current_user.id
                new_id = insert('intervenants', data)
                audit('CREATE', 'intervenants', new_id,
                      utilisateur_id=current_user.id,
                      nouvelle_valeur=f"{data['prenom']} {data['nom']}")

                # Re-sauvegarder la photo avec l'id réel (inconnu avant l'insert)
                if photo_file and photo_file.filename:
                    photo_file.seek(0)
                    real_path, _ = _save_photo(photo_file, new_id)
                    if real_path:
                        execute("UPDATE intervenants SET photo_path=? WHERE id=?",
                                (real_path, new_id))

                # Créer une participation pour l'édition courante si elle existe
                eid = edition_courante_id()
                if eid:
                    insert('participations_intervenants', {
                        'intervenant_id': new_id,
                        'edition_id': eid,
                        'statut_code': 'a_contacter',
                        'created_by': current_user.id,
                    })

                action_btn = request.form.get('action', '').strip()
                if action_btn == 'create_and_add_session':
                    flash('Intervenant créé. Créez maintenant sa session.', 'success')
                    return redirect(url_for('sessions.form', intervenant_id=new_id))

                sid_lien = request.form.get('session_id', '').strip()
                if sid_lien:
                    try:
                        insert('session_intervenants', {
                            'session_id':      int(sid_lien),
                            'intervenant_id':  new_id,
                            'role_code':       'principal',
                            'ordre_affichage': 1,
                        })
                    except Exception:
                        pass
                    flash('Intervenant créé et ajouté à la session.', 'success')
                    return redirect(url_for('sessions.fiche', sid=int(sid_lien)))

                flash('Intervenant créé.', 'success')
                return redirect(url_for('intervenants.fiche', iid=new_id))
        except Exception as e:
            flash(f'Erreur : {e}', 'danger')

    civilites = query("SELECT * FROM ref_civilites ORDER BY ordre")
    editions  = query("SELECT * FROM editions ORDER BY annee DESC")
    eid = edition_courante_id()
    edition_sel = query("SELECT * FROM editions WHERE id=?", (eid,), one=True) if eid else None

    return render_template('intervenants/form.html',
                           intervenant=intervenant,
                           civilites=civilites,
                           editions=editions,
                           edition_sel=edition_sel,
                           edition_id=eid,
                           session_id=session_id)


# ------------------------------------------------------------------
# PARTICIPATION À UNE ÉDITION
# ------------------------------------------------------------------
@bp.route('/<int:iid>/participation', methods=['POST'])
@login_required
def participation_update(iid):
    if not current_user.a_permission('intervenants', 'modifier'):
        return jsonify({'error': 'Non autorisé'}), 403

    eid = int(request.form.get('edition_id', 0))
    if not eid:
        flash('Édition non spécifiée.', 'danger')
        return redirect(url_for('intervenants.fiche', iid=iid))

    # Vérifier si une participation existe déjà
    existing = query("""
        SELECT id FROM participations_intervenants
        WHERE intervenant_id = ? AND edition_id = ?
    """, (iid, eid), one=True)

    data = {
        'statut_code':           request.form.get('statut_code', 'a_contacter'),
        'type_presence_code':    request.form.get('type_presence_code') or None,
        'logement_fourni':       1 if request.form.get('logement_fourni') else 0,
        'type_logement':         request.form.get('type_logement', '').strip() or None,
        'heure_arrivee':         request.form.get('heure_arrivee', '').strip() or None,
        'heure_depart':          request.form.get('heure_depart', '').strip() or None,
        'remuneration':          1 if request.form.get('remuneration') else 0,
        'montant_remuneration':  float(request.form.get('montant_remuneration') or 0),
        'contraintes':           request.form.get('contraintes', '').strip() or None,
        'commentaires_equipe':   request.form.get('commentaires_equipe', '').strip() or None,
        'livres_a_vendre':       request.form.get('livres_a_vendre', '').strip() or None,
        'dedicace':              1 if request.form.get('dedicace') else 0,
        'invite_officiel':       1 if request.form.get('invite_officiel') else 0,
        'propose_par':           request.form.get('propose_par', '').strip() or None,
    }

    if existing:
        cols = ', '.join(f"{k} = ?" for k in data.keys())
        execute(f"""
            UPDATE participations_intervenants
            SET {cols}, updated_at = datetime('now')
            WHERE intervenant_id = ? AND edition_id = ?
        """, list(data.values()) + [iid, eid])
    else:
        data.update({'intervenant_id': iid, 'edition_id': eid, 'created_by': current_user.id})
        insert('participations_intervenants', data)

    flash('Participation mise à jour.', 'success')
    return redirect(url_for('intervenants.fiche', iid=iid))


# ------------------------------------------------------------------
# ATTACHER / DÉTACHER UNE SESSION
# ------------------------------------------------------------------
@bp.route('/<int:iid>/session/ajouter', methods=['POST'])
@login_required
def session_ajouter(iid):
    if not current_user.a_permission('sessions', 'modifier'):
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('intervenants.fiche', iid=iid))

    session_id = request.form.get('session_id')
    role_code  = request.form.get('role_code', 'principal')
    try:
        insert('session_intervenants', {
            'session_id': session_id,
            'intervenant_id': iid,
            'role_code': role_code,
            'ordre_affichage': 1,
        })
        flash('Session liée.', 'success')
    except Exception as e:
        flash(f'Erreur : {e}', 'danger')
    return redirect(url_for('intervenants.fiche', iid=iid))


@bp.route('/<int:iid>/session/<int:sid>/retirer', methods=['POST'])
@login_required
def session_retirer(iid, sid):
    if not current_user.a_permission('sessions', 'modifier'):
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('intervenants.fiche', iid=iid))
    execute("DELETE FROM session_intervenants WHERE session_id=? AND intervenant_id=?",
            (sid, iid))
    flash('Session détachée.', 'success')
    return redirect(url_for('intervenants.fiche', iid=iid))


# ------------------------------------------------------------------
# FORMULAIRE PUBLIC PAR TOKEN
# ------------------------------------------------------------------
def _envoyer_email_formulaire(intervenant, token, edition_nom=''):
    """Envoie l'email d'invitation au formulaire. Retourne (True, None) ou (False, message)."""
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from flask import current_app
    cfg = current_app.config
    lien = url_for('intervenants.formulaire_public', token=token, _external=True)
    msg = MIMEMultipart('alternative')
    msg['From']    = cfg['MAIL_FROM']
    msg['To']      = intervenant['email_principal']
    msg['Subject'] = f"Complétez votre fiche intervenant — Limoud {edition_nom}".strip()
    corps = f"""<p>Bonjour {intervenant.get('prenom', '')} {intervenant.get('nom', '')},</p>
<p>L'équipe Limoud vous invite à compléter votre fiche intervenant et à proposer vos sessions.</p>
<p>Ce formulaire vous permet de :</p>
<ul>
  <li>Renseigner votre biographie et vos informations publiques</li>
  <li>Proposer une ou plusieurs sessions / interventions</li>
</ul>
<p style="margin:1.5em 0">
  <a href="{lien}" style="background:#1a5276;color:#fff;padding:10px 24px;
     text-decoration:none;border-radius:4px;font-weight:bold;">
    Accéder au formulaire
  </a>
</p>
<p>Ce lien est valable 30 jours et peut être utilisé à tout moment jusqu'à confirmation finale.
Si vous n'êtes pas à l'origine de cette demande, ignorez ce message.</p>
<p>L'équipe Limoud</p>"""
    msg.attach(MIMEText(corps, 'html', 'utf-8'))
    try:
        with smtplib.SMTP_SSL(cfg['MAIL_SERVER'], cfg['MAIL_PORT']) as srv:
            srv.login(cfg['MAIL_USERNAME'], cfg['MAIL_PASSWORD'])
            srv.sendmail(cfg['MAIL_FROM'], intervenant['email_principal'], msg.as_string())
        return True, None
    except Exception as e:
        return False, str(e)


@bp.route('/<int:iid>/envoyer-formulaire', methods=['POST'])
@login_required
def envoyer_formulaire(iid):
    import secrets

    if not current_user.a_permission('intervenants', 'modifier'):
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('intervenants.fiche', iid=iid))

    intervenant = query("SELECT * FROM intervenants WHERE id=?", (iid,), one=True)
    if not intervenant or not intervenant['email_principal']:
        flash("L'intervenant n'a pas d'adresse email renseignée.", 'danger')
        return redirect(url_for('intervenants.fiche', iid=iid))

    eid = edition_courante_id()
    if not eid:
        flash("Aucune édition active.", 'danger')
        return redirect(url_for('intervenants.fiche', iid=iid))

    # Vérifier si un token actif existe déjà
    token_existant = query("""
        SELECT token FROM tokens_formulaire_intervenant
        WHERE intervenant_id = ? AND edition_id = ? AND utilise = 0
          AND expire_at > datetime('now')
        ORDER BY created_at DESC LIMIT 1
    """, (iid, eid), one=True)

    action = request.form.get('action', 'nouveau')

    if token_existant and action != 'forcer_nouveau':
        # Proposer de renvoyer le même lien
        edition = query("SELECT nom FROM editions WHERE id=?", (eid,), one=True)
        edition_nom = edition['nom'] if edition else ''
        ok, err = _envoyer_email_formulaire(intervenant, token_existant['token'], edition_nom)
        if ok:
            flash(f"Lien existant renvoyé à {intervenant['email_principal']}.", 'success')
        else:
            flash(f"Erreur lors de l'envoi email : {err}", 'danger')
        return redirect(url_for('intervenants.fiche', iid=iid))

    # Invalider les tokens existants non utilisés
    execute("""
        UPDATE tokens_formulaire_intervenant
        SET utilise = 1, utilise_at = datetime('now')
        WHERE intervenant_id = ? AND edition_id = ? AND utilise = 0
    """, (iid, eid))

    token = secrets.token_urlsafe(32)
    execute("""
        INSERT INTO tokens_formulaire_intervenant
            (intervenant_id, edition_id, token, expire_at, created_by)
        VALUES (?, ?, ?, datetime('now', '+30 days'), ?)
    """, (iid, eid, token, current_user.id))

    edition = query("SELECT nom FROM editions WHERE id=?", (eid,), one=True)
    edition_nom = edition['nom'] if edition else ''
    ok, err = _envoyer_email_formulaire(intervenant, token, edition_nom)
    if ok:
        execute("""
            UPDATE participations_intervenants
            SET statut_code = 'formulaire_envoye', updated_at = datetime('now')
            WHERE intervenant_id = ? AND edition_id = ?
        """, (iid, eid))
        flash(f"Formulaire envoyé à {intervenant['email_principal']}.", 'success')
    else:
        flash(f"Erreur lors de l'envoi email : {err}", 'danger')

    return redirect(url_for('intervenants.fiche', iid=iid))


@bp.route('/formulaire/<token>', methods=['GET', 'POST'])
@bp.route('/formulaire/<token>/etape/<int:etape>', methods=['GET', 'POST'])
def formulaire_public(token, etape=1):
    from datetime import datetime, timezone

    tok = query("""
        SELECT t.*, i.civilite_code, i.nom, i.prenom, i.nom_affichage,
               i.fonction_titre, i.mini_bio, i.specialites, i.institutions,
               i.oeuvres_publications, i.site_web, i.twitter, i.instagram,
               i.linkedin, i.accord_photo, i.accord_podcast, i.email_livret_choix,
               i.photo_path
        FROM tokens_formulaire_intervenant t
        JOIN intervenants i ON i.id = t.intervenant_id
        WHERE t.token = ?
    """, (token,), one=True)

    if not tok:
        return render_template('intervenants/formulaire_public.html', erreur="Lien invalide.")
    if tok['utilise']:
        return render_template('intervenants/formulaire_public.html', erreur="Ce lien a déjà été utilisé. Merci pour votre participation !")
    if tok['expire_at'] < datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S'):
        return render_template('intervenants/formulaire_public.html', erreur="Ce lien a expiré.")

    iid = tok['intervenant_id']
    eid = tok['edition_id']

    # ── Étape 1 : Identité ──────────────────────────────────────────────
    if etape == 1:
        if request.method == 'POST':
            data = {
                'civilite_code':        request.form.get('civilite_code') or None,
                'nom_affichage':        request.form.get('nom_affichage', '').strip() or None,
                'fonction_titre':       request.form.get('fonction_titre', '').strip() or None,
                'mini_bio':             request.form.get('mini_bio', '').strip() or None,
                'specialites':          request.form.get('specialites', '').strip() or None,
                'institutions':         request.form.get('institutions', '').strip() or None,
                'oeuvres_publications': request.form.get('oeuvres_publications', '').strip() or None,
                'site_web':             request.form.get('site_web', '').strip() or None,
                'twitter':              request.form.get('twitter', '').strip() or None,
                'instagram':            request.form.get('instagram', '').strip() or None,
                'linkedin':             request.form.get('linkedin', '').strip() or None,
                'accord_photo':         1 if request.form.get('accord_photo') else 0,
                'accord_podcast':       1 if request.form.get('accord_podcast') else 0,
                'email_livret_choix':   request.form.get('email_livret_choix', 'aucun'),
            }

            photo_file = request.files.get('photo')
            photo_path_new, _ = _save_photo(photo_file, iid)
            if photo_path_new:
                data['photo_path'] = photo_path_new

            cols = ', '.join(f"{k} = ?" for k in data.keys())
            execute(f"UPDATE intervenants SET {cols}, updated_at = datetime('now') WHERE id = ?",
                    list(data.values()) + [iid])
            return redirect(url_for('intervenants.formulaire_public', token=token, etape=2))

        civilites = query("SELECT * FROM ref_civilites ORDER BY ordre")
        return render_template('intervenants/formulaire_public.html',
                               tok=tok, civilites=civilites, etape=1, token=token)

    # ── Étape 2 : Sessions ──────────────────────────────────────────────
    if etape == 2:
        formats  = query("SELECT * FROM ref_formats_session WHERE actif=1 ORDER BY code")
        langues  = query("SELECT * FROM ref_langues WHERE actif=1 ORDER BY code")
        niveaux  = query("SELECT * FROM ref_niveaux_session ORDER BY ordre")

        if request.method == 'POST':
            action = request.form.get('action', '')

            if action == 'ajouter_session':
                titre = request.form.get('titre', '').strip()
                if titre:
                    sid = insert('sessions', {
                        'edition_id':          eid,
                        'titre':               titre,
                        'description':         request.form.get('description', '').strip() or None,
                        'format_code':         request.form.get('format_code') or None,
                        'duree_minutes':       int(request.form.get('duree_minutes') or 60),
                        'langue_code':         request.form.get('langue_code', 'fr'),
                        'niveau_code':         request.form.get('niveau_code') or None,
                        'besoin_micro':        1 if request.form.get('besoin_micro') else 0,
                        'besoin_video':        1 if request.form.get('besoin_video') else 0,
                        'besoin_sono':         1 if request.form.get('besoin_sono') else 0,
                        'materiel_intervenant': request.form.get('materiel_intervenant', '').strip() or None,
                        'statut_code':         'soumis',
                    })
                    try:
                        insert('session_intervenants', {
                            'session_id':      sid,
                            'intervenant_id':  iid,
                            'role_code':       'principal',
                            'ordre_affichage': 1,
                        })
                    except Exception:
                        pass
                return redirect(url_for('intervenants.formulaire_public', token=token, etape=2))

            elif action == 'supprimer_session':
                sid = int(request.form.get('session_id', 0))
                if sid:
                    # Ne supprimer que les sessions soumises via ce formulaire
                    execute("""
                        DELETE FROM sessions
                        WHERE id = ? AND edition_id = ? AND statut_code = 'soumis'
                          AND id IN (
                              SELECT session_id FROM session_intervenants WHERE intervenant_id = ?
                          )
                    """, (sid, eid, iid))
                return redirect(url_for('intervenants.formulaire_public', token=token, etape=2))

            elif action == 'suivant':
                return redirect(url_for('intervenants.formulaire_public', token=token, etape=3))

        sessions_soumises = query("""
            SELECT s.* FROM sessions s
            JOIN session_intervenants si ON si.session_id = s.id
            WHERE si.intervenant_id = ? AND s.edition_id = ? AND s.statut_code = 'soumis'
            ORDER BY s.titre
        """, (iid, eid))

        return render_template('intervenants/formulaire_public.html',
                               tok=tok, etape=2, token=token,
                               sessions_soumises=sessions_soumises,
                               formats=formats, langues=langues, niveaux=niveaux)

    # ── Étape 3 : Confirmation ──────────────────────────────────────────
    if etape == 3:
        if request.method == 'POST':
            # Marquer le token comme utilisé définitivement
            execute("""
                UPDATE tokens_formulaire_intervenant
                SET utilise = 1, utilise_at = datetime('now') WHERE token = ?
            """, (token,))
            execute("""
                UPDATE participations_intervenants
                SET statut_code = 'formulaire_recu', updated_at = datetime('now')
                WHERE intervenant_id = ? AND edition_id = ?
            """, (iid, eid))
            return render_template('intervenants/formulaire_public.html',
                                   confirme=True, tok=tok)

        intervenant_complet = query("SELECT * FROM intervenants WHERE id=?", (iid,), one=True)
        sessions_soumises = query("""
            SELECT s.* FROM sessions s
            JOIN session_intervenants si ON si.session_id = s.id
            WHERE si.intervenant_id = ? AND s.edition_id = ? AND s.statut_code = 'soumis'
            ORDER BY s.titre
        """, (iid, eid))

        return render_template('intervenants/formulaire_public.html',
                               tok=tok, etape=3, token=token,
                               intervenant_complet=intervenant_complet,
                               sessions_soumises=sessions_soumises)

    # Étape inconnue → retour étape 1
    return redirect(url_for('intervenants.formulaire_public', token=token, etape=1))


# ------------------------------------------------------------------
# INVITATION RAPIDE
# ------------------------------------------------------------------
@bp.route('/inviter', methods=['GET', 'POST'])
@login_required
def inviter():
    import secrets
    if not current_user.a_permission('intervenants', 'creer'):
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('intervenants.liste'))

    if request.method == 'POST':
        civilite = request.form.get('civilite_code') or None
        prenom   = request.form.get('prenom', '').strip()
        nom      = request.form.get('nom', '').strip().upper()
        email    = request.form.get('email', '').strip().lower()

        if not prenom or not nom or not email:
            flash('Prénom, nom et email sont obligatoires.', 'danger')
        else:
            eid = edition_courante_id()
            try:
                iid = insert('intervenants', {
                    'civilite_code': civilite,
                    'prenom': prenom,
                    'nom': nom,
                    'email_principal': email,
                    'created_by': current_user.id,
                })
                if eid:
                    insert('participations_intervenants', {
                        'intervenant_id': iid,
                        'edition_id': eid,
                        'statut_code': 'formulaire_envoye',
                        'created_by': current_user.id,
                    })

                # Générer le token
                token = secrets.token_urlsafe(32)
                execute("""
                    INSERT INTO tokens_formulaire_intervenant
                        (intervenant_id, edition_id, token, expire_at, created_by)
                    VALUES (?, ?, ?, datetime('now', '+30 days'), ?)
                """, (iid, eid, token, current_user.id))

                intervenant = query("SELECT * FROM intervenants WHERE id=?", (iid,), one=True)
                edition = query("SELECT nom FROM editions WHERE id=?", (eid,), one=True) if eid else None
                edition_nom = edition['nom'] if edition else ''
                ok, err = _envoyer_email_formulaire(intervenant, token, edition_nom)

                if ok:
                    flash(f"Invitation envoyée à {email}. L'intervenant peut dès maintenant compléter sa fiche.", 'success')
                else:
                    flash(f"Intervenant créé mais erreur d'envoi email : {err}", 'warning')
                return redirect(url_for('intervenants.liste'))
            except Exception as e:
                flash(f'Erreur : {e}', 'danger')

    civilites = query("SELECT * FROM ref_civilites ORDER BY ordre")
    editions  = query("SELECT * FROM editions ORDER BY annee DESC")
    eid = edition_courante_id()
    edition_sel = query("SELECT * FROM editions WHERE id=?", (eid,), one=True) if eid else None
    return render_template('intervenants/inviter.html',
                           civilites=civilites,
                           editions=editions,
                           edition_sel=edition_sel,
                           edition_id=eid)
