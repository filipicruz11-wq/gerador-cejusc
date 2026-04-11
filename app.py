import streamlit as st
import re
import io
import zipfile
from datetime import datetime
from collections import defaultdict
from PIL import Image, ImageDraw, ImageFont

def get_dia_semana(data_str):
    try:
        dias = ["Segunda-Feira", "Terça-Feira", "Quarta-Feira", "Quinta-Feira", "Sexta-Feira", "Sábado", "Domingo"]
        data = datetime.strptime(data_str, "%d/%m/%Y")
        return dias[data.weekday()]
    except: return ""

def gerar_jpg_bytes(mediador, registros):
    # Configurações de imagem (simulando um landscape A4)
    largura, altura = 1123, 794
    imagem = Image.new('RGB', (largura, altura), color=(255, 255, 255))
    draw = ImageDraw.Draw(imagem)
    
    try:
        # Tenta carregar uma fonte padrão do sistema, se falhar usa a básica
        font_titulo = ImageFont.truetype("arial.ttf", 24)
        font_texto = ImageFont.truetype("arial.ttf", 12)
    except:
        font_titulo = ImageFont.load_default()
        font_texto = ImageFont.load_default()

    # Desenhar Título
    draw.text((largura//2, 40), mediador, fill=(0, 0, 0), font=font_titulo, anchor="mm")

    # Cabeçalhos e Tabela
    headers = ["SEMANA", "DATA", "HORA", "PROCESSO", "SENHA", "VARA", "MEDIADOR"]
    col_widths = [130, 100, 70, 160, 100, 150, 300]
    x_start, y_start = 50, 100
    row_height = 25

    # Desenhar Cabeçalho
    curr_x = x_start
    for i, h in enumerate(headers):
        draw.rectangle([curr_x, y_start, curr_x + col_widths[i], y_start + row_height], fill="#f2cfc2", outline="black")
        draw.text((curr_x + 5, y_start + 5), h, fill="black", font=font_texto)
        curr_x += col_widths[i]

    # Desenhar Registros
    for row_idx, reg in enumerate(registros):
        curr_x = x_start
        y = y_start + (row_idx + 1) * row_height
        for i, text in enumerate(reg):
            draw.rectangle([curr_x, y, curr_x + col_widths[i], y + row_height], fill="#fff9c4", outline="black")
            draw.text((curr_x + 5, y + 5), str(text), fill="black", font=font_texto)
            curr_x += col_widths[i]

    buffer = io.BytesIO()
    imagem.save(buffer, format="JPEG", quality=95)
    return buffer.getvalue()

st.set_page_config(page_title="Gerador de JPGs CEJUSC", layout="centered")
st.title("🖼️ Gerador de JPGs - CEJUSC")
st.write("Cole a pauta abaixo e clique no botão para gerar as imagens.")

texto_pauta = st.text_area("Cole a pauta aqui:", height=300)

if st.button("GERAR JPGs"):
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
                    jpg_data = gerar_jpg_bytes(med, regs)
                    zip_file.writestr(f"{med.replace(' ', '_')}.jpg", jpg_data)
            
            st.success(f"Sucesso! {len(dados_por_mediador)} mediadores identificados.")
            st.download_button(label="📥 BAIXAR TODOS OS JPGs (ZIP)", data=zip_buffer.getvalue(), file_name="pautas_cejusc.zip", mime="application/zip")
