import pandas as pd
import requests
import time
import logging
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuração de logs
logging.basicConfig(
    filename='validacao_enderecos.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filemode='w'
)

def detect_delimiter(file_path, encoding='latin1'):
    with open(file_path, 'r', encoding=encoding) as f:
        sample = f.read(1024)
        sniffer = csv.Sniffer()
        return sniffer.sniff(sample).delimiter

def detect_encoding(file_path):
    encodings = ['utf-8', 'utf-8-sig', 'latin1', 'iso-8859-1', 'windows-1252']
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                f.read(1024)
            return encoding
        except UnicodeDecodeError:
            continue
    return 'latin1'  # padrão seguro para dados brasileiros

# Configurações principais
INPUT_CSV = 'dados_completos1.csv'
OUTPUT_CSV = 'dados_validados.csv'
ENCODING = detect_encoding(INPUT_CSV)
DELIMITER = detect_delimiter(INPUT_CSV, ENCODING)

print(f"Encoding detectado: {ENCODING}")
print(f"Delimitador detectado: '{DELIMITER}'")

# API Nominatim
DELAY = 1  # 1 requisição/segundo
HEADERS = {'User-Agent': 'validacao_postes_iluminacao_v1.0'}

import unicodedata

def normalizar_nome(nome):
    if not isinstance(nome, str):
        return ""
    
    # Substituições de abreviações
    substituicoes = {
        'av.': 'avenida',
        'r.': 'rua',
        'dr.': 'doutor',
        'br.': 'barão',
        's.': 'são',
        'av ': 'avenida ',
        'rua ': 'rua ',
        'estr.': 'estrada',
        'est.': 'estrada',
        'al.': 'alameda',
        'praça': 'praça',
        'pc.': 'praça'
    }
    
    # 1. Converter para minúsculas
    nome = nome.lower().strip()
    
    # 2. Remover acentos e caracteres especiais
    nome = unicodedata.normalize('NFKD', nome)
    nome = ''.join([c for c in nome if not unicodedata.combining(c)])
    
    # 3. Substituir abreviações
    for abbrev, completo in substituicoes.items():
        nome = nome.replace(abbrev, completo)
    
    # 4. Remover caracteres especiais e múltiplos espaços
    nome = ''.join(c for c in nome if c.isalnum() or c.isspace() or c in (',', '-'))
    nome = ' '.join(nome.split())  # Remove espaços múltiplos
    
    return nome

# Adicione isso após a definição da função normalizar_nome
def comparar_enderecos(endereco1, endereco2):
    norm1 = normalizar_nome(endereco1)
    norm2 = normalizar_nome(endereco2)
    
    # Casos especiais
    if norm1.replace(' ', '') == norm2.replace(' ', ''):
        return True
    
    # Permite pequenas diferenças de digitação
    if norm1 in norm2 or norm2 in norm1:
        return True
        
    return norm1 == norm2


def reverse_geocode(lat, lon, tentativas=3):
    url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}"
    
    for tentativa in range(tentativas):
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            address = data.get('address', {})
            return (address.get('road') or 
                    address.get('pedestrian') or 
                    address.get('footway') or 
                    "")
                    
        except requests.exceptions.RequestException as e:
            if tentativa == tentativas - 1:
                logging.error(f"Falha na geocodificação ({lat}, {lon}) após {tentativas} tentativas: {str(e)}")
                return None
            time.sleep(2)
    
    return None

