class Clube:
    def __init__(self, id_clube, id_liga):
        self.id_clube = id_clube
        self.id_liga = id_liga
    
    def __repr__(self):
        return f"Clube [{self.id_clube}]: {self.id_liga}"
    
class Jogador:
    def __init__(self, id_jogador, nome_jogador, clubes=None, maos=None):
        self.id_jogador = id_jogador
        self.nome_jogador = nome_jogador
        self.clubes = clubes if clubes else []
        self.maos = maos if maos else []
    
    def adicionar_mao(self, mao):
        self.maos.append(mao)
        if mao.clube not in self.clubes:
            self.clubes.append(mao.clube)
    def __repr__(self):
        return f"Jogador [{self.id_jogador}]: {self.nome_jogador} - Clubes: {', '.join([str(clube) for clube in self.clubes])}"
    
class Mao:
    def __init__(self, data, jogador, clube, id_mao, id_mesa, nome_mesa, ganhos, rake):
        self.data = data
        self.jogador = jogador
        self.clube = clube
        self.id_mao = id_mao
        self.id_mesa = id_mesa
        self.nome_mesa = nome_mesa
        self.ganhos = ganhos
        self.rake = rake
    
    def __repr__(self):
        return (f"[{self.id_mao}]: {self.jogador.nome_jogador} - {self.clube.id_clube} - {self.ganhos} - {self.rake}")
