#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <signal.h>
#include " DADOS.h"

// Variáveis globais
Doente *head = NULL; // Cabeça da lista ligada global
int numDoentes = 0; // Número de doentes

// Funções de validação
int validarData(int dia, int mes, int ano) {
    if (dia < 1 || dia > 31 || mes < 1 || mes > 12 || ano < 1900 || ano > 2100)
        return 0;
    if (mes == 2) {
        // Verificar ano bissexto
        int bissexto = (ano % 4 == 0 && (ano % 100 != 0 || ano % 400 == 0));
        if (dia > 29 || (dia == 29 && !bissexto))
            return 0;
    } else if (mes == 4 || mes == 6 || mes == 9 || mes == 11) {
        if (dia > 30)
            return 0;
    }
    return 1;
}

int validarTelefone(const char *telefone) {
    if (strlen(telefone) != 9) {
        return 0;
    }
    for (int i = 0; i < 9; i++) {
        if (!isdigit(telefone[i])) {
            return 0;
        }
    }
    return 1;
}

int validarEmail(const char *email) {
    const char *arroba = strchr(email, '@');
    if (arroba == NULL) {
        return 0;
    }
    const char *ponto = strrchr(arroba, '.');
    if (ponto == NULL || ponto == arroba + 1 || ponto[1] == '\0') {
        return 0;
    }
    return 1;
}

int validarCartaoCidadao(const char *cartaoCidadao) {
    if (strlen(cartaoCidadao) != 14) {
        return 0;
    }
    for (int i = 0; i < 8; i++) {
        if (!isdigit(cartaoCidadao[i])) {
            return 0;
        }
    }
    if (cartaoCidadao[8] != '-') {
        return 0;
    }
    if (!isdigit(cartaoCidadao[9])) {
        return 0;
    }
    if (cartaoCidadao[10] != '-') {
        return 0;
    }
    for (int i = 11; i < 14; i++) {
        if (!isalnum(cartaoCidadao[i])) {
            return 0;
        }
    }
    return 1;
}

int validarNome(const char *nome) {
    for (int i = 0; nome[i] != '\0'; i++) {
        if (!isalpha(nome[i]) && nome[i] != ' ') {
            return 0;
        }
    }
    return 1;
}

