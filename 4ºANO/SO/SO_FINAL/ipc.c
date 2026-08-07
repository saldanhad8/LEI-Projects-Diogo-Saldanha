
/*
 * Projeto SO 2025/2026
 * Grupo de Trabalho:
 *
 *   Diogo de Oliveira Mendes Dias Saldanha  —  Nº 2022232761
 *   João Maria Moreira Dias                —  Nº 2022225061
 *
 */

#include <stdio.h>
#include <stdlib.h>
#include <sys/ipc.h>
#include <sys/shm.h>
#include <sys/sem.h>
#include <sys/msg.h>
#include <string.h>
#include <errno.h>
#include "ipc.h"

static int shm_id = -1;

void lock_stats(shared_data_t *shm) {
    if (shm != NULL) sem_wait(&(shm->stats_mutex));
}

void unlock_stats(shared_data_t *shm) {
    if (shm != NULL) sem_post(&(shm->stats_mutex));
}

int create_shared_memory(shared_data_t **shm) {
    shm_id = shmget(SHM_KEY, sizeof(shared_data_t), IPC_CREAT | 0666);
    if (shm_id == -1) return -1;
    *shm = (shared_data_t *)shmat(shm_id, NULL, 0);
    
    // INICIALIZAR O SEMÁFORO POSIX AQUI (pshared = 1 para processos)
    if (sem_init(&((*shm)->stats_mutex), 1, 1) == -1) {
        perror("Error init sem_stats");
        return -1;
    }
    return 0;
}

void destroy_shared_memory(shared_data_t *shm) {
    if (shm != (void *)-1) {
        sem_destroy(&(shm->stats_mutex)); // Destruir semáforo
        shmdt(shm);
    }
    if (shm_id >= 0) shmctl(shm_id, IPC_RMID, NULL);
}

int create_message_queue() {
    int id = msgget(MSQ_KEY, IPC_CREAT | 0666);
    if (id == -1) { perror("Failed to create MSQ"); return -1; }
    return id;
}

void send_patient_to_doctor(int msq_id, patient_t p) {
    msgbuf_t msg;
    msg.mtype = (long)p.priority;
    msg.data = p;
    if (msgsnd(msq_id, &msg, sizeof(patient_t), 0) == -1) perror("Erro msgsnd");
}

int receive_patient_from_queue(int msq_id, patient_t *p, long type) {
    msgbuf_t msg;
    // REMOVER IPC_NOWAIT para que o processo bloqueie e não gaste CPU
    if (msgrcv(msq_id, &msg, sizeof(patient_t), type, 0) == -1) {
        return -1;
    }
    *p = msg.data;
    return 0;
}

void destroy_message_queue(int msq_id) {
    if (msq_id != -1) msgctl(msq_id, IPC_RMID, NULL);
}

// --- NOVA FUNÇÃO ---
int get_msq_count(int msq_id) {
    struct msqid_ds buf;
    if (msgctl(msq_id, IPC_STAT, &buf) == -1) {
        perror("Erro ao ler stats MSQ");
        return 0;
    }
    return (int)buf.msg_qnum;
}