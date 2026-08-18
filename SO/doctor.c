/*
 * Projeto SO 2025/2026
 * Grupo de Trabalho:
 *
 *   Diogo de Oliveira Mendes Dias Saldanha  —  Nº 2022232761
 *   João Maria Moreira Dias                —  Nº 2022225061
 *
 */

#ifndef _POSIX_C_SOURCE
#define _POSIX_C_SOURCE 200809L
#endif

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/msg.h>
#include <time.h>
#include "config.h"
#include "ipc.h"
#include "stats.h"
#include "logger.h"

void doctor_process_main(shared_data_t *sh, const config_t *config, int is_temp) {
    pid_t pid = getpid();
    int msq_id = msgget(MSQ_KEY, 0666);

    if (is_temp) {
        log_write("[Doctor %d] INICIADO (Reforço Temporário).", pid);
    } else {
        log_write("[Doctor %d] Turno iniciado.", pid);
    }
    
    time_t start_shift = time(NULL);
    
    while (1) {
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
        // CORREÇÃO: Usamos mtype = -3 para bloquear até haver o paciente mais prioritário.
        // Isto elimina a necessidade de tentar 1, depois 2, depois 3 e o sleep final.
        if (receive_patient_from_queue(msq_id, &p, -3) == 0) {
            clock_gettime(CLOCK_REALTIME, &p.start_attend);
            double wait_doc_ms = (p.start_attend.tv_sec - p.end_triage.tv_sec) * 1000.0 +
                                 (p.start_attend.tv_nsec - p.end_triage.tv_nsec) / 1000000.0;

            log_write("[Doctor %d] A atender paciente %d (Prio %d).", pid, p.id, p.priority);

            struct timespec ts = {p.attend_time / 1000, (p.attend_time % 1000) * 1000000};
            nanosleep(&ts, NULL);
            
            clock_gettime(CLOCK_REALTIME, &p.end_attend);
            double total_ms = (p.end_attend.tv_sec - p.arrival_time.tv_sec) * 1000.0 +
                              (p.end_attend.tv_nsec - p.arrival_time.tv_nsec) / 1000000.0;

            lock_stats(sh);
            sh->stats.total_attended += 1;
            sh->stats.sum_wait_attend += wait_doc_ms;
            sh->stats.sum_total_time += total_ms;
            unlock_stats(sh);

            log_write("[Doctor %d] Alta paciente %d.", pid, p.id);
        }
        // O else com nanosleep foi removido pois o receive agora bloqueia corretamente.
    }
}