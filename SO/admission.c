/*
 * Projeto SO 2025/2026
 * Grupo de Trabalho:
 *
 *   Diogo de Oliveira Mendes Dias Saldanha  —  Nº 2022232761
 *   João Maria Moreira Dias                —  Nº 2022225061
 *
 */

#define _POSIX_C_SOURCE 200809L 
#define _XOPEN_SOURCE 700       

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <time.h>
#include <pthread.h>
#include <stdatomic.h>
#include <signal.h>
#include <errno.h>
#include <sys/select.h>

#include "config.h"
#include "triage_queue.h"
#include "ipc.h"
#include "stats.h"
#include "triage.h"
#include "logger.h"

atomic_int stop = 0;
triage_queue_t triage_queue;
pthread_t *triage_threads_arr;
shared_data_t *shm;
int msq_id = -1;
pid_t *doctor_pids = NULL;


void doctor_process_main(shared_data_t *sh, const config_t *config, int is_temp);
void print_system_statistics(shared_data_t *shm);

void handle_sigint(int sig) {
    (void)sig;
    log_write("[Admission] SIGINT recebido. A iniciar paragem...");
    stop = 1;
}

void handle_stats(int sig) {
    (void)sig;
    print_system_statistics(shm); 
}

pid_t create_single_doctor(shared_data_t *sh, const config_t *config, int is_temp){
    pid_t pid = fork();
    if (pid == 0) {
        doctor_process_main(sh, config, is_temp);
        exit(0);
    }
    return pid;
}

