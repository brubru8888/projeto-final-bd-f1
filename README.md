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
2. Garanta que o Docker esteja em execução. Se necessário, selecione o contexto correto para o seu sistema:

   Você pode listar os contextos disponíveis com:
   ```bash
   docker context ls
   ```

   E selecionar o correto (geralmente `default` no Linux nativo, ou `desktop-linux` no Windows/macOS com Docker Desktop):
   ```bash
   # Para Linux nativo (padrão):
   docker context use default

   # Para Windows / macOS com Docker Desktop:
   docker context use desktop-linux
   ```

3. Suba os containers:

```bash
docker compose up -d --build
```

> [!TIP]
> **Dica de Sincronização:** Se quiser que o terminal espere ativamente que todo o processo de inicialização do banco (importação de dados) e o seed de usuários na aplicação web (geração de senhas via bcrypt) terminem antes de liberar o prompt, você pode subir os contêineres usando a flag `--wait`:
> ```bash
> docker compose up -d --build --wait
> ```
> O comando ficará aguardando e só terminará exibindo `f1_web Healthy`, garantindo que o site já pode ser acessado de imediato.

4. Verifique os logs se quiser acompanhar o progresso em tempo real:

```bash
docker logs -f f1_db
docker logs -f f1_web
```

5. Quando o sistema estiver pronto, acesse:

```text
http://localhost:3000
```

## Como saber que já ficou pronto

Graças aos testes de saúde (`healthcheck`) configurados no arquivo `docker-compose.yml`, a aplicação web só aceitará conexões quando todo o banco de dados estiver estruturado e os usuários estiverem cadastrados.

Você pode acompanhar o status de prontidão executando:

```bash
docker compose ps
```

* Enquanto o banco carrega os dados ou a web calcula os hashes de senha, o status da aplicação mostrará `(health: starting)`.
* Assim que o site estiver disponível para uso, o status mudará para `(healthy)`.

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
