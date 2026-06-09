-- EXTENSÃO PARA CRIPTOGRAFIA DE SENHAS
CREATE EXTENSION IF NOT EXISTS pgcrypto;

/*
 * DDL: Tabelas de Sistema e Autenticação
 * Armazena usuários do sistema (Admin, Escuderia, Piloto) e logs de acesso.
 */
CREATE TABLE USERS (
    userid SERIAL PRIMARY KEY,
    login VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('Admin', 'Escuderia', 'Piloto')),
    id_original INTEGER NULL
);

CREATE TABLE USERS_LOG (
    logid SERIAL PRIMARY KEY,
    userid INTEGER REFERENCES USERS(userid) ON DELETE CASCADE,
    action VARCHAR(20) NOT NULL CHECK (action IN ('LOGIN', 'LOGOUT')),
    action_date TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Inserção do usuário Administrador padrão
INSERT INTO USERS (login, password, tipo, id_original)
VALUES ('admin', crypt('admin', gen_salt('bf', 8)), 'Admin', NULL);

/*
 * Triggers de Validação (BEFORE INSERT/UPDATE)
 * Garante unicidade e formatação de logins para novos pilotos e escuderias.
 */
CREATE OR REPLACE FUNCTION trg_check_driver_login_duplicate()
RETURNS TRIGGER AS $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM USERS 
        WHERE login = NEW.driver_ref || '_d' 
          AND (id_original IS NULL OR id_original <> NEW.id OR tipo <> 'Piloto')
    ) THEN
        RAISE EXCEPTION 'Erro: Já existe um usuário com o login %', NEW.driver_ref || '_d';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION trg_check_constructor_login_duplicate()
RETURNS TRIGGER AS $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM USERS 
        WHERE login = NEW.constructor_ref || '_c' 
          AND (id_original IS NULL OR id_original <> NEW.id OR tipo <> 'Escuderia')
    ) THEN
        RAISE EXCEPTION 'Erro: Já existe um usuário com o login %', NEW.constructor_ref || '_c';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_drivers_before_insert_update
BEFORE INSERT OR UPDATE ON drivers
FOR EACH ROW EXECUTE FUNCTION trg_check_driver_login_duplicate();

CREATE TRIGGER trg_constructors_before_insert_update
BEFORE INSERT OR UPDATE ON constructors
FOR EACH ROW EXECUTE FUNCTION trg_check_constructor_login_duplicate();


/*
 * Triggers de Sincronização (AFTER INSERT/UPDATE)
 * Espelha a criação de pilotos e escuderias na tabela USERS com senha inicial gerada (bcrypt).
 */
CREATE OR REPLACE FUNCTION trg_sync_driver_user()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO USERS (login, password, tipo, id_original)
        VALUES (
            NEW.driver_ref || '_d',
            crypt(NEW.driver_ref, gen_salt('bf', 8)),
            'Piloto',
            NEW.id
        );
    ELSIF TG_OP = 'UPDATE' THEN
        UPDATE USERS
        SET login = NEW.driver_ref || '_d',
            password = crypt(NEW.driver_ref, gen_salt('bf', 8))
        WHERE id_original = OLD.id AND tipo = 'Piloto';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION trg_sync_constructor_user()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO USERS (login, password, tipo, id_original)
        VALUES (
            NEW.constructor_ref || '_c',
            crypt(NEW.constructor_ref, gen_salt('bf', 8)),
            'Escuderia',
            NEW.id
        );
    ELSIF TG_OP = 'UPDATE' THEN
        UPDATE USERS
        SET login = NEW.constructor_ref || '_c',
            password = crypt(NEW.constructor_ref, gen_salt('bf', 8))
        WHERE id_original = OLD.id AND tipo = 'Escuderia';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_drivers_after_insert_update
AFTER INSERT OR UPDATE ON drivers
FOR EACH ROW EXECUTE FUNCTION trg_sync_driver_user();

CREATE TRIGGER trg_constructors_after_insert_update
AFTER INSERT OR UPDATE ON constructors
FOR EACH ROW EXECUTE FUNCTION trg_sync_constructor_user();


