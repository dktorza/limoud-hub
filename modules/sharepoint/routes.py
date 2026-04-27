from flask import (Blueprint, render_template, flash, redirect,
                   url_for, current_app, request, jsonify,
                   session as flask_session)
from flask_login import login_required, current_user
from database import query, execute, insert
from .client import SharePointClient

bp = Blueprint("sharepoint", __name__, template_folder="templates")


def _get_client():
    cfg = current_app.config
    return SharePointClient(
        tenant_id     = cfg.get("SHAREPOINT_TENANT_ID", ""),
        client_id     = cfg.get("SHAREPOINT_CLIENT_ID", ""),
        client_secret = cfg.get("SHAREPOINT_CLIENT_SECRET", ""),
        site_url      = cfg.get("SHAREPOINT_SITE_URL", ""),
    )


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


def _check_admin():
    if not current_user.a_permission("admin", "voir_liste"):
        flash("Accès non autorisé.", "danger")
        return False
    return True


# ── Index ───────────────────────────────────────────────────────────────────

@bp.route("/")
@login_required
def index():
    if not _check_admin():
        return redirect(url_for("dashboard"))

    cfg = current_app.config
    config_ok = all([
        cfg.get("SHAREPOINT_TENANT_ID"),
        cfg.get("SHAREPOINT_CLIENT_ID"),
        cfg.get("SHAREPOINT_CLIENT_SECRET"),
        cfg.get("SHAREPOINT_SITE_URL"),
    ])
    eid = _edition_courante_id()
    edition = query("SELECT * FROM editions WHERE id=?", (eid,), one=True) if eid else None
    nb_salles = query(
        "SELECT COUNT(*) as n FROM salles WHERE edition_id=? AND actif=1", (eid,), one=True
    )["n"] if eid else 0
    nb_plages = query(
        "SELECT COUNT(*) as n FROM plages_horaires WHERE edition_id=?", (eid,), one=True
    )["n"] if eid else 0

    return render_template(
        "sharepoint/index.html",
        config_ok=config_ok,
        edition=edition,
        nb_salles=nb_salles,
        nb_plages=nb_plages,
    )


# ── Test connexion ───────────────────────────────────────────────────────────

@bp.route("/test-connexion")
@login_required
def test_connexion():
    if not _check_admin():
        return redirect(url_for("dashboard"))

    client = _get_client()
    listes = None
    erreur = None
    token_ok = False

    try:
        client._get_token()
        token_ok = True
        listes = client.get_available_lists()
    except Exception as e:
        erreur = str(e)

    return render_template(
        "sharepoint/test.html",
        token_ok=token_ok,
        listes=listes,
        erreur=erreur,
        preview=None,
    )


# ── Salles ───────────────────────────────────────────────────────────────────

@bp.route("/salles")
@login_required
def preview_salles():
    if not _check_admin():
        return redirect(url_for("dashboard"))

    list_name = "Salles Interventions 2026"
    client = _get_client()
    items_sp = None
    erreur = None
    token_ok = False
    eid = _edition_courante_id()
    edition = query("SELECT * FROM editions WHERE id=?", (eid,), one=True) if eid else None
    salles_bdd = query(
        "SELECT * FROM salles WHERE edition_id=? ORDER BY nom", (eid,)
    ) if eid else []

    try:
        client._get_token()
        token_ok = True
        items_sp = client.get_list_items(
            list_name,
            select=["Id", "Title", "Capacite", "Etage", "TypeSalle", "Note"],
            top=200,
        )
        # Mapper chaque item SP
        items_sp = [client.map_item(list_name, it) for it in items_sp]
    except Exception as e:
        erreur = str(e)

    return render_template(
        "sharepoint/salles.html",
        token_ok=token_ok,
        items_sp=items_sp,
        salles_bdd=salles_bdd,
        erreur=erreur,
        edition=edition,
        edition_id=eid,
    )


@bp.route("/salles/import", methods=["POST"])
@login_required
def import_salles():
    if not _check_admin():
        return redirect(url_for("dashboard"))

    eid = _edition_courante_id()
    if not eid:
        flash("Aucune édition active sélectionnée.", "warning")
        return redirect(url_for("sharepoint.preview_salles"))

    list_name = "Salles Interventions 2026"
    client = _get_client()
    nb_crees = 0
    nb_maj = 0
    erreur = None

    try:
        items_sp = client.get_list_items(
            list_name,
            select=["Id", "Title", "Capacite", "Etage", "TypeSalle", "Note"],
            top=200,
        )
        for it in items_sp:
            mapped = client.map_item(list_name, it)
            nom = mapped.get("nom") or ""
            if not nom:
                continue
            existing = query(
                "SELECT id FROM salles WHERE edition_id=? AND nom=?",
                (eid, nom), one=True
            )
            if existing:
                execute(
                    "UPDATE salles SET capacite=?, etage=?, type_salle=?, note=?, actif=1 "
                    "WHERE id=?",
                    (mapped.get("capacite"), mapped.get("etage"),
                     mapped.get("type_salle"), mapped.get("note"),
                     existing["id"]),
                )
                nb_maj += 1
            else:
                insert("salles", {
                    "edition_id": eid,
                    "nom":        nom,
                    "capacite":   mapped.get("capacite"),
                    "etage":      mapped.get("etage"),
                    "type_salle": mapped.get("type_salle"),
                    "note":       mapped.get("note"),
                    "actif":      1,
                })
                nb_crees += 1
    except Exception as e:
        erreur = str(e)

    if erreur:
        flash(f"Erreur lors de l'import : {erreur}", "danger")
    else:
        flash(f"Import terminé : {nb_crees} salle(s) créée(s), {nb_maj} mise(s) à jour.", "success")

    return redirect(url_for("sharepoint.preview_salles"))


