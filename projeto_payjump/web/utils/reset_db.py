'''
Script para limpar dados do banco (mantém estrutura)
'''

from database import Session, FraudadorIdentificado, HistoricoRessarcimento, Acumulado

def limpar_banco_completo():
    '''
    Remove TODOS os dados de todas as tabelas.
    '''
    session = Session()
    try:
        # Contar antes
        count_fraudadores = session.query(FraudadorIdentificado).count()
        count_historico = session.query(HistoricoRessarcimento).count()
        count_acumulados = session.query(Acumulado).count()

        print(f'📊 ANTES DA LIMPEZA:')
        print(f'\tFraudadores: {count_fraudadores}')
        print(f'\tHistórico: {count_historico}')
        print(f'\tAcumulados: {count_acumulados}')
        print()

        # Deletar tudo
        session.query(FraudadorIdentificado).delete()
        session.query(HistoricoRessarcimento).delete()
        session.query(Acumulado).delete()

        session.commit()

        print('✅ Banco limpo com sucesso!')
        print()
        print('📊 DEPOIS DA LIMPEZA:')
        print(f'\tFraudadores: {count_fraudadores}')
        print(f'\tHistórico: {count_historico}')
        print(f'\tAcumulados: {count_acumulados}')
        print()

    except Exception as e:
        session.rollback()
        print(f'❌ Erro ao limpar o banco: {e}')
    
    finally:
        session.close()

def limpar_fraudadores():
    '''
    Remove apenas os fraudadores
    '''
    session = Session()
    try:
        count = session.query(FraudadorIdentificado).count()
        session.query(FraudadorIdentificado).delete()
        session.commit()
        print(f'✅ {count} fraudador(es) removido(s)')
    
    except Exception as e:
        session.rollback()
        print(f'❌ Erro ao limpar os fraudadores: {e}')
    
    finally:
        session.close()

def limpar_historico():
    '''
    Remove apenas o histórico
    '''
    session = Session()
    try:
        count = session.query(HistoricoRessarcimento).count()
        session.query(HistoricoRessarcimento).delete()
        session.commit()
        print(f'✅ {count} ressarcimento(s) removido(s)')
    
    except Exception as e:
        session.rollback()
        print(f'❌ Erro ao limpar o histórico de ressarcimentos: {e}')
    
    finally:
        session.close()

def limpar_acumulados():
    '''
    Remove apenas os acumulados
    '''
    session = Session()
    try:
        count = session.query(Acumulado).count()
        session.query(Acumulado).delete()
        session.commit()
        print(f'✅ {count} acumulado(s) removido(s)')
    
    except Exception as e:
        session.rollback()
        print(f'❌ Erro ao limpar o acumulado: {e}')
    
    finally:
        session.close()

if __name__ == '__main__':
    print('=' * 60)
    print('🗑️   RESET DO BANCO DE DADOS')
    print('=' * 60)
    print()
    print('Escolha uma opção:')
    print('1 - Limpar TUDO (fraudadores + histórico + acumulados)')
    print('2 - Limpar apenas Fraudadores')
    print('3 - Limpar apenas Histórico')
    print('4 - Limpar apenas Acumulados')
    print('0 - Cancelar')
    print()

    escolha = input('Opção: ').strip()
    match escolha:
        case '1':
            confirma = input('\n⚠️  ATENÇÃO: Isso vai deletar TODOS os dados! Confirma? (S/N): ')
            match confirma.lower():
                case 'sim' | 's':
                    limpar_banco_completo()
                case _:
                    print('Cancelado.')
        case '2':
            limpar_fraudadores()
        case '3':
            limpar_historico()
        case '4':
            limpar_acumulados()
        case '0':
            print('Cancelado.')
        case _:
            print('Opção inválida')