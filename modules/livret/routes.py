import os
from flask import (Blueprint, render_template, flash, redirect,
                   url_for, current_app, send_file)
from flask_login import login_required, current_user
from database import query

bp = Blueprint("livret", __name__, template_folder="templates")


def _edition_courante_id():
    from flask import session as flask_session
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
    if not current_user.a_permission("livret", "voir_liste"):
        flash("Accès non autorisé.", "danger")
        return redirect(url_for("dashboard"))

    output_folder = current_app.config["LIVRET_OUTPUT_FOLDER"]
    pdf_existe = os.path.exists(os.path.join(output_folder, "test_livret.pdf"))
    return render_template("livret/index.html", pdf_existe=pdf_existe)


@bp.route("/generer-test")
@login_required
def generer_test():
    if not current_user.a_permission("livret", "voir_liste"):
        flash("Accès non autorisé.", "danger")
        return redirect(url_for("dashboard"))

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            PageBreak, HRFlowable,
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
    except ImportError:
        flash("ReportLab n'est pas installé. Exécutez : pip install reportlab", "danger")
        return redirect(url_for("livret.index"))

    cfg = current_app.config
    output_folder = cfg["LIVRET_OUTPUT_FOLDER"]
    os.makedirs(output_folder, exist_ok=True)
    pdf_path = os.path.join(output_folder, "test_livret.pdf")

    eid = _edition_courante_id()
    edition = query("SELECT * FROM editions WHERE id=?", (eid,), one=True) if eid else None

    # ── Données BDD (ou fictives si vide) ──────────────────────────────
    sessions_bdd = []
    intervenants_bdd = []
    creneaux_bdd = []
    if eid:
        sessions_bdd = query(
            "SELECT s.*, GROUP_CONCAT(i.prenom || ' ' || i.nom, ', ') as intervenants_noms "
            "FROM sessions s "
            "LEFT JOIN session_intervenants si ON si.session_id = s.id "
            "LEFT JOIN intervenants i ON i.id = si.intervenant_id "
            "WHERE s.edition_id=? GROUP BY s.id ORDER BY s.titre",
            (eid,)
        )
        intervenants_bdd = query(
            "SELECT i.* FROM intervenants i "
            "JOIN participations_intervenants pi ON pi.intervenant_id = i.id "
            "WHERE pi.edition_id=? AND i.mini_bio IS NOT NULL "
            "ORDER BY i.nom LIMIT 20",
            (eid,)
        )
        creneaux_bdd = query(
            "SELECT c.*, s.titre as session_titre, sa.nom as salle_nom, "
            "       si_grp.intervenants_noms "
            "FROM creneaux c "
            "JOIN sessions s ON s.id = c.session_id "
            "LEFT JOIN salles sa ON sa.id = c.salle_id "
            "LEFT JOIN ("
            "  SELECT si.session_id, GROUP_CONCAT(i.prenom || ' ' || i.nom, ', ') as intervenants_noms "
            "  FROM session_intervenants si JOIN intervenants i ON i.id = si.intervenant_id "
            "  GROUP BY si.session_id"
            ") si_grp ON si_grp.session_id = c.session_id "
            "WHERE c.edition_id=? ORDER BY c.jour, c.heure_debut",
            (eid,)
        )

    # Données fictives si BDD vide
    if not edition:
        edition = {
            "nom": "Limoud Paris 2026",
            "date_debut": "2026-06-06",
            "date_fin": "2026-06-08",
            "couleur_principale": "#1a5276",
            "couleur_secondaire": "#e97132",
        }
    if not intervenants_bdd:
        intervenants_bdd = [
            {"prenom": "Sarah", "nom": "COHEN", "fonction_titre": "Professeure de philosophie",
             "mini_bio": "Sarah Cohen est professeure agrégée de philosophie à l'Université Paris-Sorbonne. Ses recherches portent sur l'éthique juive contemporaine et le dialogue interreligieux.", "photo_path": None},
            {"prenom": "David", "nom": "LEVY", "fonction_titre": "Rabbin, Directeur du CRIF",
             "mini_bio": "David Levy est rabbin depuis 20 ans et préside le Centre de Ressources pour les Institutions Françaises. Il est l'auteur de plusieurs ouvrages sur la pensée talmudique moderne.", "photo_path": None},
            {"prenom": "Miriam", "nom": "BLOCH", "fonction_titre": "Chercheuse, CNRS",
             "mini_bio": "Miriam Bloch dirige le laboratoire d'études hébraïques au CNRS. Spécialiste de la littérature midrashique, elle a publié 8 ouvrages traduits en 12 langues.", "photo_path": None},
        ]
    if not creneaux_bdd:
        creneaux_bdd = [
            {"jour": "Vendredi", "heure_debut": "20:00", "heure_fin": "21:30",
             "session_titre": "Soirée d'ouverture", "salle_nom": "Grande salle", "intervenants_noms": "David LEVY"},
            {"jour": "Samedi", "heure_debut": "09:30", "heure_fin": "11:00",
             "session_titre": "Torah et modernité", "salle_nom": "Salle A", "intervenants_noms": "Sarah COHEN"},
            {"jour": "Samedi", "heure_debut": "09:30", "heure_fin": "11:00",
             "session_titre": "Kabbale pratique", "salle_nom": "Salle B", "intervenants_noms": "Miriam BLOCH"},
            {"jour": "Samedi", "heure_debut": "11:30", "heure_fin": "13:00",
             "session_titre": "Identité juive en France", "salle_nom": "Grande salle", "intervenants_noms": "David LEVY"},
            {"jour": "Dimanche", "heure_debut": "10:00", "heure_fin": "12:00",
             "session_titre": "Table ronde : L'avenir du judaïsme", "salle_nom": "Grande salle",
             "intervenants_noms": "Sarah COHEN, David LEVY, Miriam BLOCH"},
        ]

    # ── Construire le PDF ───────────────────────────────────────────────
    couleur_principale = colors.HexColor(edition.get("couleur_principale") or "#1a5276")
    couleur_secondaire = colors.HexColor(edition.get("couleur_secondaire") or "#e97132")

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm,  bottomMargin=2*cm,
    )
    styles = getSampleStyleSheet()

    # Styles personnalisés
    style_titre = ParagraphStyle("titre_limoud",
        fontSize=52, fontName="Helvetica-Bold",
        textColor=couleur_principale, alignment=TA_CENTER, spaceAfter=0.5*cm)
    style_sous_titre = ParagraphStyle("sous_titre",
        fontSize=18, fontName="Helvetica",
        textColor=couleur_secondaire, alignment=TA_CENTER, spaceAfter=0.3*cm)
    style_section = ParagraphStyle("section",
        fontSize=14, fontName="Helvetica-Bold",
        textColor=couleur_principale, spaceBefore=0.4*cm, spaceAfter=0.2*cm)
    style_corps = ParagraphStyle("corps",
        fontSize=10, fontName="Helvetica",
        leading=14, spaceAfter=0.15*cm)
    style_centre = ParagraphStyle("centre",
        fontSize=10, fontName="Helvetica",
        alignment=TA_CENTER, spaceAfter=0.2*cm)

    story = []

    # ── PAGE DE COUVERTURE ─────────────────────────────────────────────
    story.append(Spacer(1, 4*cm))
    story.append(Paragraph("LIMOUD", style_titre))
    story.append(Paragraph(edition.get("nom", ""), style_sous_titre))

    dates_str = ""
    if edition.get("date_debut") and edition.get("date_fin"):
        dates_str = f"{edition['date_debut'][:10]}  →  {edition['date_fin'][:10]}"
    elif edition.get("date_debut"):
        dates_str = edition["date_debut"][:10]
    if dates_str:
        story.append(Paragraph(dates_str, style_centre))

    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width="100%", thickness=3, color=couleur_secondaire))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph("Programme & Intervenants", style_sous_titre))
    story.append(PageBreak())

    # ── PLANNING par jour ──────────────────────────────────────────────
    jours = ["Vendredi", "Samedi", "Dimanche"]
    for jour in jours:
        sessions_jour = [c for c in creneaux_bdd if c.get("jour") == jour]
        if not sessions_jour:
            continue

        story.append(Paragraph(f"Planning — {jour}", style_section))
        story.append(HRFlowable(width="100%", thickness=1, color=couleur_principale))
        story.append(Spacer(1, 0.2*cm))

        table_data = [["Horaire", "Salle", "Session", "Intervenants"]]
        for c in sessions_jour:
            table_data.append([
                f"{c.get('heure_debut', '')[:5]} – {c.get('heure_fin', '')[:5]}",
                c.get("salle_nom") or "—",
                Paragraph(c.get("session_titre") or "—", style_corps),
                Paragraph(c.get("intervenants_noms") or "—", style_corps),
            ])

        t = Table(table_data, colWidths=[2.8*cm, 3.5*cm, 7*cm, 4.5*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND",  (0, 0), (-1, 0), couleur_principale),
            ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
            ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",    (0, 0), (-1, 0), 9),
            ("FONTSIZE",    (0, 1), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
            ("GRID",        (0, 0), (-1, -1), 0.4, colors.HexColor("#dee2e6")),
            ("VALIGN",      (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING",  (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.4*cm))

    story.append(PageBreak())

    # ── BIOGRAPHIES (2 colonnes) ───────────────────────────────────────
    story.append(Paragraph("Intervenants", style_section))
    story.append(HRFlowable(width="100%", thickness=1, color=couleur_principale))
    story.append(Spacer(1, 0.3*cm))

    col_w = (A4[0] - 4*cm) / 2 - 0.3*cm

    for i in range(0, len(intervenants_bdd), 2):
        row_items = intervenants_bdd[i:i+2]
        cells = []
        for iv in row_items:
            nom_complet = f"{iv.get('prenom', '')} {iv.get('nom', '')}"
            fonction    = iv.get("fonction_titre") or ""
            bio         = iv.get("mini_bio") or ""
            cell_story  = [
                Paragraph(f"<b>{nom_complet}</b>", style_corps),
            ]
            if fonction:
                cell_story.append(
                    Paragraph(f"<i>{fonction}</i>",
                              ParagraphStyle("fn", fontSize=9, textColor=colors.HexColor("#6c757d"), spaceAfter=4))
                )
            if bio:
                cell_story.append(Paragraph(bio[:400], style_corps))
            cells.append(cell_story)

        if len(cells) == 1:
            cells.append([""])

        bio_table = Table(
            [cells],
            colWidths=[col_w, col_w],
            hAlign="LEFT",
        )
        bio_table.setStyle(TableStyle([
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LINEBELOW",     (0, 0), (-1, -1), 0.3, colors.HexColor("#dee2e6")),
        ]))
        story.append(bio_table)

    doc.build(story)

    return send_file(pdf_path, as_attachment=True, download_name="livret_test.pdf")
