"""
SharePoint Online client via Microsoft Graph / SharePoint REST API.
Authentification : client credentials (Azure AD App Registration).
"""

import requests


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
            "Accept":        "application/json;odata=nometadata",
        }

    def get_list_items(self, list_name, select=None, filter_query=None, top=100):
        """Récupère les items d'une liste SharePoint via REST API."""
        encoded = requests.utils.quote(list_name)
        url = f"{self.site_url}/_api/web/lists/getbytitle('{encoded}')/items"
        params = {"$top": top}
        if select:
            params["$select"] = ",".join(select)
        if filter_query:
            params["$filter"] = filter_query
        resp = requests.get(url, headers=self._headers(), params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data.get("value", [])

    def get_available_lists(self):
        """Liste toutes les listes disponibles sur le site."""
        url = f"{self.site_url}/_api/web/lists"
        params = {
            "$select": "Title,ItemCount,Hidden",
            "$filter": "Hidden eq false",
            "$orderby": "Title",
        }
        resp = requests.get(url, headers=self._headers(), params=params, timeout=15)
        resp.raise_for_status()
        return resp.json().get("value", [])

    def map_item(self, list_name, sp_item):
        """Convertit un item SharePoint vers un dict BDD selon le mapping."""
        mapping = self.LIST_MAPPINGS.get(list_name, {})
        champs = mapping.get("champs", {})
        result = {"_table": mapping.get("table", "?")}
        for sp_field, bdd_field in champs.items():
            result[bdd_field] = sp_item.get(sp_field)
        return result
