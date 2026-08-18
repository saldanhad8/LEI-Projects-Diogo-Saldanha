"""
Módulo para carregamento dos dados do dataset FORTH-TRACE
"""

import numpy as np
import csv
import os

def load_device_file(filepath):
    """
    Carrega um ficheiro CSV de um dispositivo
    
    Parameters:
    -----------
    filepath : str
        Caminho para o ficheiro CSV
        
    Returns:
    --------
    data : numpy array
        Array com os dados do dispositivo
    """
    data = []
    
    try:
        with open(filepath, 'r') as file:
            csv_reader = csv.reader(file)
            next(csv_reader)  # Skip header se existir
            
            for row in csv_reader:
                # Converter cada linha para float
                try:
                    numeric_row = [float(val) for val in row]
                    data.append(numeric_row)
                except ValueError:
                    # Skip linhas com problemas
                    continue
    except FileNotFoundError:
        print(f"Aviso: Ficheiro não encontrado: {filepath}")
        return np.array([])
    
    return np.array(data)

def load_participant_data(data_path, participant_id):
    """
    Carrega todos os dados de um participante (5 dispositivos)
    
    Parameters:
    -----------
    data_path : str
        Caminho para a pasta com os dados
    participant_id : int
        ID do participante (1-15)
        
    Returns:
    --------
    data : numpy array
        Array concatenado com todos os dados do participante
        Shape: (n_samples, 12)
    """
    all_data = []
    
    # CORREÇÃO: Usar participant_id - 1 para mapear ID (1..N) para pasta (part0..partN-1)
    # A pasta do participante '1' será 'part0', a pasta de '14' será 'part13'.
    participant_file_id = participant_id - 1
    
    participant_folder = os.path.join(data_path, f'part{participant_file_id}')
    
    # Carregar dados dos 5 dispositivos
    for device_id in range(1, 6):
        # CORREÇÃO: Usar participant_file_id no nome do ficheiro também
        filename = f'part{participant_file_id}dev{device_id}.csv'
        filepath = os.path.join(participant_folder, filename)
        
        device_data = load_device_file(filepath)
        
        if device_data.size > 0:
            all_data.append(device_data)
    
    if len(all_data) == 0:
        print(f"Erro: Nenhum dado encontrado para o participante {participant_id}")
        return np.array([])
    
    # Concatenar dados de todos os dispositivos
    combined_data = np.vstack(all_data)
    
    return combined_data

def get_all_participants_data(data_path, num_participants=15):
    """
    Carrega dados de todos os participantes
    
    Parameters:
    -----------
    data_path : str
        Caminho para a pasta com os dados
    num_participants : int
        Número de participantes a carregar (default: 15)
        
    Returns:
    --------
    data : numpy array
        Array com todos os dados de todos os participantes
    """
    all_data = []
    
    for participant_id in range(1, num_participants + 1):
        print(f"  Carregando participante {participant_id}/{num_participants}...", 
              end='\r')
        participant_data = load_participant_data(data_path, participant_id)
        
        if participant_data.size > 0:
            all_data.append(participant_data)
    
    print()  # Nova linha após o loading
    
    if len(all_data) == 0:
        print("Erro: Nenhum dado foi carregado!")
        return np.array([])
    
    combined = np.vstack(all_data)
    print(f"  Total de amostras carregadas: {combined.shape[0]}")
    
    return combined

def get_sensor_data(data, device_id=None):
    """
    Extrai dados de sensores específicos
    
    Parameters:
    -----------
    data : numpy array
        Array com os dados
    device_id : int, optional
        ID do dispositivo (1-5). Se None, retorna todos.
        
    Returns:
    --------
    dict com arrays numpy:
        'accelerometer': shape (n, 3)
        'gyroscope': shape (n, 3)
        'magnetometer': shape (n, 3)
        'timestamp': shape (n,)
        'activity': shape (n,)
    """
    if device_id is not None:
        mask = data[:, 0] == device_id
        filtered_data = data[mask]
    else:
        filtered_data = data
    
    return {
        'accelerometer': filtered_data[:, 1:4],
        'gyroscope': filtered_data[:, 4:7],
        'magnetometer': filtered_data[:, 7:10],
        'timestamp': filtered_data[:, 10],
        'activity': filtered_data[:, 11]
    }

def calculate_magnitudes(data, device_id=None):
    """
    Calcula módulos dos vetores de aceleração, giroscópio e magnetómetro
    
    Parameters:
    -----------
    data : numpy array
        Array com os dados
    device_id : int, optional
        ID do dispositivo (1-5)
        
    Returns:
    --------
    dict com arrays numpy:
        'acc_magnitude': módulo da aceleração
        'gyro_magnitude': módulo do giroscópio
        'mag_magnitude': módulo do magnetómetro
        'activity': labels das atividades
    """
    sensor_data = get_sensor_data(data, device_id)
    
    acc_mag = np.sqrt(np.sum(sensor_data['accelerometer']**2, axis=1))
    gyro_mag = np.sqrt(np.sum(sensor_data['gyroscope']**2, axis=1))
    mag_mag = np.sqrt(np.sum(sensor_data['magnetometer']**2, axis=1))
    
    return {
        'acc_magnitude': acc_mag,
        'gyro_magnitude': gyro_mag,
        'mag_magnitude': mag_mag,
        'activity': sensor_data['activity']
    }

# Mapeamento de nomes de atividades
ACTIVITY_NAMES = {
    1: "Stand",
    2: "Sit",
    3: "Sit and Talk",
    4: "Walk",
    5: "Walk and Talk",
    6: "Climb Stairs",
    7: "Climb Stairs and Talk",
    8: "Stand->Sit",
    9: "Sit->Stand",
    10: "Stand->Sit and Talk",
    11: "Sit->Stand and Talk",
    12: "Stand->Walk",
    13: "Walk->Stand",
    14: "Stand->Climb Stairs",
    15: "Climb Stairs->Walk",
    16: "Climb Stairs Talk->Walk Talk"
}

# Mapeamento de nomes de dispositivos
DEVICE_NAMES = {
    1: "Pulso Esquerdo",
    2: "Pulso Direito",
    3: "Peito",
    4: "Perna Superior Direita",
    5: "Perna Inferior Esquerda"
}