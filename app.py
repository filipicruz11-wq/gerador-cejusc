import streamlit as st
import re
import os
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
    # Configuração de tamanho e resolução (Landscape)
    largura = 1200
    altura_base = 600
    imagem = Image.new('RGB', (largura, altura_base), color=(255, 255, 255))
    draw = ImageDraw.Draw(imagem)
    
    # Tenta carregar fontes do sistema para evitar erro de acentuação (quadradinhos)
    font_path = "arial.ttf" # Windows
    if not os.path.exists(font_path):
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" # Linux/Render

    try:
        font_titulo = ImageFont.truetype(font_path, 28)
        font_cabecalho = ImageFont.truetype(font_path, 14)
        font_texto = ImageFont.truetype(font_path, 13)
    except:
        font_titulo = font_cabecalho = font_texto = ImageFont.load_default()

    # Título centralizado
    texto_titulo = str(mediador).upper()
    draw.text((largura//2, 50), texto_titulo, fill=(0, 0, 0), font=font_titulo, anchor="mm")

    # Configuração da Tabela (Medidas baseadas no seu PDF original)
    headers = ["SEMANA", "DATA", "HORA", "PROCESSO", "SENHA", "VARA", "MEDIADOR"]
    col_widths = [120, 90, 70, 160, 110, 180, 320] 
    x_start = (largura - sum(col_widths)) // 2
    y_start = 100
    row_height = 35

    # Desenhar Cabeçalho (Cor Hex #f2cfc2)
    curr_x = x_start
    for i, h in enumerate(headers):
        draw.rectangle([curr_x, y_start, curr_x + col_widths[i], y_start + row_height], fill="#f2cfc2", outline="black")
        # Centralizar texto no cabeçalho
        bbox = draw.textbbox((0, 0), h, font=font_cabecalho)
        w_text = bbox[2] - bbox[0]
        draw.text((curr_x + (col_widths[i] - w_text)/2, y_start + 10), h, fill="black", font=font_cabecalho)
        curr_x += col_widths[i]

    # Desenhar Linhas de Dados (Cor Hex #fff9c4)
    for row_idx, reg in enumerate(registros):
        curr_x = x_start
        y = y_start + (row_idx + 1) * row_height
        for i, text in enumerate(reg):
            draw.rectangle([curr_x, y, curr_x + col_widths[i], y + row_height], fill="#fff9c4", outline="black")
            # Centralizar texto na célula
            txt = str(text)
            bbox = draw.textbbox((0, 0), txt, font=font_texto)
            w_text = bbox[2] - bbox[0]
            draw.text((curr_x + (col_widths[i] - w_text)/2, y + 10), txt, fill="black", font=font_texto)
            curr_x += col_widths[i]

    # Corta a imagem para remover o excesso de branco abaixo da tabela
    altura_final = y_start + (len(registros) + 2) * row_height
    imagem = imagem.crop((0, 0, largura, altura_final))

    buffer = io.BytesIO()
    imagem.save(buffer, format="JPEG", quality=100)
    return buffer.getvalue()

# Interface Streamlit
st.set_page_config(page_title="Gerador de Imagens CEJUSC", layout="centered")
st.title("🖼️ Gerador de Imagens (JPG) - CEJUSC")
st.write("Cole a pauta abaixo para gerar os arquivos em imagem.")

texto_pauta = st.text_area("Cole a pauta aqui:", height=300)

if st.button("GERAR IMAGENS"):
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
                    # Gerar a imagem para cada mediador
                    img_data = gerar_jpg_bytes(med, regs)
                    zip_file.writestr(f"{med.replace(' ', '_')}.jpg", img_data)
            
            st.success(f"Sucesso! {len(dados_por_mediador)} pautas geradas.")
            st.download_button(
                label="📥 BAIXAR TODAS AS IMAGENS (ZIP)", 
                data=zip_buffer.getvalue(), 
                file_name="pautas_cejusc_jpg.zip", 
                mime="application/zip"
            )
