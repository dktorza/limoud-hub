from flask import (Blueprint, render_template, flash, redirect,
                   url_for, request, jsonify, session as flask_session)
from flask_login import login_required, current_user
from database import query, execute, insert

bp = Blueprint("planning", __name__, template_folder="templates")

# Créneaux par défaut si aucune plage définie en BDD pour l'édition
CRENEAUX_DEFAUT = [
    "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
    "12:00", "12:30", "14:00", "14:30", "15:00", "15:30",
    "16:00", "16:30", "17:00", "17:30", "18:00", "19:00",
    "20:00", "21:00",
]
JOURS = ["Vendredi", "Samedi", "Dimanche"]


def _edition_courante_id():
    eid = flask_session.get("edition_id")
    if eid:
        return eid
    row = query(
        "SELECT id FROM editions WHERE statut_code != 'archivee' "
        "ORDER BY date_debut DESC LIMIT 1",
        one=True,
    )
    return row["id"] if row else None


def _creneaux_pour_edition(eid):
    """Retourne la liste des horaires ouverts pour l'édition (depuis BDD ou défaut)."""
    if not eid:
        return CRENEAUX_DEFAUT
    plages = query(
        "SELECT heure_debut FROM plages_horaires "
        "WHERE edition_id=? AND ouvert=1 ORDER BY jour, heure_debut",
        (eid,)
    )
    if not plages:
        return CRENEAUX_DEFAUT
    seen = set()
    result = []
    for p in plages:
        h = p["heure_debut"][:5]
        if h not in seen:
            seen.add(h)
            result.append(h)
    return sorted(result)


# ── Planning principal ───────────────────────────────────────────────────────

@bp.route("/")
@login_required
def index():
    if not current_user.a_permission("planning", "voir_liste"):
        flash("Accès non autorisé.", "danger")
        return redirect(url_for("dashboard"))

    eid = _edition_courante_id()
    salles = query(
        "SELECT * FROM salles WHERE edition_id=? AND actif=1 ORDER BY nom", (eid,)
    ) if eid else []

    sessions_planifiees   = []
    sessions_non_planifiees = []
    creneaux = []
    if eid:
        toutes = query(
            "SELECT s.id, s.titre, s.format_code, s.statut_code, "
            "       t.couleur_hex as theme_couleur, "
            "       GROUP_CONCAT(i.prenom || ' ' || i.nom, ', ') as intervenants "
            "FROM sessions s "
            "LEFT JOIN themes t ON t.id = s.theme_id "
            "LEFT JOIN session_intervenants si ON si.session_id = s.id "
            "LEFT JOIN intervenants i ON i.id = si.intervenant_id "
            "WHERE s.edition_id=? AND s.statut_code != 'annule' "
            "GROUP BY s.id ORDER BY s.titre",
            (eid,)
        )
        creneaux = query(
            "SELECT c.*, s.titre as session_titre, s.format_code, "
            "       t.couleur_hex as theme_couleur "
            "FROM creneaux c "
            "JOIN sessions s ON s.id = c.session_id "
            "LEFT JOIN themes t ON t.id = s.theme_id "
            "WHERE c.edition_id=? ORDER BY c.jour, c.heure_debut",
            (eid,)
        )
        planifiees_ids = {c["session_id"] for c in creneaux}
        for s in toutes:
            if s["id"] in planifiees_ids:
                sessions_planifiees.append(s)
            else:
                sessions_non_planifiees.append(s)

    grille = {}
    for c in creneaux:
        key = (c["jour"], c["heure_debut"][:5], c["salle_id"])
        grille[key] = c

    creneaux_horaires = _creneaux_pour_edition(eid)
    edition_sel = query("SELECT * FROM editions WHERE id=?", (eid,), one=True) if eid else None

    return render_template(
        "planning/index.html",
        salles=salles,
        sessions_planifiees=sessions_planifiees,
        sessions_non_planifiees=sessions_non_planifiees,
        creneaux=creneaux,
        grille=grille,
        jours=JOURS,
        creneaux_horaires=creneaux_horaires,
        edition_sel=edition_sel,
        edition_id=eid,
    )


# ── API planning ─────────────────────────────────────────────────────────────

