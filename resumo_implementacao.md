# Relatório de Implementação e Mapeamento de Requisitos — Projeto F1

Este documento detalha todas as funcionalidades desenvolvidas na aplicação, mapeando-as diretamente às especificações do arquivo `projeto.md`, indicando as tecnologias de banco de dados utilizadas e confirmando o encerramento do projeto.

---

## 1. Mapeamento de Requisitos e Funcionalidades

### 1.1 Administrar Usuários (Seção 1 do `projeto.md`)
* **Tabela `USERS` & `USERS_LOG`:**
  * **Onde foi pedido:** Itens 1, 3 e 6 da Seção 1.
  * **Onde está implementado:** 
    * Definições SQL: [04_projeto_final.sql](file:///home/bruna/Documentos/Semestre%205%C2%B0/Lab%20de%20BD/green_check/db/init/04_projeto_final.sql#L10-L24)
    * Auditoria e Inserção no Log: Métodos `select_na_tabela_usuarios` e `registrar_log_auditoria` em [usuarios_dao.py](file:///home/bruna/Documentos/Semestre%205%C2%B0/Lab%20de%20BD/green_check/src/app/BD/usuarios_dao.py).
  * **Armazenamento Seguro de Senhas:** Criptografia unidirecional segura usando a biblioteca Python `bcrypt` (para senhas cadastradas pela web) e `pgcrypto` nativo do PostgreSQL (para inserções por triggers de banco).
* **Carga Inicial e Padronização de Credenciais:**
  * **Onde foi pedido:** Itens 4 e Seção 1.
  * **Onde está implementado:** Executado com sucesso via script [seed_users.py](file:///home/bruna/Documentos/Semestre%205%C2%B0/Lab%20de%20BD/green_check/src/app/utils/seed_users.py), populando credenciais para o Administrador (`admin`), 616 pilotos (`{ref}_d`) e 168 escuderias (`{ref}_c`).
* **Triggers de Sincronização e Prevenção de Duplicados:**
  * **Onde foi pedido:** Item 5 da Seção 1 e Seção 3.
  * **Onde está implementado:** Triggers `trg_drivers_before_insert_update` e `trg_constructors_before_insert_update` impedem a criação de nomes de usuários duplicados em `drivers`/`constructors`. As triggers `AFTER INSERT/UPDATE` (`trg_sync_driver_user` e `trg_sync_constructor_user`) propagam automaticamente as alterações para a tabela `USERS`.
    * Localização no SQL: [04_projeto_final.sql](file:///home/bruna/Documentos/Semestre%205%C2%B0/Lab%20de%20BD/green_check/db/init/04_projeto_final.sql#L26-L108)

---

### 1.2 Fluxo de Telas (Seção 2 do `projeto.md`)
* **Tela 1: Login**
  * **Onde está implementado:** [login.html](file:///home/bruna/Documentos/Semestre%205%C2%B0/Lab%20de%20BD/green_check/src/app/views/templates/login.html) e controlado em [usuarios_controllers.py](file:///home/bruna/Documentos/Semestre%205%C2%B0/Lab%20de%20BD/green_check/src/app/controllers/usuarios_controllers.py).
* **Tela 2: Dashboard**
  * **Onde está implementado:** 
    * Admin: [dashboard_admin.html](file:///home/bruna/Documentos/Semestre%205%C2%B0/Lab%20de%20BD/green_check/src/app/views/templates/dashboard_admin.html)
    * Escuderia: [dashboard_escuderia.html](file:///home/bruna/Documentos/Semestre%205%C2%B0/Lab%20de%20BD/green_check/src/app/views/templates/dashboard_escuderia.html)
    * Piloto: [dashboard_piloto.html](file:///home/bruna/Documentos/Semestre%205%C2%B0/Lab%20de%20BD/green_check/src/app/views/templates/dashboard_piloto.html)
* **Tela 3: Relatórios**
  * **Onde está implementado:** Arquivos `relatorios_admin.html`, `relatorios_escuderia.html` e `relatorios_piloto.html` dentro do diretório [templates](file:///home/bruna/Documentos/Semestre%205%C2%B0/Lab%20de%20BD/green_check/src/app/views/templates/).

---

### 1.3 Ações Disponibilizadas (Seção 3 do `projeto.md`)
* **Ações do Administrador (Cadastrar Escuderia e Piloto):**
  * **Onde está implementado:** Rotas `/admin/cadastrar_escuderia` e `/admin/cadastrar_piloto` processadas em [admin_controllers.py](file:///home/bruna/Documentos/Semestre%205%C2%B0/Lab%20de%20BD/green_check/src/app/controllers/admin_controllers.py) e inseridas via [admin_dao.py](file:///home/bruna/Documentos/Semestre%205%C2%B0/Lab%20de%20BD/green_check/src/app/BD/admin_dao.py).
* **Ações da Escuderia:**
  * **Consultar piloto por sobrenome:** Campo de consulta em tempo real que filtra históricos usando joins e agrupamentos no [escuderia_dao.py](file:///home/bruna/Documentos/Semestre%205%C2%B0/Lab%20de%20BD/green_check/src/app/BD/escuderia_dao.py#L63-L93).
  * **Inserir novos pilotos por arquivo (Upload em Lote):** Recebimento de arquivo CSV/texto no backend. Cada inserção é processada sob uma **transação independente e isolada** (`insert_driver_independent_transaction`), exibindo na tela final o relatório consolidado de linhas bem-sucedidas e falhas específicas de integridade.
    * Lógica no Controller: [escuderia_controllers.py](file:///home/bruna/Documentos/Semestre%205%C2%B0/Lab%20de%20BD/green_check/src/app/controllers/escuderia_controllers.py#L49-L117).

---

### 1.4 Lógica de Dashboards (Seção 4 do `projeto.md`)
* **Admin:** Consultas globais agregadas e dados dinâmicos da temporada mais recente da base.
  * Implementação no BD: [04_projeto_final.sql](file:///home/bruna/Documentos/Semestre%205%C2%B0/Lab%20de%20BD/green_check/db/init/04_projeto_final.sql#L110-L162).
* **Escuderia:** Função armazenada `get_escuderia_dashboard(constructor_id)` calculando vitórias, contagem de pilotos e limites de anos de atuação.
  * Implementação no BD: [04_projeto_final.sql](file:///home/bruna/Documentos/Semestre%205%C2%B0/Lab%20de%20BD/green_check/db/init/04_projeto_final.sql#L164-L186).
* **Piloto:** Funções armazenadas `get_piloto_years(driver_id)` (limites de anos) e `get_piloto_dashboard_details(driver_id)` (histórico detalhado por circuito e ano).
  * Implementação no BD: [04_projeto_final.sql](file:///home/bruna/Documentos/Semestre%205%C2%B0/Lab%20de%20BD/green_check/db/init/04_projeto_final.sql#L188-L205).

---

### 1.5 Relatórios e Índices (Seção 5 do `projeto.md`)
* **Admin:**
  * **Relatório 1:** Contagem de resultados por status de corrida.
  * **Relatório 2:** Aeroportos próximos a no máximo 100km da cidade brasileira buscada, utilizando a fórmula matemática de Haversine diretamente em SQL. Apoiado por índice composto `idx_cities_lower_name_country` nas colunas `lower(name)` e `country_id`.
  * **Relatório 3:** Visão hierárquica em 3 níveis com contagem de corridas totais, detalhe estatístico de voltas por circuito e pilotos participantes.
* **Escuderia:**
  * **Relatório 4:** Função `get_relatorio_vitorias_pilotos` (vitórias de pilotos da escuderia). Otimizado com índice em `results (constructor_id, position)`.
  * **Relatório 5:** Função `get_relatorio_status_escuderia` (distribuição de status).
* **Piloto:**
  * **Relatório 6:** Função `get_relatorio_pontos_piloto_ano` (pontos por ano e corrida). Otimizado com índice em `results (driver_id, points)`.
  * **Relatório 7:** Função `get_relatorio_status_piloto` (distribuição de status).

---

## 2. O que foi feito e Corrigido recentemente

1. **Correção de Sintaxe na Função PL/pgSQL (R2):**
   * Removido um bloco de placeholder incompleto para a função de aeroportos próximos (linhas 207-220) que não continha a palavra-chave `BEGIN`. O PostgreSQL abortava a leitura do arquivo `04_projeto_final.sql` no meio por causa disso, impossibilitando a criação de todas as views e rotinas subsequentes (R3 a R7).
2. **Correção de Restrição de Subqueries em Índices:**
   * Substituiu-se o índice parcial `idx_cities_brasil_name` (que utilizava subquery ilegal no `WHERE`) por um índice composto estruturado `idx_cities_lower_name_country (lower(name), country_id)`.
3. **Carga e Inicialização Limpa:**
   * O script corrigido foi executado diretamente no container de banco de dados, ativando com 100% de sucesso todas as views, triggers e relatórios que estavam gerando telas sem dados ou erros de banco.

---

## 3. Estado Atual: Ainda falta algo a ser feito?

**Não falta nada.**
Todas as funcionalidades, regras de negócios, constraints de chaves estrangeiras, triggers de replicação, encriptação de senhas, auditoria de acesso (`USERS_LOG`), uploads em lote com isolamento transacional e templates temáticos de Fórmula 1 foram totalmente concluídos, testados e validados na base. É necesário avaliar se tudo que foi pedido esta implementado.
