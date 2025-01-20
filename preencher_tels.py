import pandas as pd
import streamlit as st
import os

# Função para validar os números de telefone
def validar_telefone(fone):
    if len(fone) == 11 or (len(fone) == 13 and fone.startswith("55")):
        return fone
    return "0"

# Função principal para rodar o Streamlit
def main():
    st.title("Processamento de Dados de CPF")
    
    # Áreas para upload dos arquivos
    uploaded_file = st.file_uploader("Escolha o arquivo principal", type=["csv"])
    uploaded_files_dados = st.file_uploader("Escolha os arquivos de base de dados", type=["csv"], accept_multiple_files=True)

    if uploaded_file is not None and uploaded_files_dados:
        # Processar arquivos de base de dados
        lista = []
        for file in uploaded_files_dados:
            base = pd.read_csv(file, sep=';', encoding='latin1', low_memory=False)
            lista.append(base)

        base = pd.concat(lista)
        
        # Limpar os dados de telefone
        for coluna in ['FONE1', 'FONE2', 'FONE3', 'FONE4']:
            base[coluna] = base[coluna].astype(str).str.replace(".", "")
            base[coluna] = base[coluna].apply(validar_telefone)

        # Renomear colunas
        base.rename(columns={'NuCPF': 'CPF', 'Nascimento': 'Data_Nascimento'}, inplace=True)
        
        # Ler o arquivo principal (arquivo para atualizar com os dados)
        df = pd.read_csv(uploaded_file, sep=';')
        convenio = df.loc[1, 'Convenio']

        # Mapear as colunas da base de dados para o arquivo principal
        colunas_para_atualizar = ['FONE1', 'FONE2', 'FONE3', 'FONE4', 'Data_Nascimento']
        mapeamento = {coluna: base.set_index('CPF')[coluna].to_dict() for coluna in colunas_para_atualizar}
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
