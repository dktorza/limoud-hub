"""
Synchronisation SharePoint (Graph) → base Limoud Hub.

Chaque fonction importer_* lit une liste SharePoint et crée/met à jour les
lignes correspondantes pour l'édition donnée. L'import est rejouable :
la correspondance se fait sur sp_item_id (id de l'item SharePoint).

Ordre recommandé : thèmes → salles → plages → intervenants → sessions
(les sessions référencent les quatre autres).
"""

import json
import re
import unicodedata
from database import query, execute, insert

LISTE_THEMES       = "Thèmes Interventions"
LISTE_SALLES       = "Salles Interventions 2026"
LISTE_PLAGES       = "Créneaux d'intervention"
LISTE_INTERVENANTS = "Base Intervenants"
LISTE_SESSIONS     = "Liste interventions 2026"


# ── Utilitaires ──────────────────────────────────────────────────────────────

def _slug(txt):
    txt = unicodedata.normalize("NFKD", txt or "").encode("ascii", "ignore").decode()
    txt = re.sub(r"[^a-zA-Z0-9]+", "_", txt).strip("_").lower()
    return txt or "x"


def _oui(v):
    """'Oui'/'Non'/True/False/None → 1/0 (None → None)."""
    if v is None or v == "":
        return None
    if isinstance(v, bool):
        return int(v)
    return 1 if str(v).strip().lower() in ("oui", "true", "1", "yes") else 0


def _hex(v, defaut=None):
    v = (v or "").strip().lstrip("#")
    return f"#{v}" if re.fullmatch(r"[0-9A-Fa-f]{6}", v) else defaut


def _txt(v):
    if v is None:
        return None
    if isinstance(v, list):
        return ", ".join(str(x) for x in v)
    s = str(v).strip()
    # Les choix multiples SharePoint arrivent parfois en JSON texte
    if s.startswith("[") and s.endswith("]"):
        try:
            return ", ".join(str(x) for x in json.loads(s))
        except ValueError:
            pass
    return s or None


def _lookup_ids(v):
    """Champ lookup Graph → liste d'ids d'items."""
    if not v:
        return []
    if isinstance(v, dict):
        v = [v]
    ids = []
    for x in v:
        if isinstance(x, dict) and x.get("LookupId") is not None:
            ids.append(int(x["LookupId"]))
    return ids


def _stats():
    return {"crees": 0, "maj": 0, "ignores": 0, "avertissements": []}


# ── Thèmes ───────────────────────────────────────────────────────────────────

def importer_themes(client, edition_id):
    st = _stats()
    for it in client.get_list_items(LISTE_THEMES, top=100):
        libelle = _txt(it.get("Title"))
        if not libelle:
            st["ignores"] += 1
            continue
        sp_id = int(it["_id"])
        data = {
            "libelle":           libelle,
            "couleur_hex":       _hex(it.get("Code_Couleur"), "#1a5276"),
            "couleur_texte_hex": _hex(it.get("Code_Couleur_Texte"), "#ffffff"),
            "actif":             1,
        }
        row = (query("SELECT id FROM themes WHERE sp_item_id=?", (sp_id,), one=True)
               or query("SELECT id FROM themes WHERE lower(libelle)=lower(?) AND edition_id IS NULL",
                        (libelle,), one=True))
        if row:
            execute("UPDATE themes SET libelle=?, couleur_hex=?, couleur_texte_hex=?, actif=1, "
                    "sp_item_id=? WHERE id=?",
                    (data["libelle"], data["couleur_hex"], data["couleur_texte_hex"], sp_id, row["id"]))
            st["maj"] += 1
        else:
            insert("themes", {**data, "edition_id": None, "code": _slug(libelle),
                              "ordre": 100 + sp_id, "sp_item_id": sp_id})
            st["crees"] += 1
    return st


# ── Salles ───────────────────────────────────────────────────────────────────

