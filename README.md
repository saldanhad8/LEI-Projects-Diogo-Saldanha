# 🎓 LEI Projects — Diogo Saldanha

> Repositório com os projetos académicos realizados durante a **Licenciatura em Engenharia Informática (LEI)**.

---

## 👨‍💻 Sobre

**Autor:** Diogo Saldanha  
**Curso:** Licenciatura em Engenharia Informática  
**Instituição:** Universidade de Coimbra (LEI)

Este repositório contém uma seleção de projetos práticos desenvolvidos ao longo da licenciatura, abrangendo diversas áreas da Engenharia Informática: programação de sistemas, bases de dados, inteligência artificial, computação evolucionária e sistemas operativos.

---

## 📂 Estrutura do Repositório

```
LEI-Projects-Diogo-Saldanha/
│
├── 2ºANO/
│   └── PPP/
│       └── projeto_final/         # Projeto Final de PPP — Gestão de Doentes em C
│
└── 4ºANO/
    ├── ECAC/
    │   └── TP1/                   # Classificação de Atividades Humanas (ML + Python)
    ├── SO/
    │   └── SO_FINAL/              # Sistema de Urgências Hospitalar (C, IPC, threads)
    ├── FIA/
    │   └── TP1/                   # Lunar Lander com Reinforcement Learning (Python)
    └── BD/
        └── metafinal/             # API REST para Sistema de Metro (Flask + PostgreSQL)
```

---

## 📚 Projetos

### 🔵 PPP — Paradigmas de Programação em Português *(2º Ano)*

**Localização:** [`2ºANO/PPP/projeto_final/`](./2ºANO/PPP/projeto_final/)

Projeto final da cadeira de PPP, desenvolvido em **linguagem C**. Implementa um sistema de gestão de doentes com:

- Estrutura de dados de **lista ligada** para armazenar registos de doentes
- Operações CRUD completas (criar, ler, atualizar, eliminar)
- Validação robusta de dados (datas, números de telefone, etc.)
- Persistência de dados em ficheiros de texto (`doentes.txt`, `registos.txt`)
- Tratamento de sinais (`signal.h`)

**Tecnologias:** `C` · `stdio.h` · `stdlib.h` · `signal.h`

---

### 🟢 ECAC — Exploração e Classificação de Atividades Computacionais *(4º Ano)*

**Localização:** [`4ºANO/ECAC/TP1/`](./4ºANO/ECAC/TP1/)

Trabalho prático de **classificação de atividades humanas** com base em dados de sensores inerciais (acelerómetro/giroscópio). O projeto inclui um pipeline completo de Machine Learning:

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

### 🟠 SO — Sistemas Operativos *(4º Ano)*

**Localização:** [`4ºANO/SO/SO_FINAL/`](./4ºANO/SO/SO_FINAL/)

**Autores:** Diogo Saldanha · João Dias

Projeto final de Sistemas Operativos que simula um **sistema de urgências hospitalar** com múltiplos processos concorrentes. Implementa:

- Arquitetura multi-processo com **processos de triagem** e **processos médicos**
- Comunicação inter-processo (**IPC**): memória partilhada, semáforos e pipes
- **Fila de triagem** com prioridades (`triage_queue.c`)
- Sistema de **logging** de eventos (`logger.c`)
- **Estatísticas** em tempo real (`stats.c`)
- Ficheiro de configuração parametrizável (`config.txt`)
- `Makefile` para compilação

**Tecnologias:** `C` · `POSIX IPC` · `Semáforos` · `Memória Partilhada` · `Pthreads` · `Makefile`

---

### 🟣 FIA — Fundamentos de Inteligência Artificial *(4º Ano)*

**Localização:** [`4ºANO/FIA/TP1/`](./4ºANO/FIA/TP1/)

Trabalho prático de **Reinforcement Learning** usando o ambiente `LunarLander-v3` do OpenAI Gymnasium. O agente aprende a aterrar uma nave lunar em modo de ação contínua:

- Implementação de agente com controlo contínuo (4 impulsos)
- Critérios de aterragem bem-sucedida (posição, velocidade, ângulo, contacto)
- Suporte a condições adversas: **vento** e **turbulência** configuráveis
- Modo sem renderização para treino rápido em batch (1000 episódios)

**Tecnologias:** `Python` · `OpenAI Gymnasium` · `NumPy` · `Pygame`

---

### 🔴 BD — Bases de Dados *(4º Ano)*

**Localização:** [`4ºANO/BD/metafinal/`](./4ºANO/BD/metafinal/)

Projeto final de Bases de Dados — desenvolvimento de uma **API REST** para um sistema de **Metro**. Inclui:

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
