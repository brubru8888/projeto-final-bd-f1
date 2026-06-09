# Projeto Final: Banco de Dados Fórmula 1 🏎️

Este projeto é a implementação prática do trabalho final da disciplina de Laboratório de Banco de Dados. Ele consiste na criação de um banco de dados relacional robusto (PostgreSQL) populado com a base histórica da **Kaggle** (1950 a 2023) e da base de cidades da **Geonames**, acoplado a uma aplicação Web (Python Flask) que consome esses dados.

## Estrutura do Repositório

* `/dados`: Arquivos CSV originais do Kaggle e da Geonames. Também contém a pasta `/testes_erro/` com exemplos de arquivos `.csv` para validação de erros de negócio.
* `/db/init`: Scripts SQL que montam todo o esquema, fazem a carga dos dados, limpeza/padronização de cidades (script pesado de correção) e a definição dos nossos Triggers, Views e Stored Functions.
* `/src`: Aplicação Web desenvolvida em Python (Flask) utilizando a arquitetura MVC/DAO.
* `docker-compose.yml`: Arquitetura de microsserviços (Banco de Dados + Servidor Web).

---

## 🚀 Como Rodar o Projeto (Docker)

O projeto está totalmente "conteinerizado", o que significa que você não precisa instalar Python nem PostgreSQL diretamente na sua máquina, apenas o **Docker**.

### 1. Inicializar os Serviços
Abra o terminal na pasta raiz do projeto e execute:
```bash
docker compose up -d --build
```

### 2. ⏳ AGUARDE A CARGA DO BANCO DE DADOS (IMPORTANTE)
Como o sistema carrega e cruza **milhões** de linhas de dados históricos do Kaggle e da Geonames (incluindo deduplicação pesada das cidades), a inicialização do banco de dados pode levar **alguns minutos**.

Se você tentar acessar o site imediatamente e receber um erro de "Conexão Recusada" (Connection Refused), significa que o banco ainda está processando os arquivos `.sql`. 

**Para acompanhar o progresso, veja os logs do banco:**
```bash
docker logs -f f1_db
```
*(Quando parar de rolar mensagens na tela ou aparecer "database system is ready to accept connections", o banco estará pronto!)*

### 3. Acessar o Site
Se o site deu erro de carregamento no início, reinicie o container da web apenas para ele reconectar com o banco recém-criado:
```bash
docker restart f1_web
```

Acesse o sistema no navegador:
👉 **http://localhost:3000**

---

## 🔑 Credenciais de Teste

Nós utilizamos uma tabela própria (`USERS`) blindada com senhas criptografadas em `bcrypt`. O sistema conta com três níveis de acesso e três Dashboards diferentes. 

Para testar todas as funcionalidades desenvolvidas, utilize os logins gerados automaticamente pelo sistema:

**1. Administrador** (Acesso total e relatórios gerenciais)
* **Login:** `admin`
* **Senha:** `admin`

**2. Escuderia** (Upload de pilotos e relatórios da equipe)
* **Login:** `ferrari_c` (Exemplo da Ferrari)
* **Senha:** `ferrari`

**3. Piloto** (Upload de resultados e relatórios individuais)
* **Login:** `hamilton_d` (Exemplo de Lewis Hamilton)
* **Senha:** `hamilton`

---

## 🧪 Como Testar as Regras e Restrições do Banco de Dados?

O PDF do trabalho exige a demonstração de validações físicas do banco e da aplicação (barrar dados inconsistentes).

Acesse o sistema como **Escuderia** (ex: `ferrari_c`) e utilize a tela de **"Inserção de Piloto por Arquivo CSV"**. Dentro da pasta `dados/testes_erro/` do repositório, você encontrará 3 arquivos de teste preparados para falhar intencionalmente e provar as restrições:

1. **`1_piloto_duplicado.csv`**: Tenta inserir um nome/sobrenome que já existe (aciona a checagem lógica).
2. **`2_piloto_sem_ref.csv`**: Tenta inserir um piloto sem o atributo principal (aciona restrição `NOT NULL`).
3. **`3_resultado_fk_invalida.csv`**: (Para usar na tela de upload de resultados do Piloto) Tenta subir uma corrida usando um ID de corrida inexistente (aciona restrição de `FOREIGN KEY`).

---

## Comandos Úteis

* **Desligar o sistema e apagar os dados** (Útil para zerar o banco de dados e aplicar novos scripts SQL):
  ```bash
  docker compose down -v
  ```
* **Limpar a tela de logs da Web:**
  ```bash
  docker logs -f f1_web
  ```
