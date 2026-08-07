-- ====================================================================
-- 1. LIMPEZA TOTAL (DROP DAS TABELAS ANTIGAS E NOVAS)
-- ====================================================================
DROP TABLE IF EXISTS 
    avisoCliente, paragens, admin, histPrecos, tipoBilhete, bilhetePasse, movimentoCarteira, 
    validacao, mov_carteira, titulo_viagem, tarifario, promocao, tipo_produto, 
    aviso, viagem, estacao_linha, linhaEstacao, estacao, linha_operacao, linha, 
    cliente, administrador, super_admin, utilizador 
CASCADE;

-- ====================================================================
-- 2. CRIAÇÃO DAS TABELAS (MODELO FINAL)
-- ====================================================================

-- Tabela Base de Utilizadores (Herança Pai)
-- Nota: Adicionei 'username' para ser compatível com o teu login do Checkpoint 1, 
-- e 'email' para ser compatível com o registo pedido no enunciado final.
-- ====================================================================
-- 1. LIMPEZA TOTAL (DROP DAS TABELAS ANTIGAS E NOVAS)
-- ====================================================================
DROP TABLE IF EXISTS 
    avisoCliente, paragens, admin, histPrecos, tipoBilhete, bilhetePasse, movimentoCarteira, 
    validacao, mov_carteira, titulo_viagem, tarifario, promocao, tipo_produto, 
    aviso, viagem, estacao_linha, linhaEstacao, estacao, linha_operacao, linha, 
    cliente, administrador, super_admin, utilizador 
CASCADE;

-- ====================================================================
-- 2. CRIAÇÃO DAS TABELAS (MODELO FINAL)
-- ====================================================================

-- Tabela Base de Utilizadores (Herança Pai)
-- Nota: Adicionei 'username' para ser compatível com o teu login do Checkpoint 1, 
-- e 'email' para ser compatível com o registo pedido no enunciado final.
CREATE TABLE utilizador (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    nome VARCHAR(100) NOT NULL
);

-- Tabela SuperAdmin (Filha de Utilizador)
CREATE TABLE super_admin (
    id INT PRIMARY KEY REFERENCES utilizador(id) ON DELETE CASCADE
);

-- Tabela Administrador (Filha de Utilizador)
CREATE TABLE administrador (
    id INT PRIMARY KEY REFERENCES utilizador(id) ON DELETE CASCADE
);

-- Tabela Cliente (Filha de Utilizador)
CREATE TABLE cliente (
    id INT PRIMARY KEY REFERENCES utilizador(id) ON DELETE CASCADE,
    nif VARCHAR(9) UNIQUE NOT NULL,
    telefone VARCHAR(20) UNIQUE NOT NULL,
    saldo_carteira DOUBLE PRECISION NOT NULL DEFAULT 0.0 CHECK(saldo_carteira >= 0)
);

-- Tabela Linha
CREATE TABLE linha (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    tipo VARCHAR(50) -- 'urbano' ou 'regional'
);

-- Tabela Linha Operação (Configurações da Linha - 1:1 com Linha)
CREATE TABLE linha_operacao (
    linha_id INT PRIMARY KEY REFERENCES linha(id) ON DELETE CASCADE,
    hora_inicio TIME NOT NULL,
    hora_fim TIME NOT NULL,
    freq_minutos INT NOT NULL,
    capacidade_veic INT NOT NULL DEFAULT 50 -- Conforme o enunciado
);

-- Tabela Estação
CREATE TABLE estacao (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    latitude VARCHAR(50),
    longitude VARCHAR(50)
);

-- Tabela N:M entre Estação e Linha (para definir a ordem)
CREATE TABLE estacao_linha (
    linha_id INT NOT NULL REFERENCES linha(id) ON DELETE CASCADE,
    estacao_id INT NOT NULL REFERENCES estacao(id) ON DELETE CASCADE,
    ordem INT NOT NULL,
    PRIMARY KEY (linha_id, estacao_id)
);

-- Tabela Viagem (Instância de uma partida)
CREATE TABLE viagem (
    id SERIAL PRIMARY KEY,
    linha_id INT NOT NULL REFERENCES linha(id),
    data_hrpartida TIMESTAMP NOT NULL,
    capacidade_atual INT NOT NULL,
    direcao VARCHAR(100) NOT NULL -- Ex: 'Portagem -> Hospital'
);

-- Tabela Tipo de Produto (Bilhetes e Passes)
CREATE TABLE tipo_produto (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(50) UNIQUE NOT NULL,
    categoria VARCHAR(50) NOT NULL -- 'ticket' ou 'pass'
);

