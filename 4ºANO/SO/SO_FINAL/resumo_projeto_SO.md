# 🏥 Projeto SO — Análise Detalhada Função a Função

> **Cadeira:** Sistemas Operativos 2025/2026  
> **Autores:** Diogo Saldanha (2022232761) · João Dias (2022225061)

---

## Índice

1. [Arquitetura e Fluxo Geral](#1-arquitetura-e-fluxo-geral)
2. [config.h / config.c](#2-configh--configc)
3. [patient.h](#3-patienth)
4. [stats.h / stats.c](#4-statsh--statsc)
5. [ipc.h / ipc.c](#5-ipch--ipcc)
6. [logger.h / logger.c](#6-loggerh--loggerc)
7. [triage_queue.h / triage_queue.c](#7-triage_queueh--triage_queuec)
8. [triage.h / triage.c](#8-triageh--triagec)
9. [doctor.c](#9-doctorc)
10. [admission.c](#10-admissionc)
11. [Makefile](#11-makefile)
12. [Variáveis de Condição — Teoria e Uso no Projeto](#12-variáveis-de-condição--teoria-e-uso-no-projeto)
13. [Semáforos — Tipos, Teoria e Uso no Projeto](#13-semáforos--tipos-teoria-e-uso-no-projeto)
14. [Mapa de Conceitos Teóricos](#14-mapa-de-conceitos-teóricos)
15. [Perguntas de Defesa](#15-perguntas-de-defesa)

---

## 1. Arquitetura e Fluxo Geral

O projeto simula um sistema de urgências hospitalar com vários níveis de concorrência. Antes de analisar cada ficheiro, é essencial compreender a arquitetura global e **porquê cada mecanismo foi escolhido**.

```
 [Utilizador escreve no FIFO]
          │
          ▼
 ┌─────────────────────────────────┐
 │        admission (processo pai) │
 │                                 │
 │  ┌──────────────────────────┐   │
 │  │  triage_queue (buffer    │   │   ← partilhada por threads via memória do processo
 │  │  circular em memória)    │   │
 │  └──────────┬───────────────┘   │
 │             │ triage_queue_pop  │
 │  ┌──────────▼───────────────┐   │
 │  │  Thread Triagem 1        │   │   ← pthread_create()
 │  │  Thread Triagem 2        │   │
 │  │  Thread Triagem N        │   │
 │  └──────────┬───────────────┘   │
 └─────────────│───────────────────┘
               │ msgsnd() → Message Queue (System V)
               ▼
 ┌─────────────────────────────────┐
 │  Doctor 1 (processo filho)      │   ← fork()
 │  Doctor 2 (processo filho)      │
 │  Doctor N (processo filho)      │
 └─────────────┬───────────────────┘
               │ lock_stats / unlock_stats
               ▼
 ┌─────────────────────────────────┐
 │  Shared Memory (estatísticas)   │   ← shmget / shmat
 │  + Semáforo POSIX pshared=1     │
 └─────────────────────────────────┘

 ┌─────────────────────────────────┐
 │  Memory-Mapped File (logger)    │   ← mmap MAP_SHARED
 │  + Semáforo POSIX pshared=1     │   ← visível em TODOS os processos
 └─────────────────────────────────┘
```

### Por que esta divisão processo/thread?

| Entidade | Mecanismo | Justificação |
|---|---|---|
| **Médico** | Processo (`fork`) | Isolamento de falhas. Se um médico travar, o pai deteta via `waitpid` e cria outro. Processos têm espaço de endereçamento separado. |
| **Triagem** | Thread (`pthread_create`) | Partilha direta da `triage_queue` (buffer em memória do pai). Criar processos exigiria IPC extra para partilhar a fila. Threads são mais leves. |
| **Admission** | Processo pai | Orquestra tudo: lê o FIFO, cria/monitoriza processos e threads, gere sinais. |

---

## 2. `config.h` / `config.c`

### `config.h` — A estrutura `config_t`

```c
#ifndef CONFIG_H        // Header guard — evita inclusão dupla
#define CONFIG_H

typedef struct {
    int triage_queue_size;  // Capacidade da fila de triagem
    int triage_threads;     // Nº de threads de triagem a criar
    int doctors;            // Nº de médicos permanentes (processos)
    int shift_length;       // Duração do turno em ms
    int msq_wait_max;       // Limiar da message queue para criar médico de reforço
} config_t;

int load_config(const char *filename, config_t *config);

#endif
```

**Por que um `typedef struct` e não variáveis globais?**  
Agrupar toda a configuração numa estrutura permite passá-la como argumento único para threads (`pthread_create(..., &config)`) e processos filhos (`doctor_process_main(sh, &config, ...)`). Variáveis globais espalhadas seriam mais difíceis de gerir e de passar entre funções/módulos.

**Por que `int` e não `unsigned int`?**  
Os campos são inicializados a `-1` em `load_config` para detetar valores em falta. Com `unsigned int`, `-1` converteria para o valor máximo (`UINT_MAX`), tornando a validação impossível.

---

### `config.c` — Função `rtrim`

> **Contexto:** Função auxiliar privada chamada unicamente por `load_config`. O ficheiro `config.txt` usa o formato `"CHAVE = VALOR"`, pelo que a chave lida pelo `sscanf` pode incluir espaços antes do `=`. O `rtrim` limpa esses espaços para que as comparações com `strcmp` funcionem corretamente.

```c
static void rtrim(char *s) {
    size_t len = strlen(s);
    while (len > 0 && (s[len-1] == ' ' || s[len-1] == '\t' || s[len-1] == '\n')) {
        s[len-1] = '\0';
        len--;
    }
}
```

**Por que `static`?**  
`static` numa função de ficheiro `.c` limita a sua visibilidade àquele ficheiro (linkage interno). É uma função auxiliar interna que não faz parte da interface pública do módulo — não deve ser acessível nem causar conflitos de nomes noutros ficheiros.

**Por que `rtrim` é necessária?**  
O `sscanf` com `"%63[^=]"` lê tudo até ao `=`, incluindo espaços antes do `=`. Por exemplo, em `"TRIAGE_QUEUE_MAX = 50"`, a chave lida seria `"TRIAGE_QUEUE_MAX "` (com espaço à direita). Sem `rtrim`, o `strcmp` com `"TRIAGE_QUEUE_MAX"` falharia.

**Por que usar `len-1` como índice e não `len`?**  
Strings em C são indexadas de 0 a `len-1`. O `strlen` retorna o número de caracteres sem contar o `\0` terminador. Assim, `s[len-1]` é o último caractere real da string.

---

### `config.c` — Função `load_config`

> **Contexto:** É a primeira função chamada no `main` (a seguir ao `logger_init`). Lê o ficheiro `config.txt` e preenche a estrutura `config_t` com os parâmetros do sistema — quantas threads de triagem criar, quantos médicos lançar, qual o tamanho da fila, etc. Se falhar, o programa termina imediatamente antes de criar qualquer recurso do SO.

```c
int load_config(const char *filename, config_t *config) {
    FILE *file = fopen(filename, "r");
    if (file == NULL) {
        perror("Failed to open config file");
        return -1;
    }

    // Inicialização defensiva: -1 indica "ainda não lido"
    config->triage_queue_size = -1;
    config->triage_threads    = -1;
    config->doctors           = -1;
    config->shift_length      = -1;
    config->msq_wait_max      = -1;

    char line[256];
    while (fgets(line, sizeof(line), file) != NULL) {
        char key[64];
        int value;

        if (sscanf(line, " %63[^=]= %d", key, &value) == 2) {
            rtrim(key);

            if      (strcmp(key, "TRIAGE_QUEUE_MAX") == 0) config->triage_queue_size = value;
            else if (strcmp(key, "TRIAGE")           == 0) config->triage_threads    = value;
            else if (strcmp(key, "DOCTORS")          == 0) config->doctors           = value;
            else if (strcmp(key, "SHIFT_LENGTH")     == 0) config->shift_length      = value;
            else if (strcmp(key, "MSQ_WAIT_MAX")     == 0) config->msq_wait_max      = value;
            else fprintf(stderr, "Aviso: chave desconhecida: %s\n", key);
        }
    }
    fclose(file);

    // Validação: se algum campo ficou a -1, a config está incompleta
    if (config->triage_queue_size < 0 || config->triage_threads < 0 ||
        config->doctors < 0 || config->shift_length < 0 || config->msq_wait_max < 0) {
        fprintf(stderr, "Configuração incompleta em %s\n", filename);
        return -1;
    }
    return 0;
}
```

**Por que `fgets` + `sscanf` em vez de `fscanf` direto?**  
`fgets` lê uma linha de cada vez de forma segura (com limite de tamanho). `fscanf` aplicado diretamente ao `FILE*` pode saltar linhas ou comportar-se de forma inesperada com espaços e newlines. A combinação `fgets` + `sscanf` dá controlo total sobre cada linha.

**Por que o formato `" %63[^=]= %d"`?**  
- O espaço inicial `" "` consome qualquer whitespace antes da chave.  
- `%63[^=]` lê até 63 caracteres, parando no `=` (o `[^=]` é um "conjunto negado" — lê tudo exceto `=`). O `63` evita buffer overflow no array `key[64]`.  
- `= %d` consome o `=` e o valor inteiro, ignorando espaços entre eles.

**Por que verificar `== 2` no retorno do `sscanf`?**  
`sscanf` retorna o número de itens lidos com sucesso. Se a linha for um comentário, estiver vazia, ou tiver formato errado, retorna menos de 2 — e a linha é ignorada em segurança.

**Por que inicializar a `-1` e validar no final?**  
Padrão **fail-fast**: se o ficheiro de configuração estiver incompleto (faltam parâmetros), o programa termina imediatamente com uma mensagem clara, em vez de continuar com valores por omissão silenciosos que poderiam causar comportamentos indefinidos.

---

## 3. `patient.h`

```c
#ifndef PATIENT_H
#define PATIENT_H

#include <time.h>   // necessário para struct timespec

typedef struct {
    int  id;              // Identificador único sequencial
    char name[100];       // Nome do paciente (tamanho fixo!)
    int  triage_time;     // Tempo de triagem simulado (ms)
    int  attend_time;     // Tempo de atendimento simulado (ms)
    int  priority;        // 1=Vermelho(urgente), 2=Amarelo, 3=Verde

    struct timespec arrival_time;   // Momento de chegada ao sistema
    struct timespec start_triage;   // Momento em que começou a triagem
    struct timespec end_triage;     // Momento em que terminou a triagem
    struct timespec start_attend;   // Momento em que o médico o começou a atender
    struct timespec end_attend;     // Momento da alta
} patient_t;

#endif
```

**Por que `char name[100]` com tamanho fixo e não `char *name`?**  
Esta estrutura é **transmitida por valor** através da message queue System V (`msgsnd`/`msgrcv`). As message queues copiam bytes contíguos de memória. Se `name` fosse um `char *` (ponteiro), seria copiado o endereço de memória do processo que enviou — completamente inválido no espaço de endereçamento do processo receptor. Com array de tamanho fixo, os dados estão embutidos na estrutura e são copiados corretamente.

**Por que `struct timespec` e não `time_t`?**  
`time_t` (usado por `time()`) tem resolução de **segundos**. `struct timespec` (usada por `clock_gettime`) tem resolução de **nanossegundos**, com os campos `tv_sec` (segundos) e `tv_nsec` (nanossegundos). Como os tempos de espera são medidos em milissegundos, a resolução de segundos seria insuficiente.

**Por que `CLOCK_REALTIME` e não `CLOCK_MONOTONIC`?**  
`CLOCK_REALTIME` é o relógio de parede (hora real do sistema). `CLOCK_MONOTONIC` nunca recua (ignora ajustes de NTP), sendo mais adequado para medir intervalos. Neste projeto, `CLOCK_REALTIME` é usado por simplicidade — os intervalos calculados são diferenças entre timestamps da mesma sessão, pelo que ajustes de NTP não são um problema prático.

**Por que cinco timestamps?**  
Permitem calcular três métricas distintas:
- `start_triage - arrival_time` = tempo de espera antes da triagem
- `end_triage - start_triage` = duração da triagem
- `start_attend - end_triage` = tempo de espera na fila para o médico
- `end_attend - arrival_time` = tempo total no sistema

---

## 4. `stats.h` / `stats.c`

### `stats.h` — As estruturas `stats_t` e `shared_data_t`

```c
typedef struct {
    unsigned long total_triaged;    // Total de pacientes que passaram pela triagem
    unsigned long total_attended;   // Total de pacientes atendidos por médicos
    double sum_wait_triage;         // Soma acumulada de esperas antes da triagem (ms)
    double sum_wait_attend;         // Soma acumulada de esperas antes do médico (ms)
    double sum_total_time;          // Soma acumulada do tempo total no sistema (ms)
} stats_t;

typedef struct {
    stats_t stats;        // Os dados em si
    sem_t stats_mutex;    // Semáforo POSIX de exclusão mútua
} shared_data_t;
```

**Por que `unsigned long` para os contadores?**  
Contadores que só crescem não precisam de valores negativos — `unsigned long` oferece o dobro do alcance de `long` positivo. Em sistemas com muitos pacientes, `int` (≈2 mil milhões) poderia transbordar.

**Por que somar e não calcular a média diretamente?**  
Se guardássemos a média corrente, cada atualização exigiria uma divisão: `media = (media * (n-1) + novo_valor) / n`. Acumular a soma e o total permite calcular a média a qualquer momento como `soma / total` com uma única divisão — mais simples e numericamente mais estável.

**Por que o semáforo está dentro de `shared_data_t` e não numa variável global?**  
O semáforo precisa de estar em memória acessível a todos os processos (pai e filhos). Colocá-lo dentro da estrutura que é mapeada em memória partilhada (`shmat`) garante que todos os processos acedem ao **mesmo semáforo físico** e não a cópias independentes.

---

### `stats.c` — Função `print_system_statistics`

> **Contexto:** É invocada exclusivamente pelo signal handler `handle_stats` quando o utilizador envia `SIGUSR1` ao processo (`kill -USR1 <pid>`). Acede à memória partilhada para ler as estatísticas acumuladas por todos os médicos e imprime um relatório no ecrã, sem interromper o funcionamento do sistema.

```c
void print_system_statistics(shared_data_t *shm) {
    if (!shm) return;

    lock_stats(shm);   // sem_wait — bloqueia até ter acesso exclusivo

    unsigned long triaged  = shm->stats.total_triaged;
    unsigned long attended = shm->stats.total_attended;

    // Evita divisão por zero com o operador ternário
    double avg_wait_triage = (triaged  > 0) ? (shm->stats.sum_wait_triage / triaged)  : 0.0;
    double avg_wait_attend = (attended > 0) ? (shm->stats.sum_wait_attend / attended) : 0.0;
    double avg_total_time  = (attended > 0) ? (shm->stats.sum_total_time  / attended) : 0.0;

    printf("\n==========================================\n");
    printf("       ESTATÍSTICAS DO SISTEMA (SIGUSR1)\n");
    printf("==========================================\n");
    printf("Pacientes Triados:               %lu\n", triaged);
    printf("Pacientes Atendidos:             %lu\n", attended);
    printf("------------------------------------------\n");
    printf("Tempo Médio de Espera (Triagem): %.2f ms\n", avg_wait_triage);
    printf("Tempo Médio de Espera (Médico):  %.2f ms\n", avg_wait_attend);
    printf("Tempo Médio Total no Sistema:    %.2f ms\n", avg_total_time);
    printf("==========================================\n\n");

    unlock_stats(shm); // sem_post — liberta o acesso
}
```

**Por que fazer `lock` antes de ler e não só antes de escrever?**  
Mesmo a leitura de múltiplos campos precisa de ser atómica. Um processo médico poderia atualizar `total_attended` e `sum_wait_attend` entre as duas leituras desta função, resultando em estatísticas inconsistentes (ex: média calculada com denominador já incrementado mas numerador ainda antigo).

**Por que `(triaged > 0) ? ... : 0.0`?**  
Divisão por zero em ponto flutuante em C produz `+Inf` ou `NaN` — valores que seriam impressos de forma incompreensível. O operador ternário garante que o resultado é `0.0` quando não há dados.

**Por que esta função é chamada num handler de sinal (`handle_stats`)?**  
O sinal `SIGUSR1` é definido pelo utilizador e pode ser enviado a qualquer momento com `kill -USR1 <pid>`. Permite obter um "snapshot" do estado do sistema sem interrompê-lo — útil para monitorização em tempo real.

---

## 5. `ipc.h` / `ipc.c`

### `ipc.h` — Definições e tipos

```c
#define SHM_KEY 0x1234   // Chave hexadecimal para identificar o segmento de shared memory
#define MSQ_KEY 0x9012   // Chave hexadecimal para identificar a message queue

typedef struct {
    long      mtype;   // OBRIGATÓRIO pelo POSIX: primeiro campo, tipo long, identifica a mensagem
    patient_t data;    // Payload: estrutura completa do paciente
} msgbuf_t;
```

**Por que chaves hexadecimais (`0x1234`, `0x9012`)?**  
As chaves System V (`key_t`) são inteiros que identificam recursos IPC no kernel. São valores arbitrários escolhidos pelo programador — desde que não colidam com outros programas no sistema. Hexadecimal é convencional para facilitar leitura e debug com ferramentas como `ipcs`.

**Por que o campo `mtype` tem de ser `long` e ser o primeiro campo?**  
É um requisito estrito da interface `msgsnd`/`msgrcv` do POSIX/System V. O kernel interpreta os primeiros `sizeof(long)` bytes da estrutura como o tipo da mensagem. Se `mtype` não for `long` ou não for o primeiro campo, o comportamento é **indefinido**. O `mtype` é o que permite filtragem por prioridade.

**Por que `mtype = p.priority` e não outro valor?**  
Na message queue System V, quando `msgrcv` é chamado com `type < 0`, o kernel devolve a mensagem com o **menor `mtype`** disponível que seja `<= abs(type)`. Como prioridade 1 (vermelho/urgente) < 2 (amarelo) < 3 (verde), usar a prioridade diretamente como `mtype` implementa a ordenação correta automaticamente.

---

### `ipc.c` — Memória Partilhada

```c
static int shm_id = -1;   // ID do segmento — static para encapsular no ficheiro
```

**Por que `static int shm_id`?**  
É uma variável de estado interno do módulo `ipc.c`. `static` ao nível de ficheiro significa que não é visível noutros ficheiros (linkage interno), forçando o uso das funções `create_shared_memory` e `destroy_shared_memory` em vez de manipulação direta do ID.

> **Contexto:** `lock_stats` e `unlock_stats` são os guardas da secção crítica das estatísticas. São chamadas por **todos** os processos médicos (`doctor.c`) e pelas threads de triagem (`triage.c`) sempre que precisam de atualizar os contadores em memória partilhada. Funcionam como um par acquire/release do semáforo binário `stats_mutex`.

```c
void lock_stats(shared_data_t *shm) {
    if (shm != NULL) sem_wait(&(shm->stats_mutex));
}

void unlock_stats(shared_data_t *shm) {
    if (shm != NULL) sem_post(&(shm->stats_mutex));
}
```

**Por que verificar `shm != NULL` antes de `sem_wait`?**  
Durante a inicialização ou terminação, `shm` pode ainda não estar mapeado. A verificação evita segmentation fault. É uma guarda defensiva.

**Por que `sem_wait` e não `pthread_mutex_lock`?**  
`pthread_mutex_t` **não pode ser partilhado entre processos** a não ser com atributos especiais (`PTHREAD_PROCESS_SHARED`). O semáforo POSIX com `pshared=1` foi desenhado explicitamente para funcionar entre processos que partilham memória. É a escolha correta para sincronizar processos filhos (doctors) com o pai.

> **Contexto:** `create_shared_memory` é chamada uma única vez no `main` antes de qualquer `fork`. Cria o segmento de memória partilhada System V onde vivem as estatísticas globais e o semáforo que as protege. Após o `fork`, todos os processos médicos herdam o acesso a este segmento sem precisar de o re-mapear.

```c
int create_shared_memory(shared_data_t **shm) {
    shm_id = shmget(SHM_KEY, sizeof(shared_data_t), IPC_CREAT | 0666);
    if (shm_id == -1) return -1;

    *shm = (shared_data_t *)shmat(shm_id, NULL, 0);

    if (sem_init(&((*shm)->stats_mutex), 1, 1) == -1) {
        perror("Error init sem_stats");
        return -1;
    }
    return 0;
}
```

**Por que `shared_data_t **shm` (duplo ponteiro)?**  
A função precisa de modificar o valor do ponteiro `shm` no código chamador (o `main` em `admission.c`). Em C, para modificar uma variável passada a uma função, é necessário passar o seu endereço. Como `shm` é um ponteiro (`shared_data_t *`), o seu endereço é um ponteiro para ponteiro (`shared_data_t **`).

**Por que `IPC_CREAT | 0666`?**  
- `IPC_CREAT`: cria o segmento se não existir; se já existir (de uma execução anterior que não limpou), abre o existente.  
- `0666`: permissões de acesso (leitura e escrita para owner, group e others) — necessário para que os processos filhos (que podem ter UIDs diferentes em sistemas multi-utilizador) acedam.

**Por que `shmat(shm_id, NULL, 0)`?**  
- `NULL`: deixa o kernel escolher o endereço virtual onde mapear o segmento — portável e seguro.  
- `0` (flags): acesso de leitura e escrita (sem flags especiais como `SHM_RDONLY`).

**Por que `sem_init(..., 1, 1)` e não `sem_init(..., 0, 1)`?**  
- Segundo argumento `pshared=1`: indica que o semáforo será partilhado entre **processos** (não apenas threads do mesmo processo). O kernel usa uma implementação diferente internamente.  
- Terceiro argumento `value=1`: valor inicial do semáforo. Com valor 1, o primeiro `sem_wait` passa imediatamente (como um mutex desbloqueado).

> **Contexto:** `destroy_shared_memory` é chamada na fase final de terminação do `admission`, depois de todos os processos filhos terem sido aguardados com `wait`. Destrói o semáforo embutido, desmapeia o segmento do processo pai e remove-o do kernel para não deixar recursos IPC órfãos no sistema.

```c
void destroy_shared_memory(shared_data_t *shm) {
    if (shm != (void *)-1) {
        sem_destroy(&(shm->stats_mutex));
        shmdt(shm);
    }
    if (shm_id >= 0) shmctl(shm_id, IPC_RMID, NULL);
}
```

**Por que verificar `shm != (void *)-1`?**  
`shmat` retorna `(void *)-1` em caso de erro (não `NULL`). Esta verificação protege contra tentar destruir um segmento que nunca foi mapeado com sucesso.

**Por que `sem_destroy` antes de `shmdt`?**  
O semáforo está embutido na memória partilhada. Se fizermos `shmdt` primeiro, o ponteiro `shm` fica inválido — qualquer acesso posterior (incluindo `sem_destroy`) seria undefined behavior.

**Por que `shmctl(shm_id, IPC_RMID, NULL)` depois de `shmdt`?**  
`shmdt` apenas desmapeia o segmento do espaço de endereçamento do processo corrente. O segmento continua a existir no kernel. `IPC_RMID` marca-o para remoção — o kernel elimina-o quando todos os processos que o mapearam fizerem `shmdt`. Se não for chamado, o segmento persiste após o programa terminar (visível com `ipcs -m`).

---

### `ipc.c` — Message Queue

> **Contexto:** `create_message_queue` é chamada no `main` a seguir à criação da shared memory. Cria a fila de mensagens System V que serve de canal de comunicação entre as threads de triagem (produtoras) e os processos médicos (consumidores). É o único ponto de criação — todos os outros módulos abrem a fila existente com `msgget` sem `IPC_CREAT`.

```c
int create_message_queue() {
    int id = msgget(MSQ_KEY, IPC_CREAT | 0666);
    if (id == -1) { perror("Failed to create MSQ"); return -1; }
    return id;
}
```

**Por que retornar o `id` em vez de usar uma variável global?**  
O ID da message queue é necessário tanto no processo pai (`admission`) como nos processos filhos (`doctor`) e nas threads de triagem (`triage`). Retornar o ID permite que cada entidade o obtenha de forma adequada:
- O pai guarda-o na variável global `msq_id`.  
- Os filhos e threads chamam `msgget(MSQ_KEY, 0666)` (sem `IPC_CREAT`) para obter o ID de uma fila já existente.

> **Contexto:** `send_patient_to_doctor` é chamada no final de cada iteração das threads de triagem (`triage.c`), depois de a triagem do paciente estar concluída. Empacota o `patient_t` numa `msgbuf_t` com `mtype = prioridade` e entrega-o na fila de mensagens, onde os médicos o irão retirar por ordem de urgência.

```c
void send_patient_to_doctor(int msq_id, patient_t p) {
    msgbuf_t msg;
    msg.mtype = (long)p.priority;
    msg.data  = p;
    if (msgsnd(msq_id, &msg, sizeof(patient_t), 0) == -1) perror("Erro msgsnd");
}
```

**Por que `sizeof(patient_t)` e não `sizeof(msgbuf_t)`?**  
O terceiro argumento de `msgsnd` é o tamanho do **payload** (os dados depois do `mtype`). `sizeof(msgbuf_t)` incluiria o `mtype` no tamanho, o que está errado. O POSIX especifica que o tamanho passado deve ser o tamanho de `mtype` excluído.

**Por que o último argumento é `0` (flags)?**  
Com flags = `0`, `msgsnd` **bloqueia** se a fila estiver cheia (atingiu o limite de bytes do kernel). `IPC_NOWAIT` tornaria a chamada não-bloqueante mas exigiria tratamento de erros adicional. O bloqueio é aceitável porque as threads de triagem raramente deveriam encontrar a fila cheia.

> **Contexto:** `receive_patient_from_queue` é o ponto de bloqueio de cada processo médico (`doctor.c`). O médico fica suspenso aqui enquanto não houver pacientes — o kernel só o acorda quando uma thread de triagem depositar uma mensagem na fila. O parâmetro `type = -3` garante que o médico recebe sempre o paciente mais urgente disponível.

```c
int receive_patient_from_queue(int msq_id, patient_t *p, long type) {
    msgbuf_t msg;
    if (msgrcv(msq_id, &msg, sizeof(patient_t), type, 0) == -1) {
        return -1;
    }
    *p = msg.data;
    return 0;
}
```

**Por que o parâmetro `type` e não um valor fixo?**  
Torna a função genérica. Na prática é sempre chamada com `type = -3`, mas a abstração permite futura flexibilidade.

**Por que `type = -3` especificamente?**  
Semântica de `msgrcv` com `type < 0`:
- O kernel procura na fila a mensagem com o **menor `mtype`** que seja `<= abs(type)`.
- Com `type = -3`, procura a mensagem com menor `mtype` entre 1, 2 e 3.
- Como 1 (vermelho) < 2 (amarelo) < 3 (verde), o médico recebe sempre o paciente mais urgente.
- Se usássemos `type = 1`, só receberíamos mensagens de prioridade 1 — o médico ficaria bloqueado sem pacientes vermelhos mesmo com a fila cheia de amarelos e verdes.

**Por que flags = `0` no `msgrcv` (bloqueante)?**  
Um médico sem pacientes para atender deve **dormir** (estar suspenso no kernel), sem consumir CPU. Com `IPC_NOWAIT`, o médico estaria num loop de busy-wait, desperdiçando ciclos de CPU. O bloqueio é a solução correta.

> **Contexto:** `get_msq_count` é chamada no loop principal do `admission` em cada iteração de 100ms. Serve como mecanismo de monitorização de carga: se o número de pacientes à espera na fila exceder `MSQ_WAIT_MAX`, o `admission` cria dinamicamente um médico de reforço temporário para reduzir o backlog.

```c
int get_msq_count(int msq_id) {
    struct msqid_ds buf;
    if (msgctl(msq_id, IPC_STAT, &buf) == -1) {
        perror("Erro ao ler stats MSQ");
        return 0;
    }
    return (int)buf.msg_qnum;
}
```

**Para que serve esta função?**  
Permite ao processo pai (`admission`) monitorizar o **backlog** de pacientes à espera de médico. Se `msg_qnum > MSQ_WAIT_MAX`, o sistema está sobrecarregado e um médico de reforço é criado dinamicamente. `IPC_STAT` preenche a estrutura `msqid_ds` com metadados da fila (número de mensagens, bytes totais, timestamps, etc.).

---

## 6. `logger.h` / `logger.c`

### `logger.h` — A estrutura `log_mmf_t`

```c
#define LOG_SIZE     (2 * 1024 * 1024)    // 2 MB de buffer
#define LOG_FILENAME "DEI_Emergency.log"

typedef struct {
    sem_t  mutex;           // Semáforo POSIX — exclusão mútua para escrita
    size_t write_pos;       // Offset de escrita atual no buffer
    char   data[LOG_SIZE];  // Buffer de texto — 2 MB embutidos na estrutura
} log_mmf_t;
```

**Por que `data[LOG_SIZE]` dentro da estrutura e não um ponteiro `char *`?**  
A estrutura inteira é mapeada em memória via `mmap`. Se `data` fosse um ponteiro, apontaria para um endereço do processo que inicializou o logger — endereço inválido noutros processos. Com o array embutido, os 2 MB de buffer fazem parte do ficheiro mapeado e são acessíveis a todos os processos que mapeiem o mesmo ficheiro.

**Por que 2 MB?**  
É um valor arbitrário suficientemente grande para uma sessão típica. O sistema não cresce dinamicamente (não há `realloc` num `mmap` fixo) — se o log encher, novas mensagens são simplesmente descartadas (verificado pela condição `if (write_pos + len < LOG_SIZE)`).

**Por que o semáforo está dentro da estrutura mapeada?**  
O semáforo precisa de estar em memória acessível a todos os processos (pai + filhos médicos). Ao estar dentro da `log_mmf_t` que é mapeada com `MAP_SHARED`, todos os processos que mapeiem o mesmo ficheiro partilham o mesmo semáforo físico.

---

### `logger.c` — Função `logger_init`

> **Contexto:** `logger_init` é a primeira função chamada no `main`, antes de qualquer outra inicialização. Cria o ficheiro `DEI_Emergency.log`, pré-aloca o espaço necessário e mapeia-o em memória com `mmap(MAP_SHARED)`. A partir deste momento, **todos** os processos (pai e filhos criados com `fork`) escrevem no mesmo buffer de log de forma sincronizada.

```c
static log_mmf_t *log_ptr = NULL;   // Ponteiro para a estrutura mapeada
static int log_fd = -1;             // File descriptor do ficheiro de log
```

**Por que `static` nestas variáveis globais?**  
`static` ao nível de ficheiro limita a visibilidade ao módulo `logger.c`. Outros ficheiros não acedem a `log_ptr` ou `log_fd` diretamente — usam as funções `log_write` e `logger_close`. É encapsulamento em C.

```c
int logger_init() {
    unlink(LOG_FILENAME);   // Remove o log anterior se existir

    log_fd = open(LOG_FILENAME, O_RDWR | O_CREAT | O_TRUNC, 0666);
    if (log_fd == -1) { perror("[Logger] Erro ao abrir ficheiro"); return -1; }

    size_t total_size = sizeof(log_mmf_t);

    // Pré-aloca espaço no ficheiro
    if (lseek(log_fd, total_size - 1, SEEK_SET) == -1) { ... }
    if (write(log_fd, "", 1) != 1) { ... }

    lseek(log_fd, 0, SEEK_SET);

    // Mapeia o ficheiro em memória partilhada
    log_ptr = mmap(NULL, total_size, PROT_READ | PROT_WRITE, MAP_SHARED, log_fd, 0);
    if (log_ptr == MAP_FAILED) { ... }

    sem_init(&log_ptr->mutex, 1, 1);   // Semáforo entre processos, valor inicial = 1
    log_ptr->write_pos = 0;
    memset(log_ptr->data, 0, LOG_SIZE);

    return 0;
}
```

**Por que `unlink(LOG_FILENAME)` antes de criar?**  
Garante que o log começa sempre vazio, sem restos de execuções anteriores. Sem `unlink`, o `O_TRUNC` no `open` truncaria o ficheiro existente, mas se o ficheiro anterior fosse maior, poderia deixar dados antigos acessíveis.

**Por que `O_RDWR | O_CREAT | O_TRUNC`?**  
- `O_RDWR`: `mmap` com `PROT_WRITE` requer que o ficheiro esteja aberto para escrita; `PROT_READ` requer leitura — logo `O_RDWR`.  
- `O_CREAT`: cria o ficheiro se não existir.  
- `O_TRUNC`: se existir, trunca para tamanho zero (limpa o conteúdo antigo).

**Por que a sequência `lseek` + `write("")`?**  
`mmap` não pode mapear além do tamanho atual do ficheiro. Um ficheiro recém-criado tem tamanho 0 — `mmap` de `sizeof(log_mmf_t)` bytes falharia com `SIGBUS`. A sequência:
1. `lseek(log_fd, total_size - 1, SEEK_SET)` — posiciona o cursor no último byte desejado.
2. `write(log_fd, "", 1)` — escreve um byte nulo nessa posição.  
Isto força o sistema de ficheiros a alocar `total_size` bytes para o ficheiro, tornando o `mmap` válido.

**Por que `mmap(NULL, total_size, PROT_READ | PROT_WRITE, MAP_SHARED, log_fd, 0)`?**  
- `NULL`: o kernel escolhe o endereço virtual — portável.  
- `PROT_READ | PROT_WRITE`: o mapeamento é legível e escrevível.  
- `MAP_SHARED`: escritas são visíveis a todos os outros processos que mapeiem o mesmo ficheiro, **e** são propagadas para o ficheiro em disco (via page cache do kernel).  
- `log_fd`: o ficheiro subjacente.  
- `0` (offset): mapeia desde o início do ficheiro.

**Diferença entre `MAP_SHARED` e `MAP_PRIVATE`:**
- `MAP_SHARED`: escritas propagam-se ao ficheiro e são visíveis entre processos.  
- `MAP_PRIVATE`: cria uma cópia privada (Copy-On-Write) — escritas não são visíveis noutros processos nem persistidas.

---

### `logger.c` — Função `log_write`

> **Contexto:** `log_write` é usada em todos os módulos (`admission`, `doctor`, `triage`) para registar eventos com timestamp. Como é chamada concorrentemente por processos e threads diferentes, usa o semáforo do logger para garantir que cada linha de log é escrita de forma atómica — sem interleaving com linhas de outros processos.

```c
void log_write(const char *format, ...) {
    if (!log_ptr) return;

    char buffer[1024];
    char time_str[64];

    time_t now = time(NULL);
    struct tm *t = localtime(&now);
    strftime(time_str, sizeof(time_str), "%H:%M:%S", t);

    va_list args;
    va_start(args, format);
    char msg_content[800];
    vsnprintf(msg_content, sizeof(msg_content), format, args);
    va_end(args);

    snprintf(buffer, sizeof(buffer), "[%s] %s\n", time_str, msg_content);

    printf("%s", buffer);    // Saída no ecrã (stdout)
    fflush(stdout);          // Força escrita imediata

    sem_wait(&log_ptr->mutex);   // Entra na secção crítica

    size_t len = strlen(buffer);
    if (log_ptr->write_pos + len < LOG_SIZE) {
        memcpy(log_ptr->data + log_ptr->write_pos, buffer, len);
        log_ptr->write_pos += len;
    }

    sem_post(&log_ptr->mutex);   // Sai da secção crítica
}
```

**Por que `va_list`, `va_start`, `va_end` e `vsnprintf`?**

A função `log_write` é declarada com reticências (`...`), o que a torna uma **função variádica** — aceita um número variável de argumentos, tal como `printf`:

```c
void log_write(const char *format, ...);

// Pode ser chamada assim:
log_write("[Doctor %d] A atender paciente %d.", pid, p.id);
log_write("[Admission] Sistema pronto.");
log_write("[Triagem] Espera: %.2f ms", wait_ms);
```

O problema é que em C, quando uma função recebe `...`, o compilador não sabe à partida quantos argumentos extra existem nem quais os seus tipos — essa informação vem da string de formato em tempo de execução. O mecanismo `va_list` é a forma padronizada (definida em `<stdarg.h>`) de aceder a esses argumentos.

**O que cada macro/tipo faz, passo a passo:**

```c
va_list args;
//  └─ Declara uma variável do tipo opaco va_list.
//     Internamente é tipicamente um ponteiro para a stack frame
//     onde os argumentos extras foram empilhados pelo chamador.
//     O seu tipo concreto depende da arquitetura e do ABI
//     (em x86-64 Linux é uma struct com ponteiros para registos e stack).

va_start(args, format);
//  └─ Inicializa `args` para apontar para o PRIMEIRO argumento
//     que vem DEPOIS do último parâmetro nomeado (`format`).
//     A macro precisa de saber qual é o último parâmetro fixo
//     exatamente para calcular o offset correto na stack.
//     Sem va_start, `args` seria lixo — comportamento indefinido.

vsnprintf(msg_content, sizeof(msg_content), format, args);
//  └─ Versão de snprintf que recebe um va_list em vez de `...`.
//     Lê a string `format`, percorre cada especificador (%d, %s, %.2f, ...),
//     e para cada um consome o próximo argumento de `args`
//     com o tipo correto (int, char*, double, ...).
//     O resultado fica em msg_content com no máximo sizeof(msg_content) bytes.

va_end(args);
//  └─ "Fecha" o va_list. Em algumas arquiteturas faz limpeza
//     de recursos internos. Em x86 é muitas vezes um no-op,
//     mas é OBRIGATÓRIO pelo padrão C — não chamá-lo é
//     comportamento indefinido. Deve ser sempre chamado antes
//     de `return` ou de reutilizar `args`.
```

**Por que não se pode simplesmente passar `...` diretamente ao `snprintf`?**

Não é possível "repassar" os `...` de uma função para outra em C. Quando `log_write` recebe `...`, esses argumentos já foram colocados na stack (ou em registos) pelo chamador. A única forma de os passar adiante é capturá-los num `va_list` com `va_start` e depois passar o `va_list` a uma função que o aceite — que é exatamente o que as funções com prefixo `v` fazem (`vprintf`, `vsprintf`, `vsnprintf`, `vfprintf`).

```
Chamada: log_write("[Doctor %d] Alta %d.", pid, p.id)
         │
         ▼
Stack frame de log_write:
  ┌──────────────────────┐
  │  format → "[Doctor..." │  ← parâmetro nomeado
  ├──────────────────────┤
  │  pid  (int)          │  ← 1º argumento extra (...)
  ├──────────────────────┤
  │  p.id (int)          │  ← 2º argumento extra (...)
  └──────────────────────┘
         │
         │ va_start(args, format) aponta args para cá
         ▼
  args → [pid][p.id]  ← vsnprintf lê daqui, guiado por "%d" e "%d" no format
```

**Por que `vsnprintf` e não `vsprintf`?**

`vsprintf` escreve para um buffer sem verificar o tamanho — se a mensagem formatada for maior que o buffer, há **buffer overflow**. `vsnprintf` recebe o tamanho máximo (`sizeof(msg_content) = 800`) e garante que nunca escreve além desse limite, truncando a mensagem se necessário. É sempre a escolha segura.

**Por que `fflush(stdout)` após `printf`?**  
`stdout` é geralmente **buffered por linha** em modo terminal, mas **totalmente buffered** quando a saída é redirecionada para um ficheiro ou pipe. `fflush` garante que a mensagem aparece imediatamente, independentemente do modo de buffering.

**Por que `memcpy` em vez de `strcpy` ou `fprintf`?**  
`memcpy` com tamanho explícito é mais eficiente (o compilador pode otimizar para instruções SIMD) e mais seguro (não para no `\0` interno). `fprintf` sobre um buffer de memória não faz sentido — o log é um array de bytes, não um `FILE*`.

**Por que incrementar `write_pos` em vez de procurar o `\0`?**  
Manter o offset explícito evita ter de percorrer todo o buffer a cada escrita para encontrar o fim, tornando a operação O(1) em vez de O(n).

---

### `logger.c` — Função `logger_close`

> **Contexto:** `logger_close` é a última função chamada no `main`, depois de todos os recursos terem sido libertados. Destrói o semáforo do logger, desmapeia o ficheiro de memória e fecha o file descriptor. A ordem importa: o semáforo tem de ser destruído **antes** do `munmap`, caso contrário o ponteiro ficaria inválido.

```c
void logger_close() {
    if (log_ptr) {
        sem_destroy(&log_ptr->mutex);
        munmap(log_ptr, sizeof(log_mmf_t));
        log_ptr = NULL;
    }
    if (log_fd != -1) {
        close(log_fd);
        log_fd = -1;
    }
}
```

**Por que `sem_destroy` antes de `munmap`?**  
Após `munmap`, o ponteiro `log_ptr` fica inválido. Invocar `sem_destroy` depois seria acesso a memória inválida (undefined behavior). A ordem correta é sempre: limpar o que está na memória → depois desmapear.

**Por que `log_ptr = NULL` e `log_fd = -1` após libertar?**  
Prevenção de **double-free** e uso após libertação. Se `logger_close` for chamada acidentalmente duas vezes, os guards `if (log_ptr)` e `if (log_fd != -1)` impedem que `munmap` e `close` sejam chamados com valores inválidos.

---

## 7. `triage_queue.h` / `triage_queue.c`

### `triage_queue.h` — A estrutura `triage_queue_t`

```c
typedef struct {
    patient_t      *buffer;      // Array circular de pacientes (alocado dinamicamente)
    int             capacity;    // Capacidade máxima (de config.txt: TRIAGE_QUEUE_MAX)
    int             count;       // Número de elementos atualmente na fila
    int             front;       // Índice de leitura (onde pop lê)
    int             rear;        // Índice de escrita (onde push escreve)
    pthread_mutex_t mutex;       // Mutex POSIX para exclusão mútua entre threads
    pthread_cond_t  not_empty;   // Condição: fila deixou de estar vazia
    pthread_cond_t  not_full;    // Condição: fila deixou de estar cheia
} triage_queue_t;
```

**Por que `pthread_mutex_t` aqui e `sem_t` nas estatísticas?**  
A `triage_queue` é partilhada **apenas entre threads** do processo pai (o `admission` faz `push`, as threads de triagem fazem `pop`). `pthread_mutex_t` é adequado para threads do mesmo processo e integra nativamente com `pthread_cond_wait`. O semáforo foi necessário nas estatísticas porque os médicos são **processos** separados.

**Por que duas variáveis de condição (`not_empty` e `not_full`)?**  
São dois estados distintos que interessam a entidades diferentes:
- `not_empty` interessa às **threads de triagem** (consumidoras) — só devem tentar consumir quando há algo.  
- `not_full` interessa ao **produtor** (`admission`) — só deve tentar inserir quando há espaço.  
Usar uma única variável de condição exigiria `broadcast` em vez de `signal`, acordando threads desnecessariamente.

**Por que `front` e `rear` separados e não apenas um índice?**  
Implementação clássica de **buffer circular (ring buffer)**:
- `front`: onde o próximo `pop` vai ler.
- `rear`: onde o próximo `push` vai escrever.
- Quando `rear` chega ao fim do array, volta a 0 com aritmética modular: `rear = (rear + 1) % capacity`.  
Com um único índice, não seria possível distinguir "fila vazia" de "fila cheia" sem um campo `count` adicional.

---

### `triage_queue.c` — Função `triage_queue_init`

> **Contexto:** Chamada no `main` antes de criar qualquer thread de triagem. Aloca o buffer circular com `malloc` (o tamanho vem do `config.triage_queue_size`) e inicializa o mutex e as duas variáveis de condição que sincronizam o acesso à fila. Sem esta inicialização, qualquer `push` ou `pop` resultaria em comportamento indefinido.

```c
void triage_queue_init(triage_queue_t *queue, int capacity) {
    queue->buffer   = (patient_t *)malloc(sizeof(patient_t) * capacity);
    queue->capacity = capacity;
    queue->count    = 0;
    queue->front    = 0;
    queue->rear     = 0;
    pthread_mutex_init(&queue->mutex, NULL);
    pthread_cond_init(&queue->not_empty, NULL);
    pthread_cond_init(&queue->not_full, NULL);
}
```

**Por que `malloc` e não um array estático?**  
O tamanho é lido do ficheiro de configuração em runtime — não é conhecido em tempo de compilação. `malloc` aloca a memória no heap com o tamanho exato necessário.

**Por que `NULL` como segundo argumento de `pthread_mutex_init` e `pthread_cond_init`?**  
O segundo argumento são atributos. `NULL` usa atributos por omissão, que são adequados para mutexes e variáveis de condição standard entre threads do mesmo processo.

---

### `triage_queue.c` — Função `triage_queue_push`

> **Contexto:** Chamada pelo loop principal do `admission` sempre que chega um novo paciente pelo FIFO. É o lado **produtor** do padrão Produtor-Consumidor: insere o paciente no buffer circular e acorda uma thread de triagem que esteja bloqueada à espera. Se a fila estiver cheia, rejeita imediatamente sem bloquear — o `admission` não pode ficar parado.

```c
int triage_queue_push(triage_queue_t *queue, const patient_t *patient) {
    pthread_mutex_lock(&queue->mutex);

    if (queue->count == queue->capacity) {
        pthread_mutex_unlock(&queue->mutex);
        return -1;   // Fila cheia — rejeita sem bloquear
    }

    queue->buffer[queue->rear] = *patient;                    // Copia o paciente
    queue->rear = (queue->rear + 1) % queue->capacity;        // Avança índice circular
    queue->count++;

    pthread_cond_signal(&queue->not_empty);    // Sinaliza um consumidor à espera
    pthread_mutex_unlock(&queue->mutex);
    return 0;
}
```

**Por que rejeitar (`return -1`) em vez de bloquear quando cheio?**  
O produtor (`admission`) não deve bloquear — precisa de continuar a processar o loop principal (verificar filhos terminados, criar reforços, etc.). Se a fila estiver cheia, é preferível descartar o paciente e registar o evento no log, mantendo o sistema responsivo.

**Por que `*patient` (desreferência) em vez de apenas `patient`?**  
`patient` é um ponteiro para `patient_t`. `queue->buffer[queue->rear] = *patient` copia o **valor** da estrutura para o buffer. Se fosse `= patient`, copiaria o endereço — que seria inválido quando o chamador dealocasse o `patient_t` local.

**Por que `pthread_cond_signal` e não `pthread_cond_broadcast`?**  
`signal` acorda **exatamente um** thread à espera na condição. Só um consumidor (thread de triagem) deve acordar para processar este novo paciente — acordar todos seria ineficiente (todos acordariam, mas só um encontraria o paciente e os restantes voltariam a dormir).

**Por que sinalizar `not_empty` antes de `unlock`?**  
Por convenção, a sinalização dentro do lock evita que a thread que acorda corra antes de `unlock` e encontre o mutex ocupado — minimiza wake-then-sleep desnecessários. Ambas as ordens (signal antes ou depois de unlock) são corretas, mas signal-dentro-do-lock é a prática idiomática em POSIX.

---

### `triage_queue.c` — Função `triage_queue_pop`

> **Contexto:** Chamada no início de cada iteração do loop de cada thread de triagem. É o lado **consumidor** do padrão Produtor-Consumidor: bloqueia a thread enquanto a fila está vazia (sem desperdiçar CPU), retira um paciente quando houver, e sinaliza que há espaço na fila. Na terminação do sistema, retorna um paciente sentinel com `id=0` para que a thread saiba que deve terminar.

```c
patient_t triage_queue_pop(triage_queue_t *queue) {
    pthread_mutex_lock(&queue->mutex);

    while (queue->count == 0) {
        if (stop) {
            pthread_mutex_unlock(&queue->mutex);
            patient_t dummy;
            memset(&dummy, 0, sizeof(dummy));   // Paciente sentinel (id=0)
            return dummy;
        }
        pthread_cond_wait(&queue->not_empty, &queue->mutex);
    }

    patient_t patient = queue->buffer[queue->front];
    queue->front = (queue->front + 1) % queue->capacity;
    queue->count--;

    pthread_cond_signal(&queue->not_full);
    pthread_mutex_unlock(&queue->mutex);
    return patient;
}
```

**Por que `while (count == 0)` e não `if (count == 0)`?**  
Proteção contra **spurious wakeups**. O POSIX permite que `pthread_cond_wait` retorne sem ter sido sinalizado — é uma limitação documentada das implementações de pthreads (pode acontecer por razões internas do kernel/biblioteca). O `while` garante que a condição é re-verificada após cada wakeup, seja ele real ou espúrio.

**Por que `pthread_cond_wait` liberta o mutex atomicamente?**  
É a propriedade fundamental desta primitiva:
1. Liberta o mutex (permite ao produtor fazer `push`).  
2. Suspende a thread (coloca-a na fila de espera da condição).  

As operações 1 e 2 são **atómicas** do ponto de vista do sistema — não há janela temporal entre libertar o mutex e suspender a thread onde um `signal` poderia ser perdido.

**Por que retornar um `dummy` com `id=0` quando `stop=1`?**  
As threads de triagem verificam `if (stop && patient.id == 0) break`. O paciente sentinel (com `id=0`) é o sinal para a thread terminar o seu loop. Não é possível retornar um código de erro diretamente porque a função retorna `patient_t` por valor (não tem canal de erro separado). O valor `id=0` nunca é usado para pacientes reais (o counter começa em 1).

**Por que `memset(&dummy, 0, sizeof(dummy))` em vez de inicializar campo a campo?**  
`memset` garante que **todos** os bytes da estrutura ficam a zero — incluindo campos de padding que o compilador pode inserir entre campos para alinhamento. Sem isso, bits de lixo nos campos de padding poderiam causar comportamentos inesperados ao comparar estruturas.

---

### `triage_queue.c` — Função `triage_queue_has_space`

> **Contexto:** Chamada no `admission` **antes** de tentar inserir um grupo de N pacientes. Permite tomar a decisão de aceitar ou rejeitar o grupo inteiro de forma atómica — evita inserir metade de um grupo e ficar com a fila cheia a meio. É uma verificação de pré-condição protegida pelo mutex.

```c
int triage_queue_has_space(triage_queue_t *queue, int n) {
    if (n <= 0) return 1;   // Pedir 0 ou menos espaços é sempre válido

    pthread_mutex_lock(&queue->mutex);
    int free_slots = queue->capacity - queue->count;
    pthread_mutex_unlock(&queue->mutex);

    return (free_slots >= n);
}
```

**Por que verificar espaço antes de inserir o grupo todo?**  
Um grupo de N pacientes ou cabe todo de uma vez ou é rejeitado completamente. Inserir metade de um grupo e rejeitar a outra metade deixaria o sistema num estado inconsistente. Esta verificação atómica (protegida pelo mutex) garante a decisão correta antes de começar as inserções.

**Por que o lock é necessário mesmo só para ler `count`?**  
Sem o lock, uma thread de triagem poderia estar a fazer `pop` simultaneamente, decrementando `count` — a leitura de `count` seria uma **race condition** (leitura não atómica de um inteiro não atómico).

---

## 8. `triage.h` / `triage.c`

### `triage.h`

```c
void *triage_thread_func(void *arg);
```

**Por que a assinatura `void *(void *)`?**  
É o contrato obrigatório do POSIX para funções passadas ao `pthread_create`. O argumento `void *` é genérico — permite passar qualquer tipo de dados (neste caso, `&config`). O retorno `void *` permite retornar um resultado ao `pthread_join` (neste caso, `NULL`).

---

### `triage.c` — Variáveis `extern`

```c
extern triage_queue_t triage_queue;   // Definida em admission.c
extern shared_data_t *shm;            // Definida em admission.c
extern atomic_int stop;               // Definida em admission.c
```

**Por que `extern` e não passar como argumento?**  
Threads partilham o espaço de endereçamento do processo — variáveis globais são naturalmente acessíveis. O uso de `extern` declara que as variáveis estão **definidas noutro ficheiro** (`admission.c`), evitando re-definição e conflitos de linkagem. É uma alternativa a passar tudo via o argumento `void *arg` do `pthread_create`.

**Por que `atomic_int stop` e não `volatile int stop`?**  
`volatile` apenas garante que o compilador não otimiza acessos (não faz cache em registo) — mas **não garante atomicidade**. Em arquiteturas com múltiplos cores e caches, uma escrita `volatile` pode não ser visível imediatamente noutros cores. `atomic_int` (de `<stdatomic.h>`) garante:
1. Operações de leitura/escrita atómicas ao nível do hardware.  
2. Barreiras de memória (memory fences) que tornam a escrita visível a outros cores.

---

### `triage.c` — Função `triage_thread_func`

> **Contexto:** É o corpo de execução de cada thread de triagem, criada com `pthread_create` no `main`. Cada thread corre este loop indefinidamente: retira um paciente da `triage_queue`, simula a triagem com `nanosleep`, regista as métricas em shared memory e deposita o paciente na message queue com a sua prioridade — onde os médicos o irão buscar.

```c
void *triage_thread_func(void *arg) {
    (void)arg;   // Suprime warning de parâmetro não usado

    int msq_id = msgget(MSQ_KEY, 0666);   // Abre a MSQ já criada pelo pai

    while (1) {
        patient_t patient = triage_queue_pop(&triage_queue);   // Bloqueia se vazia

        if (stop && patient.id == 0) break;   // Sentinel de terminação

        // --- Início da triagem ---
        clock_gettime(CLOCK_REALTIME, &patient.start_triage);

        double wait_ms = (patient.start_triage.tv_sec  - patient.arrival_time.tv_sec)  * 1000.0 +
                         (patient.start_triage.tv_nsec - patient.arrival_time.tv_nsec) / 1000000.0;

        log_write("[Triagem] Thread %lu a processar paciente ID %d (Espera: %.2f ms)",
                  (unsigned long)pthread_self(), patient.id, wait_ms);

        // Simula o tempo de triagem
        struct timespec ts;
        ts.tv_sec  = patient.triage_time / 1000;
        ts.tv_nsec = (patient.triage_time % 1000) * 1000000;
        nanosleep(&ts, NULL);

        clock_gettime(CLOCK_REALTIME, &patient.end_triage);
        // --- Fim da triagem ---

        lock_stats(shm);
        shm->stats.total_triaged    += 1;
        shm->stats.sum_wait_triage  += wait_ms;
        unlock_stats(shm);

        // Valida prioridade (fallback para Amarelo se inválida)
        if (patient.priority < 1 || patient.priority > 3) patient.priority = 2;

        send_patient_to_doctor(msq_id, patient);   // Envia para a message queue

        log_write("[Triagem] Paciente ID %d enviado para MSQ (Prio: %d).", patient.id, patient.priority);
    }
    return NULL;
}
```

**Por que `(void)arg`?**  
O argumento `void *arg` é passado pelo `pthread_create` mas não é usado (a thread acede às variáveis globais). Sem o cast `(void)arg`, o compilador emitiria um warning `-Wunused-parameter` (ativado pelo `-Wextra` no Makefile). O cast para `void` é o idioma C para silenciar este warning intencionalmente.

**Por que `msgget(MSQ_KEY, 0666)` sem `IPC_CREAT`?**  
A message queue já foi criada pelo processo pai em `admission.c`. A thread apenas precisa de obter o seu ID para usá-la. Sem `IPC_CREAT`, `msgget` falha se a fila não existir — o que seria um erro legítimo (a thread não deveria existir sem a fila).

**Por que o cálculo de `wait_ms` com `tv_sec` e `tv_nsec` separados?**  
`struct timespec` armazena os segundos e nanossegundos em campos separados. Para calcular a diferença em milissegundos:
- `(sec2 - sec1) * 1000.0` converte a diferença de segundos para ms.
- `(nsec2 - nsec1) / 1000000.0` converte a diferença de nanosegundos para ms.  
Somar os dois dá a diferença total em milissegundos. Esta operação é necessária porque `tv_nsec` pode ser negativo se os nanosegundos do tempo final forem menores que os do inicial (o que é compensado pelos segundos).

**Por que `nanosleep` em vez de `sleep` ou `usleep`?**  
- `sleep(n)` tem resolução de **segundos** — demasiado impreciso.  
- `usleep(n)` tem resolução de **microssegundos** mas está obsoleto no POSIX moderno.  
- `nanosleep` tem resolução de **nanossegundos**, é POSIX.1-2001, e permite especificar o tempo com `struct timespec`. É a solução padrão e portável.

**Por que `if (patient.priority < 1 || patient.priority > 3) patient.priority = 2`?**  
Validação defensiva: o utilizador poderia inserir uma prioridade inválida (ex: 0, 4, -1). Em vez de rejeitar o paciente ou terminar com erro, o sistema atribui a prioridade por omissão (Amarelo = 2), que é a categoria intermédia de triagem de Manchester.

---

## 9. `doctor.c`

> **Contexto geral:** `doctor_process_main` é a função que cada processo médico executa após ser criado com `fork` em `create_single_doctor`. O médico fica num loop a retirar pacientes da message queue (bloqueando quando está vazia), simula o atendimento com `nanosleep` e atualiza as estatísticas em shared memory. Quando o turno termina (permanente) ou a fila baixa (reforço), a função retorna e o processo termina com `exit(0)`.

```c
void doctor_process_main(shared_data_t *sh, const config_t *config, int is_temp) {
    pid_t pid    = getpid();
    int msq_id   = msgget(MSQ_KEY, 0666);

    if (is_temp) {
        log_write("[Doctor %d] INICIADO (Reforço Temporário).", pid);
    } else {
        log_write("[Doctor %d] Turno iniciado.", pid);
    }

    time_t start_shift = time(NULL);

    while (1) {
        // --- Condição de saída ---
        if (is_temp) {
            int current_waiting = get_msq_count(msq_id);
            if (current_waiting < (int)(config->msq_wait_max * 0.8)) {
                log_write("[Doctor %d] Reforço terminado.", pid);
                break;
            }
        } else {
            if (difftime(time(NULL), start_shift) >= config->shift_length) {
                log_write("[Doctor %d] Turno terminado.", pid);
                break;
            }
        }

        patient_t p;
        if (receive_patient_from_queue(msq_id, &p, -3) == 0) {

            clock_gettime(CLOCK_REALTIME, &p.start_attend);

            double wait_doc_ms = (p.start_attend.tv_sec  - p.end_triage.tv_sec)  * 1000.0 +
                                 (p.start_attend.tv_nsec - p.end_triage.tv_nsec) / 1000000.0;

            log_write("[Doctor %d] A atender paciente %d (Prio %d).", pid, p.id, p.priority);

            struct timespec ts = {p.attend_time / 1000, (p.attend_time % 1000) * 1000000};
            nanosleep(&ts, NULL);

            clock_gettime(CLOCK_REALTIME, &p.end_attend);

            double total_ms = (p.end_attend.tv_sec  - p.arrival_time.tv_sec)  * 1000.0 +
                              (p.end_attend.tv_nsec - p.arrival_time.tv_nsec) / 1000000.0;

            lock_stats(sh);
            sh->stats.total_attended  += 1;
            sh->stats.sum_wait_attend += wait_doc_ms;
            sh->stats.sum_total_time  += total_ms;
            unlock_stats(sh);

            log_write("[Doctor %d] Alta paciente %d.", pid, p.id);
        }
    }
}
```

**Por que `getpid()` no início?**  
Após o `fork`, o processo filho tem um novo PID. `getpid()` obtém o PID do processo corrente — usado nas mensagens de log para identificar qual médico está a agir. O pai tem o PID do filho disponível no retorno de `fork`, mas o filho precisa de usar `getpid()`.

**Por que `is_temp` diferencia o comportamento de saída?**  
Os dois tipos de médico têm ciclos de vida diferentes:
- **Permanente** (`is_temp=0`): trabalha por um turno completo (`SHIFT_LENGTH`). Após o turno, termina — o pai deteta via `waitpid` e cria um substituto.
- **Reforço** (`is_temp=1`): criado quando há sobrecarga. Termina quando a fila baixa para 80% do limiar (`msq_wait_max * 0.8`), voltando ao estado normal.

**Por que o limiar de saída do reforço é 80% e não 100%?**  
Histerese: se o reforço saísse exatamente quando a fila atingisse o limiar `msq_wait_max`, e o sistema continuasse a gerar pacientes ao mesmo ritmo, a fila voltaria imediatamente a ultrapassar o limiar, criando outro reforço — e assim sucessivamente (oscilação). Os 80% criam uma margem de segurança antes de o reforço se despedir.

**Por que verificar a condição de saída **antes** de `msgrcv`?**  
`msgrcv` bloqueia o processo enquanto a fila está vazia. Se a condição de saída fosse verificada depois, um médico de reforço poderia bloquear indefinidamente em `msgrcv` mesmo depois de a fila ter baixado — nunca chegando a verificar se deve sair. Verificar antes garante que a condição é testada antes de potencialmente bloquear.

**Por que `difftime(time(NULL), start_shift)`?**  
`difftime` calcula a diferença em segundos entre dois `time_t` de forma portável (em algumas plataformas, `time_t` pode não ser diretamente subtraível). `time(NULL)` retorna o tempo atual em segundos desde o epoch UNIX.

**Por que os médicos acedem à shared memory via ponteiro `sh` e não re-mapeiam?**  
Após o `fork`, o espaço de endereçamento do filho é uma **cópia** do pai. O ponteiro `sh` (que aponta para o segmento mapeado com `shmat`) continua válido no filho — o kernel mantém os mapeamentos de memória partilhada através do `fork`. O filho acede ao **mesmo segmento físico** que o pai, não a uma cópia.

---

## 10. `admission.c`

Este é o ficheiro mais complexo — contém o `main` e orquestra todos os componentes.

### Variáveis globais e seus motivos

```c
atomic_int     stop = 0;           // Flag de paragem — atómica para ser segura em signal handlers
triage_queue_t triage_queue;       // Fila partilhada entre main e threads de triagem
pthread_t     *triage_threads_arr; // Array dinâmico de TIDs (pode crescer com TRIAGE=N)
shared_data_t *shm;                // Ponteiro para shared memory — necessário no signal handler
int            msq_id = -1;        // ID da message queue — necessário no signal handler
pid_t         *doctor_pids = NULL; // Array de PIDs dos médicos — para waitpid e kill
```

**Por que `shm` e `msq_id` são globais?**  
Os signal handlers (`handle_sigint`, `handle_stats`) são funções que não recebem argumentos além do número do sinal. Para aceder a `shm` (necessário em `handle_stats` para imprimir estatísticas) e para a limpeza no shutdown, estas variáveis têm de estar acessíveis globalmente.

**Por que `atomic_int stop` em vez de `volatile int stop`?**  
Um signal handler pode ser invocado a qualquer momento, inclusive durante a leitura de `stop` noutro ponto do código. `atomic_int` garante que a leitura/escrita é indivisível — não pode haver leitura parcial. `volatile` não seria suficiente para garantir atomicidade em arquiteturas multi-core.

---

### Signal Handlers

> **Contexto:** `handle_sigint` é registado para `SIGINT` (Ctrl+C) e `handle_stats` para `SIGUSR1`. São funções que o kernel invoca de forma **assíncrona**, interrompendo o fluxo normal do programa. O `handle_sigint` limita-se a ativar a flag `stop` para que o loop principal termine de forma ordenada; o `handle_stats` imprime as estatísticas atuais sem parar o sistema.

```c
void handle_sigint(int sig) {
    (void)sig;
    log_write("[Admission] SIGINT recebido. A iniciar paragem...");
    stop = 1;
}

void handle_stats(int sig) {
    (void)sig;
    print_system_statistics(shm);
}
```

**Por que `(void)sig`?**  
O POSIX exige que os handlers tenham a assinatura `void handler(int sig)`. O argumento `sig` contém o número do sinal, mas aqui não é necessário diferenciá-los (cada handler está registado para um único sinal). O cast suprime o warning do compilador.

**Por que apenas `stop = 1` no handler de SIGINT e não fazer a limpeza aqui?**  
Signal handlers são executados de forma **assíncrona** e interrompem o código principal em qualquer ponto. As funções de limpeza (`destroy_message_queue`, `shmdt`, etc.) não são **async-signal-safe** — chamá-las num handler poderia causar deadlocks ou corrupção. A abordagem correta é: handler apenas sinaliza (`stop = 1`), e o loop principal verifica e faz a limpeza de forma ordenada.

---

### Função `create_single_doctor`

> **Contexto:** É o wrapper de `fork` + `doctor_process_main`. Chamada no `main` durante a inicialização (para criar os `config.doctors` médicos permanentes) e durante o loop principal em dois casos: quando um médico permanente termina o turno (detetado via `waitpid`) ou quando a message queue fica sobrecarregada (cria um reforço temporário). Retorna o PID do filho para o pai poder monitorizá-lo.

```c
pid_t create_single_doctor(shared_data_t *sh, const config_t *config, int is_temp) {
    pid_t pid = fork();
    if (pid == 0) {
        doctor_process_main(sh, config, is_temp);
        exit(0);
    }
    return pid;
}
```

**Por que `exit(0)` após `doctor_process_main`?**  
`doctor_process_main` retorna quando o médico termina o turno. Sem `exit(0)`, o processo filho continuaria a executar o código após o `fork` no processo pai — o que é errado. `exit(0)` termina o processo filho limpa e imediatamente após o médico terminar o trabalho.

**Por que não verificar `if (pid == -1)` (fork falhado)?**  
Esta é uma omissão no código (simplificação para projeto académico). Em produção, dever-se-ia verificar e lidar com falhas de `fork` (falta de memória, limite de processos do sistema atingido).

**Por que o pai não fecha file descriptors desnecessários no filho?**  
Após `fork`, o filho herda todos os file descriptors do pai (incluindo `fd_pipe` do FIFO). Em produção, o filho deveria fechar os FDs que não precisa (`fd_pipe`, etc.) para evitar manter referências abertas. Novamente, simplificação académica.

---

### `main` — Inicialização

> **Contexto:** A fase de inicialização do `main` segue uma ordem deliberada: logger → sinais → configuração → shared memory → message queue → FIFO → threads de triagem → processos médicos. Cada passo depende do anterior — por exemplo, os médicos só podem ser criados depois da shared memory e da message queue existirem. Qualquer falha nesta fase termina o programa imediatamente com limpeza mínima.

```c
int main() {
    if (logger_init() != 0) {
        fprintf(stderr, "Erro fatal logger.\n");
        return 1;
    }
    log_write("[Admission] Sistema de Urgências a iniciar...");

    signal(SIGINT,  handle_sigint);
    signal(SIGUSR1, handle_stats);

    config_t config;
    if (load_config("config.txt", &config) != 0) {
        logger_close();
        return 1;
    }

    create_shared_memory(&shm);
    msq_id = create_message_queue();

    unlink("input_pipe");
    if (mkfifo("input_pipe", 0666) == -1) {
        perror("mkfifo"); logger_close(); return 1;
    }

    triage_queue_init(&triage_queue, config.triage_queue_size);
    triage_threads_arr = malloc(sizeof(pthread_t) * config.triage_threads);
    for (int i = 0; i < config.triage_threads; i++)
        pthread_create(&triage_threads_arr[i], NULL, triage_thread_func, &config);

    doctor_pids = malloc(sizeof(pid_t) * config.doctors);
    for (int i = 0; i < config.doctors; i++)
        doctor_pids[i] = create_single_doctor(shm, &config, 0);
    
    int fd_pipe = open("input_pipe", O_RDWR);
```

**Por que `signal` é registado antes de `load_config`?**  
Para que o sistema responda a `SIGINT` o mais cedo possível. Se o utilizador premir Ctrl+C durante a leitura da configuração, o sinal é tratado graciosamente.

**Por que `unlink("input_pipe")` antes de `mkfifo`?**  
Se o programa terminou anteriormente de forma abrupta, o FIFO pode já existir no filesystem. `mkfifo` falha se o ficheiro existir (`EEXIST`). `unlink` remove-o previamente, garantindo criação limpa.

**Por que `open("input_pipe", O_RDWR)` em vez de `O_RDONLY`?**  
Um FIFO com `O_RDONLY` bloquearia o `open` até haver um escritor. Com `O_RDWR`, o processo abre o FIFO para leitura e escrita — o "escritor" somos nós mesmos, evitando o bloqueio. Esta é uma técnica comum para abrir FIFOs de forma não-bloqueante no lado do leitor.

**Por que criar as threads antes dos processos médicos?**  
As threads de triagem precisam de existir para processar pacientes da fila e enviá-los para a message queue. Os médicos tentarão imediatamente receber da message queue — se as threads não existissem, a queue estaria sempre vazia e os médicos bloqueariam indefinidamente (o que é correto, mas é melhor iniciar os produtores antes dos consumidores).

---

### `main` — Loop Principal com `select`

> **Contexto:** É o coração do `admission` — corre continuamente enquanto `stop == 0`. Em cada iteração de ~100ms (definida pelo timeout do `select`), o loop faz três coisas: verifica se algum médico filho terminou e cria substituto, verifica se a fila está sobrecarregada e cria reforço, e lê input do FIFO para admitir novos pacientes. O `select` é a chave que permite fazer tudo isto sem bloquear em nenhuma das três tarefas.

```c
while (!stop) {
    // 1. Verificar filhos terminados (non-blocking)
    int status;
    pid_t p = waitpid(-1, &status, WNOHANG);
    if (p > 0) {
        for (int i = 0; i < config.doctors; i++) {
            if (doctor_pids[i] == p) {
                doctor_pids[i] = create_single_doctor(shm, &config, 0);
                log_write("[Admission] Doctor permanente %d substituído por %d", p, doctor_pids[i]);
                break;
            }
        }
    }

    // 2. Monitorizar sobrecarga e criar reforço
    static time_t last_boost_time = 0;
    int current_queue = get_msq_count(msq_id);
    if (current_queue > config.msq_wait_max && (time(NULL) - last_boost_time) >= 1) {
        log_write("[Admission] ALERTA: Fila com %d pacientes. Criando reforço!", current_queue);
        create_single_doctor(shm, &config, 1);
        last_boost_time = time(NULL);
    }

    // 3. I/O Multiplexing: ler FIFO com timeout de 100ms
    fd_set read_fds;
    struct timeval tv;
    FD_ZERO(&read_fds);
    FD_SET(fd_pipe, &read_fds);
    tv.tv_sec  = 0;
    tv.tv_usec = 100000;   // 100 ms

    int retval = select(fd_pipe + 1, &read_fds, NULL, NULL, &tv);

    if (retval > 0 && FD_ISSET(fd_pipe, &read_fds)) {
        // Ler e processar input...
    }
}
```

**Por que `waitpid(-1, &status, WNOHANG)` e não `wait(NULL)`?**  
- `-1`: espera por **qualquer** processo filho (não apenas um específico).  
- `WNOHANG`: **não bloqueia** — se nenhum filho terminou, retorna imediatamente com 0. Sem esta flag, o loop principal bloquearia até um filho terminar, tornando o sistema irresponsivo.

**Por que `static time_t last_boost_time = 0`?**  
`static` numa variável local inicializa-a uma única vez (em zero) e preserva o valor entre chamadas ao loop. Permite calcular quanto tempo decorreu desde o último reforço. Sem `static`, `last_boost_time` seria re-inicializada a zero em cada iteração do loop, e um reforço seria criado em cada iteração enquanto a fila estivesse cheia.

**Por que o `(time(NULL) - last_boost_time) >= 1` no critério de reforço?**  
Evita criar múltiplos reforços em rápida sucessão. Sem este guard, se a fila continuasse cheia depois de criar um reforço, a próxima iteração do loop (100ms depois) criaria outro. A espera de 1 segundo dá tempo ao reforço de começar a atender pacientes antes de criar mais.

**Por que `select` com timeout de 100ms?**  
O `select` é usado para **I/O multiplexing** — monitorizar múltiplos file descriptors (aqui apenas `fd_pipe`) sem bloquear indefinidamente. O timeout de 100ms garante que o loop principal acorda pelo menos 10 vezes por segundo para:
1. Verificar se `stop=1` (SIGINT recebido).
2. Fazer `waitpid` para detetar filhos terminados.
3. Verificar a carga da message queue.

**Por que `fd_pipe + 1` como primeiro argumento de `select`?**  
O POSIX especifica que o primeiro argumento deve ser o **maior file descriptor** no conjunto `+1`. O kernel só verifica FDs de 0 a `nfds-1`. Com apenas `fd_pipe` no conjunto, `fd_pipe + 1` é o valor correto.

**Por que `FD_ZERO` antes de `FD_SET`?**  
`FD_ZERO` inicializa o conjunto a "nenhum FD". Sem isso, o `fd_set` conteria lixo de memória, e `select` poderia monitorizar FDs aleatórios.

---

### `main` — Processamento do Input do FIFO

> **Contexto:** Este bloco executa quando o `select` deteta dados disponíveis no FIFO `input_pipe`. Lê o comando/paciente enviado pelo utilizador, determina se é um comando de controlo (`TRIAGE=N`), um paciente individual (`Nome t_tri t_atend prio`) ou um grupo (`N t_tri t_atend prio`), e age em conformidade — ajustando threads ou criando pacientes na `triage_queue`.

```c
if (retval > 0 && FD_ISSET(fd_pipe, &read_fds)) {
    ssize_t n = read(fd_pipe, buffer, sizeof(buffer)-1);
    if (n > 0) {
        buffer[n] = '\0';
        if (buffer[n-1] == '\n') buffer[n-1] = '\0';

        // Comando especial: ajustar threads de triagem dinamicamente
        if (strncmp(buffer, "TRIAGE=", 7) == 0) {
            int new_threads = atoi(buffer + 7);
            if (new_threads > config.triage_threads) {
                int diff = new_threads - config.triage_threads;
                triage_threads_arr = realloc(triage_threads_arr, sizeof(pthread_t) * new_threads);
                for (int i = 0; i < diff; i++)
                    pthread_create(&triage_threads_arr[config.triage_threads + i], NULL, triage_thread_func, &config);
                config.triage_threads = new_threads;
            }
            continue;
        }

        char token1[100];
        int t_tri, t_atend, prio;
        if (sscanf(buffer, "%s %d %d %d", token1, &t_tri, &t_atend, &prio) == 4) {
            char *endptr;
            long num_patients = strtol(token1, &endptr, 10);

            if (*endptr == '\0') {
                // token1 é um número → pedido de grupo
                for (int i = 0; i < num_patients; i++) { /* criar pacientes */ }
            } else {
                // token1 é um nome → paciente individual
                patient_t new_p;
                strncpy(new_p.name, token1, 99);
                // ... preencher e fazer push
            }
        }
    }
}
```

**Por que `buffer[n] = '\0'` após `read`?**  
`read` não termina o buffer com `\0` — retorna apenas o número de bytes lidos. Sem a terminação manual, funções como `sscanf`, `strcmp` e `strncmp` poderiam ler além do final dos dados válidos (buffer overflow de leitura).

**Por que `if (buffer[n-1] == '\n') buffer[n-1] = '\0'`?**  
O utilizador escreve `echo "Nome 1000 1000 1" > input_pipe`. O `echo` adiciona um `\n` no final. `sscanf("%s")` para no whitespace, mas verificações como `strcmp` falhariam se a string incluísse `\n`. Remover o `\n` final normaliza o input.

**Por que `strncmp(buffer, "TRIAGE=", 7)` e não `strcmp`?**  
`strncmp` compara apenas os primeiros N caracteres — mais eficiente quando se quer verificar um prefixo. `strcmp` verificaria toda a string, mas aqui interessa apenas saber se começa por `"TRIAGE="`.

**Por que `strtol` para detetar se `token1` é número, e não `sscanf` com `%d`?**  
`strtol(token1, &endptr, 10)` converte para inteiro e coloca em `endptr` o ponteiro para o primeiro caractere que **não faz parte do número**. Se `*endptr == '\0'`, toda a string era numérica. `sscanf("%d")` ignoraria caracteres após o número, tornando impossível distinguir `"3abc"` de `"3"`.

**Por que `realloc` ao crescer `triage_threads_arr`?**  
O array de TIDs foi alocado inicialmente com `malloc(sizeof(pthread_t) * config.triage_threads)`. Para adicionar mais threads, o array precisa de crescer. `realloc` redimensiona o bloco existente (ou aloca novo e copia, se necessário), preservando os TIDs existentes.

---

### `main` — Terminação

> **Contexto:** Este bloco executa depois do loop principal terminar (quando `stop == 1` por SIGINT). A terminação segue uma ordem estrita: primeiro eliminar os processos filhos (médicos), depois acordar e juntar as threads (triagem), e só então libertar os recursos IPC (message queue, shared memory). Inverter esta ordem causaria use-after-free ou erros de acesso em recursos já destruídos.

```c
close(fd_pipe);
unlink("input_pipe");

log_write("[Admission] A terminar processos filhos...");
for (int i = 0; i < config.doctors; i++) kill(doctor_pids[i], SIGTERM);
while (wait(NULL) > 0);   // Espera por TODOS os filhos

pthread_mutex_lock(&triage_queue.mutex);
stop = 1;
pthread_cond_broadcast(&triage_queue.not_empty);
pthread_mutex_unlock(&triage_queue.mutex);

for (int i = 0; i < config.triage_threads; i++) pthread_join(triage_threads_arr[i], NULL);

triage_queue_destroy(&triage_queue);
destroy_message_queue(msq_id);
destroy_shared_memory(shm);
free(doctor_pids);
free(triage_threads_arr);
```

**Por que `kill(doctor_pids[i], SIGTERM)` e não `SIGKILL`?**  
`SIGTERM` é o sinal de terminação "educada" — o processo pode instalar um handler para `SIGTERM` e fazer limpeza antes de sair. `SIGKILL` não pode ser capturado ou ignorado — termina imediatamente sem hipótese de limpeza. `SIGTERM` é sempre a primeira escolha; `SIGKILL` é o último recurso.

**Por que `while (wait(NULL) > 0)` em vez de esperar cada filho individualmente?**  
Após `kill(SIGTERM)`, os filhos podem terminar em ordem arbitrária. `wait(NULL)` espera pelo **próximo** filho a terminar (qualquer um) e retorna -1 quando não há mais filhos. O loop garante que todos os filhos são "colhidos", prevenindo processos zombie.

**Por que `pthread_cond_broadcast` em vez de N vezes `pthread_cond_signal`?**  
Há N threads de triagem bloqueadas em `pthread_cond_wait`. `pthread_cond_signal` acorda exatamente uma — seria necessário chamá-lo N vezes. `pthread_cond_broadcast` acorda **todas** de uma vez, mais eficiente e sem risco de esquecer alguma.

**Por que é necessário o lock antes de `pthread_cond_broadcast`?**  
O POSIX permite chamar `pthread_cond_broadcast` sem o lock, mas é uma boa prática fazê-lo com o lock adquirido para evitar race conditions: uma thread poderia estar a entrar em `pthread_cond_wait` (entre verificar `count==0` e executar `wait`) exatamente quando o broadcast é enviado, perdendo-o. Com o lock, isso não pode acontecer.

**Por que `pthread_join` após o broadcast?**  
`pthread_join` bloqueia até a thread terminar. Sem ele, o processo pai poderia libertar a `triage_queue` enquanto uma thread ainda a está a usar — use-after-free. `pthread_join` garante sincronização completa antes da libertação de recursos.

**Por que a ordem de limpeza é triage → MSQ → SHM?**  
A ordem inversa de criação (SHM foi criada antes da MSQ, e ambas antes da triage_queue, mas as threads usam a triage_queue e a MSQ). Libertando a triage_queue primeiro, as threads terminam antes de a MSQ ser destruída. Se a MSQ fosse destruída primeiro, as threads de triagem receberiam erros ao tentar fazer `msgsnd`.

---

## 11. `Makefile`

```makefile
CC      = gcc
CFLAGS  = -Wall -Wextra -g -pthread -D_POSIX_C_SOURCE=200809L -D_DEFAULT_SOURCE -D_XOPEN_SOURCE=700
LDFLAGS = -pthread -lrt

OBJS = admission.o config.o ipc.o doctor.o triage.o stats.o triage_queue.o logger.o

urgencias: $(OBJS)
	$(CC) $(CFLAGS) -o urgencias $(OBJS) $(LDFLAGS)
```

**Por que as dependências estão especificadas por ficheiro `.o`?**  
O Make reconstrói apenas os ficheiros objeto cujos ficheiros fonte ou headers mudaram — compilação incremental. Se apenas `doctor.c` mudar, apenas `doctor.o` é recompilado. Sem estas dependências, `make` não saberia quando recompilar.

**Por que `-pthread` aparece tanto em `CFLAGS` como em `LDFLAGS`?**  
`-pthread` em `CFLAGS` ativa definições de macros necessárias durante a **compilação** (ex: `_REENTRANT`). Em `LDFLAGS`, liga a biblioteca `libpthread` durante o **linking**. Ambos são necessários para pthreads funcionar corretamente.

**Por que `-lrt`?**  
`lrt` é a biblioteca POSIX Real-Time. Em versões antigas de Linux, `clock_gettime` e os semáforos POSIX (`sem_init`) estavam nesta biblioteca. Em Linux moderno com glibc ≥ 2.17, estas funções já estão na libc, mas `-lrt` é mantido por portabilidade.

**Por que `-D_POSIX_C_SOURCE=200809L`?**  
Ativa as declarações POSIX.1-2008 nos headers do sistema. Sem esta macro, funções como `nanosleep`, `clock_gettime`, `pthread_*` podem não estar declaradas nos headers, causando warnings ou erros de compilação.

---

## 12. Variáveis de Condição — Teoria e Uso no Projeto

### 12.1 O Problema que as Variáveis de Condição Resolvem

Imagina que uma thread de triagem precisa de esperar que haja pacientes na fila. A abordagem ingénua seria um **busy-wait**:

```c
// ERRADO — busy-wait: desperdiça CPU continuamente
while (queue->count == 0) {
    // não faz nada, só verifica repetidamente
}
patient = queue->buffer[queue->front];
```

Isso seria catastrófico: a thread consumiria 100% de um core de CPU sem fazer trabalho útil. A solução com `sleep` também não serve:

```c
// AINDA ERRADO — latente e com race condition
while (queue->count == 0) {
    sleep(1);  // espera arbitrária, introduz latência, e perde sinais
}
```

As **variáveis de condição POSIX** (`pthread_cond_t`) resolvem este problema: permitem que uma thread **bloqueie sem consumir CPU** até que outra thread sinalize que a condição de interesse se tornou verdadeira.

---

### 12.2 A API POSIX de Variáveis de Condição

```c
pthread_cond_t cond;                        // declara a variável de condição
pthread_cond_init(&cond, NULL);             // inicializa (NULL = atributos por omissão)

// --- Lado do CONSUMIDOR (thread que espera) ---
pthread_mutex_lock(&mutex);
while (!condição_satisfeita) {
    pthread_cond_wait(&cond, &mutex);       // liberta mutex + suspende atomicamente
}
// ... usa o recurso ...
pthread_mutex_unlock(&mutex);

// --- Lado do PRODUTOR (thread que sinaliza) ---
pthread_mutex_lock(&mutex);
// ... modifica estado partilhado ...
pthread_cond_signal(&cond);                 // acorda UM consumidor
// ou
pthread_cond_broadcast(&cond);              // acorda TODOS os consumidores
pthread_mutex_unlock(&mutex);

// --- Limpeza ---
pthread_cond_destroy(&cond);
```

> **Regra fundamental:** uma variável de condição **tem sempre de ser usada em conjunto com um mutex**. Nunca se usa `pthread_cond_wait` sem o mutex associado.

---

### 12.3 O que `pthread_cond_wait` Faz Internamente

Esta é a operação mais importante e a que mais confusão gera. Ela faz **três coisas atomicamente**:

```
pthread_cond_wait(&cond, &mutex)
    │
    ├─► 1. Liberta o mutex (equivalente a pthread_mutex_unlock)
    ├─► 2. Suspende a thread na fila de espera da condição (sem consumir CPU)
    └─► [bloqueada até receber sinal]
             │
             └─► 3. Ao ser acordada: re-adquire o mutex (equivalente a
                    pthread_mutex_lock) e só então retorna
```

**Porquê as operações 1 e 2 têm de ser atómicas?**

Se fossem operações separadas, existiria uma **janela de vulnerabilidade** entre libertar o mutex e suspender a thread:

```
Thread Consumidora (triagem):           Thread Produtora (admission):

pthread_mutex_unlock(&mutex)
                                        pthread_mutex_lock(&mutex)
                                        queue->count++
                                        pthread_cond_signal(&cond)   ← SINAL PERDIDO!
                                        pthread_mutex_unlock(&mutex)
pthread_cond_wait(...)   ← bloqueia para sempre!
```

Com a atomicidade garantida pelo kernel, este cenário é impossível: o sinal só pode ser enviado antes de `wait` (e a thread ainda não está bloqueada, o `count > 0` é detetado pelo `while`) ou depois (e a thread já está bloqueada e recebe o sinal corretamente).

---

### 12.4 Spurious Wakeups — Porquê o `while` é Obrigatório

O POSIX permite que `pthread_cond_wait` **acorde sem ter sido sinalizado** — o chamado *spurious wakeup*. Isto acontece por razões internas do kernel/biblioteca (ex: receção de um sinal Unix pelo processo, otimizações de implementação em sistemas multiprocessador, ou simplesmente por ser mais simples de implementar corretamente assim a nível de kernel).

**O erro clássico de usar `if` em vez de `while`:**

```c
// ERRADO: se houver spurious wakeup, a thread tenta consumir
// uma fila vazia — comportamento indefinido
pthread_mutex_lock(&mutex);
if (queue->count == 0) {            // if: verifica apenas uma vez
    pthread_cond_wait(&cond, &mutex);
}                                   // após wakeup (espúrio ou real), NÃO re-verifica!
patient = queue->buffer[queue->front];  // pode estar a ler lixo!
```

```c
// CORRETO: o while garante que a condição é re-verificada
// após cada wakeup, seja ele real ou espúrio
pthread_mutex_lock(&mutex);
while (queue->count == 0) {         // while: re-verifica sempre
    pthread_cond_wait(&cond, &mutex);
}                                   // só sai daqui quando count > 0 é de facto verdade
patient = queue->buffer[queue->front];  // seguro!
```

**No projeto, em `triage_queue_pop`:**

```c
while (queue->count == 0) {
    if (stop) {
        // Caso especial: terminação do sistema
        pthread_mutex_unlock(&queue->mutex);
        patient_t dummy; memset(&dummy, 0, sizeof(dummy));
        return dummy;
    }
    pthread_cond_wait(&queue->not_empty, &queue->mutex);
    // Após cada wakeup (real ou espúrio), o while re-verifica:
    //   - Se count > 0  → sai do loop e consome o paciente
    //   - Se count == 0 → volta a esperar
    //   - Se stop == 1  → retorna sentinel (id=0)
}
```

---

### 12.5 `pthread_cond_signal` vs `pthread_cond_broadcast`

| Função | Efeito | Quando usar |
|---|---|---|
| `pthread_cond_signal` | Acorda **exatamente uma** thread bloqueada na condição | Quando só uma thread pode (ou deve) agir sobre o evento |
| `pthread_cond_broadcast` | Acorda **todas** as threads bloqueadas na condição | Quando múltiplas threads devem verificar a condição, ou na terminação |

**No projeto existem dois sítios onde a escolha é deliberada:**

**`triage_queue_push` usa `signal`:**
```c
queue->count++;
pthread_cond_signal(&queue->not_empty);  // acorda UMA thread de triagem
```
Razão: foi inserido **um** paciente — apenas **uma** thread o pode consumir. Acordar todas seria inútil: as restantes acordariam, verificariam o `while (count == 0)` e voltariam a dormir imediatamente — *thundering herd* desnecessário.

**`main` (terminação) usa `broadcast`:**
```c
pthread_mutex_lock(&triage_queue.mutex);
stop = 1;
pthread_cond_broadcast(&triage_queue.not_empty);  // acorda TODAS as threads
pthread_mutex_unlock(&triage_queue.mutex);
```
Razão: **todas** as N threads de triagem estão bloqueadas em `pthread_cond_wait` e têm de terminar. Com `signal`, só uma acordaria; as restantes ficariam bloqueadas indefinidamente. O `broadcast` garante que todas verificam `stop == 1` e terminam.

---

### 12.6 As Duas Variáveis de Condição da `triage_queue`

A `triage_queue_t` declara duas variáveis de condição:

```c
pthread_cond_t not_empty;   // "há pacientes para triar"
pthread_cond_t not_full;    // "há espaço para inserir"
```

**Por que duas e não uma?**

Se houvesse uma única variável de condição (`cond`), seria necessário usar `broadcast` em vez de `signal` para não correr o risco de acordar a thread "errada":

```
Fila cheia. Produtor e consumidores bloqueados na mesma `cond`.
Produtor faz signal → acorda um consumidor (correto)
Mas... e se acordar outro produtor? Ele tentaria inserir numa fila cheia → erro.
```

Com duas variáveis de condição separadas, cada tipo de entidade acorda apenas quem lhe interessa:

| Quem acorda | Usando | Acorda |
|---|---|---|
| `triage_queue_push` (produtor) | `signal(&not_empty)` | uma thread de triagem (consumidora) |
| `triage_queue_pop` (consumidor) | `signal(&not_full)` | o admission (produtor), se estivesse bloqueado |

> **Nota:** no projeto, o produtor (`admission`) não bloqueia quando a fila está cheia — rejeita imediatamente com `return -1`. Por isso `not_full` nunca tem ninguém à espera. O `pthread_cond_signal(&queue->not_full)` em `pop` sinaliza sem ninguém estar à espera, o que é inofensivo — o POSIX garante que sinalizar uma condição sem ninguém à espera é uma operação válida e sem efeito.

---

### 12.7 Trace Completo: Ciclo de Vida de um Paciente na `triage_queue`

```
[ADMISSION — Thread Principal]

 1. Lê paciente do FIFO
 2. Chama triage_queue_push(&triage_queue, &new_p)
       ├─ pthread_mutex_lock(&queue->mutex)      ← adquire o lock
       ├─ queue->buffer[rear] = *patient         ← copia paciente para o buffer
       ├─ rear = (rear + 1) % capacity           ← avança índice circular
       ├─ count++
       ├─ pthread_cond_signal(&not_empty)        ← acorda UMA thread de triagem
       └─ pthread_mutex_unlock(&queue->mutex)    ← liberta o lock

[THREAD DE TRIAGEM — estava bloqueada em pthread_cond_wait]

 3. pthread_cond_wait retorna
       ├─ re-adquire o mutex automaticamente
       ├─ verifica while (count == 0): count = 1, sai do while
       ├─ patient = buffer[front]               ← lê o paciente
       ├─ front = (front + 1) % capacity
       ├─ count--
       ├─ pthread_cond_signal(&not_full)         ← sinaliza espaço (sem efeito aqui)
       └─ pthread_mutex_unlock(&queue->mutex)    ← liberta o lock

 4. A thread realiza a triagem (nanosleep)
 5. Envia paciente para a message queue com send_patient_to_doctor()
 6. Volta ao início do loop → chama triage_queue_pop() novamente
       ├─ pthread_mutex_lock(&queue->mutex)
       ├─ count == 0: entra no while
       └─ pthread_cond_wait(&not_empty, &mutex)  ← bloqueia até ao próximo paciente

[TERMINAÇÃO — SIGINT recebido]

 7. stop = 1
 8. pthread_cond_broadcast(&not_empty)           ← acorda TODAS as threads bloqueadas
 9. Cada thread verifica: while(count==0) { if(stop) return dummy; }
10. Todas retornam sentinel (id=0) e terminam o loop
11. pthread_join() no main espera que cada thread termine completamente
```

---

### 12.8 Variáveis de Condição vs. Semáforos — Quando Usar Cada Um

| Critério | Variável de Condição (`pthread_cond_t`) | Semáforo (`sem_t`) |
|---|---|---|
| **Uso típico** | Esperar que uma **condição lógica** se torne verdadeira | Controlar acesso a **N recursos** |
| **Mutex necessário** | Sim — obrigatório | Não |
| **Memória do sinal** | Não: sinal emitido sem ninguém à espera é **perdido** | Sim: `sem_post` incrementa o valor mesmo sem ninguém bloqueado |
| **Escopo** | Só entre threads do mesmo processo | Entre threads ou processos (`pshared=1`) |
| **Pattern** | Produtor-Consumidor com condição arbitrária | Mutex simples, pool de recursos |

**A diferença de memória do sinal é importante no projeto:**

Se o `admission` fizesse `push` **antes** de qualquer thread de triagem estar pronta, um `sem_post` num semáforo ficaria "guardado" e a thread acordaria quando chegasse. Com `pthread_cond_signal`, o sinal é perdido se ninguém estiver à espera — mas isso não é problema aqui porque as threads são criadas **antes** de qualquer paciente ser inserido (como garantido pela ordem de inicialização no `main`), e porque o `while` sempre re-verifica `count` ao acordar.

---

## 13. Semáforos — Tipos, Teoria e Uso no Projeto

### 13.1 O que é um Semáforo?

Um **semáforo** é uma primitiva de sincronização definida por Dijkstra (1965). É essencialmente um inteiro não-negativo mantido pelo kernel (ou pela biblioteca de threads) sobre o qual só são permitidas duas operações atómicas:

- **`wait` (P / down / `sem_wait`)**: decrementa o valor. Se o valor for 0, o processo/thread **bloqueia** até outro fazer `signal`.
- **`signal` (V / up / `sem_post`)**: incrementa o valor. Se houver processos/threads bloqueados, acorda um deles.

A atomicidade é **garantida pelo kernel** — não há janela temporal entre verificar o valor e decrementá-lo onde outro processo pudesse interferir.

```
Estado do semáforo: valor = 1  (livre)

Processo A: sem_wait() → valor = 0  (A entra na secção crítica)
Processo B: sem_wait() → valor seria -1 → B BLOQUEIA
Processo A: sem_post() → valor = 0  → B É ACORDADO
Processo B: entra na secção crítica
```

---

### 13.2 Semáforo Binário vs. Semáforo Contador

| Tipo | Valores possíveis | Uso típico |
|---|---|---|
| **Binário** (mutex semaphore) | 0 ou 1 | Exclusão mútua — só um processo/thread de cada vez |
| **Contador** (counting semaphore) | 0 a N | Controlar acesso a N recursos idênticos (ex: pool de ligações) |

No projeto, **todos os semáforos são binários** (inicializados com `value=1`):

```c
sem_init(&shm->stats_mutex, 1, 1);   // value=1 → binário
sem_init(&log_ptr->mutex,   1, 1);   // value=1 → binário
```

Um semáforo binário comporta-se como um **mutex** — garante que apenas um processo/thread de cada vez entra na secção crítica. A diferença teórica entre um semáforo binário e um mutex é que num mutex o **mesmo** processo/thread que fez lock tem de fazer unlock; num semáforo binário, um processo pode fazer `sem_post` sobre um semáforo que outro processo fez `sem_wait`. No projeto, no entanto, são sempre usados de forma simétrica (lock/unlock no mesmo contexto), pelo que funcionam equivalentemente a mutexes.

---

### 13.3 As Três Famílias de Semáforos em POSIX/Linux

Existem três famílias distintas de semáforos disponíveis em Linux. O projeto faz escolhas deliberadas sobre qual usar em cada situação.

#### Família 1 — Semáforos System V (`semget` / `semop`)

```c
// Exemplo de uso (NÃO usado no projeto)
int semid = semget(key, 1, IPC_CREAT | 0666);
semctl(semid, 0, SETVAL, 1);         // inicializar a 1

struct sembuf sb = {0, -1, 0};       // operação: decrement
semop(semid, &sb, 1);                // wait

struct sembuf sb2 = {0, +1, 0};      // operação: increment
semop(semid, &sb2, 1);               // signal
```

**Características:**
- Identificados por uma chave (`key_t`) e geridos pelo kernel (visíveis com `ipcs -s`).
- Suportam operações atómicas em **conjuntos de semáforos** (múltiplos semáforos numa operação `semop`).
- Existem persistentemente no kernel até serem explicitamente removidos com `semctl(IPC_RMID)` — se o programa crashar sem limpar, ficam no sistema.
- Interface mais complexa e verbosa.
- Partilháveis entre processos não relacionados (via chave).

**Por que NÃO foram usados no projeto?**  
A interface `semop` é mais verbosa e complexa (requer definir `struct sembuf`, usar arrays, etc.). Para o caso de uso do projeto — mutex simples entre processos que partilham memória — os semáforos POSIX são mais adequados e diretos.

---

#### Família 2 — Semáforos POSIX em Memória (`sem_init` / `sem_wait` / `sem_post`)

```c
sem_t semaforo;
sem_init(&semaforo, pshared, value);
sem_wait(&semaforo);    // P / down / lock
sem_post(&semaforo);    // V / up   / unlock
sem_destroy(&semaforo); // liberta recursos
```

**O parâmetro `pshared` — a distinção crítica:**

| `pshared` | Significado | Onde deve residir o semáforo |
|---|---|---|
| `0` | Partilhado entre **threads** do mesmo processo | Qualquer memória (stack, heap, global) |
| `1` | Partilhado entre **processos** | Memória partilhada (`shmat` ou `mmap MAP_SHARED`) |

**Por que `pshared=1` nas estatísticas e no logger?**

Os médicos são **processos separados** (criados com `fork`). Cada processo tem o seu próprio espaço de endereçamento virtual. Um semáforo com `pshared=0` em memória privada seria uma cópia independente em cada processo — as operações `sem_wait`/`sem_post` de processos diferentes não afetariam o mesmo semáforo físico.

Com `pshared=1`, o kernel sabe que o semáforo está em memória partilhada física e usa um mecanismo de sincronização adequado (tipicamente futex no Linux, que funciona sobre o endereço físico).

```
 pshared=0 (ERRADO para processos):
┌──────────────────┐    ┌──────────────────┐
│  Processo Pai    │    │  Processo Filho  │
│  sem_t mutex     │    │  sem_t mutex     │  ← CÓPIAS INDEPENDENTES!
│  valor = 1       │    │  valor = 1       │  ← sem_wait num não afeta o outro
└──────────────────┘    └──────────────────┘

 pshared=1 (CORRETO para processos):
┌──────────────────┐    ┌──────────────────┐
│  Processo Pai    │    │  Processo Filho  │
│  ptr → shm       │    │  ptr → shm       │
└────────┬─────────┘    └────────┬─────────┘
         │                       │
         ▼                       ▼
   ┌─────────────────────────────────┐
   │  MEMÓRIA PARTILHADA (kernel)    │
   │  sem_t mutex  (valor = 1)       │  ← UM SÓ SEMÁFORO FÍSICO
   └─────────────────────────────────┘
```

**Uso no projeto — `stats_mutex` (em `shared_data_t`):**
```c
// Criação (em ipc.c, create_shared_memory):
shm_id = shmget(SHM_KEY, sizeof(shared_data_t), IPC_CREAT | 0666);
*shm = shmat(shm_id, NULL, 0);          // mapeia shared memory
sem_init(&(*shm)->stats_mutex, 1, 1);   // pshared=1, valor inicial=1

// Uso (em ipc.c, lock_stats / unlock_stats):
void lock_stats(shared_data_t *shm)   { sem_wait(&shm->stats_mutex); }
void unlock_stats(shared_data_t *shm) { sem_post(&shm->stats_mutex); }
```

Protege a estrutura `stats_t` de acessos concorrentes por múltiplos processos médicos. Sem este semáforo, dois médicos a atualizar `total_attended` ao mesmo tempo causariam uma **race condition**:

```
Médico A: lê total_attended = 5 (em registo da CPU)
Médico B: lê total_attended = 5 (em registo da CPU)
Médico A: escreve total_attended = 6
Médico B: escreve total_attended = 6  ← ERRADO: devia ser 7
```

**Uso no projeto — `mutex` do logger (em `log_mmf_t`):**
```c
// Criação (em logger.c, logger_init):
log_ptr = mmap(NULL, total_size, PROT_READ | PROT_WRITE, MAP_SHARED, log_fd, 0);
sem_init(&log_ptr->mutex, 1, 1);   // pshared=1: o semáforo está no mmap partilhado

// Uso (em logger.c, log_write):
sem_wait(&log_ptr->mutex);         // entra na secção crítica
memcpy(log_ptr->data + log_ptr->write_pos, buffer, len);
log_ptr->write_pos += len;
sem_post(&log_ptr->mutex);         // sai da secção crítica
```

Protege o buffer de log de escritas concorrentes. O `write_pos` e o `data[]` têm de ser atualizados atomicamente — sem proteção, dois processos poderiam escrever no mesmo offset, corrompendo ambas as mensagens.

---

#### Família 3 — Semáforos POSIX Nomeados (`sem_open` / `sem_close` / `sem_unlink`)

```c
// Exemplo de uso (NÃO usado no projeto)
sem_t *sem = sem_open("/meu_semaforo", O_CREAT, 0666, 1);
sem_wait(sem);
sem_post(sem);
sem_close(sem);
sem_unlink("/meu_semaforo");   // remove do sistema de ficheiros
```

**Características:**
- Identificados por um nome no sistema de ficheiros (namespace `/`).
- Não precisam de estar em memória partilhada — o kernel gere a partilha.
- Partilháveis entre processos **não relacionados** (sem `fork`) que conheçam o nome.
- Persistem no filesystem até `sem_unlink` (ou reboot).

**Por que NÃO foram usados no projeto?**  
Os processos que precisam de partilhar semáforos neste projeto têm todos relação pai-filho (via `fork`). Os semáforos POSIX em memória com `pshared=1` são suficientes e mais simples — não exigem gestão de nomes nem `sem_unlink`.

---

### 13.4 Mutex POSIX (`pthread_mutex_t`) vs. Semáforo POSIX (`sem_t`)

No projeto, **ambos** são usados — em contextos diferentes.

| Característica | `pthread_mutex_t` | `sem_t` (binário) |
|---|---|---|
| **Usado na** | `triage_queue` | `stats_mutex`, logger `mutex` |
| **Partilha** | Threads do mesmo processo | Processos diferentes (`pshared=1`) |
| **Integração com `pthread_cond_t`** | ✅ Sim (obrigatório) | ❌ Não |
| **Ownership** | Deve ser desbloqueado pela **mesma** thread que bloqueou | Pode ser desbloqueado por **outra** thread/processo |
| **Inicialização** | `pthread_mutex_init` | `sem_init` |
| **Lock/Unlock** | `pthread_mutex_lock` / `pthread_mutex_unlock` | `sem_wait` / `sem_post` |
| **Destruição** | `pthread_mutex_destroy` | `sem_destroy` |

**Por que `pthread_mutex_t` na `triage_queue` e não `sem_t`?**

A `triage_queue` usa **variáveis de condição** (`pthread_cond_t`). A função `pthread_cond_wait` **exige** um `pthread_mutex_t` como argumento — ela precisa de libertar o mutex e suspender a thread de forma atómica. Não existe equivalente com `sem_t`.

```c
// Isto é obrigatório: pthread_cond_wait requer pthread_mutex_t
pthread_cond_wait(&queue->not_empty, &queue->mutex);  // mutex tem de ser pthread_mutex_t
//                                    ↑ NÃO pode ser sem_t
```

Se quiséssemos usar `sem_t` com variáveis de condição, precisaríamos de reimplementar o mecanismo de condição manualmente — muito mais complexo e propenso a erros.

**Por que `sem_t` nas estatísticas e não `pthread_mutex_t`?**

Os médicos são processos separados. `pthread_mutex_t` por defeito tem `pshared=PTHREAD_PROCESS_PRIVATE` — não funciona entre processos.

Seria possível usar `pthread_mutex_t` entre processos com:
```c
pthread_mutexattr_t attr;
pthread_mutexattr_init(&attr);
pthread_mutexattr_setpshared(&attr, PTHREAD_PROCESS_SHARED);  // ativar partilha
pthread_mutex_init(&mutex, &attr);
```
Mas o semáforo POSIX com `pshared=1` é mais simples para o mesmo efeito.

---

### 13.5 Resumo de Todos os Semáforos no Projeto

```
┌─────────────────────┬──────────────────────────┬──────────────┬─────────┬─────────────────────────────┐
│ Variável            │ Tipo                     │ Localização  │ pshared │ Protege                     │
├─────────────────────┼──────────────────────────┼──────────────┼─────────┼─────────────────────────────┤
│ triage_queue.mutex  │ pthread_mutex_t (mutex)  │ Heap (pai)   │  N/A    │ triage_queue (threads)      │
│ shm->stats_mutex    │ sem_t binário POSIX      │ Shared Mem.  │   1     │ stats_t (processos)         │
│ log_ptr->mutex      │ sem_t binário POSIX      │ mmap file    │   1     │ buffer do logger (processos)│
└─────────────────────┴──────────────────────────┴──────────────┴─────────┴─────────────────────────────┘
```

**Regra geral aplicada no projeto:**
- **Threads** do mesmo processo → `pthread_mutex_t` (integra com `pthread_cond_t`)
- **Processos** diferentes → `sem_t` com `pshared=1` (colocado em memória partilhada)

---

### 13.6 O Problema da Secção Crítica e as Condições de Dijkstra

Uma **secção crítica** é uma região de código que acede a recursos partilhados e onde apenas um processo/thread pode estar de cada vez. Os semáforos garantem as quatro condições de Dijkstra:

1. **Exclusão Mútua**: `sem_wait` garante que só um entra de cada vez.
2. **Progresso**: se a secção crítica estiver livre e houver processos à espera, um deles entra — o kernel acorda-o via `sem_post`.
3. **Ausência de Starvation** (espera limitada): o kernel implementa filas de espera FIFO para os semáforos — nenhum processo fica à espera indefinidamente.
4. **Ausência de Busy-Wait**: `sem_wait` suspende o processo/thread no kernel sem consumir CPU — ao contrário de um spin-lock.

---

### 13.7 Ciclo de Vida Completo dos Semáforos no Projeto

```
[logger_init]
    │
    ├─ mmap(MAP_SHARED) → log_ptr aponta para ficheiro mapeado
    └─ sem_init(&log_ptr->mutex, pshared=1, value=1)
                                                │
                    ┌───────────────────────────┘
                    │  Cada log_write:
                    │  sem_wait ──► secção crítica ──► sem_post
                    │
[logger_close]
    ├─ sem_destroy(&log_ptr->mutex)   ← ANTES de munmap!
    └─ munmap(log_ptr, ...)

[create_shared_memory]
    │
    ├─ shmget + shmat → shm aponta para segmento partilhado
    └─ sem_init(&shm->stats_mutex, pshared=1, value=1)
                                                │
             ┌──────────────────────────────────┘
             │  Cada acesso às stats (triage + doctors):
             │  lock_stats ──► secção crítica ──► unlock_stats
             │
[destroy_shared_memory]
    ├─ sem_destroy(&shm->stats_mutex)  ← ANTES de shmdt!
    └─ shmdt(shm) + shmctl(IPC_RMID)
```

---

## 14. Mapa de Conceitos Teóricos

```
┌────────────────────────┬───────────────────────────────────────────────────┐
│ CONCEITO TEÓRICO       │ ONDE É APLICADO NO PROJETO                        │
├────────────────────────┼───────────────────────────────────────────────────┤
│ Processos (fork/exec)  │ Médicos criados com fork() em create_single_doctor│
│ Threads POSIX          │ Triagem com pthread_create/join                   │
│ Signals                │ SIGINT→stop gracioso, SIGUSR1→estatísticas        │
│ Named Pipe (FIFO)      │ mkfifo("input_pipe") → canal de input do utilizad.│
│ I/O Multiplexing       │ select() com timeout de 100ms no loop principal   │
│ Shared Memory System V │ shmget/shmat para stats partilhadas entre proc.   │
│ Message Queue System V │ msgget/msgsnd/msgrcv com prioridade via mtype     │
│ Semáforos POSIX        │ sem_init(pshared=1) para mutex entre processos    │
│ Mutex POSIX            │ pthread_mutex_t na triage_queue (entre threads)   │
│ Variáveis de Condição  │ pthread_cond_wait/signal/broadcast na triage_queue│
│ Produtor-Consumidor    │ admission→triage_queue→threads triagem            │
│ Memory-Mapped Files    │ mmap(MAP_SHARED) para logger partilhado           │
│ Operações Atómicas     │ atomic_int stop (seguro em signal handlers)       │
│ Tempo Real POSIX       │ clock_gettime(CLOCK_REALTIME) + nanosleep         │
│ Zombie Prevention      │ waitpid(WNOHANG) + while(wait(NULL)>0)           │
│ Escalonamento Elástico │ Médico de reforço criado/destruído dinamicamente  │
└────────────────────────┴───────────────────────────────────────────────────┘
```

---

## 15. Perguntas de Defesa

**Q: Por que usar `fork()` para médicos e `pthread_create()` para triagem?**  
R: Médicos são processos isolados — falha num não afeta os outros. As threads de triagem precisam de acesso direto à `triage_queue` na memória do processo pai; entre processos, isso exigiria IPC adicional. Threads partilham memória do processo, tornando a comunicação direta e eficiente.

**Q: O que é um spurious wakeup e onde é tratado?**  
R: É um wakeup de `pthread_cond_wait` sem ter havido `pthread_cond_signal`. O POSIX permite que aconteça por razões internas da implementação. Em `triage_queue_pop`, o `while (queue->count == 0)` (em vez de `if`) re-verifica a condição após cada wakeup, tratando corretamente spurious wakeups.

**Q: Como funciona a prioridade na message queue?**  
R: O campo `mtype` da `msgbuf_t` é definido como a prioridade do paciente (1=vermelho, 2=amarelo, 3=verde). `msgrcv` com `type=-3` pede a mensagem com menor `mtype` disponível (≤3). Como menor `mtype` = maior urgência, o médico recebe sempre o paciente mais crítico automaticamente — sem lógica de ordenação manual.

**Q: O que acontece se `admission` receber SIGINT durante `select`?**  
R: O sinal interrompe `select`, que retorna -1 com `errno=EINTR`. O `handle_sigint` é executado (define `stop=1`). Na próxima avaliação de `while (!stop)`, o loop termina e a limpeza é feita de forma ordenada.

**Q: Por que `sem_init` com `pshared=1` e não `pthread_mutex_t` nas estatísticas?**  
R: `pthread_mutex_t` por omissão não é partilhável entre processos. Seria necessário `pthread_mutexattr_setpshared(PTHREAD_PROCESS_SHARED)` e colocar o mutex em memória partilhada. O semáforo POSIX com `pshared=1` foi desenhado exatamente para este caso — é mais simples e direto.

**Q: Como é que os processos filhos (médicos) acedem à shared memory?**  
R: Após `fork()`, o filho herda todos os mapeamentos de memória do pai, incluindo o segmento mapeado com `shmat`. O ponteiro `sh` continua válido no filho e aponta para o mesmo segmento físico. As alterações feitas pelo filho são visíveis no pai (e vice-versa) porque é memória partilhada.

**Q: Por que o logger usa `mmap` e não a shared memory System V?**  
R: `mmap` sobre um ficheiro cria automaticamente a persistência em disco — o log fica gravado no ficheiro `DEI_Emergency.log`. Com shared memory System V (`shmget`), os dados existiriam apenas em RAM e seriam perdidos quando o programa terminasse. O `mmap` com `MAP_SHARED` combina partilha entre processos com persistência.

**Q: Como é evitado o problema de zombie processes?**  
R: O loop principal chama `waitpid(-1, &status, WNOHANG)` em cada iteração. Quando um médico termina, `waitpid` retorna o seu PID e "colhe" o processo, removendo a sua entrada da tabela de processos. No shutdown, `while(wait(NULL) > 0)` garante que todos os filhos restantes são colhidos.
