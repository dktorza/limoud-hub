from flask import Blueprint, render_template, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
import requests

bp = Blueprint("helloasso", __name__, template_folder="templates")


def _get_ha_token(cfg):
    """Obtient un token OAuth2 client_credentials depuis HelloAsso."""
    resp = requests.post(
        "https://api.helloasso.com/oauth2/token",
        data={
            "grant_type":    "client_credentials",
            "client_id":     cfg["HELLOASSO_CLIENT_ID"],
            "client_secret": cfg["HELLOASSO_CLIENT_SECRET"],
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


@bp.route("/")
@login_required
def index():
    if not current_user.a_permission("helloasso", "voir_liste"):
        flash("Accès non autorisé.", "danger")
        return redirect(url_for("dashboard"))
    return render_template("helloasso/index.html")


@bp.route("/test-connexion")
@login_required
def test_connexion():
    if not current_user.a_permission("helloasso", "voir_liste"):
        flash("Accès non autorisé.", "danger")
        return redirect(url_for("dashboard"))

    cfg = current_app.config
    org_slug = cfg.get("HELLOASSO_ORG_SLUG", "limoud-france")
    token = None
    formulaires = None
    erreur = None

    try:
        token = _get_ha_token(cfg)
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(
            f"https://api.helloasso.com/v5/organizations/{org_slug}/forms",
            headers=headers,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        formulaires = data.get("data", data) if isinstance(data, dict) else data
    except requests.HTTPError as e:
        erreur = f"HTTP {e.response.status_code} : {e.response.text[:300]}"
    except Exception as e:
        erreur = str(e)

    return render_template(
        "helloasso/test.html",
        token_ok=token is not None,
        formulaires=formulaires,
        erreur=erreur,
        org_slug=org_slug,
        sync_data=None,
    )


@bp.route("/sync-test")
@login_required
def sync_test():
    if not current_user.a_permission("helloasso", "voir_liste"):
        flash("Accès non autorisé.", "danger")
        return redirect(url_for("dashboard"))

    cfg = current_app.config
    org_slug = cfg.get("HELLOASSO_ORG_SLUG", "limoud-france")
    form_slug = "festival-limoud-2026-special-jb"
    token = None
    items_raw = None
    items_mapped = None
    erreur = None

    try:
        token = _get_ha_token(cfg)
        headers = {"Authorization": f"Bearer {token}"}
        url = (
            f"https://api.helloasso.com/v5/organizations/{org_slug}"
            f"/forms/Event/{form_slug}/items"
        )
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        items_raw = data.get("data", []) if isinstance(data, dict) else data

        # Mapping vers la structure participants de la BDD
        items_mapped = []
        for item in (items_raw or []):
            user = item.get("user", {})
            order = item.get("order", {})
            mapped = {
                "ha_item_id":            item.get("id"),
                "ha_reference_commande": order.get("code"),
                "ha_date_commande":      order.get("date"),
                "ha_statut_commande":    order.get("status"),
                "payeur_nom":            order.get("payer", {}).get("lastName"),
                "payeur_prenom":         order.get("payer", {}).get("firstName"),
                "payeur_email":          order.get("payer", {}).get("email"),
                "nom":                   user.get("lastName"),
                "prenom":                user.get("firstName"),
                "email":                 user.get("email"),
                "telephone":             user.get("phoneNumber"),
                "type_formulaire":       item.get("type"),
                "montant_ht":            item.get("amount", 0) / 100 if item.get("amount") else 0,
                "options_raw":           item.get("customFields", []),
            }
            items_mapped.append(mapped)
    except requests.HTTPError as e:
        erreur = f"HTTP {e.response.status_code} : {e.response.text[:300]}"
    except Exception as e:
        erreur = str(e)

    return render_template(
        "helloasso/test.html",
        token_ok=token is not None,
        formulaires=None,
        erreur=erreur,
        org_slug=org_slug,
        form_slug=form_slug,
        sync_data={"items_raw": items_raw, "items_mapped": items_mapped},
    )
