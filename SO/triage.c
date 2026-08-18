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
#include <unistd.h>
#include <time.h>
#include <pthread.h>
#include <stdatomic.h>
#include <sys/msg.h>
#include "triage_queue.h"
#include "ipc.h"
#include "stats.h"
#include "config.h"
#include "logger.h"

extern triage_queue_t triage_queue;
extern shared_data_t *shm;
extern atomic_int stop;

void *triage_thread_func(void *arg) {
    (void)arg; 
    
    int msq_id = msgget(MSQ_KEY, 0666);
    
    while (1) {
     
        patient_t patient = triage_queue_pop(&triage_queue);

        
        if (stop && patient.id == 0) {
            break;
        }

        
        clock_gettime(CLOCK_REALTIME, &patient.start_triage);
        
       
        double wait_ms = (patient.start_triage.tv_sec - patient.arrival_time.tv_sec) * 1000.0 +
                         (patient.start_triage.tv_nsec - patient.arrival_time.tv_nsec) / 1000000.0;

        log_write("[Triagem] Thread %lu a processar paciente ID %d (Espera: %.2f ms)", 
               (unsigned long)pthread_self(), patient.id, wait_ms);

        
        struct timespec ts;
        ts.tv_sec = patient.triage_time / 1000;
        ts.tv_nsec = (patient.triage_time % 1000) * 1000000;
        nanosleep(&ts, NULL);

        
        clock_gettime(CLOCK_REALTIME, &patient.end_triage);

       
        lock_stats(shm);
        shm->stats.total_triaged += 1;
        shm->stats.sum_wait_triage += wait_ms; 
        unlock_stats(shm);

       
        if (patient.priority < 1 || patient.priority > 3) patient.priority = 2; // Default Amarelo
        
        send_patient_to_doctor(msq_id, patient);

        log_write("[Triagem] Paciente ID %d enviado para MSQ (Prio: %d).", patient.id, patient.priority);
    }
    return NULL;
}