// Funções de gerenciamento de doentes
Doente* adicionarDoenteOrdenado(Doente *head, int *numDoentes) {
    Doente *novoDoente = (Doente *)malloc(sizeof(Doente));
    if (!novoDoente) {
        printf("Erro ao alocar memória.\n");
        return head;
    }
    
    novoDoente->id = *numDoentes + 1; // ID atribuído automaticamente
    printf("ID do doente: %d\n", novoDoente->id);
    
    // Verificação do nome
    do {
        printf("Introduza o nome do doente: ");
        fgets(novoDoente->nome, 100, stdin);
        novoDoente->nome[strcspn(novoDoente->nome, "\n")] = '\0'; // Remover o '\n' do fim
        if (!validarNome(novoDoente->nome)) {
            printf("Nome inválido. Não deve conter dígitos ou caracteres especiais.\n");
        } else {
            break;
        }
    } while (1);

    // Verificação da data
    int dia, mes, ano;
    do {
        printf("Introduza a data de nascimento (dd/mm/aaaa): ");
        int result = scanf("%d/%d/%d", &dia, &mes, &ano);
        while (getchar() != '\n'); // Limpar o buffer
        if (result != 3 || !validarData(dia, mes, ano)) {
            printf("Data inválida. Por favor, introduza novamente no formato correto (dd/mm/aaaa).\n");
        } else {
            novoDoente->dia = dia;
            novoDoente->mes = mes;
            novoDoente->ano = ano;
            break;
        }
    } while (1);

    // Verificação do Cartão de Cidadão
    do {
        printf("Introduza o cartao de cidadao (########-#-###): ");
        fgets(novoDoente->cartaoCidadao, 20, stdin);
        novoDoente->cartaoCidadao[strcspn(novoDoente->cartaoCidadao, "\n")] = '\0'; // Remover o '\n' do fim
        if (!validarCartaoCidadao(novoDoente->cartaoCidadao)) {
            printf("Cartão de Cidadão inválido. Deve estar no formato ########-#-###.\n");
        } else {
            break;
        }
    } while (1);

    // Verificação do telefone
    do {
        printf("Introduza o telefone (9 dígitos): ");
        fgets(novoDoente->telefone, 20, stdin);
        novoDoente->telefone[strcspn(novoDoente->telefone, "\n")] = '\0'; // Remover o '\n' do fim
        if (!validarTelefone(novoDoente->telefone)) {
            printf("Número de telefone inválido. Deve conter exatamente 9 dígitos.\n");
        } else {
            break;
        }
    } while (1);

    // Verificação do e-mail
    do {
        printf("Introduza o email: ");
        fgets(novoDoente->email, 100, stdin);
        novoDoente->email[strcspn(novoDoente->email, "\n")] = '\0'; // Remover o '\n' do fim
        if (!validarEmail(novoDoente->email)) {
            printf("Email inválido. Deve conter '@' e um domínio.\n");
        } else {
            break;
        }
    } while (1);
    
    novoDoente->listaRegistos.head = NULL; // Inicializar a lista de registros
    
    // Inserir o novo doente na lista em ordem alfabética
    if (head == NULL || strcmp(novoDoente->nome, head->nome) < 0) {
        novoDoente->proximo = head;
        head = novoDoente;
    } else {
        Doente *atual = head;
        while (atual->proximo != NULL && strcmp(novoDoente->nome, atual->proximo->nome) > 0) {
            atual = atual->proximo;
        }
        novoDoente->proximo = atual->proximo;
        atual->proximo = novoDoente;
    }
    
    (*numDoentes)++;
    
    printf("Doente adicionado com sucesso!\n");
    
    return head;
}

void listarDoentes(Doente *head) {
    if (head == NULL) {
        printf("Nenhum doente registrado.\n");
        return;
    }
    
    Doente *atual = head;
    while (atual != NULL) {
        printf("ID: %d\n", atual->id);
        printf("Nome: %s\n", atual->nome);
        printf("Data de Nascimento: %02d/%02d/%04d\n", atual->dia, atual->mes, atual->ano);
        printf("Cartão de Cidadão: %s\n", atual->cartaoCidadao);
        printf("Telefone: %s\n", atual->telefone);
        printf("Email: %s\n", atual->email);
        printf("\n");
        atual = atual->proximo;
    }
}

Doente* removerDoente(Doente *head, int id) {
    Doente *atual = head;
    Doente *anterior = NULL;

    while (atual != NULL && atual->id != id) {
        anterior = atual;
        atual = atual->proximo;
    }

    if (atual == NULL) {
        printf("Doente com ID %d não encontrado.\n",id);
        return head;
    }

    if (anterior == NULL) {
        Doente *novaHead = head->proximo;
        free(head);
        printf("Doente com ID %d removido com sucesso.\n", id);
        return novaHead;
    } else {
        anterior->proximo = atual->proximo;
        free(atual);
        printf("Doente com ID %d removido com sucesso.\n", id);
        return head;
    }
}

