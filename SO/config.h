
/*
 * Projeto SO 2025/2026
 * Grupo de Trabalho:
 *
 *   Diogo de Oliveira Mendes Dias Saldanha  —  Nº 2022232761
 *   João Maria Moreira Dias                —  Nº 2022225061
 *
 */
// Ficheiro de definição da estrutura de configuração e função de carregamento
#ifndef CONFIG_H
#define CONFIG_H
typedef struct{
    int triage_queue_size;
    int triage_threads;
    int doctors;
    int shift_length;
    int msq_wait_max;
}config_t;

int load_config(const char* filename, config_t* config);

#endif // CONFIG_H