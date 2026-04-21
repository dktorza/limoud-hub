"""
modules/sessions/routes.py
Gestion des sessions : liste, fiche, création, modification, créneaux.
"""
from flask import (Blueprint, render_template, redirect, url_for,
                   request, flash, session as flask_session)
from flask_login import login_required, current_user
from database import query, execute, insert, audit

bp = Blueprint('sessions', __name__, template_folder='templates')


def edition_courante_id():
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
# LISTE DES SESSIONS
# ------------------------------------------------------------------
@bp.route('/')
@login_required
def liste():
    if not current_user.a_permission('sessions', 'voir_liste'):
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('dashboard'))

    eid     = edition_courante_id()
    search  = request.args.get('q', '').strip()
    statut  = request.args.get('statut', '')
    theme   = request.args.get('theme', '')
    format_ = request.args.get('format', '')
    page    = int(request.args.get('page', 1))
    par_page = 25
    offset  = (page - 1) * par_page

    durees = query("""
        SELECT * FROM ref_durees_session
        WHERE edition_id = ? AND actif = 1
        ORDER BY ordre, duree_min
    """, (eid or 0,))

    conditions = ['s.edition_id = ?']
    params     = [eid or 0]

    if search:
        conditions.append("(s.titre LIKE ? OR s.description LIKE ?)")
        params += [f'%{search}%', f'%{search}%']
    if statut:
        conditions.append("s.statut_code = ?")
        params.append(statut)
    if theme:
        conditions.append("s.theme_id = ?")
        params.append(theme)
    if format_:
        conditions.append("s.format_code = ?")
        params.append(format_)

    where = "WHERE " + " AND ".join(conditions)

    sessions = query(f"""
        SELECT s.*,
               t.libelle as theme_libelle, t.couleur_hex as theme_couleur,
               f.libelle as format_libelle,
               rs.libelle as statut_libelle, rs.couleur_hex as statut_couleur,
               GROUP_CONCAT(DISTINCT i.prenom || ' ' || i.nom) as intervenants_noms,
               COUNT(DISTINCT c.id) as nb_creneaux
        FROM sessions s
        LEFT JOIN themes t ON t.id = s.theme_id
        LEFT JOIN ref_formats_session f ON f.code = s.format_code
        LEFT JOIN ref_statuts_session rs ON rs.code = s.statut_code
        LEFT JOIN session_intervenants si ON si.session_id = s.id
        LEFT JOIN intervenants i ON i.id = si.intervenant_id
        LEFT JOIN creneaux c ON c.session_id = s.id
        {where}
        GROUP BY s.id
        ORDER BY s.titre
        LIMIT ? OFFSET ?
    """, params + [par_page, offset])

    total = query(f"SELECT COUNT(*) as n FROM sessions s {where}", params, one=True)['n']

    editions    = query("SELECT * FROM editions ORDER BY annee DESC")
    statuts     = query("SELECT * FROM ref_statuts_session ORDER BY ordre")
    themes = query("""
        SELECT * FROM themes
        WHERE edition_id = ?
        UNION
        SELECT * FROM themes
        WHERE edition_id IS NULL
        AND code NOT IN (SELECT code FROM themes WHERE edition_id = ?)
        ORDER BY ordre
    """, (eid or 0, eid or 0))
    formats     = query("SELECT * FROM ref_formats_session WHERE actif=1 ORDER BY libelle")
    edition_sel = query("SELECT * FROM editions WHERE id=?", (eid,), one=True) if eid else None

    return render_template('sessions/liste.html',
                           sessions=sessions, editions=editions,
                           edition_sel=edition_sel, statuts=statuts,
                           themes=themes, formats=formats,
                           search=search, statut_filtre=statut,
                           theme_filtre=theme, format_filtre=format_,
                           page=page, par_page=par_page, total=total,
                           edition_id=eid)


