from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from functools import wraps
from database import query, execute, insert, row_to_dict, audit

bp = Blueprint('admin', __name__, template_folder='templates')

def admin_requis(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.a_permission('admin', 'voir_liste'):
            flash('Accès non autorisé.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

@bp.route('/')
@admin_requis
def tableau_de_bord():
    stats = {
        'nb_utilisateurs': query("SELECT COUNT(*) as n FROM utilisateurs WHERE actif=1", one=True)['n'],
        'nb_roles': query("SELECT COUNT(*) as n FROM roles", one=True)['n'],
        'nb_organisations': query("SELECT COUNT(*) as n FROM organisations WHERE actif=1", one=True)['n'],
        'nb_editions': query("SELECT COUNT(*) as n FROM editions", one=True)['n'],
    }
    return render_template('admin/tableau_de_bord.html', stats=stats)

@bp.route('/utilisateurs')
@admin_requis
def utilisateurs_liste():
    utilisateurs = query("SELECT u.*, COUNT(DISTINCT ur.role_code) as nb_roles FROM utilisateurs u LEFT JOIN utilisateur_roles ur ON ur.utilisateur_id = u.id AND ur.actif = 1 GROUP BY u.id ORDER BY u.nom, u.prenom")
    return render_template('admin/utilisateurs_liste.html', utilisateurs=utilisateurs)

@bp.route('/utilisateurs/nouveau', methods=['GET', 'POST'])
@admin_requis
def utilisateur_nouveau():
    if request.method == 'POST':
        import secrets, string
        from werkzeug.security import generate_password_hash
        email  = request.form.get('email', '').strip().lower()
        prenom = request.form.get('prenom', '').strip()
        nom    = request.form.get('nom', '').strip()
        tel    = request.form.get('telephone', '').strip()
        mdp_prov = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
        try:
            uid = insert('utilisateurs', {
                'email': email, 'password_hash': generate_password_hash(mdp_prov),
                'nom': nom, 'prenom': prenom, 'telephone': tel, 'actif': 1,
            })
            flash(f'Utilisateur créé ! Mot de passe provisoire : {mdp_prov}', 'success')
            return redirect(url_for('admin.utilisateur_roles_edit', uid=uid))
        except Exception as e:
            flash(f'Erreur : {e}', 'danger')
    return render_template('admin/utilisateur_form.html', utilisateur=None)

@bp.route('/utilisateurs/<int:uid>/roles', methods=['GET', 'POST'])
@admin_requis
def utilisateur_roles_edit(uid):
    utilisateur = query("SELECT * FROM utilisateurs WHERE id=?", (uid,), one=True)
    if not utilisateur:
        flash('Introuvable.', 'danger')
        return redirect(url_for('admin.utilisateurs_liste'))
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'ajouter_role':
            try:
                insert('utilisateur_roles', {
                    'utilisateur_id': uid,
                    'role_code': request.form.get('role_code'),
                    'organisation_id': request.form.get('organisation_id') or None,
                    'edition_id': request.form.get('edition_id') or None,
                    'actif': 1, 'attribue_par': current_user.id,
                    'expire_le': request.form.get('expire_le') or None,
                })
                flash('Rôle ajouté.', 'success')
            except Exception as e:
                flash(f'Erreur : {e}', 'danger')
        elif action == 'supprimer_role':
            execute("UPDATE utilisateur_roles SET actif=0 WHERE id=?", (request.form.get('role_id'),))
            flash('Rôle retiré.', 'success')
        return redirect(url_for('admin.utilisateur_roles_edit', uid=uid))
    roles_utilisateur = query("SELECT ur.*, r.libelle, r.couleur_hex, o.nom as org_nom, e.nom as edition_nom FROM utilisateur_roles ur JOIN roles r ON r.code = ur.role_code LEFT JOIN organisations o ON o.id = ur.organisation_id LEFT JOIN editions e ON e.id = ur.edition_id WHERE ur.utilisateur_id = ? AND ur.actif = 1", (uid,))
    return render_template('admin/utilisateur_roles.html',
        utilisateur=utilisateur,
        roles_utilisateur=roles_utilisateur,
        tous_les_roles=query("SELECT * FROM roles ORDER BY ordre"),
        toutes_les_orgas=query("SELECT * FROM organisations WHERE actif=1"),
        toutes_les_editions=query("SELECT * FROM editions ORDER BY annee DESC"))

@bp.route('/roles')
@admin_requis
def roles_liste():
    roles = query("SELECT * FROM roles ORDER BY ordre")
    return render_template('admin/roles_liste.html', roles=roles)

@bp.route('/editions')
@admin_requis
def editions_liste():
    editions = query("SELECT e.*, o.nom as org_nom, s.libelle as statut_libelle, s.couleur_hex as statut_couleur FROM editions e JOIN organisations o ON o.id = e.organisation_id LEFT JOIN ref_statuts_edition s ON s.code = e.statut_code ORDER BY e.annee DESC")
    return render_template('admin/editions_liste.html', editions=editions)

@bp.route('/editions/nouvelle', methods=['GET', 'POST'])
@admin_requis
def edition_nouvelle():
    if request.method == 'POST':
        data = {
            'organisation_id':    request.form.get('organisation_id'),
            'nom':                request.form.get('nom'),
            'slug':               request.form.get('slug'),
            'annee':              request.form.get('annee'),
            'date_debut':         request.form.get('date_debut') or None,
            'date_fin':           request.form.get('date_fin') or None,
            'theme_principal':    request.form.get('theme_principal') or None,
            'ha_organisation_slug': request.form.get('ha_organisation_slug') or None,
            'couleur_principale': request.form.get('couleur_principale', '#1a5276'),
            'couleur_secondaire': request.form.get('couleur_secondaire', '#e97132'),
            'statut_code':        'en_preparation',
        }
        try:
            insert('editions', data)
            flash('Edition créée avec succès.', 'success')
            return redirect(url_for('admin.editions_liste'))
        except Exception as e:
            flash(f'Erreur : {e}', 'danger')
    organisations = query("SELECT * FROM organisations WHERE actif=1")
    return render_template('admin/edition_form.html', edition=None, organisations=organisations)

@bp.route('/editions/<int:eid>/durees', methods=['GET', 'POST'])
@admin_requis
def edition_durees(eid):
    edition = query("SELECT * FROM editions WHERE id=?", (eid,), one=True)
    if not edition:
        flash('Édition introuvable.', 'danger')
        return redirect(url_for('admin.editions_liste'))
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'ajouter':
            duree_min = request.form.get('duree_min', '').strip()
            libelle   = request.form.get('libelle', '').strip()
            ordre     = request.form.get('ordre', '0').strip() or '0'
            if not duree_min or not libelle:
                flash('La durée (minutes) et le libellé sont obligatoires.', 'danger')
            else:
                try:
                    insert('ref_durees_session', {
                        'edition_id': eid,
                        'duree_min':  int(duree_min),
                        'libelle':    libelle,
                        'ordre':      int(ordre),
                        'actif':      1,
                    })
                    flash('Durée ajoutée.', 'success')
                except Exception as e:
                    flash(f'Erreur : {e}', 'danger')
        elif action == 'supprimer':
            did = request.form.get('duree_id')
            execute("DELETE FROM ref_durees_session WHERE id=? AND edition_id=?", (did, eid))
            flash('Durée supprimée.', 'success')
        return redirect(url_for('admin.edition_durees', eid=eid))
    durees = query("SELECT * FROM ref_durees_session WHERE edition_id=? ORDER BY ordre, duree_min", (eid,))
    return render_template('admin/edition_durees.html', edition=edition, durees=durees)

@bp.route('/audit')
@admin_requis
def audit_log():
    logs = query("SELECT a.*, u.nom || ' ' || u.prenom as user_nom FROM audit_log a LEFT JOIN utilisateurs u ON u.id = a.utilisateur_id ORDER BY a.created_at DESC LIMIT 100")
    return render_template('admin/audit_log.html', logs=logs)

@bp.route('/references')
@admin_requis
def references_liste():
    return render_template('admin/references_liste.html')