# ── Plages horaires ──────────────────────────────────────────────────────────

@bp.route("/plages")
@login_required
def preview_plages():
    if not _check_admin():
        return redirect(url_for("dashboard"))

    # Nom de la liste SharePoint pour les plages (peut ne pas exister)
    list_name = "Plages horaires"
    client = _get_client()
    items_sp = None
    erreur = None
    token_ok = False
    eid = _edition_courante_id()
    edition = query("SELECT * FROM editions WHERE id=?", (eid,), one=True) if eid else None
    plages_bdd = query(
        "SELECT * FROM plages_horaires WHERE edition_id=? ORDER BY jour, heure_debut",
        (eid,)
    ) if eid else []

    try:
        client._get_token()
        token_ok = True
        raw = client.get_list_items(
            list_name,
            select=["Id", "Title", "Jour", "HeureDebut", "Ouvert", "Note"],
            top=200,
        )
        items_sp = raw
    except Exception as e:
        # La liste peut ne pas exister dans SP — ce n'est pas bloquant
        erreur = str(e)

    return render_template(
        "sharepoint/plages.html",
        token_ok=token_ok,
        items_sp=items_sp,
        plages_bdd=plages_bdd,
        erreur=erreur,
        edition=edition,
        edition_id=eid,
        jours=["Vendredi", "Samedi", "Dimanche"],
    )


@bp.route("/plages/import", methods=["POST"])
@login_required
def import_plages():
    """Importe les plages depuis SharePoint dans la BDD."""
    if not _check_admin():
        return redirect(url_for("dashboard"))

    eid = _edition_courante_id()
    if not eid:
        flash("Aucune édition active.", "warning")
        return redirect(url_for("sharepoint.preview_plages"))

    list_name = "Plages horaires"
    client = _get_client()
    nb_crees = 0
    nb_maj = 0
    erreur = None

    try:
        raw = client.get_list_items(
            list_name,
            select=["Id", "Title", "Jour", "HeureDebut", "Ouvert", "Note"],
            top=200,
        )
        for it in raw:
            jour       = it.get("Jour") or ""
            heure      = (it.get("HeureDebut") or "")[:5]
            ouvert_val = 0 if str(it.get("Ouvert", "Oui")).lower() in ("non", "false", "0") else 1
            note       = it.get("Note") or ""
            if not jour or not heure:
                continue
            existing = query(
                "SELECT id FROM plages_horaires WHERE edition_id=? AND jour=? AND heure_debut=?",
                (eid, jour, heure), one=True
            )
            if existing:
                execute(
                    "UPDATE plages_horaires SET ouvert=?, note=? WHERE id=?",
                    (ouvert_val, note, existing["id"]),
                )
                nb_maj += 1
            else:
                insert("plages_horaires", {
                    "edition_id": eid,
                    "jour": jour,
                    "heure_debut": heure,
                    "ouvert": ouvert_val,
                    "note": note,
                })
                nb_crees += 1
    except Exception as e:
        erreur = str(e)

    if erreur:
        flash(f"Erreur lors de l'import : {erreur}", "danger")
    else:
        flash(f"Import terminé : {nb_crees} plage(s) créée(s), {nb_maj} mise(s) à jour.", "success")

    return redirect(url_for("sharepoint.preview_plages"))


# ── Preview intervenants (ancien POC) ────────────────────────────────────────

@bp.route("/preview-intervenants")
@login_required
def preview_intervenants():
    if not _check_admin():
        return redirect(url_for("dashboard"))

    list_name = "Base Intervenants"
    client = _get_client()
    items_raw = None
    items_mapped = None
    champs_disponibles = None
    erreur = None
    token_ok = False

    try:
        client._get_token()
        token_ok = True
        items_raw = client.get_list_items(list_name, top=5)
        if items_raw:
            champs_disponibles = [k for k in items_raw[0].keys()
                                  if not k.startswith("odata")]
        items_mapped = [client.map_item(list_name, it) for it in (items_raw or [])]
    except Exception as e:
        erreur = str(e)

    mapping_def = SharePointClient.LIST_MAPPINGS.get(list_name, {})

    return render_template(
        "sharepoint/test.html",
        token_ok=token_ok,
        listes=None,
        erreur=erreur,
        preview={
            "list_name":          list_name,
            "items_raw":          items_raw,
            "items_mapped":       items_mapped,
            "champs_disponibles": champs_disponibles,
            "mapping_def":        mapping_def,
        },
    )
