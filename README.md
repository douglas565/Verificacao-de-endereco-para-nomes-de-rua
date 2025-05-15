# Validador de Endereços por Geocodificação Reversa

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Pandas](https://img.shields.io/badge/Pandas-1.3%2B-orange)
![OpenStreetMap](https://img.shields.io/badge/OpenStreetMap-Nominatim-lightgreen)

Um script Python robusto para validação de endereços utilizando geocodificação reversa através da API Nominatim (OpenStreetMap).

## Funcionalidades Principais

✔ Validação automática de endereços a partir de coordenadas geográficas  
✔ Comparação inteligente que ignora maiúsculas, acentos e abreviações  
✔ Processamento paralelo para melhor performance  
✔ Detecção automática de encoding e delimitador do arquivo CSV  
✔ Sistema de tentativas para lidar com falhas temporárias da API  
✔ Geração de relatório detalhado com status de validação  

## Como Usar

### Pré-requisitos
- Python 3.8+
- Bibliotecas: pandas, requests

### Instalação
```bash
pip install pandas requests
```

### Execução
1. Prepare um arquivo CSV contendo:
   - Colunas de latitude/longitude (podem ter vários nomes como 'lat', 'latitude', etc.)
   - Coluna de endereço (opcional, para comparação)

2. Execute o script:
```bash
python validacao_enderecos.py
```

3. Os resultados serão salvos em `dados_validados.csv` com:
   - Todos os dados originais
   - Nome do logradouro obtido da API
   - Status da validação
   - Detalhes de divergências (se houver)

### Configuração
Edite as variáveis no início do script para personalizar:
```python
INPUT_CSV = 'seu_arquivo.csv'  # Arquivo de entrada
OUTPUT_CSV = 'resultados.csv'  # Arquivo de saída
DELAY = 1  # Intervalo entre requisições (em segundos)
```

## Exemplo de Saída

| Latitude | Longitude | Endereço Original | Endereço API | Status     |
|----------|-----------|--------------------|--------------|------------|
| -23.5505 | -46.6333  | Av Paulista         | Avenida Paulista | OK       |
| -22.9068 | -43.1729  | Rua Primeiro Março  | Rua 1º de Março | DIVERGENCIA |

## Tratamento de Casos Especiais

O script é capaz de lidar inteligentemente com:
- Diferenças de maiúsculas/minúsculas
- Caracteres acentuados e não acentuados
- Abreviações comuns (Av. → Avenida, R. → Rua)
- Pequenas variações de digitação
- Espaçamento irregular

## Limitações

- Requer conexão com a internet para acessar a API Nominatim
- Sujeito aos limites de requisições da API (1 requisição/segundo)
- A precisão depende da qualidade dos dados no OpenStreetMap

## Contribuição

Contribuições são bem-vindas! Sinta-se à vontade para:
- Reportar problemas
- Sugerir melhorias
- Enviar pull requests
