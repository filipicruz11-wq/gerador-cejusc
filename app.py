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
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=20, leftMargin=30, rightMargin=30)
    styles = getSampleStyleSheet()
    elementos = [Paragraph(f"Pauta: {mediador}", styles['Title']), Spacer(1, 15)]
    
    headers = ["SEMANA", "DATA", "HORA", "PROCESSO", "SENHA", "VARA", "MEDIADOR"]
    
    t = Table([headers] + registros, colWidths=[85, 65, 45, 110, 75, 100, 220])
    
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f2cfc2")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#fff9c4")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
    ]))
    elementos.append(t)
    doc.build(elementos)
    return buffer.getvalue()

st.set_page_config(page_title="Gerador de PDFs CEJUSC", layout="centered")
st.title("📄 Gerador de PDFs - CEJUSC")
st.write("Cole a pauta no novo formato (Colunas separadas por TAB ou espaços).")

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
            
            # Divide a linha por TAB ou múltiplos espaços
            partes = re.split(r'\t|\s{2,}', linha)
            
            if len(partes) >= 6:
                data_pt = partes[0].strip()
                hora_pt = partes[1].strip()
                processo = partes[2].strip()
                senha = partes[3].strip()
                vara = partes[4].strip()
                mediador_chave = partes[5].strip()

                # Lógica para tratar Cancelados ou Sem Disponibilidade
                # Se o texto "CANCELADA" aparecer em qualquer lugar da linha, agrupamos no arquivo de cancelados
                if "CANCELADA" in linha.upper() or "CANCELADO" in linha.upper():
                    mediador_chave = "AUDIÊNCIA CANCELADA"
                elif "SEM DISPONIBILIDADE" in linha.upper():
                    mediador_chave = "SEM DISPONIBILIDADE"

                dados_por_mediador[mediador_chave].append([
                    get_dia_semana(data_pt), 
                    data_pt, 
                    hora_pt, 
                    processo, 
                    senha, 
                    vara, 
                    mediador_chave
                ])

        if dados_por_mediador:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                # Ordena os mediadores por nome para o ZIP ficar organizado
                for med in sorted(dados_por_mediador.keys()):
                    regs = dados_por_mediador[med]
                    pdf_data = gerar_pdf_bytes(med, regs)
                    # Limpa o nome do arquivo para evitar erros de caracteres
                    nome_arquivo = med.replace(' ', '_').replace('/', '-')
                    zip_file.writestr(f"{nome_arquivo}.pdf", pdf_data)
            
            st.success(f"Sucesso! {len(dados_por_mediador)} categorias/mediadores identificados.")
            st.download_button(
                label="📥 BAIXAR TODOS OS PDFs (ZIP)", 
                data=zip_buffer.getvalue(), 
                file_name="pautas_cejusc.zip", 
                mime="application/zip"
            )
