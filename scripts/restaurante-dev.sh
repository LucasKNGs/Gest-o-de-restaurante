#!/usr/bin/env bash

set -e

cd "$(dirname "$0")/.."

echo "🍽️ Iniciando sistema do restaurante..."

# Cria o .env se não existir
if [ ! -f .env ]; then
  echo "📄 Criando .env..."
  cp .env.example .env
fi

# Instala dependências se necessário
if [ ! -d node_modules ]; then
  echo "📦 Instalando dependências..."
  npm install
fi

NOVO_BANCO=0

# Cria o PostgreSQL se ele ainda não existir
if ! docker inspect restaurante-postgres >/dev/null 2>&1; then
  echo "🐘 Criando PostgreSQL..."

  docker run \
    --name restaurante-postgres \
    -e POSTGRES_USER=postgres \
    -e POSTGRES_PASSWORD=postgres \
    -e POSTGRES_DB=restaurante_financeiro \
    -p 5432:5432 \
    -v restaurante_pgdata:/var/lib/postgresql/data \
    -d postgres:16 >/dev/null

  NOVO_BANCO=1
else
  echo "🐘 Ligando PostgreSQL..."
  docker start restaurante-postgres >/dev/null 2>&1 || true
fi

echo "⏳ Esperando PostgreSQL..."

until docker exec restaurante-postgres pg_isready -U postgres >/dev/null 2>&1
do
  sleep 1
done

echo "✅ PostgreSQL pronto."

echo "🔧 Gerando Prisma..."
npm run db:generate

echo "🗃️ Sincronizando banco..."
npm run db:push

if [ "$NOVO_BANCO" = "1" ]; then
  echo "🌱 Criando dados iniciais..."
  npm run db:seed
fi

echo ""
echo "🚀 Abrindo sistema..."
echo ""

npm run dev
