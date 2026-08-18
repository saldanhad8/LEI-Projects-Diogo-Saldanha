import gymnasium as gym
import numpy as np
import pygame

ENABLE_WIND = False  #set to True for the wind challenge
WIND_POWER = 15.0
TURBULENCE_POWER = 0.0
GRAVITY = -10.0
RENDER_MODE = None  #set to None for faster batch testing
#RENDER_MODE = None #seleccione esta opção para não visualizar o ambiente (testes mais rápidos)
EPISODES = 1000

env = gym.make("LunarLander-v3", render_mode =RENDER_MODE, 
    continuous=True, gravity=GRAVITY, 
    enable_wind=ENABLE_WIND, wind_power=WIND_POWER, 
    turbulence_power=TURBULENCE_POWER)

def check_successful_landing(observation):
    #check if the landing was successful according to the requirement s
    x = observation[0]
    vy = observation[3]
    theta = observation[4]
    contact_left = observation[6]
    contact_right = observation[7]

    legs_touching = contact_left == 1 and contact_right == 1

    on_landing_pad = abs(x) <= 0.2

    stable_velocity = vy > -0.2
    stable_orientation = abs(theta) < np.deg2rad(20)
    stable = stable_velocity and stable_orientation
 
    if legs_touching and on_landing_pad and stable:
        print("Aterragem bem sucedida!")
        return True

    print("Aterragem falhada!")        
    return False
        
def simulate(steps=1000,seed=None, policy = None):    
    observ, _ = env.reset(seed=seed)
    for step in range(steps):
        action = policy(observ)

        observ, _, term, trunc, _ = env.step(action)

        if term or trunc:
            break

    success = check_successful_landing(observ)
    return step, success

#Perceptions
# Helper functions that extract meaningful information from observations
# A observação traz os valores da Tabela 1 do enunciado.
# Vamos criar funções lógicas (booleanas) para avaliar o estado da nave.

def is_landing_finished(observation):
    # P1: Ambas as pernas tocam no solo
    return observation[6] == 1 and observation[7] == 1

def is_falling_too_fast(observation):
    # P2: Velocidade vertical abaixo do limite de segurança
    # Usamos o índice 3 (vy) e o índice 1 (y) para uma travagem progressiva
    y, vy = observation[1], observation[3]
    if y < 0.1: return vy < -0.1  # Muito perto do chão, exige-se vy > -0.2
    return vy < -0.3

def is_tilted_left(observation):
    # P3: Nave inclinada para a esquerda (theta positivo)
    return observation[4] > 0.1

def is_tilted_right(observation):
    # P4: Nave inclinada para a direita (theta negativo)
    return observation[4] < -0.1

def is_off_center_left(observation):
    # P5: À esquerda do alvo (x negativo)
    return observation[0] < -0.1

def is_off_center_right(observation):
    # P6: À direita do alvo (x positivo)
    return observation[0] > 0.1

#Actions
# As ações são um array com [motor_principal, motores_secundarios]
# O motor principal vai de 0 a 1. Os secundários vão de -1 a 1.

def action_idle():
    # A1: Desligar motores
    return np.array([0.0, 0.0])

def action_thrust_main(power=1.0):
    # A2: Ativar motor principal contra a gravidade
    return np.array([power, 0.0])

def action_correct_rotation_right():
    # A3: Ativar motor esquerdo para rodar para a direita
    return np.array([0.1, 1.0])

def action_correct_rotation_left():
    # A4: Ativar motor direito para rodar para a esquerda
    return np.array([0.1, -1.0])

# REACTIVE AGENT
def reactive_agent(observation):
    # REGRA 1: Se aterrou, desliga tudo
    if is_landing_finished(observation):
        return action_idle()

    # REGRA 2: Prioridade total à estabilidade angular (P3 e P4)
    # Se a nave não estiver vertical, não consegue aterrar em segurança
    if is_tilted_left(observation):
        return action_correct_rotation_right()
    if is_tilted_right(observation):
        return action_correct_rotation_left()

    # REGRA 3: Controlo de velocidade vertical (P2)
    # Evita que a nave se despenhe devido à gravidade
    if is_falling_too_fast(observation):
        return action_thrust_main(power=0.8)

    # REGRA 4: Correção de posição horizontal (P5 e P6)
    # Garante que aterragem é entre as bandeiras
    if is_off_center_left(observation):
        return action_correct_rotation_right()
    if is_off_center_right(observation):
        return action_correct_rotation_left()

    # REGRA 5: Comportamento por defeito (A1)
    return action_idle()
    
#KEYBOARD AGENT (for testing)
def keyboard_agent(observation):
    action = [0,0] 
    keys = pygame.key.get_pressed()
    
    print('observação:',observation)

    if keys[pygame.K_UP]:  
        action =+ np.array([1,0]) #main engine
    if keys[pygame.K_LEFT]:  
        action =+ np.array( [0,-1]) #rotate right
    if keys[pygame.K_RIGHT]: 
        action =+ np.array([0,1]) #rotate left

    return action
    
#EVALUATION
success = 0.0
steps = 0.0
for i in range(EPISODES):
    st, su = simulate(steps=1000000, policy=reactive_agent)
    
    if su:
        steps += st
    success += su
    
    if su>0:
        print('Média de passos das aterragens bem sucedidas:', steps/success*100)
    print('Taxa de sucesso:', success/(i+1)*100)
    
