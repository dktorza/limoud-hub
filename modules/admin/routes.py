from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from functools import wraps
from database import query, execute, insert, row_to_dict, rows_to_list, audit

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
    raw = query("SELECT * FROM utilisateurs ORDER BY nom, prenom")
    utilisateurs = rows_to_list(raw)
    for u in utilisateurs:
        u['roles'] = query("""
            SELECT r.libelle, r.couleur_hex, r.code
            FROM utilisateur_roles ur
            JOIN roles r ON r.code = ur.role_code
            WHERE ur.utilisateur_id = ? AND ur.actif = 1
              AND (ur.expire_le IS NULL OR ur.expire_le > datetime('now'))
            ORDER BY r.ordre
        """, (u['id'],))
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
                'nom': nom, 'prenom': prenom, 'telephone': tel,
                'actif': 1, 'doit_changer_mdp': 1,
            })
            return render_template('admin/utilisateur_form.html',
                                   utilisateur=None,
                                   mdp_prov=mdp_prov,
                                   new_uid=uid,
                                   new_nom=f"{prenom} {nom}")
        except Exception as e:
            flash(f'Erreur : {e}', 'danger')
    return render_template('admin/utilisateur_form.html', utilisateur=None)

@bp.route('/utilisateurs/<int:uid>/modifier', methods=['GET', 'POST'])
@admin_requis
def utilisateur_modifier(uid):
    utilisateur = query("SELECT * FROM utilisateurs WHERE id=?", (uid,), one=True)
    if not utilisateur:
        flash('Utilisateur introuvable.', 'danger')
        return redirect(url_for('admin.utilisateurs_liste'))

    mdp_prov = None
    if request.method == 'POST':
        from werkzeug.security import generate_password_hash
        action = request.form.get('action', 'sauvegarder')

        if action == 'reinitialiser_mdp':
            import secrets, string
            mdp_prov = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
            execute("""
                UPDATE utilisateurs
                SET password_hash=?, doit_changer_mdp=1, updated_at=datetime('now')
                WHERE id=?
            """, (generate_password_hash(mdp_prov), uid))
            flash('Mot de passe réinitialisé.', 'success')
            utilisateur = query("SELECT * FROM utilisateurs WHERE id=?", (uid,), one=True)
            return render_template('admin/utilisateur_form.html',
                                   utilisateur=utilisateur,
                                   mdp_prov=mdp_prov,
                                   mode='modifier')
        else:
            email  = request.form.get('email', '').strip().lower()
            prenom = request.form.get('prenom', '').strip()
            nom    = request.form.get('nom', '').strip()
            tel    = request.form.get('telephone', '').strip()
            actif  = 1 if request.form.get('actif') else 0
            try:
                execute("""
                    UPDATE utilisateurs
                    SET email=?, prenom=?, nom=?, telephone=?, actif=?,
                        updated_at=datetime('now')
                    WHERE id=?
                """, (email, prenom, nom, tel, actif, uid))
                flash('Utilisateur mis à jour.', 'success')
                return redirect(url_for('admin.utilisateurs_liste'))
            except Exception as e:
                flash(f'Erreur : {e}', 'danger')

    return render_template('admin/utilisateur_form.html',
                           utilisateur=utilisateur,
                           mode='modifier')


@bp.route('/utilisateurs/<int:uid>/desactiver', methods=['POST'])
@admin_requis
def utilisateur_desactiver(uid):
    if uid == current_user.id:
        flash('Vous ne pouvez pas désactiver votre propre compte.', 'danger')
        return redirect(url_for('admin.utilisateurs_liste'))
    execute("UPDATE utilisateurs SET actif=0, updated_at=datetime('now') WHERE id=?", (uid,))
    flash('Utilisateur désactivé.', 'success')
    return redirect(url_for('admin.utilisateurs_liste'))


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
    roles = query("""
        SELECT r.*,
               COUNT(DISTINCT p.id)  as nb_permissions,
               COUNT(DISTINCT ur.utilisateur_id) as nb_utilisateurs
        FROM roles r
        LEFT JOIN permissions p ON p.role_code = r.code
        LEFT JOIN utilisateur_roles ur ON ur.role_code = r.code AND ur.actif = 1
        GROUP BY r.code
        ORDER BY r.ordre
    """)
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

