/*
 * Projeto SO 2025/2026
 * Grupo de Trabalho:
 *
 *   Diogo de Oliveira Mendes Dias Saldanha  —  Nº 2022232761
 *   João Maria Moreira Dias                —  Nº 2022225061
 *
 */

#ifndef LOGGER_H
#define LOGGER_H

#include <semaphore.h>
#include <stddef.h>

#define LOG_SIZE (2 * 1024 * 1024)
#define LOG_FILENAME "DEI_Emergency.log"

typedef struct {
    sem_t mutex;            
    size_t write_pos;       
    char data[LOG_SIZE];    
} log_mmf_t;


int logger_init();


void log_write(const char *format, ...);


void logger_close();

#endif // LOGGER_H