/*
 * Função utilitária: Haversine Distance
 * Calcula a distância em km entre duas coordenadas geográficas.
 * Utilizada no processamento geográfico do R2.
 */
CREATE OR REPLACE FUNCTION haversine_distance(
    lat1 DOUBLE PRECISION, 
    lon1 DOUBLE PRECISION, 
    lat2 DOUBLE PRECISION, 
    lon2 DOUBLE PRECISION
)
RETURNS DOUBLE PRECISION AS $$
DECLARE
    r DOUBLE PRECISION := 6371.0; -- Raio da Terra em km
    dlat DOUBLE PRECISION;
    dlon DOUBLE PRECISION;
    a DOUBLE PRECISION;
    c DOUBLE PRECISION;
BEGIN
    dlat := radians(lat2 - lat1);
    dlon := radians(lon2 - lon1);
    a := sin(dlat/2) * sin(dlat/2) + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2) * sin(dlon/2);
    c := 2 * atan2(sqrt(a), sqrt(1-a));
    RETURN r * c;
END;
$$ LANGUAGE plpgsql;


/*
 * Bloco: Funções de agregação para dashboards analíticos.
 * Otimizadas com subqueries correlacionadas para reduzir tráfego no pool de conexões.
 */

/*
 * Retorna KPIs sumarizados para o dashboard da escuderia logada.
 * @param p_constructor_id ID da escuderia no esquema base.
 * @return vitorias, quantidade de pilotos distintos, ano inicial e ano final.
 */
