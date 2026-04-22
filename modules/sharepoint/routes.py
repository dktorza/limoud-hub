from flask import Blueprint, render_template, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
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


@bp.route("/test-connexion")
@login_required
def test_connexion():
    if not current_user.a_permission("admin", "voir_liste"):
        flash("Accès non autorisé.", "danger")
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
        list_name=None,
    )


@bp.route("/preview-intervenants")
@login_required
def preview_intervenants():
    if not current_user.a_permission("admin", "voir_liste"):
        flash("Accès non autorisé.", "danger")
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
            # Collecter tous les champs disponibles depuis le premier item
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
        list_name=list_name,
    )
