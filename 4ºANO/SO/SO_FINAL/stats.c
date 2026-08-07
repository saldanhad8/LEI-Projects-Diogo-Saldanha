/*
 * Projeto SO 2025/2026
 * Grupo de Trabalho:
 *
 * Diogo de Oliveira Mendes Dias Saldanha  —  Nº 2022232761
 * João Maria Moreira Dias                —  Nº 2022225061
 *
 */
#include <stdio.h>
#include "stats.h"
#include "ipc.h"

void print_system_statistics(shared_data_t *shm) {
    if (!shm) return;

    lock_stats(shm);

    unsigned long triaged = shm->stats.total_triaged;
    unsigned long attended = shm->stats.total_attended;
    
    double avg_wait_triage = (triaged > 0) ? (shm->stats.sum_wait_triage / triaged) : 0.0;
    double avg_wait_attend = (attended > 0) ? (shm->stats.sum_wait_attend / attended) : 0.0;
    double avg_total_time  = (attended > 0) ? (shm->stats.sum_total_time / attended) : 0.0;

    printf("\n==========================================\n");
    printf("       ESTATÍSTICAS DO SISTEMA (SIGUSR1)    \n");
    printf("==========================================\n");
    printf("Pacientes Triados:            %lu\n", triaged);
    printf("Pacientes Atendidos:          %lu\n", attended);
    printf("------------------------------------------\n");
    printf("Tempo Médio de Espera (Triagem): %.2f ms\n", avg_wait_triage);
    printf("Tempo Médio de Espera (Médico):  %.2f ms\n", avg_wait_attend);
    printf("Tempo Médio Total no Sistema:    %.2f ms\n", avg_total_time);
    printf("==========================================\n\n");

    unlock_stats(shm);
}