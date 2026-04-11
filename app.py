import streamlit as st
import re
import os
from datetime import datetime
from collections import defaultdict
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import io
import zipfile

def get_dia_semana(data_str):
    try:
        dias = ["Segunda-Feira", "Terça-Feira", "Quarta-Feira", "Quinta-Feira", "Sexta-Feira", "Sábado", "Domingo"]
        data = datetime.strptime(data_str, "%d/%m/%Y")
        return dias[data.weekday()]
    except: return ""

def gerar_pdf_bytes(mediador, registros):
    buffer = io.BytesIO()
    # Margens menores para aproveitar melhor o espaço
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=20, leftMargin=30, rightMargin=30)
    styles = getSampleStyleSheet()
    elementos = [Paragraph(mediador, styles['Title']), Spacer(1, 15)]
    
    headers = ["SEMANA", "DATA", "HORA", "PROCESSO", "SENHA", "VARA", "MEDIADOR"]
    
    # AJUSTE AQUI: Coluna MEDIADOR agora tem 220 de largura
    t = Table([headers] + registros, colWidths=[85, 65, 45, 110, 75, 100, 220])
    
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f2cfc2")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#fff9c4")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 0), (-1, -1), 9), # Tamanho da fonte fixo para garantir que caiba
    ]))
    elementos.append(t)
    doc.build(elementos)
    return buffer.getvalue()

st.set_page_config(page_title="Gerador de PDFs CEJUSC", layout="centered")
st.title("📄 Gerador de PDFs - CEJUSC")
st.write("Cole a pauta abaixo e clique no botão para gerar os arquivos.")

texto_pauta = st.text_area("Cole a pauta aqui:", height=300)

if st.button("GERAR PDFs"):
    if not texto_pauta.strip():
        st.warning("Por favor, cole os dados antes de processar.")
    else:
        dados_por_mediador = defaultdict(list)
        linhas = texto_pauta.strip().split("\n")
        
        for linha in linhas:
            linha = linha.strip()
            if not linha: continue
            match_base = re.search(r"(\d{2}/\d{2}/\d{4})\s+(\d{1,2}:\d{2})\s+(\d{7}-\d{2}\.\d{4})\s+(.*)", linha)
            if match_base:
                data_pt, hora_pt, processo, resto = match_base.groups()
                if "SEM DISPONIBILIDADE" in resto.upper(): 
                    mediador_chave = "SEM DISPONIBILIDADE"; miolo = resto.upper().split("SEM DISPONIBILIDADE")[0].strip()
                elif "AUDIÊNCIA CANCELADA" in resto.upper(): 
                    mediador_chave = "AUDIÊNCIA CANCELADA"; miolo = resto.upper().split("AUDIÊNCIA CANCELADA")[0].strip()
                elif "SIM" in resto: 
                    partes_sim = resto.rsplit("SIM", 1); miolo = partes_sim[0].strip(); mediador_chave = partes_sim[1].strip()
                else: 
                    partes = resto.rsplit(maxsplit=1); miolo = partes[0] if len(partes) > 1 else ""; mediador_chave = partes[1] if len(partes) > 1 else "OUTROS"
                
                partes_miolo = miolo.split(maxsplit=1)
                senha = ""; vara = miolo
                if partes_miolo:
                    primeira = partes_miolo[0]
                    if "ª" not in primeira and "º" not in primeira or primeira.upper() == "CANCELADA":
                        senha = primeira; vara = partes_miolo[1] if len(partes_miolo) > 1 else ""
                
                dados_por_mediador[mediador_chave].append([get_dia_semana(data_pt), data_pt, hora_pt, processo, senha, vara, mediador_chave])

        if dados_por_mediador:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                for med, regs in dados_por_mediador.items():
                    pdf_data = gerar_pdf_bytes(med, regs)
                    zip_file.writestr(f"{med.replace(' ', '_')}.pdf", pdf_data)
            
            st.success(f"Sucesso! {len(dados_por_mediador)} mediadores identificados.")
            st.download_button(label="📥 BAIXAR TODOS OS PDFs (ZIP)", data=zip_buffer.getvalue(), file_name="pautas_cejusc.zip", mime="application/zip")