def importer_salles(client, edition_id):
    st = _stats()
    for it in client.get_list_items(LISTE_SALLES, top=200):
        nom = _txt(it.get("Title"))
        if not nom:
            st["ignores"] += 1
            continue
        sp_id = int(it["_id"])
        cap = it.get("Capacit_x00e9_")
        capacite = int(float(cap)) if cap not in (None, "") else None
        row = (query("SELECT id FROM salles WHERE edition_id=? AND sp_item_id=?", (edition_id, sp_id), one=True)
               or query("SELECT id FROM salles WHERE edition_id=? AND lower(nom)=lower(?)",
                        (edition_id, nom), one=True))
        if row:
            execute("UPDATE salles SET nom=?, capacite=?, actif=1, sp_item_id=? WHERE id=?",
                    (nom, capacite, sp_id, row["id"]))
            st["maj"] += 1
        else:
            insert("salles", {"edition_id": edition_id, "nom": nom, "capacite": capacite,
                              "actif": 1, "sp_item_id": sp_id})
            st["crees"] += 1
    return st


# ── Plages horaires ──────────────────────────────────────────────────────────

def _decouper_heure(h):
    """'15:45-16:45' → ('15:45', '16:45') ; '15h45 - 16h45' accepté aussi."""
    if not h:
        return None, None
    parts = re.findall(r"(\d{1,2})[:h](\d{2})", str(h))
    if not parts:
        return None, None
    fmt = lambda p: f"{int(p[0]):02d}:{p[1]}"
    debut = fmt(parts[0])
    fin = fmt(parts[1]) if len(parts) > 1 else None
    return debut, fin


def importer_plages(client, edition_id):
    st = _stats()
    items = client.get_list_items(LISTE_PLAGES, top=200)
    # Si certaines plages sont cochées "Limoud 2026", on ne garde que celles-là
    if any(_oui(it.get("Limoud2026")) for it in items):
        items = [it for it in items if _oui(it.get("Limoud2026"))]
    for it in items:
        jour = _txt(it.get("Jour"))
        debut, fin = _decouper_heure(it.get("Heure"))
        if not jour or not debut:
            st["ignores"] += 1
            continue
        sp_id = int(it["_id"])
        couleur = _hex(it.get("Code_Couleur_Creneau"))
        note = _txt(it.get("Title"))
        row = (query("SELECT id FROM plages_horaires WHERE edition_id=? AND sp_item_id=?",
                     (edition_id, sp_id), one=True)
               or query("SELECT id FROM plages_horaires WHERE edition_id=? AND jour=? AND heure_debut=?",
                        (edition_id, jour, debut), one=True))
        if row:
            execute("UPDATE plages_horaires SET jour=?, heure_debut=?, heure_fin=?, couleur_hex=?, "
                    "note=?, ouvert=1, sp_item_id=? WHERE id=?",
                    (jour, debut, fin, couleur, note, sp_id, row["id"]))
            st["maj"] += 1
        else:
            insert("plages_horaires", {"edition_id": edition_id, "jour": jour, "heure_debut": debut,
                                       "heure_fin": fin, "couleur_hex": couleur, "note": note,
                                       "ouvert": 1, "sp_item_id": sp_id})
            st["crees"] += 1
    return st


# ── Intervenants ─────────────────────────────────────────────────────────────

CIVILITES = {"madame": "Mme", "monsieur": "M", "docteur": "Dr", "professeur": "Pr",
             "maître": "Me", "maitre": "Me", "rav": "Rav"}

EMAIL_LIVRET = {
    "email principal":                  "principal",
    "oui, mon email principal":         "principal",
    "email secondaire":                 "secondaire",
    "oui, mon email secondaire":        "secondaire",
    "aucun email ne doit figurer":      "aucun",
    "non":                              "aucun",
}

STATUTS_CONTACT = {
    "a contacter":              "a_contacter",
    "à contacter":              "a_contacter",
    "en discussion":            "en_discussion",
    "en attente du formulaire": "formulaire_envoye",
    "inscrit":                  "confirme",
}


