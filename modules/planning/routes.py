from flask import (Blueprint, render_template, flash, redirect,
                   url_for, request, jsonify, session as flask_session)
from flask_login import login_required, current_user
from database import query, execute, insert

bp = Blueprint("planning", __name__, template_folder="templates")

CRENEAUX_HORAIRES = [
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


@bp.route("/")
@login_required
def index():
    if not current_user.a_permission("planning", "voir_liste"):
        flash("Accès non autorisé.", "danger")
        return redirect(url_for("dashboard"))

    eid = _edition_courante_id()

    # Salles de l'édition
    salles = query(
        "SELECT * FROM salles WHERE edition_id=? AND actif=1 ORDER BY nom",
        (eid,)
    ) if eid else []

    # Sessions avec leurs créneaux (peut être None pour créneau)
    sessions_planifiees = []
    sessions_non_planifiees = []
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
        planifiees_ids = set()

        creneaux = query(
            "SELECT c.*, s.titre as session_titre, s.format_code, "
            "       t.couleur_hex as theme_couleur "
            "FROM creneaux c "
            "JOIN sessions s ON s.id = c.session_id "
            "LEFT JOIN themes t ON t.id = s.theme_id "
            "WHERE c.edition_id=? ORDER BY c.jour, c.heure_debut",
            (eid,)
        )

        for c in creneaux:
            planifiees_ids.add(c["session_id"])

        for s in toutes:
            if s["id"] in planifiees_ids:
                sessions_planifiees.append(s)
            else:
                sessions_non_planifiees.append(s)
    else:
        creneaux = []

    # Grouper les créneaux par (jour, heure_debut, salle_id) pour la grille
    grille = {}
    for c in creneaux:
        key = (c["jour"], c["heure_debut"][:5], c["salle_id"])
        grille[key] = c

    edition_sel = query("SELECT * FROM editions WHERE id=?", (eid,), one=True) if eid else None

    return render_template(
        "planning/index.html",
        salles=salles,
        sessions_planifiees=sessions_planifiees,
        sessions_non_planifiees=sessions_non_planifiees,
        creneaux=creneaux,
        grille=grille,
        jours=JOURS,
        creneaux_horaires=CRENEAUX_HORAIRES,
        edition_sel=edition_sel,
        edition_id=eid,
    )


@bp.route("/deplacer-session", methods=["POST"])
@login_required
def deplacer_session():
    if not current_user.a_permission("planning", "modifier"):
        return jsonify({"error": "Non autorisé"}), 403

    data = request.get_json(silent=True) or {}
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
            # Déplacer un créneau existant
            execute(
                "UPDATE creneaux SET salle_id=?, jour=?, heure_debut=?, heure_fin=?, "
                "updated_at=datetime('now') WHERE id=?",
                (salle_id, jour, heure_debut, heure_fin, creneau_id),
            )
        else:
            # Créer un nouveau créneau pour cette session
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

    data = request.get_json(silent=True) or {}
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