Doente* lerDoentesDeArquivo(Doente *head, int *numDoentes) {
    FILE *file = fopen("doentes.txt", "r");
    if (!file) {
        printf("Erro ao abrir o arquivo doentes.txt.\n");
        return head;
    }
    
    while (!feof(file)) {
        Doente *novoDoente = (Doente *)malloc(sizeof(Doente));
        if (!novoDoente) {
            printf("Erro ao alocar memória.\n");
            fclose(file);
            return head;
        }
        
        if (fscanf(file, "%d\n", &novoDoente->id) != 1) break;
        if (fgets(novoDoente->nome, 100, file) == NULL) break;
        novoDoente->nome[strcspn(novoDoente->nome, "\n")] = '\0';
        if (fscanf(file, "%d/%d/%d\n", &novoDoente->dia, &novoDoente->mes, &novoDoente->ano) != 3) break;
        if (fgets(novoDoente->cartaoCidadao, 20, file) == NULL) break;
        novoDoente->cartaoCidadao[strcspn(novoDoente->cartaoCidadao, "\n")] = '\0';
        if (fgets(novoDoente->telefone, 10, file) == NULL) break;
        novoDoente->telefone[strcspn(novoDoente->telefone, "\n")] = '\0';
        if (fgets(novoDoente->email, 100, file) == NULL) break;
        novoDoente->email[strcspn(novoDoente->email, "\n")] = '\0';
        
        novoDoente->listaRegistos.head = NULL;

        if (head == NULL || strcmp(novoDoente->nome, head->nome) < 0) {
            novoDoente->proximo = head;
            head = novoDoente;
        } else {
            Doente *atual = head;
            while (atual->proximo != NULL && strcmp(novoDoente->nome, atual->proximo->nome) > 0) {
                atual = atual->proximo;
            }
            novoDoente->proximo = atual->proximo;
            atual->proximo = novoDoente;
        }
        
        (*numDoentes)++;
    }
    
    fclose(file);
    return head;
}

void escreverDoentesNoArquivo(Doente *head) {
    FILE *file = fopen("doentes.txt", "w");
    if (!file) {
        printf("Erro ao abrir o arquivo doentes.txt para escrita.\n");
        return;
    }

    Doente *atual = head;
    while (atual != NULL) {
        fprintf(file, "%d\n", atual->id);
        fprintf(file, "%s\n", atual->nome);
        fprintf(file, "%02d/%02d/%04d\n", atual->dia, atual->mes, atual->ano);
        fprintf(file, "%s\n", atual->cartaoCidadao);
        fprintf(file, "%s\n", atual->telefone);
        fprintf(file, "%s\n", atual->email);
        atual = atual->proximo;
    }

    fclose(file);
}

void adicionarRegisto(Doente *head, int idDoente) {
    Doente *atual = head;

    while (atual != NULL && atual->id != idDoente) {
        atual = atual->proximo;
    }

    if (atual == NULL) {
        printf("Doente com ID %d não encontrado.\n", idDoente);
        return;
    }

    Registo *novoRegisto = (Registo *)malloc(sizeof(Registo));
    if (!novoRegisto) {
        printf("Erro ao alocar memória.\n");
        return;
    }

    novoRegisto->idDoente = idDoente;

    
    int dia, mes, ano;
    do {
        printf("Introduza a data do registo (dia/mes/ano): ");
        int result = scanf("%d/%d/%d", &dia, &mes, &ano);
        while (getchar() != '\n'); // Limpar o buffer
        if (result != 3 || !validarData(dia, mes, ano)) {
            printf("Data inválida. Por favor, introduza novamente no formato correto (dd/mm/aaaa).\n");
        } else {
            novoRegisto->dia = dia;
            novoRegisto->mes = mes;
            novoRegisto->ano = ano;
            break;
        }
    } while (1);
    
    printf("Introduza a tensão máxima: ");
    scanf("%d", &novoRegisto->tensaoMaxima);

    printf("Introduza a tensão mínima: ");
    scanf("%d", &novoRegisto->tensaoMinima);

    printf("Introduza o peso: ");
    scanf("%d", &novoRegisto->peso);

    printf("Introduza a altura: ");
    scanf("%d", &novoRegisto->altura);

    novoRegisto->proximo = atual->listaRegistos.head;
    atual->listaRegistos.head = novoRegisto;

    printf("Registro adicionado com sucesso!\n");
}