_PERMISSION_TEMPLATES = {
    'lecteur': [
        ('intervenants', 'voir_liste'), ('intervenants', 'voir_fiche'),
        ('sessions',     'voir_liste'), ('sessions',     'voir_fiche'),
        ('planning',     'voir_liste'), ('participants',  'voir_liste'),
    ],
    'editeur': [
        ('intervenants', 'voir_liste'), ('intervenants', 'voir_fiche'),
        ('intervenants', 'modifier'),
        ('sessions',     'voir_liste'), ('sessions',     'voir_fiche'),
        ('sessions',     'modifier'),
        ('planning',     'voir_liste'), ('participants',  'voir_liste'),
        ('badges',       'voir_liste'),
    ],
    'responsable': [
        ('intervenants', 'voir_liste'), ('intervenants', 'voir_fiche'),
        ('intervenants', 'creer'),      ('intervenants', 'modifier'),
        ('sessions',     'voir_liste'), ('sessions',     'voir_fiche'),
        ('sessions',     'creer'),      ('sessions',     'modifier'),
        ('planning',     'voir_liste'), ('participants',  'voir_liste'),
        ('badges',       'voir_liste'), ('helloasso',     'voir_liste'),
        ('livret',       'voir_liste'), ('admin',         'voir_liste'),
    ],
}


@bp.route('/roles/nouveau', methods=['GET', 'POST'])
@admin_requis
def role_nouveau():
    if request.method == 'POST':
        code    = request.form.get('code', '').strip().lower().replace(' ', '_')
        libelle = request.form.get('libelle', '').strip()
        desc    = request.form.get('description', '').strip() or None
        couleur = request.form.get('couleur_hex', '#6c757d').strip()
        tpl     = request.form.get('template_permissions', '')

        erreurs = []
        if not code or not code.replace('_', '').isalnum():
            erreurs.append('Le code ne doit contenir que des lettres, chiffres et underscores.')
        if not libelle:
            erreurs.append('Le libellé est obligatoire.')
        if not erreurs and query("SELECT code FROM roles WHERE code = ?", (code,), one=True):
            erreurs.append(f'Le code "{code}" existe déjà.')

        if erreurs:
            for e in erreurs:
                flash(e, 'danger')
            return render_template('admin/role_form.html', role=None,
                                   templates=list(_PERMISSION_TEMPLATES.keys()))

        try:
            insert('roles', {'code': code, 'libelle': libelle,
                             'description': desc, 'couleur_hex': couleur,
                             'est_systeme': 0, 'ordre': 999})
            if tpl and tpl in _PERMISSION_TEMPLATES:
                for module, action in _PERMISSION_TEMPLATES[tpl]:
                    execute("""
                        INSERT OR IGNORE INTO permissions (role_code, module, action, champ, autorise)
                        VALUES (?, ?, ?, NULL, 1)
                    """, (code, module, action))
            flash(f'Rôle "{libelle}" créé.', 'success')
            return redirect(url_for('admin.role_detail', code=code))
        except Exception as e:
            flash(f'Erreur : {e}', 'danger')

    return render_template('admin/role_form.html', role=None,
                           templates=list(_PERMISSION_TEMPLATES.keys()))


@bp.route('/roles/<code>')
@admin_requis
def role_detail(code):
    role = query("SELECT * FROM roles WHERE code = ?", (code,), one=True)
    if not role:
        flash('Rôle introuvable.', 'danger')
        return redirect(url_for('admin.roles_liste'))
    permissions = query("SELECT * FROM permissions WHERE role_code = ? ORDER BY module, action", (code,))
    utilisateurs = query("""
        SELECT u.prenom, u.nom, u.email, ur.edition_id, ur.organisation_id,
               ur.expire_le, ur.id as ur_id
        FROM utilisateur_roles ur
        JOIN utilisateurs u ON u.id = ur.utilisateur_id
        WHERE ur.role_code = ? AND ur.actif = 1
        ORDER BY u.nom, u.prenom
    """, (code,))
    return render_template('admin/role_detail.html',
                           role=role, permissions=permissions,
                           utilisateurs=utilisateurs)


