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

    return render_template('intervenants/liste.html',
                           intervenants=intervenants,
                           editions=editions,
                           edition_sel=edition_sel,
                           statuts=statuts,
                           search=search,
                           statut_filtre=statut,
                           page=page, par_page=par_page, total=total,
                           edition_id=eid)


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

    editions = query("SELECT * FROM editions ORDER BY annee DESC")
    edition_sel = query("SELECT * FROM editions WHERE id=?", (eid,), one=True) if eid else None

    return render_template('intervenants/fiche.html',
                           intervenant=intervenant,
                           participation=participation,
                           historique=historique,
                           sessions=sessions,
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

        try:
            if iid:
                # Audit des changements
                for champ, nouvelle_val in data.items():
                    ancienne_val = intervenant[champ] if champ in intervenant.keys() else None
                    if str(ancienne_val) != str(nouvelle_val):
                        audit('UPDATE', 'intervenants', iid,
                              champ=champ,
                              ancienne_valeur=ancienne_val,
                              nouvelle_valeur=nouvelle_val,
                              utilisateur_id=current_user.id)

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

                # Créer une participation pour l'édition courante si elle existe
                eid = edition_courante_id()
                if eid:
                    insert('participations_intervenants', {
                        'intervenant_id': new_id,
                        'edition_id': eid,
                        'statut_code': 'a_contacter',
                        'created_by': current_user.id,
                    })

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
                           edition_id=eid)


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