void lerRegistosDeArquivo(Doente *head) {
    FILE *file = fopen("registos.txt", "r");
    if (!file) {
        printf("Erro ao abrir o arquivo registos.txt.\n");
        return;
    }

    while (!feof(file)) {
        Registo *novoRegisto = (Registo *)malloc(sizeof(Registo));
        if (!novoRegisto) {
            printf("Erro ao alocar memória.\n");
            fclose(file);
            return;
        }

        if (fscanf(file, "%d\n", &novoRegisto->idDoente) != 1) break;
        if (fscanf(file, "%d/%d/%d\n", &novoRegisto->dia, &novoRegisto->mes, &novoRegisto->ano) != 3) break;
        if (fscanf(file, "%d\n", &novoRegisto->tensaoMaxima) != 1) break;
        if (fscanf(file, "%d\n", &novoRegisto->tensaoMinima) != 1) break;
        if (fscanf(file, "%d\n", &novoRegisto->peso) != 1) break;
        if (fscanf(file, "%d\n", &novoRegisto->altura) != 1) break;

        Doente *atual = head;
        while (atual != NULL && atual->id != novoRegisto->idDoente) {
            atual = atual->proximo;
        }

        if (atual != NULL) {
            novoRegisto->proximo = atual->listaRegistos.head;
            atual->listaRegistos.head = novoRegisto;
        } else {
            free(novoRegisto);
        }
    }

    fclose(file);
}

void escreverRegistosNoArquivo(Doente *head) {
    FILE *file = fopen("registos.txt", "w");
    if (!file) {
        printf("Erro ao abrir o arquivo registos.txt para escrita.\n");
        return;
    }

    Doente *atualDoente = head;
    while (atualDoente != NULL) {
        Registo *atualRegisto = atualDoente->listaRegistos.head;
        while (atualRegisto != NULL) {
            fprintf(file, "%d\n", atualRegisto->idDoente);
            fprintf(file, "%02d/%02d/%04d\n", atualRegisto->dia, atualRegisto->mes, atualRegisto->ano);
            fprintf(file, "%d\n", atualRegisto->tensaoMaxima);
            fprintf(file, "%d\n", atualRegisto->tensaoMinima);
            fprintf(file, "%d\n", atualRegisto->peso);
            fprintf(file, "%d\n", atualRegisto->altura);
            atualRegisto = atualRegisto->proximo;
        }
        atualDoente = atualDoente->proximo;
    }

    fclose(file);
}

void listarRegistosDoDoente(Doente *head, int idDoente) {
    Doente *atual = head;

    while (atual != NULL && atual->id != idDoente) {
        atual = atual->proximo;
    }

    if (atual == NULL) {
        printf("Doente com ID %d não encontrado.\n", idDoente);
        return;
    }

    printf("Registos do Doente ID: %d\n", idDoente);
    Registo *registoAtual = atual->listaRegistos.head;
    while (registoAtual != NULL) {
        printf("Data: %02d/%02d/%04d\n", registoAtual->dia, registoAtual->mes, registoAtual->ano);
        printf("Tensão Máxima: %d\n", registoAtual->tensaoMaxima);
        printf("Tensão Mínima: %d\n", registoAtual->tensaoMinima);
        printf("Peso: %d\n", registoAtual->peso);
        printf("Altura: %d\n", registoAtual->altura);
        printf("\n");
        registoAtual = registoAtual->proximo;
    }
}

