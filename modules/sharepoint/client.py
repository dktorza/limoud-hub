"""
SharePoint Online client via Microsoft Graph API.
Authentification : client credentials (Azure AD App Registration).
"""

import requests


class SharePointClient:

    SITE_ID = "limoudfrance.sharepoint.com,9b4592a2-ac27-445b-9053-8769ed9cd241,4549c66f-a1ca-4663-97ed-edb16ce67409"
    GRAPH_BASE = "https://graph.microsoft.com/v1.0"

    LIST_MAPPINGS = {
        "Base Intervenants": {
            "table": "intervenants",
            "champs": {
                "field_1":  "nom",
                "field_2":  "prenom",
                "field_3":  "email_principal",
                "field_4":  "email_secondaire",
                "field_10": "tel_mobile",
                "field_11": "facebook",
                "field_12": "twitter",
                "field_13": "instagram",
                "field_14": "photo_drive_url",
                "field_18": "civilite",
                "field_19": "fonction_titre",
                "field_20": "mini_bio",
                "field_21": "institutions",
                "field_22": "specialites",
            },
        },
        "Liste interventions 2026": {
            "table": "sessions",
            "champs": {
                "Title":       "titre",
                "Description": "description",
                "Format":      "format_code",
                "Duree":       "duree_minutes",
                "Langue":      "langue_code",
                "Niveau":      "niveau_code",
                "Intervenant": "_intervenant_nom",
            },
        },
        "Salles Interventions 2026": {
            "table": "salles",
            "champs": {
                "Title":    "nom",
                "Capacite": "capacite",
                "Etage":    "etage",
                "TypeSalle":"type_salle",
                "Note":     "note",
            },
        },
        "Créneaux d'intervention": {
            "table": "creneaux",
            "champs": {
                "Jour":      "jour",
                "HeureDebut":"heure_debut",
                "HeureFin":  "heure_fin",
                "Session":   "_session_titre",
                "Salle":     "_salle_nom",
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
        return {"Authorization": f"Bearer {self._get_token()}"}

    def _get_list_id(self, list_name):
        """Retourne l'ID Graph d'une liste par son displayName."""
        resp = requests.get(
            f"{self.GRAPH_BASE}/sites/{self.SITE_ID}/lists",
            headers=self._headers(),
            timeout=15,
        )
        resp.raise_for_status()
        for l in resp.json().get("value", []):
            if l.get("displayName") == list_name or l.get("name") == list_name:
                return l["id"]
        raise ValueError(f"Liste introuvable : {list_name}")

    def get_available_lists(self):
        """Liste toutes les listes disponibles sur le site."""
        resp = requests.get(
            f"{self.GRAPH_BASE}/sites/{self.SITE_ID}/lists",
            headers=self._headers(),
            timeout=15,
        )
        resp.raise_for_status()
        return [
            {"Title": l.get("displayName"), "ItemCount": l.get("list", {}).get("itemCount", 0)}
            for l in resp.json().get("value", [])
            if not l.get("list", {}).get("hidden", False)
        ]

    def get_list_items(self, list_name, select=None, filter_query=None, top=100):
        """Récupère les items d'une liste SharePoint via Graph."""
        list_id = self._get_list_id(list_name)
        url = f"{self.GRAPH_BASE}/sites/{self.SITE_ID}/lists/{list_id}/items"
        params = {"$top": top, "$expand": "fields"}
        if filter_query:
            params["$filter"] = filter_query
        resp = requests.get(url, headers=self._headers(), params=params, timeout=15)
        resp.raise_for_status()
        items = resp.json().get("value", [])
        # Extraire les champs
        result = []
        for item in items:
            fields = item.get("fields", {})
            if select:
                fields = {k: v for k, v in fields.items() if k in select}
            result.append(fields)
        return result

    def map_item(self, list_name, sp_item):
        """Convertit un item SharePoint vers un dict BDD selon le mapping."""
        mapping = self.LIST_MAPPINGS.get(list_name, {})
        champs = mapping.get("champs", {})
        result = {"_table": mapping.get("table", "?")}
        for sp_field, bdd_field in champs.items():
            result[bdd_field] = sp_item.get(sp_field)
        return result
