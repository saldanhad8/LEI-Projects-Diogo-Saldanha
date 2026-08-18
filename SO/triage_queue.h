/*
 * Projeto SO 2025/2026
 * Grupo de Trabalho:
 *
 *   Diogo de Oliveira Mendes Dias Saldanha  —  Nº 2022232761
 *   João Maria Moreira Dias                —  Nº 2022225061
 *
 */
#ifndef TRIAGE_QUEUE_H
#define TRIAGE_QUEUE_H
#include "patient.h"
#include <pthread.h>

typedef struct {
    patient_t *buffer;
    int capacity;
    int count;
    int front;
    int rear;
    pthread_mutex_t mutex;
    pthread_cond_t not_empty;
    pthread_cond_t not_full;
} triage_queue_t;

void triage_queue_init(triage_queue_t *queue, int capacity);
void triage_queue_destroy(triage_queue_t *queue);
int triage_queue_has_space(triage_queue_t *queue, int n);

int triage_queue_push(triage_queue_t *queue, const patient_t *patient);
patient_t triage_queue_pop(triage_queue_t *queue);

#endif // TRIAGE_QUEUE_H