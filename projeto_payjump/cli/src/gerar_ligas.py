import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

dados = {
    'id-liga': [106, 107, 111, 127, 128, 132, 135, 136, 137, 145, 147, 148, 149, 
                150, 163, 164, 165, 166, 170, 171, 173, 174, 180, 184, 197, 199, 
                202, 204, 205, 213, 214],
    'nome-liga': [
        'Suprema', 'Liga Principal', 'Suprema EU', 'Suprema Peru', 'Suprema Union',
        'Suprema Ásia', 'Supreme Poker', 'Suprema México', 'Suprema Argentina',
        'Suprema Panamá', 'Suprema Colômbia', 'Suprema Venezuela', 'Suprema R Dominicana',
        'Suprema Bolívia', 'Suprema Costa Rica', 'Suprema KZ', 'Re-Stars', 'Suprema USA FN',
        'SRODEO', 'Liga Royal', 'Suprema SX USD', 'Suprema Canadá', '♠️♥️ HOME GAME ♦️♣️',
        'Suprema Chile', 'Suprema Freeroll', 'Suprema ADR USD', 'Suprema Índia',
        'Suprema Uruguai', 'Suprema SX-E', 'Vulcão', 'CERRADO POKER LEAGUE'
    ]
}

df = pd.DataFrame(dados)
df.to_csv(DATA_DIR / 'ligas.csv', index=False, encoding='utf-8-sig')
print("✅ Arquivo ligas.csv criado com sucesso!")