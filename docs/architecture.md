# Arquitetura proposta

- `src/clinic/models/`: entidades como `Appointment` mantêm atributos simples.
- `src/clinic/services/`: regras de negócio; `Scheduler` coordena inserção e listagem.
- `src/clinic/app.py`: entrypoint que pode ser expandido para CLI ou API.
- `tests/`: conjunto de smoke tests para prevenir regressões básicas.
- `scripts/`: scripts auxiliares de execução (ex.: `run_dev.sh` para subir o serviço de exemplo).
- `configs/`: local para encontrar configurações YAML, JSON ou .env compartilháveis.