def importer_intervenants(client, edition_id):
    st = _stats()
    for it in client.get_list_items(LISTE_INTERVENANTS, top=2000):
        nom, prenom = _txt(it.get("field_1")), _txt(it.get("field_2"))
        if not nom and not prenom:
            st["ignores"] += 1
            continue
        sp_id = int(it["_id"])
        email = (_txt(it.get("field_3")) or "").lower() or None

        notes = []
        if _txt(it.get("field_18")):
            notes.append(f"Titre 2 : {_txt(it.get('field_18'))}")
        if _txt(it.get("field_13")):
            notes.append(f"Photo (Drive) : {_txt(it.get('field_13'))}")
        if _txt(it.get("Commentaireintervenant")):
            notes.append(f"Commentaire intervenant : {_txt(it.get('Commentaireintervenant'))}")

        photo = it.get("Photo")
        photo_url = None
        if isinstance(photo, str) and photo.startswith("{"):
            try:
                photo = json.loads(photo)
            except ValueError:
                photo = None
        if isinstance(photo, dict) and photo.get("serverRelativeUrl"):
            photo_url = photo.get("serverUrl", "") + photo["serverRelativeUrl"]

        data = {
            "civilite_code":          CIVILITES.get((_txt(it.get("Title")) or "").lower(), ""),
            "nom":                    nom or "",
            "prenom":                 prenom or "",
            "email_principal":        email,
            "email_secondaire":       (_txt(it.get("field_4")) or "").lower() or None,
            "adresse":                _txt(it.get("field_5")),
            "code_postal":            _txt(it.get("field_6")),
            "ville":                  _txt(it.get("field_7")),
            "pays":                   _txt(it.get("field_8")) or "France",
            "tel_fixe":               _txt(it.get("field_9")),
            "tel_mobile":             _txt(it.get("field_10")),
            "facebook":               _txt(it.get("field_11")),
            "twitter":                _txt(it.get("field_12")),
            "instagram":              _txt(it.get("CompteInstagram")),
            "accord_photo":           _oui(it.get("field_14")) if _oui(it.get("field_14")) is not None else 1,
            "accord_photo_video_com": _oui(it.get("AutorisationPhotoVid_x00e9_oouti")) or 0,
            "accord_podcast":         _oui(it.get("AutorisationPodcast")) or 0,
            "email_livret_choix":     EMAIL_LIVRET.get((_txt(it.get("field_16")) or "").lower(), "aucun"),
            "nom_diffuse":            _oui(it.get("field_17")) if _oui(it.get("field_17")) is not None else 1,
            "fonction_titre":         _txt(it.get("field_19")),
            "mini_bio":               _txt(it.get("field_20")),
            "institutions":           _txt(it.get("field_21")),
            "specialites":            _txt(it.get("field_22")),
            "oeuvres_publications":   _txt(it.get("field_23")),
            "photo_path":             photo_url,
            "notes_internes":         "\n".join(notes) or None,
            "sp_item_id":             sp_id,
        }

        row = query("SELECT id FROM intervenants WHERE sp_item_id=?", (sp_id,), one=True)
        if not row and email:
            row = query("SELECT id FROM intervenants WHERE lower(email_principal)=?", (email,), one=True)
        if not row:
            row = query("SELECT id FROM intervenants WHERE lower(nom)=lower(?) AND lower(prenom)=lower(?)",
                        (data["nom"], data["prenom"]), one=True)

        if row:
            sets = ", ".join(f"{k}=?" for k in data)
            execute(f"UPDATE intervenants SET {sets}, updated_at=datetime('now') WHERE id=?",
                    (*data.values(), row["id"]))
            iid = row["id"]
            st["maj"] += 1
        else:
            iid = insert("intervenants", data)
            st["crees"] += 1

        # Participation à l'édition courante (données 2026)
        part = {
            "statut_code":        STATUTS_CONTACT.get((_txt(it.get("Avancementducontact")) or "").lower(),
                                                      "a_contacter"),
            "livres_a_vendre":    _txt(it.get("Livres_x00e0_vendre_x0028_Limoud0")),
            "dedicace":           _oui(it.get("D_x00e9_dicace_x0028_Limoud2026_")) or 0,
            "commentaires_equipe": _txt(it.get("Commentairespourl_x00e9_quipeLim")),
            "propose_par":        _txt(it.get("Personneayantpropos_x00e9_linter")),
        }
        prow = query("SELECT id FROM participations_intervenants WHERE intervenant_id=? AND edition_id=?",
                     (iid, edition_id), one=True)
        if prow:
            sets = ", ".join(f"{k}=?" for k in part)
            execute(f"UPDATE participations_intervenants SET {sets}, updated_at=datetime('now') WHERE id=?",
                    (*part.values(), prow["id"]))
        else:
            insert("participations_intervenants", {**part, "intervenant_id": iid, "edition_id": edition_id})
    return st


