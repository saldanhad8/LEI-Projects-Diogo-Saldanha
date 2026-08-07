/*
 * Projeto SO 2025/2026
 * Grupo de Trabalho:
 *
 *   Diogo de Oliveira Mendes Dias Saldanha  —  Nº 2022232761
 *   João Maria Moreira Dias                —  Nº 2022225061
 *
 */

#ifndef IPC_H
#define IPC_H

#include "stats.h"
#include "patient.h"

#define SHM_KEY 0x1234
#define MSQ_KEY 0x9012

typedef struct {
    long mtype;
    patient_t data;
} msgbuf_t;

int create_shared_memory(shared_data_t **shm);
void destroy_shared_memory(shared_data_t *shm);

void lock_stats(shared_data_t *shm);
void unlock_stats(shared_data_t *shm);

int create_message_queue();
void send_patient_to_doctor(int msq_id, patient_t p);
int receive_patient_from_queue(int msq_id, patient_t *p, long type);
void destroy_message_queue(int msq_id);


int get_msq_count(int msq_id);

#endif // IPC_H