@bp.route("/deplacer-session", methods=["POST"])
@login_required
def deplacer_session():
    if not current_user.a_permission("planning", "modifier"):
        return jsonify({"error": "Non autorisé"}), 403

    data        = request.get_json(silent=True) or {}
    session_id  = data.get("session_id")
    creneau_id  = data.get("creneau_id")
    salle_id    = data.get("salle_id")
    jour        = data.get("jour")
    heure_debut = data.get("heure_debut")
    heure_fin   = data.get("heure_fin")

    if not session_id:
        return jsonify({"error": "session_id manquant"}), 400

    try:
        if creneau_id:
            execute(
                "UPDATE creneaux SET salle_id=?, jour=?, heure_debut=?, heure_fin=?, "
                "updated_at=datetime('now') WHERE id=?",
                (salle_id, jour, heure_debut, heure_fin, creneau_id),
            )
        else:
            eid = _edition_courante_id()
            creneau_id = insert("creneaux", {
                "session_id":  session_id,
                "edition_id":  eid,
                "salle_id":    salle_id,
                "jour":        jour,
                "heure_debut": heure_debut,
                "heure_fin":   heure_fin or heure_debut,
                "statut_code": "planifie",
            })
        return jsonify({"ok": True, "creneau_id": creneau_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/creer-creneau", methods=["POST"])
@login_required
def creer_creneau():
    if not current_user.a_permission("planning", "modifier"):
        return jsonify({"error": "Non autorisé"}), 403

    data        = request.get_json(silent=True) or {}
    session_id  = data.get("session_id")
    jour        = data.get("jour")
    heure_debut = data.get("heure_debut")
    heure_fin   = data.get("heure_fin")
    salle_id    = data.get("salle_id")

    if not all([session_id, jour, heure_debut]):
        return jsonify({"error": "Paramètres manquants"}), 400

    try:
        eid = _edition_courante_id()
        creneau_id = insert("creneaux", {
            "session_id":  session_id,
            "edition_id":  eid,
            "salle_id":    salle_id,
            "jour":        jour,
            "heure_debut": heure_debut,
            "heure_fin":   heure_fin or heure_debut,
            "statut_code": "planifie",
        })
        return jsonify({"ok": True, "creneau_id": creneau_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Gestion des salles ───────────────────────────────────────────────────────

@bp.route("/salles")
@login_required
def salles_liste():
    if not current_user.a_permission("planning", "voir_liste"):
        flash("Accès non autorisé.", "danger")
        return redirect(url_for("dashboard"))

    eid = _edition_courante_id()
    salles = query(
        "SELECT * FROM salles WHERE edition_id=? ORDER BY actif DESC, nom", (eid,)
    ) if eid else []
    edition_sel = query("SELECT * FROM editions WHERE id=?", (eid,), one=True) if eid else None

    return render_template(
        "planning/salles.html",
        salles=salles,
        edition_sel=edition_sel,
        edition_id=eid,
    )


@bp.route("/salles/creer", methods=["POST"])
@login_required
def salle_creer():
    if not current_user.a_permission("planning", "modifier"):
        flash("Accès non autorisé.", "danger")
        return redirect(url_for("planning.salles_liste"))

    eid = _edition_courante_id()
    if not eid:
        flash("Aucune édition active.", "warning")
        return redirect(url_for("planning.salles_liste"))

    nom = request.form.get("nom", "").strip()
    if not nom:
        flash("Le nom est obligatoire.", "warning")
        return redirect(url_for("planning.salles_liste"))

    try:
        insert("salles", {
            "edition_id": eid,
            "nom":         nom,
            "capacite":    request.form.get("capacite") or None,
            "etage":       request.form.get("etage", "").strip() or None,
            "type_salle":  request.form.get("type_salle", "").strip() or None,
            "note":        request.form.get("note", "").strip() or None,
            "actif":       1,
        })
        flash(f"Salle « {nom} » créée.", "success")
    except Exception as e:
        flash(f"Erreur : {e}", "danger")

    return redirect(url_for("planning.salles_liste"))


@bp.route("/salles/<int:salle_id>/modifier", methods=["POST"])
@login_required
def salle_modifier(salle_id):
    if not current_user.a_permission("planning", "modifier"):
        flash("Accès non autorisé.", "danger")
        return redirect(url_for("planning.salles_liste"))

    nom = request.form.get("nom", "").strip()
    if not nom:
        flash("Le nom est obligatoire.", "warning")
        return redirect(url_for("planning.salles_liste"))

    execute(
        "UPDATE salles SET nom=?, capacite=?, etage=?, type_salle=?, note=? WHERE id=?",
        (nom,
         request.form.get("capacite") or None,
         request.form.get("etage", "").strip() or None,
         request.form.get("type_salle", "").strip() or None,
         request.form.get("note", "").strip() or None,
         salle_id),
    )
    flash("Salle mise à jour.", "success")
    return redirect(url_for("planning.salles_liste"))


@bp.route("/salles/<int:salle_id>/desactiver", methods=["POST"])
@login_required
def salle_desactiver(salle_id):
    if not current_user.a_permission("planning", "modifier"):
        flash("Accès non autorisé.", "danger")
        return redirect(url_for("planning.salles_liste"))
    execute("UPDATE salles SET actif=0 WHERE id=?", (salle_id,))
    flash("Salle désactivée.", "success")
    return redirect(url_for("planning.salles_liste"))


@bp.route("/salles/<int:salle_id>/reactiver", methods=["POST"])
@login_required
def salle_reactiver(salle_id):
    if not current_user.a_permission("planning", "modifier"):
        flash("Accès non autorisé.", "danger")
        return redirect(url_for("planning.salles_liste"))
    execute("UPDATE salles SET actif=1 WHERE id=?", (salle_id,))
    flash("Salle réactivée.", "success")
    return redirect(url_for("planning.salles_liste"))


# ── Gestion des plages horaires ──────────────────────────────────────────────

@bp.route("/plages")
@login_required
def plages_liste():
    if not current_user.a_permission("planning", "voir_liste"):
        flash("Accès non autorisé.", "danger")
        return redirect(url_for("dashboard"))

    eid = _edition_courante_id()
    plages = query(
        "SELECT * FROM plages_horaires WHERE edition_id=? ORDER BY jour, heure_debut",
        (eid,)
    ) if eid else []
    edition_sel = query("SELECT * FROM editions WHERE id=?", (eid,), one=True) if eid else None

    # Grouper par jour pour l'affichage
    par_jour = {j: [] for j in JOURS}
    for p in plages:
        if p["jour"] in par_jour:
            par_jour[p["jour"]].append(p)

    return render_template(
        "planning/plages.html",
        par_jour=par_jour,
        jours=JOURS,
        plages=plages,
        edition_sel=edition_sel,
        edition_id=eid,
        creneaux_defaut=CRENEAUX_DEFAUT,
    )


@bp.route("/plages/ajouter", methods=["POST"])
@login_required
def plage_ajouter():
    if not current_user.a_permission("planning", "modifier"):
        flash("Accès non autorisé.", "danger")
        return redirect(url_for("planning.plages_liste"))

    eid = _edition_courante_id()
    if not eid:
        flash("Aucune édition active.", "warning")
        return redirect(url_for("planning.plages_liste"))

    jour        = request.form.get("jour", "").strip()
    heure_debut = (request.form.get("heure_debut", "") or "")[:5]
    ouvert      = 1 if request.form.get("ouvert") else 0

    if not jour or not heure_debut:
        flash("Jour et heure requis.", "warning")
        return redirect(url_for("planning.plages_liste"))

    try:
        insert("plages_horaires", {
            "edition_id":  eid,
            "jour":        jour,
            "heure_debut": heure_debut,
            "ouvert":      ouvert,
        })
        flash(f"Plage {jour} {heure_debut} ajoutée.", "success")
    except Exception as e:
        if "UNIQUE" in str(e):
            flash("Cette plage existe déjà.", "warning")
        else:
            flash(f"Erreur : {e}", "danger")

    return redirect(url_for("planning.plages_liste"))


@bp.route("/plages/<int:plage_id>/supprimer", methods=["POST"])
@login_required
def plage_supprimer(plage_id):
    if not current_user.a_permission("planning", "modifier"):
        flash("Accès non autorisé.", "danger")
        return redirect(url_for("planning.plages_liste"))
    execute("DELETE FROM plages_horaires WHERE id=?", (plage_id,))
    flash("Plage supprimée.", "success")
    return redirect(url_for("planning.plages_liste"))


@bp.route("/plages/init-defaut", methods=["POST"])
@login_required
def plages_init_defaut():
    """Initialise les plages avec la liste CRENEAUX_DEFAUT pour les 3 jours."""
    if not current_user.a_permission("planning", "modifier"):
        flash("Accès non autorisé.", "danger")
        return redirect(url_for("planning.plages_liste"))

    eid = _edition_courante_id()
    if not eid:
        flash("Aucune édition active.", "warning")
        return redirect(url_for("planning.plages_liste"))

    nb = 0
    for jour in JOURS:
        for h in CRENEAUX_DEFAUT:
            try:
                insert("plages_horaires", {
                    "edition_id":  eid,
                    "jour":        jour,
                    "heure_debut": h,
                    "ouvert":      1,
                })
                nb += 1
            except Exception:
                pass  # UNIQUE constraint = déjà existant

    flash(f"{nb} plage(s) initialisée(s) avec les horaires par défaut.", "success")
    return redirect(url_for("planning.plages_liste"))
