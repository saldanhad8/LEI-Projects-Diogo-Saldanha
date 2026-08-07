/*
 * Projeto SO 2025/2026
 * Grupo de Trabalho:
 *
 * Diogo de Oliveira Mendes Dias Saldanha  —  Nº 2022232761
 * João Maria Moreira Dias                —  Nº 2022225061
 *
 */
#ifndef STATS_H
#define STATS_H

#include <time.h>
#include <semaphore.h>

typedef struct {
    
    unsigned long total_triaged;
    unsigned long total_attended;

   
    
    double sum_wait_triage;    
    double sum_wait_attend;    
    double sum_total_time;     

} stats_t;


typedef struct {
    stats_t stats;
    sem_t stats_mutex;
} shared_data_t;


void print_system_statistics(shared_data_t *shm);

#endif // STATS_H