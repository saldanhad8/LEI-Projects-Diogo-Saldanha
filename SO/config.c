/*
 * Projeto SO 2025/2026
 * Grupo de Trabalho:
 *
 *   Diogo de Oliveira Mendes Dias Saldanha  —  Nº 2022232761
 *   João Maria Moreira Dias                —  Nº 2022225061
 *
 */
#include <stdio.h>
#include "config.h"
#include <stdlib.h>
#include <string.h>

//Remove espaços em branco à direita de uma string
static void rtrim(char *s) {
    size_t len = strlen(s);
    while (len > 0 && (s[len-1] == ' ' || s[len-1] == '\t' || s[len-1] == '\n')) {
        s[len-1] = '\0';
        len--;
    }
}

//Carrega a configuração do ficheiro especificado para a estrutura config_t
int load_config(const char *filename, config_t *config) {
    FILE *file = fopen(filename, "r");
    if (file == NULL) {
        perror("Failed to open config file");
        return -1;
    }
    config->triage_queue_size = -1;
    config->triage_threads = -1;
    config->doctors = -1;
    config->shift_length = -1;
    config->msq_wait_max = -1;

    char line[256];

    while (fgets(line, sizeof(line), file) != NULL) {
        char key[64];
        int value;

        if (sscanf(line, " %63[^=]= %d", key, &value) == 2) {
            rtrim(key);

            if (strcmp(key, "TRIAGE_QUEUE_MAX") == 0) {
                config->triage_queue_size = value;
            } else if (strcmp(key, "TRIAGE") == 0) {
                config->triage_threads = value;
            } else if (strcmp(key, "DOCTORS") == 0) {
                config->doctors = value;
            } else if (strcmp(key, "SHIFT_LENGTH") == 0) {
                config->shift_length = value;
            } else if (strcmp(key, "MSQ_WAIT_MAX") == 0) {
                config->msq_wait_max = value;
            } else {
                fprintf(stderr, "Aviso: chave desconhecida na config: %s\n", key);
            }
        }
    }
    fclose(file);

     if (config->triage_queue_size < 0 || config->triage_threads < 0 ||
        config->doctors < 0 ||config->shift_length < 0 || config->msq_wait_max < 0) {
        fprintf(stderr, "Configuração incompleta ou inválida em %s\n", filename);
        return -1;
    }
    return 0;
}