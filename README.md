# Projeto Final: Banco de Dados Fórmula 1

Aplicação web desenvolvida para a disciplina de Laboratório de Banco de Dados.
O sistema usa a base histórica da Fórmula 1, com dados de cidades e aeroportos,
e oferece login, dashboards, relatórios e cadastros por perfil de usuário.

## O que tem no projeto

- Banco PostgreSQL com esquema, carga e correções da base.
- Aplicação web em Flask.
- Autenticação por tabela `USERS`.
- Perfis `Admin`, `Escuderia` e `Piloto`.
- Dashboards e relatórios específicos para cada perfil.

## Estrutura principal

- `db/init`: scripts SQL de schema, carga, correção e rotinas do projeto.
- `dados`: arquivos CSV/TSV usados na carga e nos testes de erro.
- `src`: aplicação Flask, controllers, DAOs e utilitários.
- `docker-compose.yml`: sobe banco e aplicação.

## Como rodar

1. Abra o terminal na raiz do projeto.
2. Garanta que o Docker Desktop esteja aberto e no contexto Linux:

```bash
docker context use desktop-linux
```

3. Suba os containers:

```bash
docker compose up -d --build
```

4. Na primeira execução, aguarde a carga do banco terminar. Ela pode levar alguns minutos.
5. Verifique os logs se quiser acompanhar a inicialização:

```bash
docker logs -f f1_db
docker logs -f f1_web
```

6. Quando o sistema estiver pronto, acesse:

```text
http://localhost:3000
```

## Como saber que já ficou pronto

O site só deve responder depois que:

- o container `f1_db` estiver saudável;
- o banco terminar a carga inicial;
- o container `f1_web` subir sem erro;
- a porta `3000` estiver disponível no navegador.

Se a tela ficar em branco, der `ERR_EMPTY_RESPONSE` ou abrir antes da hora, espere mais um pouco e recarregue a página.

Se preferir ver tudo no terminal na primeira vez, use:

```bash
docker compose up --build
```

Sem o `-d`, você acompanha a inicialização até o sistema ficar pronto.

## Credenciais de teste

### Admin

- Login: `admin`
- Senha: `admin`

### Escuderia

- Login: `ferrari_c`
- Senha: `ferrari`

### Piloto

- Login: `hamilton_d`
- Senha: `hamilton`

## Como testar as regras do banco

No login de escuderia, use a tela de upload de pilotos e os arquivos da pasta `dados/testes_erro/`:

1. `1_piloto_duplicado.csv`
2. `2_piloto_sem_ref.csv`
3. `3_resultado_fk_invalida.csv`

Eles foram preparados para falhar e ajudar a demonstrar as restrições do banco.

## Comandos úteis

Desligar tudo e apagar os dados:

```bash
docker compose down -v
```

Reiniciar só a aplicação web:

```bash
docker restart f1_web
```

Ver logs da web:

```bash
docker logs -f f1_web
```

Ver logs do banco:

```bash
docker logs -f f1_db
```

Ver se os containers estão ativos:

```bash
docker ps
```