# ------------------------------------------------------------------
# FICHE SESSION
# ------------------------------------------------------------------
@bp.route('/<int:sid>')
@login_required
def fiche(sid):
    if not current_user.a_permission('sessions', 'voir_fiche'):
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('sessions.liste'))

    session = query("""
        SELECT s.*,
               t.libelle as theme_libelle, t.couleur_hex as theme_couleur,
               f.libelle as format_libelle,
               rs.libelle as statut_libelle, rs.couleur_hex as statut_couleur,
               e.nom as edition_nom
        FROM sessions s
        LEFT JOIN themes t ON t.id = s.theme_id
        LEFT JOIN ref_formats_session f ON f.code = s.format_code
        LEFT JOIN ref_statuts_session rs ON rs.code = s.statut_code
        LEFT JOIN editions e ON e.id = s.edition_id
        WHERE s.id = ?
    """, (sid,), one=True)

    if not session:
        flash('Session introuvable.', 'danger')
        return redirect(url_for('sessions.liste'))

    intervenants = query("""
        SELECT i.*, si.role_code, r.libelle as role_libelle,
               pi.statut_code as part_statut, pi.ha_inscrit
        FROM session_intervenants si
        JOIN intervenants i ON i.id = si.intervenant_id
        LEFT JOIN ref_roles_session r ON r.code = si.role_code
        LEFT JOIN participations_intervenants pi
            ON pi.intervenant_id = i.id AND pi.edition_id = ?
        WHERE si.session_id = ?
        ORDER BY si.ordre_affichage
    """, (session['edition_id'], sid))

    creneaux = query("""
        SELECT c.*, sa.nom as salle_nom
        FROM creneaux c
        LEFT JOIN salles sa ON sa.id = c.salle_id
        WHERE c.session_id = ?
        ORDER BY c.jour, c.heure_debut
    """, (sid,))

    # Intervenants disponibles pour cette édition (pour ajouter)
    intervenants_dispo = query("""
        SELECT i.id, i.prenom, i.nom
        FROM intervenants i
        LEFT JOIN participations_intervenants pi
            ON pi.intervenant_id = i.id AND pi.edition_id = ?
        WHERE i.id NOT IN (
            SELECT intervenant_id FROM session_intervenants WHERE session_id = ?
        )
        ORDER BY i.nom, i.prenom
    """, (session['edition_id'], sid))

    salles = query("SELECT * FROM salles WHERE edition_id=? ORDER BY nom",
                   (session['edition_id'],))
    roles  = query("SELECT * FROM ref_roles_session ORDER BY ordre")

    eid = edition_courante_id()
    editions    = query("SELECT * FROM editions ORDER BY annee DESC")
    edition_sel = query("SELECT * FROM editions WHERE id=?", (eid,), one=True) if eid else None

    peut_modifier = current_user.a_permission('sessions', 'modifier')

    return render_template('sessions/fiche.html',
                           session=session,
                           intervenants=intervenants,
                           creneaux=creneaux,
                           intervenants_dispo=intervenants_dispo,
                           salles=salles, roles=roles,
                           peut_modifier=peut_modifier,
                           editions=editions, edition_sel=edition_sel,
                           edition_id=eid)


# ------------------------------------------------------------------
# CRÉER / MODIFIER UNE SESSION
# ------------------------------------------------------------------
@bp.route('/nouvelle', methods=['GET', 'POST'])
@bp.route('/<int:sid>/modifier', methods=['GET', 'POST'])
@login_required
def form(sid=None):
    if not current_user.a_permission('sessions', 'creer' if not sid else 'modifier'):
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('sessions.liste'))

    session_obj = None
    if sid:
        session_obj = query("SELECT * FROM sessions WHERE id=?", (sid,), one=True)
        if not session_obj:
            flash('Session introuvable.', 'danger')
            return redirect(url_for('sessions.liste'))

    eid = edition_courante_id()
    intervenant_id = request.args.get('intervenant_id') or request.form.get('intervenant_id') or ''

    durees = query("""
        SELECT * FROM ref_durees_session
        WHERE edition_id = ? AND actif = 1
        ORDER BY ordre, duree_min
    """, (eid or 0,))

    if request.method == 'POST':
        eid_form = int(request.form.get('edition_id', eid or 0))
        data = {
            'edition_id':           eid_form,
            'titre':                request.form.get('titre', '').strip(),
            'description':          request.form.get('description', '').strip() or None,
            'theme_id':             request.form.get('theme_id') or None,
            'format_code':          request.form.get('format_code') or None,
            'langue_code':          request.form.get('langue_code', 'fr'),
            'niveau_code':          request.form.get('niveau_code', 'tout_public'),
            'duree_minutes':        int(request.form.get('duree_minutes') or 60),
            'est_focus':            1 if request.form.get('est_focus') else 0,
            'est_pays_honneur':     1 if request.form.get('est_pays_honneur') else 0,
            'est_18_35':            1 if request.form.get('est_18_35') else 0,
            'est_famille':          1 if request.form.get('est_famille') else 0,
            'est_shabbat':          1 if request.form.get('est_shabbat') else 0,
            'materiel_salle':       request.form.get('materiel_salle', '').strip() or None,
            'materiel_intervenant': request.form.get('materiel_intervenant', '').strip() or None,
            'besoin_micro':         1 if request.form.get('besoin_micro') else 0,
            'besoin_video':         1 if request.form.get('besoin_video') else 0,
            'besoin_sono':          1 if request.form.get('besoin_sono') else 0,
            'statut_code':          request.form.get('statut_code', 'brouillon'),
            'commentaire_equipe':   request.form.get('commentaire_equipe', '').strip() or None,
        }

        if not data['titre']:
            flash('Le titre est obligatoire.', 'danger')
        else:
            try:
                if sid:
                    cols = ', '.join(f"{k} = ?" for k in data.keys())
                    execute(f"UPDATE sessions SET {cols}, updated_at=datetime('now') WHERE id=?",
                            list(data.values()) + [sid])
                    flash('Session mise à jour.', 'success')
                    return redirect(url_for('sessions.fiche', sid=sid))
                else:
                    data['created_by'] = current_user.id
                    new_id = insert('sessions', data)
                    audit('CREATE', 'sessions', new_id,
                          utilisateur_id=current_user.id,
                          nouvelle_valeur=data['titre'])
                    iid_lien = request.form.get('intervenant_id', '').strip()
                    if iid_lien:
                        try:
                            insert('session_intervenants', {
                                'session_id':     new_id,
                                'intervenant_id': int(iid_lien),
                                'role_code':      'principal',
                                'ordre_affichage': 1,
                            })
                        except Exception:
                            pass
                        flash('Session créée et intervenant lié.', 'success')
                        return redirect(url_for('intervenants.fiche', iid=int(iid_lien)))
                    flash('Session créée.', 'success')
                    return redirect(url_for('sessions.fiche', sid=new_id))
            except Exception as e:
                flash(f'Erreur : {e}', 'danger')

    themes = query("""
        SELECT * FROM themes
        WHERE edition_id = ?
        UNION
        SELECT * FROM themes
        WHERE edition_id IS NULL
        AND code NOT IN (SELECT code FROM themes WHERE edition_id = ?)
        ORDER BY ordre
    """, (eid or 0, eid or 0))
    formats = query("SELECT * FROM ref_formats_session WHERE actif=1 ORDER BY libelle")
    langues = query("SELECT * FROM ref_langues WHERE actif=1")
    niveaux = query("SELECT * FROM ref_niveaux_session ORDER BY ordre")
    statuts = query("SELECT * FROM ref_statuts_session ORDER BY ordre")
    editions = query("SELECT * FROM editions ORDER BY annee DESC")
    edition_sel = query("SELECT * FROM editions WHERE id=?", (eid,), one=True) if eid else None

    return render_template('sessions/form.html',
                           session=session_obj,
                           themes=themes, formats=formats,
                           langues=langues, niveaux=niveaux, statuts=statuts,
                           editions=editions, edition_sel=edition_sel,
                           edition_id=eid, durees=durees,
                           intervenant_id=intervenant_id)