def process_row(row):
    try:
        # Verifica nomes alternativos para latitude/longitude
        lat = row.get('Latitude') or row.get('latitude') or row.get('LATITUDE') or row.get('lat')
        lon = row.get('Longitude') or row.get('longitude') or row.get('LONGITUDE') or row.get('lon')
        
        if pd.isna(lat) or pd.isna(lon):
            raise ValueError("Coordenadas não encontradas na linha")
            
        lat, lon = float(lat), float(lon)
        
        endereco_planilha = str(row.get('Endereço', '') or 
                               row.get('endereco', '') or 
                               row.get('nome_logradouro', '') or 
                               row.get('logradouro', ''))
        
        endereco_api = reverse_geocode(lat, lon)
        time.sleep(DELAY)
        
        endereco_planilha_norm = normalizar_nome(endereco_planilha)
        endereco_api_norm = normalizar_nome(endereco_api) if endereco_api else ""
        
        status = (
            "OK" if comparar_enderecos(endereco_planilha, endereco_api or "")
            else "ERRO_API" if not endereco_api
            else "DIVERGENCIA"
        )
        
        resultado = row.to_dict()
        resultado.update({
            "nome_logradouro_api": endereco_api,
            "status_validacao": status,
            "detalhes_divergencia": f"Planilha: {endereco_planilha} | API: {endereco_api}" if status == "DIVERGENCIA" else ""
        })
        
        return resultado
        
    except Exception as e:
        logging.error(f"Erro ao processar linha: {str(e)}")
        resultado = row.to_dict()
        resultado.update({
            "nome_logradouro_api": None,
            "status_validacao": "ERRO_PROCESSAMENTO",
            "detalhes_divergencia": str(e)
        })
        return resultado

def main():
    try:
        # Carrega os dados com tratamento robusto
        df = pd.read_csv(
            INPUT_CSV,
            encoding=ENCODING,
            delimiter=DELIMITER,
            dtype=str,
            on_bad_lines='skip',  # Pula linhas problemáticas
            engine='python',       # Engine mais tolerante
            quoting=csv.QUOTE_MINIMAL
        )
        
        # Normaliza nomes de colunas (remove espaços, acentos, etc.)
        df.columns = df.columns.str.strip().str.lower()
        
        # Verifica colunas obrigatórias com nomes alternativos
        col_lat = next((col for col in df.columns if 'lat' in col), None)
        col_lon = next((col for col in df.columns if 'lon' in col or 'lng' in col), None)
        
        if not col_lat or not col_lon:
            raise ValueError("Colunas de coordenadas não encontradas. Verifique se existem colunas contendo 'lat' e 'lon' no nome")
        
        # Renomeia para facilitar o processamento
        df = df.rename(columns={col_lat: 'latitude', col_lon: 'longitude'})
        
        print(f"\nPrimeiras linhas do DataFrame:\n{df.head()}")
        print(f"\nColunas disponíveis: {list(df.columns)}")
        
        # Processamento em lotes
        resultados = []
        total_linhas = len(df)
        print(f"\nTotal de linhas a processar: {total_linhas}")
        
        with ThreadPoolExecutor(max_workers=1) as executor:
            futures = [executor.submit(process_row, row) for _, row in df.iterrows()]
            
            for i, future in enumerate(as_completed(futures)):
                try:
                    resultados.append(future.result())
                except Exception as e:
                    logging.error(f"Erro ao coletar resultado: {str(e)}")
                
                if (i + 1) % 100 == 0:
                    logging.info(f"Processadas {i + 1} linhas de {total_linhas}")
                    print(f"Progresso: {i + 1}/{total_linhas} linhas")
        
        # Salva os resultados
        df_resultado = pd.DataFrame(resultados)
        
        # Mantém todas as colunas originais + as novas
        df_resultado.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
        
        print("\nProcessamento concluído com sucesso!")
        print(f"Resultados salvos em: {OUTPUT_CSV}")
        print(f"Linhas processadas: {len(resultados)}")
        print(f"Linhas com erro: {len(df_resultado[df_resultado['status_validacao'] == 'ERRO_PROCESSAMENTO'])}")
        
    except Exception as e:
        logging.error(f"Erro fatal: {str(e)}", exc_info=True)
        print(f"\nERRO: {str(e)}")
        print("Verifique o arquivo de log para mais detalhes")

if __name__ == '__main__':
    print("Iniciando processamento...")
    main()