# Clinic Scheduling System

Estrutura simples para um sistema de agendamento de consultas em Python. O layout separa domínio (`src/clinic`), testes, documentação e automações de suporte.

## Diretórios principais

- `src/clinic/`: código da aplicação com modelos, serviços e orquestração.
- `tests/`: casos de teste básicos para garantir fluxo de agendamento.
- `docs/`: notas de arquitetura e orientações de uso.
- `scripts/`: utilitários de execução/geração.
- `configs/`: exemplos de configuração e contratos.
- `data/`: cada arquivo `.db` é um banco SQLite gerenciado pelo `StorageManager`.

## Uso
1. Estabeleça um ambiente virtual e instale dependências (`pip install -r requirements.txt`).
2. A classe `StorageManager` em `src/clinic/storage.py` cria bancos em `data/`; use `storage.select_database("nome")`, `storage.create_database("nome")`, `storage.list_databases()` e `storage.delete_database("nome")` para alternar entre múltiplos arquivos.
3. Importe `clinic.app`, chame `run_scheduler()` e observe o fluxo registrar pacientes, médicos, agendamentos e check-ins no banco escolhido.
4. Para a interface interativa, rode `streamlit run streamlit_app.py`, navegue pelas abas de pacientes, médicos e visão geral e selecione/crie um banco antes de trabalhar com os dados.
5. O Painel da Recepção mostra métricas, filtros e uma agenda semanal em um layout parecido com a captura anexada, dando à recepção a visão necessária para acompanhar consultas e bloqueios naquela semana.
