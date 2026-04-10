.PHONY: up down logs collect train shell-db

# Sobe tudo
up:
	docker compose up -d

# Derruba tudo
down:
	docker compose down

# Logs do coletor em tempo real
logs:
	docker compose logs -f collector

# Roda uma coleta manual agora
collect:
	docker compose exec collector python main.py

# Treina o modelo (precisa de dados no banco)
train:
	cd ml && python train.py

# Acessa o banco via psql
shell-db:
	docker compose exec db psql -U $${DB_USER} -d mobilidade_jp

# Verifica saúde da API
health:
	curl -s http://localhost:8000/health | python3 -m json.tool

# Instala dependências locais de ML
install-ml:
	pip install -r ml/requirements.txt
