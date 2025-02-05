import pandas as pd
import streamlit as st
import re

# Função para validar os números de telefone
def validar_telefone(fone):
    try:
        fone_str = str(fone).replace('.0', '')
        fone_str = re.sub(r'[^0-9]', '', fone_str)
        if len(fone_str) == 11 or (len(fone_str) == 13 and fone_str.startswith('55')):
            if fone_str.startswith('55'):
                fone_str = fone_str[2:]
            return str(fone_str)
        return 0
    except:
        return 0

def detectar_delimitador(arquivo):
    # Ler as primeiras linhas do arquivo
    primeiro_chunk = arquivo.read(1024).decode('latin1')
    arquivo.seek(0)  # Retornar ao início do arquivo
    
    # Testar delimitadores comuns
    delimitadores = [',', ';']
    counts = {delimiter: primeiro_chunk.count(delimiter) for delimiter in delimitadores}
    
    # Retornar o delimitador mais frequente
    delimitador = max(counts, key=counts.get)
    st.write(f"Delimitador detectado para {arquivo.name}: {delimitador}")
    return delimitador

def limpar_cpf(cpf):
    # Remove todos os caracteres não numéricos
    if pd.isna(cpf):
        return cpf
    return re.sub(r'[^0-9]', '', str(cpf))

# Função principal para rodar o Streamlit
def main():
    st.title("Processamento de Dados de CPF")
    
    uploaded_file = st.file_uploader("Escolha o arquivo principal", type=["csv"])
    uploaded_files_dados = st.file_uploader("Escolha os arquivos de base de dados", type=["csv"], accept_multiple_files=True)

    if uploaded_file is not None and uploaded_files_dados:
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
                        base[coluna] = base[coluna].apply(validar_telefone)
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
                        base[coluna] = base[coluna].apply(validar_telefone)
                
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
