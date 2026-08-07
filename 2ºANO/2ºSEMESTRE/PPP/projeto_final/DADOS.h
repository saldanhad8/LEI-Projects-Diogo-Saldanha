#ifndef DADOS_H
#define DADOS_H

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <signal.h>


typedef struct Registo {
    int idDoente;
    int dia, mes, ano;
    int tensaoMaxima;
    int tensaoMinima;
    int peso;
    int altura;
    struct Registo *proximo;
} Registo;

typedef struct listaRegistos {
    Registo *head;
} listaRegistos;

typedef struct Doente {
    int id;
    char nome[100];
    int dia, mes, ano;
    char cartaoCidadao[20];
    char telefone[20];
    char email[100];
    listaRegistos listaRegistos;
    struct Doente *proximo; 
} Doente;

typedef struct AuxDoente {
    int id;
    char nome[100];
    int tensaoMaxima;
    struct AuxDoente *proximo;
} AuxDoente;

extern Doente *head; 
extern int numDoentes; 


Doente* adicionarDoenteOrdenado(Doente *head, int *numDoentes);
void listarDoentes(Doente *head);
Doente* removerDoente(Doente *head, int id);
Doente* lerDoentesDeArquivo(Doente *head, int *numDoentes);
void escreverDoentesNoArquivo(Doente *head);
void adicionarRegisto(Doente *head, int idDoente);
void lerRegistosDeArquivo(Doente *head);
void escreverRegistosNoArquivo(Doente *head);
void listarRegistosDoDoente(Doente *head, int idDoente);
void listarDoentesComTensaoSuperior(Doente *head, int tensao);

int validarData(int dia, int mes, int ano);
int validarTelefone(const char *telefone);
int validarEmail(const char *email);
int validarCartaoCidadao(const char *cartaoCidadao);
int validarNome(const char *nome);


void mostrarMenu();
void finalizarPrograma(int sig);

#endif 