-- Tabela Tarifário (Histórico de Preços)
CREATE TABLE tarifario (
    id SERIAL PRIMARY KEY,
    tipo_produto_id INT NOT NULL REFERENCES tipo_produto(id),
    preco DOUBLE PRECISION NOT NULL CHECK(preco >= 0),
    inicio_vigencia DATE NOT NULL,
    fim_vigencia DATE
);

-- Tabela Título de Viagem (O que o cliente comprou)
CREATE TABLE titulo_viagem (
    id SERIAL PRIMARY KEY,
    cliente_id INT NOT NULL REFERENCES cliente(id),
    tipo_produto_id INT NOT NULL REFERENCES tipo_produto(id),
    linha_id INT REFERENCES linha(id), -- Nullable porque um passe pode dar para todas as linhas
    data_compra TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    inicio_validade TIMESTAMP,
    fim_validade TIMESTAMP,
    preco_pago DOUBLE PRECISION NOT NULL CHECK(preco_pago >= 0)
);

-- Tabela Validação (Uso do Título)
CREATE TABLE validacao (
    id SERIAL PRIMARY KEY,
    titulo_viagem_id INT NOT NULL REFERENCES titulo_viagem(id),
    viagem_id INT NOT NULL REFERENCES viagem(id),
    estacao_id INT NOT NULL REFERENCES estacao(id),
    data_hora TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Tabela Promoção
CREATE TABLE promocao (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    percent_desconto DOUBLE PRECISION NOT NULL CHECK(percent_desconto BETWEEN 0 AND 100),
    data_inicio DATE NOT NULL,
    data_fim DATE NOT NULL,
    linha_id INT REFERENCES linha(id),
    tipo_produto_id INT REFERENCES tipo_produto(id)
);

-- Tabela Movimento da Carteira
CREATE TABLE mov_carteira (
    id SERIAL PRIMARY KEY,
    cliente_id INT NOT NULL REFERENCES cliente(id),
    valor DOUBLE PRECISION NOT NULL,
    tipo VARCHAR(50) NOT NULL, -- 'topup' (carregamento) ou 'purchase' (compra)
    data_hora TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Tabela Aviso (Broadcast)
CREATE TABLE aviso (
    id SERIAL PRIMARY KEY,
    administrador_id INT NOT NULL REFERENCES administrador(id),
    titulo VARCHAR(100) NOT NULL,
    mensagem TEXT NOT NULL,
    data_criacao TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ====================================================================
-- 3. INSERÇÃO DOS DADOS INICIAIS (SEED DATA)
-- ====================================================================

-- 3.1. Inserir o SuperAdmin "Hard-coded" exigido pelo projeto
INSERT INTO utilizador (username, email, password, nome) VALUES 
('superadmin', 'superadmin@metromondego.pt', '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918', 'Super Administrador');
INSERT INTO super_admin (id) VALUES (1);

-- (Opcional) Criar já um Administrador normal para testares a criação de avisos
INSERT INTO utilizador (username, email, password, nome) VALUES 
('admin1', 'admin1@metromondego.pt', '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918', 'Admin Operacional');
INSERT INTO administrador (id) VALUES (2);

-- 3.2. Inserir as 3 Linhas do Enunciado
INSERT INTO linha (nome, tipo) VALUES
('Portagem - Hospital', 'urbano'),
('Portagem - Estação B', 'urbano'),
('Portagem - Miranda do Corvo - Lousã (Serpins)', 'regional');

-- 3.3. Inserir as Configurações Operacionais Base das Linhas
INSERT INTO linha_operacao (linha_id, hora_inicio, hora_fim, freq_minutos, capacidade_veic) VALUES
(1, '07:30', '21:00', 20, 50),
(2, '07:45', '19:00', 30, 50),
(3, '07:00', '20:00', 30, 50);

-- 3.4. Inserir Tipos de Produto Exigidos
INSERT INTO tipo_produto (nome, categoria) VALUES
('single_trip', 'ticket'),
('daily', 'ticket'),
('monthly_pass', 'pass'),
('monthly_student_pass', 'pass'),
('monthly_senior_pass', 'pass');

-- 3.5. Inserir Preços Iniciais (Tarifário Vigente)
INSERT INTO tarifario (tipo_produto_id, preco, inicio_vigencia, fim_vigencia) VALUES
(1, 1.50, '2025-01-01', NULL),
(2, 5.00, '2025-01-01', NULL),
(3, 35.00, '2025-01-01', NULL),
(4, 20.00, '2025-01-01', NULL),
(5, 15.00, '2025-01-01', NULL);