int main(){
    if (logger_init() != 0) {
        fprintf(stderr, "Erro fatal logger.\n");
        return 1;
    }
    log_write("[Admission] Sistema de Urgências a iniciar...");

    signal(SIGINT, handle_sigint);
    signal(SIGUSR1, handle_stats);

    config_t config;
    if(load_config("config.txt", &config) != 0) {
        logger_close();
        return 1;
    }

    create_shared_memory(&shm);
    msq_id = create_message_queue();

    unlink("input_pipe");
    if (mkfifo("input_pipe", 0666) == -1) {
        perror("mkfifo");
        logger_close();
        return 1;
    }

    triage_queue_init(&triage_queue, config.triage_queue_size);
    triage_threads_arr = malloc(sizeof(pthread_t) * config.triage_threads);
    for (int i = 0; i < config.triage_threads; i++) {
        pthread_create(&triage_threads_arr[i], NULL, triage_thread_func, &config);
    }

    // Criar médicos iniciais (is_temp = 0)
    doctor_pids = malloc(sizeof(pid_t) * config.doctors);
    for (int i = 0; i < config.doctors; i++) {
        doctor_pids[i] = create_single_doctor(shm, &config, 0);
    }

    log_write("[Admission] Sistema pronto. Use 'echo \"Nome 1000 1000 1\" > input_pipe'.");

    int fd_pipe = open("input_pipe", O_RDWR); 
    if(fd_pipe == -1) { perror("open pipe"); return 1; }

    char buffer[512];
    int patient_counter = 1;
    int auto_patient_group_id = 1;

    // --- LOOP PRINCIPAL ---
    while (!stop) {
        int status;
        pid_t p = waitpid(-1, &status, WNOHANG);
        if (p > 0) {
            for(int i=0; i<config.doctors; i++){
                if(doctor_pids[i] == p) {
                    doctor_pids[i] = create_single_doctor(shm, &config, 0);
                    log_write("[Admission] Doctor permanente %d substituído por %d", p, doctor_pids[i]);
                    break;
                }
            }
        }

        static time_t last_boost_time = 0;
        int current_queue = get_msq_count(msq_id);
        // CORREÇÃO: Verifica se passou pelo menos 1 segundo desde o último reforço
        if (current_queue > config.msq_wait_max && (time(NULL) - last_boost_time) >= 1) {
            log_write("[Admission] ALERTA: Fila com %d pacientes. Criando reforço!", current_queue);
            create_single_doctor(shm, &config, 1);
            last_boost_time = time(NULL);
        }

        fd_set read_fds;
        struct timeval tv;
        FD_ZERO(&read_fds);
        FD_SET(fd_pipe, &read_fds);
        tv.tv_sec = 0;
        tv.tv_usec = 100000; 

        int retval = select(fd_pipe + 1, &read_fds, NULL, NULL, &tv);

        if (retval > 0 && FD_ISSET(fd_pipe, &read_fds)) {
            ssize_t n = read(fd_pipe, buffer, sizeof(buffer)-1);
            if (n > 0) {
                buffer[n] = '\0';
                if (buffer[n-1] == '\n') buffer[n-1] = '\0';

                if (strncmp(buffer, "TRIAGE=", 7) == 0) {
                    int new_threads = atoi(buffer + 7);
                    if (new_threads > config.triage_threads) {
                        int diff = new_threads - config.triage_threads;
                        log_write("[Admission] A aumentar threads de %d para %d", config.triage_threads, new_threads);
                        triage_threads_arr = realloc(triage_threads_arr, sizeof(pthread_t) * new_threads);
                        for (int i = 0; i < diff; i++) {
                            pthread_create(&triage_threads_arr[config.triage_threads + i], NULL, triage_thread_func, &config);
                        }
                        config.triage_threads = new_threads;
                    }
                    continue;
                }

                char token1[100];
                int t_tri, t_atend, prio;
                if (sscanf(buffer, "%s %d %d %d", token1, &t_tri, &t_atend, &prio) == 4) {
                    char *endptr;
                    long num_patients = strtol(token1, &endptr, 10);
                    
                    if (*endptr == '\0') { 
                        // Grupo
                        if (num_patients <= 0) {
                            log_write("[Admission] Pedido de grupo invalido (%ld). Ignorado.", num_patients);
                            continue;
                        }

                        if (!triage_queue_has_space(&triage_queue, (int)num_patients)) {
                            log_write("[Admission] Fila de triagem cheia. Pedido de grupo (%ld) descartado.", num_patients);
                            continue;
                        }

                        log_write("[Admission] A criar grupo de %ld pacientes...", num_patients);
                        for (int i = 0; i < num_patients; i++) {
                            patient_t new_p;
                            new_p.id = patient_counter++;
                            snprintf(new_p.name, 99, "Gen-%d-%d", auto_patient_group_id, i+1);
                            new_p.triage_time = t_tri;
                            new_p.attend_time = t_atend;
                            new_p.priority = prio;
                            clock_gettime(CLOCK_REALTIME, &new_p.arrival_time);
                            if (triage_queue_push(&triage_queue, &new_p) != 0) {
                                log_write("[Admission] Fila de triagem cheia. Paciente %s (ID %d) descartado.", new_p.name, new_p.id);
                            }
                        }
                        auto_patient_group_id++;
                    } else {
                        // Individual
                        patient_t new_p;
                        new_p.id = patient_counter++;
                        strncpy(new_p.name, token1, 99);
                        new_p.triage_time = t_tri;
                        new_p.attend_time = t_atend;
                        new_p.priority = prio;
                        clock_gettime(CLOCK_REALTIME, &new_p.arrival_time);
                        if (triage_queue_push(&triage_queue, &new_p) != 0) {
                            log_write("[Admission] Fila de triagem cheia. Paciente %s (ID %d) descartado.", new_p.name, new_p.id);
                        } else {
                            log_write("[Admission] Recebido: %s", new_p.name);
                        }
                    }
                }
            }
        }
    }

    // Limpeza
    close(fd_pipe);
    unlink("input_pipe");

    log_write("[Admission] A terminar processos filhos...");
    for (int i = 0; i < config.doctors; i++) kill(doctor_pids[i], SIGTERM);
    while(wait(NULL) > 0);

    pthread_mutex_lock(&triage_queue.mutex);
    stop = 1; 
    pthread_cond_broadcast(&triage_queue.not_empty);
    pthread_mutex_unlock(&triage_queue.mutex);

    for (int i = 0; i < config.triage_threads; i++) pthread_join(triage_threads_arr[i], NULL);

    triage_queue_destroy(&triage_queue);
    destroy_message_queue(msq_id);
    destroy_shared_memory(shm);
    free(doctor_pids);
    free(triage_threads_arr);

    log_write("[Admission] Terminação completa.");
    logger_close();
    return 0;
}