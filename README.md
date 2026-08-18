# 🎓 LEI Projects — Diogo Saldanha

> Repositório com os projetos académicos realizados durante a **Licenciatura em Engenharia Informática (LEI)**.

---

## 👨‍💻 Sobre

**Autor:** Diogo Saldanha  
**Curso:** Licenciatura em Engenharia Informática (LEI)  
**Instituição:** Universidade de Coimbra

> [!NOTE]
> Todos os projetos presentes neste repositório são trabalhos de grupo, realizados em colaboração com colegas. A autoria é partilhada e os contributos individuais variam consoante o projeto.

---

## 📂 Estrutura do Repositório

```
LEI-Projects-Diogo-Saldanha/
│
├── PPP/        # Mini-Projeto — Aplicação de Gestão de Doentes
├── ECAC/       # Classificação de Atividades Humanas
├── SO/         # Simulador de Urgências Hospitalar
├── FIA/        # Lunar Lander — Uma Abordagem Reactiva
└── BD/         # Databases Project — Sistema de Metro
```

---

## 📚 Projetos

### 🔵 Princípios de Programação Procedimental (PPP) — Mini-Projeto: Aplicação de Gestão de Doentes

**Localização:** [`PPP/`](./PPP/)

> **Trabalho de grupo** desenvolvido em **linguagem C**. Implementa um sistema de gestão de doentes com:

- Estrutura de dados de **lista ligada** para armazenar registos de doentes
- Operações CRUD completas (criar, ler, atualizar, eliminar)
- Validação robusta de dados (datas, números de telefone, etc.)
- Persistência de dados em ficheiros de texto (`doentes.txt`, `registos.txt`)
- Tratamento de sinais (`signal.h`)

**Tecnologias:** `C` · `stdio.h` · `stdlib.h` · `signal.h`

---

### 🟢 Engenharia de Características para Aprendizagem Computacional (ECAC) — Classificação de Atividades Humanas

**Localização:** [`ECAC/`](./ECAC/)

> **Trabalho de grupo** que implementa um pipeline completo de Machine Learning para **classificação de atividades humanas** com base em dados de sensores inerciais (acelerómetro/giroscópio):

- **Pré-processamento** de dados temporais multi-dispositivo (`data_loader.py`)
- **Extração de features** temporais e espectrais com janelas deslizantes (`feature_extraction.py`)
- **Deteção de outliers** via Z-score (`outlier_analysis.py`)
- **Redução de dimensionalidade** com PCA e ReliefF (`dimensionality_reduction.py`)
- **Classificação** com KNN (`knn_classifier.py`)
- **Geração de embeddings** com modelo HARNet (`embeddings_utils.py`)
- **Balanceamento** de classes com SMOTE (`smote.py`)
- Visualizações 3D de clusters K-Means e PCA

**Tecnologias:** `Python` · `scikit-learn` · `NumPy` · `SMOTE` · `HARNet`

---

### 🟠 Sistemas Operativos (SO) — Simulador de Urgências Hospitalar

**Localização:** [`SO/`](./SO/)

> **Trabalho de grupo** que simula um **sistema de urgências hospitalar** com múltiplos processos concorrentes:

- Receção de pedidos (paciente individual ou grupo) via `input_pipe` (FIFO)
- **Triagem concorrente** por um pool de threads com fila de prioridades (`triage_queue.c`)
- Encaminhamento para atendimento via **Message Queue (MSQ)** com prioridade
- Atendimento por processos **Doctor** (permanentes e temporários) (`doctor.c`)
- **Estatísticas** em memória partilhada (SHM) com `SIGUSR1` para impressão (`stats.c`)
- Sistema de **logging** de eventos (`logger.c`)
- `Makefile` para compilação

**Tecnologias:** `C` · `POSIX IPC` · `Semáforos` · `Memória Partilhada` · `Pthreads` · `Makefile`

---

### 🟣 Fundamentos de Inteligência Artificial (FIA) — Lunar Lander: Uma Abordagem Reactiva

**Localização:** [`FIA/`](./FIA/)

> **Trabalho de grupo** de **Reinforcement Learning** usando o ambiente `LunarLander-v3` do OpenAI Gymnasium. O agente aprende a aterrar uma nave lunar em modo de ação contínua:

- Implementação de agente com controlo contínuo (4 impulsos)
- Critérios de aterragem bem-sucedida (posição, velocidade, ângulo, contacto)
- Suporte a condições adversas: **vento** e **turbulência** configuráveis
- Modo sem renderização para treino rápido em batch (1000 episódios)

**Tecnologias:** `Python` · `OpenAI Gymnasium` · `NumPy` · `Pygame`

---

### 🔴 Bases de Dados (BD) — Databases Project: Sistema de Metro

**Localização:** [`BD/`](./BD/)

> **Trabalho de grupo** que desenvolve uma **API REST** para um sistema de gestão de **Metro**. Inclui:

- API REST completa com **Flask** (`metro.py`)
- Base de dados **PostgreSQL** com script de criação e população (`metafinal.sql`)
- Autenticação com **JWT** (JSON Web Tokens)
- Diagrama da base de dados (`meta2diagrama.json`)
- Coleção **Postman** para testar os endpoints (`metropostman.json`)
- Relatório do projeto (`relatorio.pdf`)

**Tecnologias:** `Python` · `Flask` · `PostgreSQL` · `psycopg2` · `JWT`

---

## 📄 Licença

Este repositório é de carácter académico e pessoal. O código é disponibilizado para fins de portfólio e referência.

---

*Diogo Saldanha — LEI, Universidade de Coimbra*
