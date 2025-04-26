import pandas as pd
import streamlit as st
import re

def validar_telefone(fone, opcao):
    try:
        fone_str = str(fone).replace('.0', '')
        fone_str = re.sub(r'[^0-9]', '', fone_str)
        if len(fone_str) == 11 or (len(fone_str) == 13 and fone_str.startswith('55')):
            if fone_str.startswith('55') and opcao == 'Outbound':
                fone_str = fone_str[2:]
            return str(fone_str)
        return 0
    except:
        return 0

def detectar_delimitador(arquivo):
    primeiro_chunk = arquivo.read(1024).decode('latin1')
    arquivo.seek(0)
    delimitadores = [',', ';']
    counts = {delimiter: primeiro_chunk.count(delimiter) for delimiter in delimitadores}
    delimitador = max(counts, key=counts.get)
    st.write(f"Delimitador detectado para {arquivo.name}: {delimitador}")
    return delimitador


def limpar_cpf(cpf):
    if pd.isna(cpf):
        return cpf
    cpf_limpo = re.sub(r'[^0-9]', '', str(cpf))
    return cpf_limpo.zfill(11)


def main():
    st.title("Processamento de Dados de CPF")

    opcao = st.radio("",("Outbound", "App"))
    
    uploaded_file = st.file_uploader("Escolha o arquivo principal", type=["csv"])
    uploaded_files_dados = st.file_uploader("Escolha os arquivos de base de dados", type=["csv"], accept_multiple_files=True)

    if uploaded_file is not None and uploaded_files_dados:

        ## Bloco do Outbound
        if opcao == "Outbound":
        # Separar arquivos RVX dos demais
            arquivos_rvx = []
            outros_arquivos = []
            for file in uploaded_files_dados:
                if "RVX" in file.name.upper():
                    arquivos_rvx.append(file)
                else:
                    outros_arquivos.append(file)

            # Processar primeiro os arquivos RVX
            base_rvx = pd.DataFrame()
            if arquivos_rvx:
                lista_rvx = []
                for file in arquivos_rvx:
                    delimitador = detectar_delimitador(file)
                    base = pd.read_csv(file, sep=delimitador, encoding='latin1', low_memory=False)
                    base.rename(columns={'NuCPF': 'CPF', 'Nascimento': 'Data_Nascimento'}, inplace=True)
                    base['CPF'] = base['CPF'].apply(limpar_cpf)
                    for coluna in ['FONE1', 'FONE2', 'FONE3', 'FONE4']:
                        if coluna not in base.columns:
                            base[coluna] = 0
                        else:
                            base[coluna] = base[coluna].apply(lambda x: validar_telefone(x, opcao))
                    lista_rvx.append(base)
                base_rvx = pd.concat(lista_rvx)

            # Processar outros arquivos
            base_outros = pd.DataFrame()
            if outros_arquivos:
                lista_outros = []
                for file in outros_arquivos:
                    delimitador = detectar_delimitador(file)
                    base = pd.read_csv(file, sep=delimitador, encoding='latin1', low_memory=False)
                    base.rename(columns={'NuCPF': 'CPF', 'Nascimento': 'Data_Nascimento'}, inplace=True)
                    base['CPF'] = base['CPF'].apply(limpar_cpf)
                    for coluna in ['FONE1', 'FONE2', 'FONE3', 'FONE4']:
                        if coluna not in base.columns:
                            base[coluna] = 0
                        else:
                            base[coluna] = base[coluna].apply(lambda x: validar_telefone(x, opcao))
                    
                    lista_outros.append(base)
                
                base_outros = pd.concat(lista_outros)

            # Combinar as bases, priorizando RVX
            if not base_rvx.empty and not base_outros.empty:
                base_rvx = base_rvx[['CPF', 'FONE1', 'FONE2', 'FONE3', 'FONE4', 'Data_Nascimento']]
                base_outros = base_outros[['CPF', 'FONE1', 'FONE2', 'FONE3', 'FONE4', 'Data_Nascimento']]
                
                base = pd.concat([base_rvx, base_outros])
                base = base.drop_duplicates(subset=['CPF'], keep='first')
            elif not base_rvx.empty:
                base = base_rvx
            else:
                base = base_outros

            # Renomear colunas
            base.rename(columns={'NuCPF': 'CPF', 'Nascimento': 'Data_Nascimento'}, inplace=True)
            
            # Ler o arquivo principal
            delimitador_principal = detectar_delimitador(uploaded_file)
            df = pd.read_csv(uploaded_file, sep=delimitador_principal)
            
            # Verificar e padronizar o nome da coluna CPF
            if 'CPF' not in df.columns:
                # Procurar por variações comuns do nome da coluna
                possiveis_nomes = ['NuCPF', 'Nu_CPF', 'Cpf', 'cpf', 'NUCPF']
                st.write("Procurando por variações do nome da coluna CPF...")
                for nome in possiveis_nomes:
                    if nome in df.columns:
                        st.write(f"Encontrada coluna '{nome}', renomeando para 'CPF'")
                        df.rename(columns={nome: 'CPF'}, inplace=True)
                        break
                else:
                    st.error("Coluna CPF não encontrada no arquivo principal. Por favor, verifique se existe uma coluna com CPF.")
                    st.write("Nomes de colunas esperados:", possiveis_nomes)
                    return

            # Limpar CPFs do arquivo principal
            df['CPF'] = df['CPF'].apply(limpar_cpf)

            # Criar colunas FONE1-4 se não existirem
            for coluna in ['FONE1', 'FONE2', 'FONE3', 'FONE4']:
                if coluna not in df.columns:
                    df[coluna] = "0"

            # Verificar se a coluna Data_Nascimento existe no DataFrame principal
            if 'Data_Nascimento' in df.columns:
                if df['Data_Nascimento'].isna().sum() > 0:
                    colunas_para_atualizar = ['FONE1', 'FONE2', 'FONE3', 'FONE4', 'Data_Nascimento']
                else:
                    colunas_para_atualizar = ['FONE1', 'FONE2', 'FONE3', 'FONE4']
                
                # Create mapping for all columns at once
                mapeamento = {coluna: base.set_index('CPF')[coluna].to_dict() for coluna in colunas_para_atualizar}
                
                # Apply mapping to all columns
                for coluna in colunas_para_atualizar:
                    df[coluna] = df['CPF'].map(mapeamento[coluna]).combine_first(df[coluna])

        ## Bloco do App
        else:
            delimitador = detectar_delimitador(uploaded_file)
            # Criação e tratamento do DF a partir da higienização
            df = pd.read_csv(uploaded_file, sep=delimitador, encoding='latin1', low_memory=False)
            df['Email'] = ""
            df['Nome_Cliente'] = df['Nome_Cliente'].str.strip()
            df[['Nome', 'Sobrenome']] = df['Nome_Cliente'].str.split(' ', n=1, expand=True)
            df['CPF'] = df['CPF'].apply(limpar_cpf) # Verificar se o filtrador já não trata os CPFs

            # Criação e tratamento do DF a partir do arquivo com os dados de telefone, data de nascimento e email
            base = pd.read_csv(uploaded_files_dados[0], sep=',', encoding='latin1', low_memory=False)
            base['cpf'] = base['cpf'].apply(limpar_cpf)
            base['telefone'] = base['telefone'].apply(lambda x: validar_telefone(x, opcao))
            base['aniversario'] = base['aniversario'].str[8:10] + "/" + base['aniversario'].str[5:7] + "/" + base['aniversario'].str[0:4]

            
            colunas_para_atualizar = ['FONE1', 'Data_Nascimento', 'Email']

            ## Dicionário de colunas
            mapeamento_colunas = {
                'FONE1': 'telefone',
                'Data_Nascimento': 'aniversario',
                'Email': 'email'
                }
            
            mapeamento = {}

            for coluna_df in colunas_para_atualizar:
                coluna_base = mapeamento_colunas[coluna_df]
                mapeamento[coluna_df] = base.set_index('cpf')[coluna_base].to_dict()

            for coluna in colunas_para_atualizar:
                df[coluna] = df['CPF'].map(mapeamento[coluna]).combine_first(df[coluna])


        # Ordenar as colunas
        ordem_colunas = [
            'ORIGEM DO DADO', 'Nome_Cliente', 'Nome', 'Sobrenome', 'Matricula',
            'CPF', 'Data_Nascimento', 'Mg_Emprestimo_Total',
            'Mg_Emprestimo_Disponivel', 'Mg_Beneficio_Saque_Total',
            'Mg_Beneficio_Saque_Disponivel', 'Mg_Cartao_Total',
            'Mg_Cartao_Disponivel', 'Convenio', 'Vinculo_Servidor', 'Lotacao',
            'Secretaria', 'FONE1', 'FONE2', 'FONE3', 'FONE4', 'Email',
            'valor_liberado_emprestimo', 'valor_liberado_beneficio',
            'valor_liberado_cartao', 'comissao_emprestimo', 'comissao_beneficio',
            'comissao_cartao', 'valor_parcela_emprestimo',
            'valor_parcela_beneficio', 'valor_parcela_cartao', 'banco_emprestimo',
            'banco_beneficio', 'banco_cartao', 'prazo_emprestimo',
            'prazo_beneficio', 'prazo_cartao', 'Campanha'
       ]
        
        df = df[ordem_colunas]


        # Exibir o dataframe resultante
        st.subheader("Arquivo Processado")
        st.write(df)

        
        # Opção para salvar o arquivo atualizado
        st.download_button(
            label="Baixar Arquivo Atualizado",
            data=df.to_csv(index=False).encode('utf-8'),
            file_name="convenio.csv",
            mime="text/csv"
        )

# Rodar o Streamlit
if __name__ == "__main__":
    main()