void listarDoentesComTensaoSuperior(Doente *head, int tensao) {
    AuxDoente *auxHead = NULL, *auxAtual, *auxAnterior;

    Doente *atual = head;
    while (atual != NULL) {
        Registo *registoAtual = atual->listaRegistos.head;
        while (registoAtual != NULL) {
            if (registoAtual->tensaoMaxima > tensao) {
                AuxDoente *novoAux = (AuxDoente *)malloc(sizeof(AuxDoente));
                if (!novoAux) {
                    printf("Erro ao alocar memória.\n");
                    return;
                }
                novoAux->id = atual->id;
                strcpy(novoAux->nome, atual->nome);
                novoAux->tensaoMaxima = registoAtual->tensaoMaxima;
                novoAux->proximo = NULL;

                if (auxHead == NULL || novoAux->tensaoMaxima > auxHead->tensaoMaxima) {
                    novoAux->proximo = auxHead;
                    auxHead = novoAux;
                } else {
                    auxAnterior = NULL;
                    auxAtual = auxHead;
                    while (auxAtual != NULL && auxAtual->tensaoMaxima >= novoAux->tensaoMaxima) {
                        auxAnterior = auxAtual;
                        auxAtual = auxAtual->proximo;
                    }
                    novoAux->proximo = auxAtual;
                    if (auxAnterior != NULL) {
                        auxAnterior->proximo = novoAux;
                    }
                }
            }
            registoAtual = registoAtual->proximo;
        }
        atual = atual->proximo;
    }

    printf("Doentes com tensão superior a %d:\n", tensao);
    auxAtual = auxHead;
    while (auxAtual != NULL) {
        printf("ID: %d, Nome: %s, Tensão Máxima: %d\n", auxAtual->id, auxAtual->nome, auxAtual->tensaoMaxima);
        AuxDoente *temp = auxAtual;
        auxAtual = auxAtual->proximo;
        free(temp);
    }
}

// Funções de utilidade
void mostrarMenu() {
    printf("Menu:\n");
    printf("1. Adicionar doente\n");
    printf("2. Listar doentes\n");
    printf("3. Remover doente\n");
    printf("4. Adicionar registo\n");
    printf("5. Listar registos de um doente\n");
    printf("6. Listar doentes com tensão superior\n");
    printf("7. Sair\n");
}

void finalizarPrograma(int sig) {
    printf("\nFinalizando o programa...\n");
    escreverDoentesNoArquivo(head);
    escreverRegistosNoArquivo(head);

    Doente *atual = head;
    while (atual != NULL) {
        Doente *temp = atual;
        atual = atual->proximo;

        Registo *atualRegisto = temp->listaRegistos.head;
        while (atualRegisto != NULL) {
            Registo *tempRegisto = atualRegisto;
            atualRegisto = atualRegisto->proximo;
            free(tempRegisto);
        }

        free(temp);
    }
    exit(0);
}

int main() {
    signal(SIGINT, finalizarPrograma);

    head = lerDoentesDeArquivo(head, &numDoentes);
    lerRegistosDeArquivo(head);

    int opcao;
    do {
        mostrarMenu();
        printf("Escolha uma opcao: ");
        scanf("%d", &opcao);
        getchar();

        switch(opcao) {
            case 1:
                head = adicionarDoenteOrdenado(head, &numDoentes);
                break;
            case 2:
                listarDoentes(head);
                break;
            case 3: {
                int id;
                printf("Introduza o ID do doente a remover: ");
                scanf("%d", &id);
                getchar();
                head = removerDoente(head, id);
                break;
            }
            case 4: {
                int id;
                printf("Introduza o ID do doente para adicionar o registo: ");
                scanf("%d", &id);
                getchar();
                adicionarRegisto(head, id);
                break;
            }
            case 5: {
                int id;
                printf("Introduza o ID do doente para listar os registos: ");
                scanf("%d", &id);
                getchar();
                listarRegistosDoDoente(head, id);
                break;
            }
            case 6: {
                int tensao;
                printf("Introduza a tensão para listar os doentes: ");
                scanf("%d", &tensao);
                getchar();
                listarDoentesComTensaoSuperior(head, tensao);
                break;
            }
            case 7:
                finalizarPrograma(0);
                break;
            default:
                printf("Opcao invalida. Tente novamente.\n");
        }
    } while(opcao != 7);
    
    return 0;
}