# ── Sessions ─────────────────────────────────────────────────────────────────

FORMATS = {
    "atelier":     "atelier",
    "spectacle":   "spectacle",
    "table ronde": "table_ronde",
    "débat":       "debat",
    "debat":       "debat",
    "conférence":  "conference",
    "conference":  "conference",
    "etude":       "etude_textes",
    "étude":       "etude_textes",
    "projection":  "projection",
    "office":      "office",
}

STATUTS_SESSION = {
    "en discussion":    "en_discussion",
    "validée":          "valide",
    "validee":          "valide",
    "payée":            "paye",
    "payee":            "paye",
    "payée avec cerfa": "paye_cerfa",
    "payee avec cerfa": "paye_cerfa",
    "invité":           "invite",
    "invite":           "invite",
    "bouclée":          "programme",
    "bouclee":          "programme",
    "annulée":          "annule",
    "annulee":          "annule",
}


def _format_code(libelle):
    l = (libelle or "").lower()
    for cle, code in FORMATS.items():
        if l.startswith(cle):
            return code
    return "conference"


def importer_sessions(client, edition_id):
    st = _stats()
    themes = {t["libelle"].lower(): t["id"] for t in query("SELECT id, libelle FROM themes WHERE actif=1")}
    interv_par_sp = {r["sp_item_id"]: r["id"]
                     for r in query("SELECT id, sp_item_id FROM intervenants WHERE sp_item_id IS NOT NULL")}
    salles_par_sp = {r["sp_item_id"]: r["id"]
                     for r in query("SELECT id, sp_item_id FROM salles WHERE edition_id=? AND sp_item_id IS NOT NULL",
                                    (edition_id,))}
    plages_par_sp = {r["sp_item_id"]: r
                     for r in query("SELECT * FROM plages_horaires WHERE edition_id=? AND sp_item_id IS NOT NULL",
                                    (edition_id,))}
    users_par_email = {u["email"].lower(): u["id"] for u in query("SELECT id, email FROM utilisateurs")}

    for it in client.get_list_items(LISTE_SESSIONS, top=1000):
        titre = _txt(it.get("Title"))
        if not titre:
            st["ignores"] += 1
            continue
        sp_id = int(it["_id"])

        theme_lib = (_txt(it.get("field_5")) or "").lower()
        theme_id = themes.get(theme_lib)
        if not theme_id and theme_lib:
            # correspondance souple : premier mot commun
            for lib, tid in themes.items():
                if lib.split()[0] == theme_lib.split()[0]:
                    theme_id = tid
                    break
            if not theme_id:
                st["avertissements"].append(f"« {titre} » : thème inconnu « {theme_lib} »")

        materiel = _txt(it.get("field_7")) or ""
        mat_l = materiel.lower()

        ref = it.get("R_x00e9_f_x00e9_rent_x00e9_quipe")
        ref_nom, ref_id = None, None
        if isinstance(ref, list) and ref:
            ref_nom = ref[0].get("LookupValue")
            ref_id = users_par_email.get((ref[0].get("Email") or "").lower())
        elif isinstance(ref, dict):
            ref_nom = ref.get("LookupValue")
            ref_id = users_par_email.get((ref.get("Email") or "").lower())

        data = {
            "edition_id":           edition_id,
            "titre":                titre,
            "description":          _txt(it.get("field_4")),
            "theme_id":             theme_id,
            "format_code":          _format_code(_txt(it.get("Format"))),
            "langue_code":          "en" if (_txt(it.get("field_6")) or "").lower().startswith("angl") else "fr",
            "est_focus":            _oui(it.get("Focus_x003f_")) or 0,
            "est_pays_honneur":     _oui(it.get("Pays_x00e0_lhonneur_x003f_")) or 0,
            "materiel_salle":       materiel or None,
            "materiel_intervenant": _txt(it.get("field_8")),
            "connectique_demandee": _txt(it.get("Connectiquedemand_x00e9_e")),
            "connectique_apportee": _txt(it.get("Connectiqueapport_x00e9_e")),
            "besoin_micro":         1 if "micro" in mat_l else 0,
            "besoin_video":         1 if ("projecteur" in mat_l or "vidéo" in mat_l or "video" in mat_l) else 0,
            "besoin_sono":          1 if ("sono" in mat_l or "enceinte" in mat_l) else 0,
            "besoin_tableau":       1 if ("tableau" in mat_l or "paperboard" in mat_l) else 0,
            "statut_code":          STATUTS_SESSION.get((_txt(it.get("Statutintervention")) or "").lower(), "soumis"),
            "commentaire_equipe":   _txt(it.get("Commentaire_x00e9_quipe")),
            "dispo_vendredi":       _oui(it.get("PossibleVendredi")) if _oui(it.get("PossibleVendredi")) is not None else 1,
            "dispo_samedi":         _oui(it.get("PossibleSamedi")) if _oui(it.get("PossibleSamedi")) is not None else 1,
            "dispo_dimanche":       _oui(it.get("PossibleDimanche")) if _oui(it.get("PossibleDimanche")) is not None else 1,
            "creneau_souhaite":     _txt(it.get("field_9")),
            "referent_id":          ref_id,
            "referent_nom":         ref_nom,
            "sp_item_id":           sp_id,
        }

        row = query("SELECT id FROM sessions WHERE edition_id=? AND sp_item_id=?", (edition_id, sp_id), one=True)
        if row:
            sets = ", ".join(f"{k}=?" for k in data)
            execute(f"UPDATE sessions SET {sets}, updated_at=datetime('now') WHERE id=?",
                    (*data.values(), row["id"]))
            sid = row["id"]
            st["maj"] += 1
        else:
            sid = insert("sessions", data)
            st["crees"] += 1

        # Intervenants (lookup vers Base Intervenants)
        execute("DELETE FROM session_intervenants WHERE session_id=?", (sid,))
        for ordre, lid in enumerate(_lookup_ids(it.get("Intervenant_x0028_s_x0029_")), start=1):
            iid = interv_par_sp.get(lid)
            if iid:
                insert("session_intervenants", {"session_id": sid, "intervenant_id": iid,
                                                "role_code": "principal", "ordre_affichage": ordre})
            else:
                st["avertissements"].append(f"« {titre} » : intervenant SharePoint #{lid} non importé")

        # Créneau planifié (TECH_Salle / TECH_Creneau = ids d'items SharePoint)
        tech_salle = _txt(it.get("TECH_Salle"))
        tech_plage = _txt(it.get("TECH_Ceneau")) or _txt(it.get("TECH_Creneau"))
        if tech_salle and tech_plage and tech_salle.isdigit() and tech_plage.isdigit():
            salle_id = salles_par_sp.get(int(tech_salle))
            plage = plages_par_sp.get(int(tech_plage))
            if salle_id and plage:
                cren = {"edition_id": edition_id, "salle_id": salle_id, "plage_id": plage["id"],
                        "jour": plage["jour"], "heure_debut": plage["heure_debut"],
                        "heure_fin": plage["heure_fin"] or plage["heure_debut"], "statut_code": "planifie"}
                crow = query("SELECT id FROM creneaux WHERE session_id=?", (sid,), one=True)
                if crow:
                    sets = ", ".join(f"{k}=?" for k in cren)
                    execute(f"UPDATE creneaux SET {sets}, updated_at=datetime('now') WHERE id=?",
                            (*cren.values(), crow["id"]))
                else:
                    insert("creneaux", {**cren, "session_id": sid})
            else:
                st["avertissements"].append(
                    f"« {titre} » : salle #{tech_salle} ou créneau #{tech_plage} inconnu (importer salles et plages d'abord)")
    return st


IMPORTS = [
    ("themes",       "Thèmes",        LISTE_THEMES,       importer_themes),
    ("salles",       "Salles",        LISTE_SALLES,       importer_salles),
    ("plages",       "Plages horaires", LISTE_PLAGES,     importer_plages),
    ("intervenants", "Intervenants",  LISTE_INTERVENANTS, importer_intervenants),
    ("sessions",     "Sessions",      LISTE_SESSIONS,     importer_sessions),
]
