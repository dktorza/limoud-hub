from flask import (Blueprint, render_template, flash, redirect,
                   url_for, current_app, request, session as flask_session)
from flask_login import login_required, current_user
from database import query, execute, insert
import requests

bp = Blueprint("helloasso", __name__, template_folder="templates")

HA_BASE    = "https://api.helloasso.com/v5"
HA_OAUTH   = "https://api.helloasso.com/oauth2/token"


def _get_ha_token(cfg):
    resp = requests.post(
        HA_OAUTH,
        data={
            "grant_type":    "client_credentials",
            "client_id":     cfg.get("HELLOASSO_CLIENT_ID", ""),
            "client_secret": cfg.get("HELLOASSO_CLIENT_SECRET", ""),
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _ha_get(token, path, params=None):
    resp = requests.get(
        f"{HA_BASE}{path}",
        headers={"Authorization": f"Bearer {token}"},
        params=params or {},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("data", data) if isinstance(data, dict) else data


def _map_item(item):
    """Mappe un item HelloAsso vers la structure participants de la BDD."""
    user  = item.get("user", {})
    order = item.get("order", {})
    payer = order.get("payer", {})
    return {
        "ha_item_id":            item.get("id"),
        "ha_reference_commande": order.get("code"),
        "ha_date_commande":      order.get("date"),
        "ha_statut_commande":    order.get("status"),
        "payeur_nom":            payer.get("lastName"),
        "payeur_prenom":         payer.get("firstName"),
        "payeur_email":          payer.get("email"),
        "nom":                   user.get("lastName"),
        "prenom":                user.get("firstName"),
        "email":                 user.get("email"),
        "telephone":             user.get("phoneNumber"),
        "type_formulaire":       item.get("type"),
        "montant_ht":            (item.get("amount") or 0) / 100,
        "options_raw":           item.get("customFields", []),
    }


def _check_perm():
    if not current_user.a_permission("helloasso", "voir_liste"):
        flash("Accès non autorisé.", "danger")
        return False
    return True


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


# ── Index ────────────────────────────────────────────────────────────────────

@bp.route("/")
@login_required
def index():
    if not _check_perm():
        return redirect(url_for("dashboard"))

    cfg = current_app.config
    config_ok = bool(cfg.get("HELLOASSO_CLIENT_ID") and cfg.get("HELLOASSO_CLIENT_SECRET"))
    org_slug  = cfg.get("HELLOASSO_ORG_SLUG", "limoud-france")

    formulaires = None
    erreur      = None
    token_ok    = False

    if config_ok:
        try:
            token = _get_ha_token(cfg)
            token_ok = True
            formulaires = _ha_get(token, f"/organizations/{org_slug}/forms",
                                  params={"pageSize": 100})
            if isinstance(formulaires, dict):
                formulaires = formulaires.get("data", [])
        except requests.HTTPError as e:
            erreur = f"HTTP {e.response.status_code} — {e.response.text[:300]}"
        except Exception as e:
            erreur = str(e)

    return render_template(
        "helloasso/index.html",
        config_ok=config_ok,
        token_ok=token_ok,
        org_slug=org_slug,
        formulaires=formulaires,
        erreur=erreur,
    )


# ── Sync par formulaire ───────────────────────────────────────────────────────

@bp.route("/sync/<form_type>/<form_slug>")
@login_required
def sync_formulaire(form_type, form_slug):
    if not _check_perm():
        return redirect(url_for("dashboard"))

    cfg      = current_app.config
    org_slug = cfg.get("HELLOASSO_ORG_SLUG", "limoud-france")

    items_raw    = None
    items_mapped = None
    nb_inseres   = 0
    nb_maj       = 0
    erreur       = None
    token_ok     = False
    do_import    = request.args.get("import") == "1"
    eid          = _edition_courante_id()

    try:
        token    = _get_ha_token(cfg)
        token_ok = True
        path     = f"/organizations/{org_slug}/forms/{form_type}/{form_slug}/items"
        raw      = _ha_get(token, path, params={"pageSize": 100})
        items_raw    = raw if isinstance(raw, list) else raw.get("data", [])
        items_mapped = [_map_item(it) for it in items_raw]

        if do_import and eid:
            for m in items_mapped:
                ha_id = m.get("ha_item_id")
                if not ha_id:
                    continue
                existing = query(
                    "SELECT id FROM participants WHERE ha_item_id=?",
                    (ha_id,), one=True
                )
                if existing:
                    execute(
                        "UPDATE participants SET "
                        "ha_statut_commande=?, nom=?, prenom=?, email=?, telephone=?, "
                        "montant_ht=?, updated_at=datetime('now') WHERE id=?",
                        (m["ha_statut_commande"], m["nom"], m["prenom"],
                         m["email"], m["telephone"], m["montant_ht"], existing["id"]),
                    )
                    nb_maj += 1
                else:
                    insert("participants", {
                        "edition_id":            eid,
                        "ha_item_id":            ha_id,
                        "ha_reference_commande": m["ha_reference_commande"],
                        "ha_date_commande":      m["ha_date_commande"],
                        "ha_statut_commande":    m["ha_statut_commande"],
                        "payeur_nom":            m["payeur_nom"],
                        "payeur_prenom":         m["payeur_prenom"],
                        "payeur_email":          m["payeur_email"],
                        "nom":                   m["nom"],
                        "prenom":                m["prenom"],
                        "email":                 m["email"],
                        "telephone":             m["telephone"],
                        "type_formulaire_code":  form_type.lower(),
                        "montant_ht":            m["montant_ht"],
                    })
                    nb_inseres += 1

            if not erreur:
                flash(
                    f"Sync terminée : {nb_inseres} participant(s) créé(s), "
                    f"{nb_maj} mis à jour.",
                    "success",
                )

    except requests.HTTPError as e:
        erreur = f"HTTP {e.response.status_code} — {e.response.text[:400]}"
    except Exception as e:
        erreur = str(e)

    return render_template(
        "helloasso/sync.html",
        token_ok=token_ok,
        org_slug=org_slug,
        form_type=form_type,
        form_slug=form_slug,
        items_raw=items_raw,
        items_mapped=items_mapped,
        nb_inseres=nb_inseres,
        nb_maj=nb_maj,
        erreur=erreur,
        do_import=do_import,
        edition_id=eid,
    )


# ── Ancien POC (garde compatibilité) ─────────────────────────────────────────

@bp.route("/test-connexion")
@login_required
def test_connexion():
    return redirect(url_for("helloasso.index"))


@bp.route("/sync-test")
@login_required
def sync_test():
    if not _check_perm():
        return redirect(url_for("dashboard"))
    cfg = current_app.config
    org_slug  = cfg.get("HELLOASSO_ORG_SLUG", "limoud-france")
    form_slug = "festival-limoud-2026-special-jb"
    return redirect(url_for("helloasso.sync_formulaire",
                            form_type="Event", form_slug=form_slug))
