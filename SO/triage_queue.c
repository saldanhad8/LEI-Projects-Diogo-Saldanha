/*
 * Projeto SO 2025/2026
 * Grupo de Trabalho:
 *
 *   Diogo de Oliveira Mendes Dias Saldanha  —  Nº 2022232761
 *   João Maria Moreira Dias                —  Nº 2022225061
 *
 */
#include <stdlib.h>
#include "triage_queue.h"
#include <string.h>
#include <stdio.h>
#include <stdatomic.h>      
extern atomic_int stop;   


void triage_queue_init(triage_queue_t *queue, int capacity) {
    queue->buffer = (patient_t *)malloc(sizeof(patient_t) * capacity);
    queue->capacity = capacity;
    queue->count = 0;
    queue->front = 0;
    queue->rear = 0;
    pthread_mutex_init(&queue->mutex, NULL);
    pthread_cond_init(&queue->not_empty, NULL);
    pthread_cond_init(&queue->not_full, NULL);
}

//Destrói a fila de triagem, libertando os recursos associados
void triage_queue_destroy(triage_queue_t *queue) {
    free(queue->buffer);
    pthread_mutex_destroy(&queue->mutex);
    pthread_cond_destroy(&queue->not_empty);
    pthread_cond_destroy(&queue->not_full);
}

//Adiciona um paciente à fila de triagem
int triage_queue_push(triage_queue_t *queue, const patient_t *patient) {
    pthread_mutex_lock(&queue->mutex);

    
    if (queue->count == queue->capacity) {
        pthread_mutex_unlock(&queue->mutex);
        return -1;
    }

    queue->buffer[queue->rear] = *patient;
    queue->rear = (queue->rear + 1) % queue->capacity;
    queue->count++;

    pthread_cond_signal(&queue->not_empty);
    pthread_mutex_unlock(&queue->mutex);
    return 0;
}


//Remove e retorna um paciente da fila de triagem
patient_t triage_queue_pop(triage_queue_t *queue){
    pthread_mutex_lock(&queue->mutex);

    while (queue->count == 0) {
       
        if (stop) {
            pthread_mutex_unlock(&queue->mutex);
            patient_t dummy;
            memset(&dummy, 0, sizeof(dummy));  
            return dummy;
        }
        pthread_cond_wait(&queue->not_empty, &queue->mutex);
    }

    patient_t patient = queue->buffer[queue->front];
    queue->front = (queue->front + 1) % queue->capacity;
    queue->count--;
    //nao é necessário
    pthread_cond_signal(&queue->not_full);
    pthread_mutex_unlock(&queue->mutex);
    return patient;
}

int triage_queue_has_space(triage_queue_t *queue, int n) {
    if (n <= 0) return 1;

    pthread_mutex_lock(&queue->mutex);
    int free_slots = queue->capacity - queue->count;
    pthread_mutex_unlock(&queue->mutex);

    return (free_slots >= n);
}

