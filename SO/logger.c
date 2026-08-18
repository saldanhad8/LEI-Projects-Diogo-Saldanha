/*
 * Projeto SO 2025/2026
 * Grupo de Trabalho:
 *
 *   Diogo de Oliveira Mendes Dias Saldanha  —  Nº 2022232761
 *   João Maria Moreira Dias                —  Nº 2022225061
 *
 */

#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <stdarg.h>
#include <string.h>
#include <time.h>
#include <errno.h>
#include "logger.h"

// Variável global interna
static log_mmf_t *log_ptr = NULL;
static int log_fd = -1;

int logger_init() {
    unlink(LOG_FILENAME);

    // 2. Abrir/Criar o ficheiro de log
    log_fd = open(LOG_FILENAME, O_RDWR | O_CREAT | O_TRUNC, 0666);
    if (log_fd == -1) {
        perror("[Logger] Erro ao abrir ficheiro");
        return -1;
    }

    // 3. Calcular tamanho total da estrutura
    size_t total_size = sizeof(log_mmf_t);

    if (lseek(log_fd, total_size - 1, SEEK_SET) == -1) {
        perror("[Logger] Erro no lseek");
        close(log_fd);
        return -1;
    }

    if (write(log_fd, "", 1) != 1) {
        perror("[Logger] Erro ao alocar espaco no ficheiro");
        close(log_fd);
        return -1;
    }


    lseek(log_fd, 0, SEEK_SET);
    // -----------------------------

 
    log_ptr = mmap(NULL, total_size, PROT_READ | PROT_WRITE, MAP_SHARED, log_fd, 0);
    if (log_ptr == MAP_FAILED) {
        perror("[Logger] Erro no mmap");
        close(log_fd);
        return -1;
    }


    if (sem_init(&log_ptr->mutex, 1, 1) == -1) {
        perror("[Logger] Erro ao iniciar mutex");
        return -1;
    }

    log_ptr->write_pos = 0;
    memset(log_ptr->data, 0, LOG_SIZE); 

    return 0;
}

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

    // Ecrã
    printf("%s", buffer);
    fflush(stdout);

    // Ficheiro Mapeado
    sem_wait(&log_ptr->mutex);
    
    size_t len = strlen(buffer);
    if (log_ptr->write_pos + len < LOG_SIZE) {
        memcpy(log_ptr->data + log_ptr->write_pos, buffer, len);
        log_ptr->write_pos += len;
    }

    sem_post(&log_ptr->mutex);
}

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