CREATE OR REPLACE FUNCTION get_escuderia_dashboard(p_constructor_id INT)
RETURNS TABLE (
    vitorias BIGINT,
    qtd_pilotos BIGINT,
    primeiro_ano INT,
    ultimo_ano INT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        (SELECT COUNT(*) FROM results r WHERE r.constructor_id = p_constructor_id AND r.position = '1') AS vitorias,
        (SELECT COUNT(DISTINCT r.driver_id) FROM results r WHERE r.constructor_id = p_constructor_id) AS qtd_pilotos,
        (SELECT MIN(ra.year) FROM results r JOIN races rc ON r.race_id = rc.id JOIN seasons ra ON rc.season_id = ra.id WHERE r.constructor_id = p_constructor_id) AS primeiro_ano,
        (SELECT MAX(ra.year) FROM results r JOIN races rc ON r.race_id = rc.id JOIN seasons ra ON rc.season_id = ra.id WHERE r.constructor_id = p_constructor_id) AS ultimo_ano;
END;
$$ LANGUAGE plpgsql;

/*
 * Busca o intervalo de atuação (anos) de um piloto.
 * @param p_driver_id ID do piloto no esquema base.
 */
CREATE OR REPLACE FUNCTION get_piloto_years(p_driver_id INT)
RETURNS TABLE (
    primeiro_ano INT,
    ultimo_ano INT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        (SELECT MIN(ra.year) FROM results r JOIN races rc ON r.race_id = rc.id JOIN seasons ra ON rc.season_id = ra.id WHERE r.driver_id = p_driver_id) AS primeiro_ano,
        (SELECT MAX(ra.year) FROM results r JOIN races rc ON r.race_id = rc.id JOIN seasons ra ON rc.season_id = ra.id WHERE r.driver_id = p_driver_id) AS ultimo_ano;
END;
$$ LANGUAGE plpgsql;

/*
 * Agrega desempenho do piloto por temporada e circuito.
 * @param p_driver_id ID do piloto.
 * @return Tabela contendo ano, circuito, pontos, vitórias e participações.
 */
CREATE OR REPLACE FUNCTION get_piloto_dashboard_details(p_driver_id INT)
RETURNS TABLE (
    ano INT,
    circuito TEXT,
    pontos NUMERIC,
    vitorias BIGINT,
    corridas BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        s.year AS ano,
        c.name AS circuito,
        COALESCE(SUM(r.points), 0) AS pontos,
        SUM(CASE WHEN r.position = '1' THEN 1 ELSE 0 END) AS vitorias,
        COUNT(r.id) AS corridas
    FROM results r
    JOIN races rc ON r.race_id = rc.id
    JOIN seasons s ON rc.season_id = s.id
    JOIN circuits c ON rc.circuit_id = c.id
    WHERE r.driver_id = p_driver_id
    GROUP BY s.year, c.name
    ORDER BY s.year DESC, pontos DESC;
END;
$$ LANGUAGE plpgsql;


/*
 * Bloco: Rotinas para os relatórios gerenciais R1-R7.
 * Implementadas via Views (quando estáticas) e Funções (quando parametrizadas).
 */

/*
 * Relatório R1: Distribuição global de resultados agrupados por status (acidente, desclassificação, etc).
 */
CREATE OR REPLACE VIEW vw_relatorio_status AS
SELECT st.status AS status_nome, COUNT(r.id) AS contagem
FROM results r
JOIN status st ON r.status_id = st.id
GROUP BY st.status
ORDER BY contagem DESC;

/*
 * Relatório R2: Busca aeroportos brasileiros próximos a uma cidade sede.
 * Filtra aeroportos de médio e grande porte num raio de 100km via Haversine.
 * @param p_cidade Nome da cidade base.
 */

CREATE OR REPLACE FUNCTION get_relatorio_aeroportos_proximos(p_cidade VARCHAR)
RETURNS TABLE (
    cidade_pesquisada VARCHAR,
    iata_code VARCHAR,
    nome_aeroporto TEXT,
    cidade_aeroporto VARCHAR,
    distancia DOUBLE PRECISION,
    tipo_aeroporto VARCHAR
) AS $$
DECLARE
    v_brasil_id INT;
BEGIN
    SELECT id INTO v_brasil_id FROM countries WHERE code = 'BR';
    
    RETURN QUERY
    SELECT
        c_orig.name AS cidade_pesquisada,
        ap.iata_code::VARCHAR,
        ap.name AS nome_aeroporto,
        c_dest.name AS cidade_aeroporto,
        haversine_distance(c_orig.latitude, c_orig.longitude, ap.latitude_deg, ap.longitude_deg) AS distancia,
        apt.type::VARCHAR AS tipo_aeroporto
    FROM cities c_orig
    CROSS JOIN airports ap
    JOIN airport_types apt ON ap.airport_type_id = apt.id
    JOIN cities c_dest ON ap.city_id = c_dest.id
    WHERE lower(c_orig.name) = lower(p_cidade)
      AND c_orig.country_id = v_brasil_id
      AND c_dest.country_id = v_brasil_id
      AND apt.type IN ('medium_airport', 'large_airport')
      AND haversine_distance(c_orig.latitude, c_orig.longitude, ap.latitude_deg, ap.longitude_deg) <= 100.0
    ORDER BY distancia ASC;
END;
$$ LANGUAGE plpgsql;

/*
 * Relatório R3: Base de dados materializada (Views) para o relatório hierárquico.
 * vw_relatorio_circuitos_voltas agrega dados em nível de circuito.
 * vw_relatorio_corridas_detalhe detalha métricas por corrida.
 */
CREATE OR REPLACE VIEW vw_relatorio_circuitos_voltas AS
SELECT
    c.id AS circuit_id,
    c.name AS circuit_name,
    COUNT(DISTINCT r.id) AS qtd_corridas,
    MIN(r_laps.max_laps) AS min_voltas,
    ROUND(AVG(r_laps.max_laps), 2) AS avg_voltas,
    MAX(r_laps.max_laps) AS max_voltas
FROM circuits c
LEFT JOIN races r ON r.circuit_id = c.id
LEFT JOIN (
    SELECT race_id, MAX(laps) AS max_laps
    FROM results
    WHERE laps IS NOT NULL AND laps > 0
    GROUP BY race_id
) r_laps ON r_laps.race_id = r.id
GROUP BY c.id, c.name;

CREATE OR REPLACE VIEW vw_relatorio_corridas_detalhe AS
SELECT
    rc.circuit_id,
    rc.id AS race_id,
    rc.race_name,
    s.year AS race_year,
    COALESCE(MAX(res.laps), 0) AS voltas,
    COUNT(DISTINCT res.driver_id) AS qtd_pilotos
FROM races rc
JOIN seasons s ON rc.season_id = s.id
LEFT JOIN results res ON res.race_id = rc.id  -- LEFT JOIN para incluir corridas sem resultados
GROUP BY rc.circuit_id, rc.id, rc.race_name, s.year;

/*
 * Extrai dados consolidados das corridas da última temporada registrada no banco.
 * Utilizado no dashboard macro do administrador.
 */
CREATE OR REPLACE FUNCTION get_dashboard_corridas_temporada_recente()
RETURNS TABLE (
    corrida_nome TEXT,
    circuito_nome TEXT,
    corrida_data DATE,
    corrida_hora TIME,
    voltas INT,
    round_num INT
) AS $$
DECLARE
    v_season_id INT;
BEGIN
    SELECT id INTO v_season_id FROM seasons ORDER BY year DESC LIMIT 1;

    RETURN QUERY
    SELECT
        rc.race_name AS corrida_nome,
        c.name AS circuito_nome,
        rc.race_date AS corrida_data,
        rc.race_time AS corrida_hora,
        COALESCE(MAX(res.laps), 0)::INT AS voltas,
        rc.round AS round_num
    FROM races rc
    JOIN circuits c ON rc.circuit_id = c.id
    LEFT JOIN results res ON res.race_id = rc.id
    WHERE rc.season_id = v_season_id
    GROUP BY rc.id, rc.race_name, c.name, rc.race_date, rc.race_time, rc.round
    ORDER BY rc.round ASC;
END;
$$ LANGUAGE plpgsql;

/*
 * Retorna o ranking de pontuação das escuderias na última temporada.
 */
CREATE OR REPLACE FUNCTION get_dashboard_escuderias_temporada_recente()
RETURNS TABLE (
    escuderia_nome VARCHAR,
    total_pontos NUMERIC,
    total_vitorias BIGINT
) AS $$
DECLARE
    v_season_id INT;
BEGIN
    SELECT id INTO v_season_id FROM seasons ORDER BY year DESC LIMIT 1;

    RETURN QUERY
    SELECT
        con.name AS escuderia_nome,
        COALESCE(SUM(res.points), 0) AS total_pontos,
        SUM(CASE WHEN res.position = '1' THEN 1 ELSE 0 END) AS total_vitorias
    FROM constructors con
    JOIN results res ON res.constructor_id = con.id
    JOIN races rc ON res.race_id = rc.id
    WHERE rc.season_id = v_season_id
    GROUP BY con.id, con.name
    ORDER BY total_pontos DESC, escuderia_nome ASC;
END;
$$ LANGUAGE plpgsql;

/*
 * Retorna o ranking de pontuação dos pilotos na última temporada.
 */
CREATE OR REPLACE FUNCTION get_dashboard_pilotos_temporada_recente()
RETURNS TABLE (
    piloto_nome TEXT,
    escuderia_nome VARCHAR,
    total_pontos NUMERIC,
    total_vitorias BIGINT
) AS $$
DECLARE
    v_season_id INT;
BEGIN
    SELECT id INTO v_season_id FROM seasons ORDER BY year DESC LIMIT 1;

    RETURN QUERY
    SELECT
        (d.given_name || ' ' || d.family_name) AS piloto_nome,
        con.name AS escuderia_nome,
        COALESCE(SUM(res.points), 0) AS total_pontos,
        SUM(CASE WHEN res.position = '1' THEN 1 ELSE 0 END) AS total_vitorias
    FROM drivers d
    JOIN results res ON res.driver_id = d.id
    JOIN constructors con ON res.constructor_id = con.id
    JOIN races rc ON res.race_id = rc.id
    WHERE rc.season_id = v_season_id
    GROUP BY d.id, d.given_name, d.family_name, con.name
    ORDER BY total_pontos DESC, piloto_nome ASC;
END;
$$ LANGUAGE plpgsql;

/*
 * Relatório R4: Agrega a quantidade de primeiros lugares conquistados por piloto para uma escuderia específica.
 * @param p_constructor_id ID da escuderia solicitante.
 */
CREATE OR REPLACE FUNCTION get_relatorio_vitorias_pilotos(p_constructor_id INT)
RETURNS TABLE (
    nome_completo TEXT,
    vitorias BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        (d.given_name || ' ' || d.family_name) AS nome_completo,
        COUNT(r.id) AS vitorias
    FROM results r
    JOIN drivers d ON r.driver_id = d.id
    WHERE r.constructor_id = p_constructor_id
      AND r.position = '1'
    GROUP BY d.id, d.given_name, d.family_name
    ORDER BY vitorias DESC, nome_completo ASC;
END;
$$ LANGUAGE plpgsql;

/*
 * Relatório R5: Histórico de status (abandonos, acidentes, falhas mecânicas) de todos os carros da escuderia.
 * @param p_constructor_id ID da escuderia solicitante.
 */
CREATE OR REPLACE FUNCTION get_relatorio_status_escuderia(p_constructor_id INT)
RETURNS TABLE (
    status_nome TEXT,
    contagem BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        st.status AS status_nome,
        COUNT(r.id) AS contagem
    FROM results r
    JOIN status st ON r.status_id = st.id
    WHERE r.constructor_id = p_constructor_id
    GROUP BY st.id, st.status
    ORDER BY contagem DESC;
END;
$$ LANGUAGE plpgsql;

/*
 * Relatório R6: Cronologia de pontuação de um piloto específico.
 * @param p_driver_id ID do piloto solicitante.
 */
CREATE OR REPLACE FUNCTION get_relatorio_pontos_piloto_ano(p_driver_id INT)
RETURNS TABLE (
    ano INT,
    corrida_nome TEXT,
    corrida_data DATE,
    pontos_obtidos NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        s.year AS ano,
        rc.race_name AS corrida_nome,
        rc.race_date AS corrida_data,
        r.points AS pontos_obtidos
    FROM results r
    JOIN races rc ON r.race_id = rc.id
    JOIN seasons s ON rc.season_id = s.id
    WHERE r.driver_id = p_driver_id
      AND r.points > 0
    ORDER BY ano DESC, corrida_data ASC;
END;
$$ LANGUAGE plpgsql;

/*
 * Relatório R7: Resumo de causas de abandono/sucesso (status) no histórico do piloto.
 * @param p_driver_id ID do piloto solicitante.
 */
CREATE OR REPLACE FUNCTION get_relatorio_status_piloto(p_driver_id INT)
RETURNS TABLE (
    status_nome TEXT,
    contagem BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        st.status AS status_nome,
        COUNT(r.id) AS contagem
    FROM results r
    JOIN status st ON r.status_id = st.id
    WHERE r.driver_id = p_driver_id
    GROUP BY st.id, st.status
    ORDER BY contagem DESC;
END;
$$ LANGUAGE plpgsql;


/*
 * Bloco: Índices B-Tree para otimização de consultas e joins pesados.
 * Foco nos filtros de relatórios (R2, R4, R5) e views de dashboard.
 */
/*
 * Índice funcional e composto: Otimiza a busca case-insensitive de cidades brasileiras no R2.
 */
CREATE INDEX IF NOT EXISTS idx_cities_lower_name_country ON cities (lower(name), country_id);

/*
 * Índices em FKs da tabela results para evitar seq scans massivos durante as agregações dos relatórios.
 */
CREATE INDEX IF NOT EXISTS idx_results_constructor_pos ON results (constructor_id, position);
CREATE INDEX IF NOT EXISTS idx_results_driver_points ON results (driver_id, points);
CREATE INDEX IF NOT EXISTS idx_results_race_id ON results (race_id);
CREATE INDEX IF NOT EXISTS idx_races_circuit_id ON races (circuit_id);
CREATE INDEX IF NOT EXISTS idx_airports_city_type ON airports (city_id, airport_type_id);