# ------------------------------------------------------------------
# AJOUTER / RETIRER UN INTERVENANT D'UNE SESSION
# ------------------------------------------------------------------
@bp.route('/<int:sid>/intervenant/ajouter', methods=['POST'])
@login_required
def intervenant_ajouter(sid):
    if not current_user.a_permission('sessions', 'modifier'):
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('sessions.fiche', sid=sid))
    try:
        insert('session_intervenants', {
            'session_id':    sid,
            'intervenant_id': request.form.get('intervenant_id'),
            'role_code':     request.form.get('role_code', 'principal'),
            'ordre_affichage': 1,
        })
        flash('Intervenant ajouté.', 'success')
    except Exception as e:
        flash(f'Erreur : {e}', 'danger')
    return redirect(url_for('sessions.fiche', sid=sid))


@bp.route('/<int:sid>/intervenant/<int:iid>/retirer', methods=['POST'])
@login_required
def intervenant_retirer(sid, iid):
    if not current_user.a_permission('sessions', 'modifier'):
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('sessions.fiche', sid=sid))
    execute("DELETE FROM session_intervenants WHERE session_id=? AND intervenant_id=?",
            (sid, iid))
    flash('Intervenant retiré.', 'success')
    return redirect(url_for('sessions.fiche', sid=sid))


# ------------------------------------------------------------------
# CRÉNEAUX
# ------------------------------------------------------------------
@bp.route('/<int:sid>/creneau/ajouter', methods=['POST'])
@login_required
def creneau_ajouter(sid):
    if not current_user.a_permission('sessions', 'modifier'):
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('sessions.fiche', sid=sid))

    session_obj = query("SELECT edition_id FROM sessions WHERE id=?", (sid,), one=True)
    try:
        insert('creneaux', {
            'session_id':  sid,
            'edition_id':  session_obj['edition_id'],
            'salle_id':    request.form.get('salle_id') or None,
            'jour':        request.form.get('jour'),
            'heure_debut': request.form.get('heure_debut'),
            'heure_fin':   request.form.get('heure_fin'),
            'statut_code': 'planifie',
            'note':        request.form.get('note', '').strip() or None,
        })
        flash('Créneau ajouté.', 'success')
    except Exception as e:
        flash(f'Erreur : {e}', 'danger')
    return redirect(url_for('sessions.fiche', sid=sid))


@bp.route('/creneau/<int:cid>/supprimer', methods=['POST'])
@login_required
def creneau_supprimer(cid):
    c = query("SELECT session_id FROM creneaux WHERE id=?", (cid,), one=True)
    execute("DELETE FROM creneaux WHERE id=?", (cid,))
    flash('Créneau supprimé.', 'success')
    return redirect(url_for('sessions.fiche', sid=c['session_id']))
