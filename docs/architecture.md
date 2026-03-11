# Arquitetura proposta

- `src/clinic/models/`: entidades como `Appointment` mantêm atributos simples.
- `src/clinic/services/`: regras de negócio; `Scheduler` coordena inserção e listagem.
- `src/clinic/app.py`: entrypoint que pode ser expandido para CLI ou API.
- `tests/`: conjunto de smoke tests para prevenir regressões básicas.
- `scripts/`: scripts auxiliares de execução (ex.: `run_dev.sh` para subir o serviço de exemplo).
- `configs/`: local para encontrar configurações YAML, JSON ou .env compartilháveis.
- `src/clinic/services/scheduler.py`: agora expõe APIs para médicos bloquearem horários e consultarem suas consultas agendadas.
- A recepção agora pode ver uma visão geral (`reception_overview`), listar consultas de um paciente específico e confirmar o check-in antes de liberar a consulta.
- `src/clinic/storage.py`: cada banco é um arquivo SQLite em `data/`; a classe lista bancos, recria do zero e permite deletar ou selecionar aquele que será usado na sessão.
- `streamlit_app.py`: expõe sessões distintas para pacientes, médicos e recepção e opera sobre os bancos criados com `StorageManager`.
