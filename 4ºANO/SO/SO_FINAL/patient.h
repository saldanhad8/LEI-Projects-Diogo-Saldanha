/*
 * Projeto SO 2025/2026
 * Grupo de Trabalho:
 *
 * Diogo de Oliveira Mendes Dias Saldanha  —  Nº 2022232761
 * João Maria Moreira Dias                —  Nº 2022225061
 *
 */
#ifndef PATIENT_H
#define PATIENT_H

#include <time.h> 


typedef struct {
    int id;
    char name[100];
    int triage_time;      
    int attend_time;      
    int priority;         
    
   
    struct timespec arrival_time; 
    struct timespec start_triage;  
    struct timespec end_triage;   
    struct timespec start_attend;  
    struct timespec end_attend;   
} patient_t;

#endif // PATIENT_H