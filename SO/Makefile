# Makefile
CC = gcc
# Adicionado -D_XOPEN_SOURCE=700 para garantir suporte a sigaction/ftruncate completo
CFLAGS = -Wall -Wextra -g -pthread -D_POSIX_C_SOURCE=200809L -D_DEFAULT_SOURCE -D_XOPEN_SOURCE=700
LDFLAGS = -pthread -lrt

# Lista de ficheiros objeto (ADICIONADO logger.o)
OBJS = admission.o config.o ipc.o doctor.o triage.o stats.o triage_queue.o logger.o

# Alvo principal
urgencias: $(OBJS)
	$(CC) $(CFLAGS) -o urgencias $(OBJS) $(LDFLAGS)

# Regras para cada ficheiro objeto
admission.o: admission.c config.h triage_queue.h ipc.h stats.h triage.h logger.h
	$(CC) $(CFLAGS) -c admission.c

config.o: config.c config.h
	$(CC) $(CFLAGS) -c config.c

ipc.o: ipc.c ipc.h stats.h
	$(CC) $(CFLAGS) -c ipc.c

doctor.o: doctor.c config.h ipc.h stats.h logger.h
	$(CC) $(CFLAGS) -c doctor.c

triage.o: triage.c triage_queue.h ipc.h stats.h config.h logger.h
	$(CC) $(CFLAGS) -c triage.c

stats.o: stats.c stats.h ipc.h
	$(CC) $(CFLAGS) -c stats.c

triage_queue.o: triage_queue.c triage_queue.h
	$(CC) $(CFLAGS) -c triage_queue.c

# Nova regra para o logger
logger.o: logger.c logger.h
	$(CC) $(CFLAGS) -c logger.c

# Limpeza
clean:
	rm -f *.o urgencias input_pipe DEI_Emergency.log

run: urgencias
	./urgencias