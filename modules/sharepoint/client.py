"""
SharePoint Online client via Microsoft Graph API (v1.0).
Authentification : client credentials (Azure App Registration "Limoud Hub",
permission d'application Sites.Read.All).

Remarque : Graph expose les colonnes par leur nom INTERNE (ex. "field_1",
"field_2"...) et non par leur libellé. Le nom interne réel de chaque colonne
est visible dans la page /sharepoint/test (clés brutes des items). Le mapping
LIST_MAPPINGS ci-dessous doit utiliser ces noms internes.
"""

import requests

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


class SharePointClient:
    # Mapping des listes SharePoint vers les tables BDD
    LIST_MAPPINGS = {
        "Base Intervenants": {
            "table": "intervenants",
            "champs": {
                "Title":          "nom",
                "Prenom":         "prenom",
                "Email":          "email_principal",
                "Telephone":      "tel_mobile",
                "FonctionTitre":  "fonction_titre",
                "MiniBio":        "mini_bio",
                "Specialites":    "specialites",
                "Institutions":   "institutions",
                "SiteWeb":        "site_web",
                "Twitter":        "twitter",
                "Instagram":      "instagram",
                "LinkedIn":       "linkedin",
            },
        },
        "Liste interventions 2026": {
            "table": "sessions",
            "champs": {
                "Title":          "titre",
                "Description":    "description",
                "Format":         "format_code",
                "Duree":          "duree_minutes",
                "Langue":         "langue_code",
                "Niveau":         "niveau_code",
                "Intervenant":    "_intervenant_nom",
            },
        },
        "Salles d'intervention": {
            "table": "salles",
            "champs": {
                "Title":          "nom",
                "Capacite":       "capacite",
                "Etage":          "etage",
                "TypeSalle":      "type_salle",
                "Note":           "note",
            },
        },
        "Créneaux d'intervention": {
            "table": "creneaux",
            "champs": {
                "Jour":           "jour",
                "HeureDebut":     "heure_debut",
                "HeureFin":       "heure_fin",
                "Session":        "_session_titre",
                "Salle":          "_salle_nom",
            },
        },
    }

    def __init__(self, tenant_id, client_id, client_secret, site_url):
        self.tenant_id     = tenant_id
        self.client_id     = client_id
        self.client_secret = client_secret
        self.site_url      = site_url.rstrip("/")
        self._token        = None
        self._site_id      = None
        self._list_ids     = {}

    def _get_token(self):
        """Obtient (ou retourne le cache) d'un token Azure AD."""
        if self._token:
            return self._token
        resp = requests.post(
            f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token",
            data={
                "grant_type":    "client_credentials",
                "client_id":     self.client_id,
                "client_secret": self.client_secret,
                "scope":         "https://graph.microsoft.com/.default",
            },
            timeout=15,
        )
        resp.raise_for_status()
        self._token = resp.json()["access_token"]
        return self._token

    def _headers(self):
        return {
            "Authorization": f"Bearer {self._get_token()}",
            "Accept":        "application/json",
        }

    def _get(self, url, params=None):
        resp = requests.get(url, headers=self._headers(), params=params, timeout=20)
        resp.raise_for_status()
        return resp.json()

    def _get_site_id(self):
        """Résout l'identifiant Graph du site à partir de SHAREPOINT_SITE_URL
        (ex. https://limoudfrance.sharepoint.com/sites/LimoudOrga)."""
        if self._site_id:
            return self._site_id
        parts = self.site_url.replace("https://", "").split("/", 1)
        hostname = parts[0]
        path = "/" + parts[1] if len(parts) > 1 else ""
        data = self._get(f"{GRAPH_BASE}/sites/{hostname}:{path}")
        self._site_id = data["id"]
        return self._site_id

    def _get_list_id(self, list_name):
        """Résout l'id d'une liste à partir de son nom d'affichage."""
        if list_name in self._list_ids:
            return self._list_ids[list_name]
        for l in self.get_available_lists():
            self._list_ids[l["Title"]] = l["Id"]
        if list_name not in self._list_ids:
            raise ValueError(f"Liste SharePoint introuvable : {list_name}")
        return self._list_ids[list_name]

    def get_available_lists(self):
        """Liste les listes visibles du site. Retourne des dicts normalisés
        {Title, Id, ItemCount} pour rester compatible avec les templates."""
        site_id = self._get_site_id()
        data = self._get(
            f"{GRAPH_BASE}/sites/{site_id}/lists",
            params={"$select": "id,displayName,list"},
        )
        result = []
        for l in data.get("value", []):
            if l.get("list", {}).get("hidden"):
                continue
            result.append({
                "Title":     l.get("displayName"),
                "Id":        l.get("id"),
                "ItemCount": None,   # non fourni par Graph sans requête supplémentaire
            })
        return sorted(result, key=lambda x: (x["Title"] or "").lower())

    def get_list_columns(self, list_name):
        """Colonnes d'une liste : nom interne, libellé affiché, type, masquée.
        C'est la table de correspondance à utiliser pour LIST_MAPPINGS."""
        site_id = self._get_site_id()
        list_id = self._get_list_id(list_name)
        data = self._get(
            f"{GRAPH_BASE}/sites/{site_id}/lists/{list_id}/columns",
            params={"$select": "name,displayName,hidden,readOnly,text,number,choice,"
                               "dateTime,boolean,lookup,personOrGroup,hyperlinkOrPicture"},
        )
        cols = []
        for c in data.get("value", []):
            for t in ("text", "number", "choice", "dateTime", "boolean",
                      "lookup", "personOrGroup", "hyperlinkOrPicture"):
                if t in c:
                    typ = t
                    break
            else:
                typ = "?"
            cols.append({
                "name":        c.get("name"),
                "displayName": c.get("displayName"),
                "type":        typ,
                "hidden":      bool(c.get("hidden")),
                "readOnly":    bool(c.get("readOnly")),
                "choices":     (c.get("choice") or {}).get("choices"),
            })
        return cols

    def get_list_items(self, list_name, select=None, filter_query=None, top=100):
        """Récupère les items d'une liste. Retourne, pour chaque item, le dict
        `fields` (colonnes par nom interne) enrichi de `_id` (id de l'item)."""
        site_id = self._get_site_id()
        list_id = self._get_list_id(list_name)
        url = f"{GRAPH_BASE}/sites/{site_id}/lists/{list_id}/items"
        expand = "fields"
        if select:
            expand = "fields($select=" + ",".join(select) + ")"
        params = {"$expand": expand, "$top": min(top, 200)}
        if filter_query:
            params["$filter"] = filter_query
        headers = self._headers()
        # Nécessaire pour filtrer sur des colonnes non indexées
        headers["Prefer"] = "HonorNonIndexedQueriesWarningMayFailRandomly"
        items = []
        while url and len(items) < top:
            resp = requests.get(url, headers=headers, params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            for it in data.get("value", []):
                fields = dict(it.get("fields", {}))
                fields["_id"] = it.get("id")
                items.append(fields)
            url = data.get("@odata.nextLink")
            params = None   # nextLink contient déjà les paramètres
        return items[:top]

    def map_item(self, list_name, sp_item):
        """Convertit un item SharePoint vers un dict BDD selon le mapping."""
        mapping = self.LIST_MAPPINGS.get(list_name, {})
        champs = mapping.get("champs", {})
        result = {"_table": mapping.get("table", "?")}
        for sp_field, bdd_field in champs.items():
            result[bdd_field] = sp_item.get(sp_field)
        return result