@bp.route('/roles/<code>/permission', methods=['POST'])
@admin_requis
def role_permission_add(code):
    if not query("SELECT code FROM roles WHERE code = ?", (code,), one=True):
        flash('Rôle introuvable.', 'danger')
        return redirect(url_for('admin.roles_liste'))
    module   = request.form.get('module', '').strip()
    action   = request.form.get('action', '').strip()
    champ    = request.form.get('champ', '').strip() or None
    autorise = 1 if request.form.get('autorise') else 0
    if not module or not action:
        flash('Module et action sont obligatoires.', 'danger')
        return redirect(url_for('admin.role_detail', code=code))
    execute("""
        INSERT INTO permissions (role_code, module, action, champ, autorise)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(role_code, module, action, champ) DO UPDATE SET autorise = excluded.autorise
    """, (code, module, action, champ, autorise))
    flash('Permission mise à jour.', 'success')
    return redirect(url_for('admin.role_detail', code=code))


@bp.route('/roles/<code>/permission/<int:pid>/supprimer', methods=['POST'])
@admin_requis
def role_permission_suppr(code, pid):
    execute("DELETE FROM permissions WHERE id = ? AND role_code = ?", (pid, code))
    flash('Permission supprimée.', 'success')
    return redirect(url_for('admin.role_detail', code=code))


@bp.route('/roles/<code>/dupliquer', methods=['GET', 'POST'])
@admin_requis
def role_dupliquer(code):
    source = query("SELECT * FROM roles WHERE code = ?", (code,), one=True)
    if not source:
        flash('Rôle introuvable.', 'danger')
        return redirect(url_for('admin.roles_liste'))
    if request.method == 'POST':
        nouveau_code = request.form.get('nouveau_code', '').strip().lower()
        nouveau_lib  = request.form.get('nouveau_libelle', '').strip()
        if not nouveau_code or not nouveau_lib:
            flash('Code et libellé obligatoires.', 'danger')
            return render_template('admin/role_form.html', role=source,
                                   duplicating=True, templates=[])
        if query("SELECT code FROM roles WHERE code = ?", (nouveau_code,), one=True):
            flash(f'Le code "{nouveau_code}" existe déjà.', 'danger')
            return render_template('admin/role_form.html', role=source,
                                   duplicating=True, templates=[])
        try:
            insert('roles', {'code': nouveau_code, 'libelle': nouveau_lib,
                             'description': source['description'],
                             'couleur_hex': source['couleur_hex'],
                             'est_systeme': 0, 'ordre': 999})
            perms = query("SELECT module, action, champ, autorise FROM permissions WHERE role_code = ?", (code,))
            for p in perms:
                execute("""
                    INSERT OR IGNORE INTO permissions (role_code, module, action, champ, autorise)
                    VALUES (?, ?, ?, ?, ?)
                """, (nouveau_code, p['module'], p['action'], p['champ'], p['autorise']))
            flash(f'Rôle dupliqué en "{nouveau_lib}".', 'success')
            return redirect(url_for('admin.role_detail', code=nouveau_code))
        except Exception as e:
            flash(f'Erreur : {e}', 'danger')
    return render_template('admin/role_form.html', role=source,
                           duplicating=True, templates=[])


@bp.route('/audit')
@admin_requis
def audit_log():
    logs = query("SELECT a.*, u.nom || ' ' || u.prenom as user_nom FROM audit_log a LEFT JOIN utilisateurs u ON u.id = a.utilisateur_id ORDER BY a.created_at DESC LIMIT 100")
    return render_template('admin/audit_log.html', logs=logs)

@bp.route('/references')
@admin_requis
def references_liste():
    return render_template('admin/references_liste.html')
